"""Allure 결과 JSON 후처리 스크립트.

`pytest --alluredir=allure-results`로 쌓이는 결과 JSON에는 기본적으로
`package`(모듈 경로) 라벨만 있고, **어느 파일의 어느 함수인지 이름으로는 안 보인다.**
또 실패 메시지는 `AssertionError: ...`처럼 파이썬 예외로 그대로 시작해서,
코드를 모르는 사람이 리포트만 보고 "뭐가 왜 잘못됐는지" 바로 감을 잡기 어렵다.

이 스크립트는 pytest 실행이 끝난 뒤(= allure generate/open 하기 전) 결과 JSON을
직접 열어 다음 두 가지를 덧붙인다.

1. **`testClass`(파일명) · `testMethod`(함수명) 라벨 추가**
   `fullName`(예: `test_vehicle_register_reseller#test_TC046_...`)을
   `#` 기준으로 나눠서 만든다. 리포트 Suites 트리에서 파일·함수 단위로
   바로 구분해서 볼 수 있게 된다.

2. **실패 메시지 앞에 한글 요약 3줄 추가**
   원본 예외 메시지(영문)는 그대로 두고 그 앞에
   `[실패 요약]` / `[실패 유형]` / `[실패 위치]` 3줄만 붙인다.
   원본을 지우지 않는 이유: 한글 요약은 "대략 어떤 문제인지" 감만 잡게 해주는
   용도고, 정확한 원인 파악에는 여전히 원본 스택 트레이스가 필요하기 때문이다.

멱등성: 이미 처리된 JSON을 다시 돌려도 라벨이 중복되지 않고,
        메시지 앞에 요약이 두 번 붙지 않는다 (재실행 안전).

사용법
------
    pytest --alluredir=allure-results
    python tools/postprocess_allure_results.py        # allure-results 처리
    allure generate allure-results -o allure-report --single-file
"""

from __future__ import annotations

import glob
import json
import os
import sys

# 원본 예외 메시지 첫 줄에서 뽑아낸 예외 클래스명 → 한글 한 줄 설명.
# 여기 없는 예외는 "그 외" 문구로 대체한다 (모든 예외를 다 알 필요는 없음).
EXCEPTION_KO: dict[str, str] = {
    "AssertionError": "예상한 값과 실제 결과가 다릅니다.",
    "TimeoutError": "정해진 시간 안에 화면 요소가 나타나지 않았습니다.",
    "Error": "테스트 중 오류가 발생했습니다.",  # 매칭되는 게 없을 때 쓰는 기본값
}

_SUMMARY_MARK = "[실패 요약]"  # 이미 후처리된 메시지인지 판단하는 표식


def _describe_exception(message: str) -> tuple[str, str]:
    """메시지 첫 줄에서 예외 클래스명을 뽑아 (한글 설명, 예외명) 을 돌려준다.

    예: "AssertionError: [FAIL] ..." → ("예상한 값과 실제 결과가 다릅니다.", "AssertionError")
        "playwright._impl._errors.TimeoutError: ..." → (..., "TimeoutError")
    """
    first_line = message.splitlines()[0] if message else ""
    exc_name = first_line.split(":", 1)[0].strip().rsplit(".", 1)[-1] or "Error"
    return EXCEPTION_KO.get(exc_name, EXCEPTION_KO["Error"]), exc_name


def _prepend_korean_summary(status_details: dict, test_class: str, test_method: str) -> None:
    """statusDetails.message 맨 앞에 한글 요약 3줄을 붙인다 (원본은 그 뒤에 그대로 유지)."""
    message = status_details.get("message") or ""
    if message.startswith(_SUMMARY_MARK):
        return  # 이미 처리됨 — 중복 방지

    ko_desc, exc_name = _describe_exception(message)
    summary = (
        f"{_SUMMARY_MARK} {ko_desc}\n"
        f"[실패 유형] {exc_name}\n"
        f"[실패 위치] {test_class} > {test_method}\n"
        f"{'-' * 40}\n"
    )
    status_details["message"] = summary + message


def _add_class_method_labels(data: dict, test_class: str, test_method: str) -> None:
    labels = data.setdefault("labels", [])
    existing_names = {label.get("name") for label in labels}
    if "testClass" not in existing_names:
        labels.append({"name": "testClass", "value": test_class})
    if "testMethod" not in existing_names:
        labels.append({"name": "testMethod", "value": test_method})


def process_result_file(path: str) -> bool:
    """result.json 하나를 처리한다. 처리 대상이 아니면(fullName 없음 등) False."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    full_name = data.get("fullName", "")
    if "#" not in full_name:
        return False  # 예상한 형식이 아니면 손대지 않고 건너뜀

    module_name, func_name = full_name.rsplit("#", 1)
    test_class = f"{module_name}.py"

    _add_class_method_labels(data, test_class, func_name)

    if data.get("status") in ("failed", "broken") and data.get("statusDetails"):
        _prepend_korean_summary(data["statusDetails"], test_class, func_name)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    return True


def process(results_dir: str) -> int:
    pattern = os.path.join(results_dir, "*-result.json")
    paths = glob.glob(pattern)
    if not paths:
        print(f"[알림] {pattern} 에 해당하는 결과 파일이 없습니다. pytest를 먼저 실행하세요.")
        return 0

    processed = sum(process_result_file(p) for p in paths)
    print(f"[완료] {results_dir} - 결과 {len(paths)}건 중 {processed}건에 testClass/testMethod 라벨과 한글 요약을 추가했습니다.")
    return processed


if __name__ == "__main__":
    target_dir = sys.argv[1] if len(sys.argv) > 1 else "allure-results"
    process(target_dir)
