# Allure 적용 노트

이 프로젝트에 Allure Report를 붙이면서 **무엇을, 왜 적용했는지** 정리했습니다.
Allure 자체가 어떻게 동작하는지와 pytest API 전체 목록은 별도 문서(`Allure Report 가이드` 아티팩트)를 참고하세요.

## 설치 & 실행

**① pytest 플러그인** — 결과 데이터(`allure-results/`)를 쌓는 역할
```bash
pip install allure-pytest
```

**② `allure` 명령줄 도구** — 그 데이터를 HTML 리포트로 바꿔주는 별개 프로그램

| | Allure 3 (권장) | Allure 2 |
|---|---|---|
| 설치 | `npm install -g allure` | Scoop(`scoop install allure`) 또는 수동 다운로드 |
| 사전 요구 | Node.js | **Java 8+** (`JAVA_HOME` 설정 필요) |
| 리포트 열기 | `allure open` | `allure serve` |

Allure 3는 npm 패키지라 Java가 아예 필요 없어서 훨씬 간단합니다.

**③ 실행**
```bash
pytest --alluredir=allure-results     # 결과 쌓기
allure open allure-results            # 리포트 열기 (Allure 2는 allure serve)
```

> CLI가 없어도 `--alluredir`로 결과 파일을 쌓는 것까지는 됩니다. 나중에 CLI를 설치하면 그 데이터로 리포트를 열 수 있습니다.

`allure-results/`·`allure-report/`는 실행할 때마다 새로 생기는 산출물이라 `.gitignore`에 넣었습니다.

> **`--clean-alluredir`은 넣지 않았습니다**
>
> `pytest.ini`에 `addopts = --alluredir=... --clean-alluredir`로 고정해둘 수도 있는데, 이 옵션은 실행할 때마다 결과 폴더를 비웁니다. 통합 탭처럼 오래 걸리는 테스트를 따로 돌리고 나머지와 합쳐서 하나의 리포트로 보는 경우가 있어서, **누적이 되도록 일부러 안 넣었습니다.** 새로 시작하고 싶으면 폴더를 직접 지우면 됩니다.

## 적용한 것 — 5가지

### 1. `@allure.step` — 헬퍼 함수에 부착 (가장 효과 큼)

**왜**: 지금까지 테스트가 실패하면 스택 트레이스를 읽어야 "어느 단계에서 깨졌는지" 알 수 있었습니다. step을 붙이면 리포트에서 단계별로 초록/빨강이 표시돼서, 실패 지점이 한눈에 보입니다.

특히 이 프로젝트에서 효과가 큰 지점:
- **TC-086** — 표본 페이지(첫/중간/마지막)를 순회하는 구조라, "115페이지로 이동"까지는 통과하고 그 다음에서 실패한 게 바로 보입니다. 실제로 이 테스트에서 겪었던 "116페이지로 못 감" 문제가 딱 이런 식으로 드러납니다.
- **TC-053** — 리셀러 변경 → 저장 → 재진입 → 다시 변경 → 저장까지 단계가 길어서, 어느 저장에서 틀어졌는지 구분이 필요합니다.

```python
@allure.step("단말기>모니터 진입 후 {tab_name} 탭으로 이동")
def _goto_monitor(page: Page, tab_name: str = "통신") -> None: ...

@allure.step("{target_page}페이지로 이동")
def _go_to_page(page: Page, target_page: int) -> None: ...

@allure.step("차량 {car_number}의 [수정] 버튼을 눌러 모달 열기")
def _open_carmgmt_edit_modal(page: Page, car_number: str) -> None: ...

@allure.step("[수정] 저장 + 확인 팝업 [OK] 클릭")
def _save_edit_modal(page: Page) -> None: ...
```

> **겪은 문제 — 따옴표가 두 번 찍힘**
>
> 처음엔 `@allure.step("업체 '{company_name}' 선택")`처럼 따옴표를 직접 넣었는데, 리포트에 `업체 ''IMS모빌리티'' 선택`으로 나왔습니다. **Allure가 문자열 파라미터를 넣을 때 자체적으로 따옴표를 붙이기 때문**입니다. 수동 따옴표를 빼서 `업체 {company_name} 선택`으로 쓰면 리포트에는 `업체 'IMS모빌리티' 선택`으로 정상 출력됩니다.

### 2. 실패 증거 자동 첨부 (화면 + 주소 + 콘솔 로그) — **실패했을 때만**

**왜**: 이번 작업 내내 문제가 생길 때마다 별도 조사 스크립트를 짜서 `page.screenshot()`을 찍고 콘솔 에러를 확인했습니다. 그 과정을 테스트가 알아서 남기도록 바꿨습니다. dev 데이터가 실시간으로 바뀌는 이 환경에서는 특히 중요한데, **"실패한 그 순간 화면이 실제로 어땠는지"가 남아야 코드 문제인지 데이터가 바뀐 건지 나중에 판단**할 수 있기 때문입니다.

실제로 이번에 겪은 사례:
- TC-053의 `Cannot read properties of undefined (reading 'helpers')` 콘솔 에러 → 이제 자동으로 리포트에 남습니다
- 세션이 서버에서 무효화됐을 때 로그인 화면이 떠 있던 것 → 스크린샷으로 바로 확인 가능

```python
# conftest.py — 실패한 그 순간(call 단계)에 훅에서 바로 첨부한다
@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    rep = yield
    if rep.when == "call" and rep.failed:
        page = item.funcargs.get("logged_in_page")
        if page is not None:
            _attach_page_evidence(page, getattr(item, "_console_logs", []))
    return rep


@pytest.fixture
def logged_in_page(browser: Browser, auth_state: str, request) -> Generator[Page, None, None]:
    context = browser.new_context(storage_state=auth_state)
    page = context.new_page()

    console_logs: list[str] = []
    page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
    page.on("pageerror", lambda exc: console_logs.append(f"[pageerror] {exc}"))
    request.node._console_logs = console_logs   # 훅이 꺼내 쓸 수 있게 테스트 객체에 달아둠

    yield page

    context.close()
```

**처음엔 통과·실패 상관없이 매번 첨부했다가 실패 시에만 남기도록 바꿨습니다.** 18개 테스트만 돌려도 스크린샷 16장에 3.3MB였고, 46개 전체면 8MB가 넘습니다. 통과한 테스트의 스크린샷은 볼 일이 거의 없어서 리포트 무게만 늘립니다.

### 겪은 문제 — fixture teardown에서 붙이면 첨부가 "Tear down" 안쪽에 숨는다

처음엔 fixture teardown에서 `allure.attach`를 불렀습니다. 동작은 했는데, 리포트에서 **테스트의 Attachments 탭이 `0`으로 비어 있고** 첨부는 Overview 맨 아래 "Tear down → logged_in_page::1"을 펼쳐야 나왔습니다. Allure는 `attach`를 부른 시점의 컨텍스트에 첨부를 붙이는데, teardown에서 부르면 그게 **fixture의 컨테이너**가 되기 때문입니다.

사수님 팀의 공식 리포트를 열어보니 첨부가 Attachments 탭에 바로 붙어 있었고, 그 차이가 여기였습니다.

**해결**: fixture teardown 대신 **`pytest_runtest_makereport` 훅의 `call` 단계**에서 첨부합니다. 이 시점은 테스트 본문이 막 실패한 직후라 아직 테스트가 "열려 있고", fixture teardown 전이라 `page`도 살아있습니다.

| | 첨부 위치 |
|---|---|
| fixture teardown에서 attach | Tear down → `logged_in_page::1` 안쪽 (Attachments 탭은 0) |
| **훅의 call 단계에서 attach** | **테스트의 Attachments 탭** (실패 시점 화면·주소·콘솔 로그 3건) |

`item.funcargs`로 그 테스트가 실제로 쓴 `logged_in_page`를 꺼내오고, 콘솔 로그는 fixture가 `request.node._console_logs`에 달아둔 걸 씁니다.

`_attach_page_evidence`는 첨부 자체가 실패해도(이미 닫힌 페이지 등) **예외를 삼키고 넘어갑니다** — 여기서 에러가 나면 정작 원래 실패 원인이 가려지기 때문입니다.

> **한계**: `logged_in_page`를 쓰는 테스트에만 적용됩니다. `test_TC103_login_fail_no_permission`은 pytest-playwright 기본 `page` fixture를 쓰기 때문에 첨부가 안 됩니다(로그인 실패 화면을 검증하는 테스트라 지금은 그대로 뒀습니다).

### 3. `@allure.title` — TC 번호와 요약이 리포트에 그대로

**왜**: 기본값으로는 리포트에 `test_TC086_monitor_reseller_filter_query_result[chromium-integrated]`처럼 함수명이 그대로 나와서 읽기 어렵습니다. TC 번호 + 한 줄 요약을 그대로 제목으로 쓰면 TC 문서와 리포트를 대조하기 쉬워집니다.

```python
@allure.title("TC-086 | 리셀러 필터 조회 결과 확인 ({tab_name} 탭)")
@pytest.mark.parametrize("tab_name", MONITOR_TABS, ids=MONITOR_TAB_IDS)
def test_TC086_monitor_reseller_filter_query_result(logged_in_page: Page, tab_name: str) -> None: ...
```

**덤으로 해결된 것**: 한글 파라미터가 `\uXXXX`로 이스케이프되는 문제 때문에 `ids=`로 영문 ID를 따로 지정했었는데(터미널 출력용), 리포트 제목에서는 `{tab_name}`이 한글 그대로 들어가서 "통합 탭"으로 읽힙니다. **터미널은 영문 ID, 리포트는 한글 제목**으로 각각 알아보기 좋게 나뉩니다.

### 4. `pytestmark = allure.feature(...)` — 화면 단위 그룹핑

**왜**: 리포트에서 테스트를 화면별로 묶어서 볼 수 있습니다. 값은 각 파일 맨 위에 이미 적어둔 **GNB 경로 주석과 똑같이** 맞췄습니다 — 따로 새 분류 체계를 만들지 않고 기존 구조를 그대로 씁니다.

| 파일 | feature |
|---|---|
| `test_login.py` | 로그인 · 권한 · test_login.py |
| `test_monitor_reseller_filter.py` | 단말기 > 모니터 · test_monitor_reseller_filter.py |
| `test_vehicle_register_reseller.py` | 차량관리 > 차스펙관리 (등록) · test_vehicle_register_reseller.py |
| `test_vehicle_edit_reseller.py` | 차량관리 > 차량관리 (수정) · test_vehicle_edit_reseller.py |
| `test_vehicle_company_transfer.py` | 차량관리 > 차량관리 (업체 변경) · test_vehicle_company_transfer.py |

```python
# 파일 상단에 한 줄이면 그 파일의 모든 테스트에 적용됨
pytestmark = allure.feature("차량관리 > 차량관리 (수정)  ·  test_vehicle_edit_reseller.py")
```

> **화면 이름 뒤에 파일명을 붙인 이유**
>
> 처음엔 화면 이름만 넣었는데, 리포트만 보고는 그 TC가 어느 파일에 있는지 알 수 없어서 코드를 찾아가기 불편했습니다. `groupBy: ["feature", "suite"]`로 2단(화면 → 파일)을 만들어봤지만, **화면과 파일이 1:1이라 클릭만 한 단계 늘고 정보는 안 늘었습니다.** 그래서 한 줄에 둘 다 넣는 쪽으로 정리했습니다.

### 5. 결과 JSON 후처리 — `tools/postprocess_allure_results.py`

**왜**: 사수님 팀의 공식 Allure 3 리포트(4.0MB)를 열어보니 우리 리포트와 다른 점이 두 가지 있었습니다.

1. Labels에 `package`(모듈 경로)뿐 아니라 **`testClass`(파일명)·`testMethod`(함수명)**가 따로 붙어 있었습니다. 원래 `allure-pytest`는 함수 기반 테스트(우리처럼 `unittest` 클래스 없이 함수로만 짠 경우)에는 이 두 라벨을 만들지 않습니다 — 있어야 정상인 게 아니라, **사수님 쪽에서 직접 후처리해서 추가한 것**이었습니다.
2. 실패 메시지가 `AssertionError: ...`처럼 영문 예외로 바로 시작하지 않고, 앞에 한글 요약이 붙어 있었습니다. 에러 자체는(스택 트레이스) 코드를 아는 사람에게는 이해되지만, **코드를 모르고 리포트만 보는 사람**에게는 한글 한 줄이 먼저 있는 쪽이 훨씬 빠르게 읽힙니다.

`allure-pytest`가 만드는 결과 JSON 자체에는 이 둘을 넣을 옵션이 없어서(플러그인이 아니라 **생성된 JSON 파일을 직접 수정**하는 방식), 같은 방식으로 후처리 스크립트를 만들었습니다.

```python
# tools/postprocess_allure_results.py
def process_result_file(path: str) -> bool:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    full_name = data.get("fullName", "")          # "test_vehicle_edit_reseller#test_TC053_..."
    if "#" not in full_name:
        return False
    module_name, func_name = full_name.rsplit("#", 1)
    test_class = f"{module_name}.py"

    _add_class_method_labels(data, test_class, func_name)

    if data.get("status") in ("failed", "broken") and data.get("statusDetails"):
        _prepend_korean_summary(data["statusDetails"], test_class, func_name)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    return True
```

**`fullName`을 쓴 이유**: 리포트 제목은 `@allure.title`로 덮어써서 한글이라 함수명을 못 뽑아내고, `name`도 마찬가지입니다. `fullName`은 pytest가 만드는 값이라 `@allure.title`과 무관하게 항상 `모듈명#함수명` 그대로이고, parametrize를 써도 `[chromium-...]` 같은 대괄호가 안 붙습니다 — 실제로 TC-046(3개 파라미터)에서 확인한 결과입니다.

**한글 요약 3줄 형식**:
```
[실패 요약] 예상한 값과 실제 결과가 다릅니다.     ← 예외 클래스를 한글 사전(EXCEPTION_KO)으로 매핑
[실패 유형] AssertionError                        ← 원본 예외 클래스명 그대로
[실패 위치] test_vehicle_edit_reseller.py > test_TC053_...
----------------------------------------
AssertionError: ...                                ← 원본 메시지는 그대로 뒤에 남김
```
원본을 지우지 않고 앞에 붙이기만 한 이유: 한글 요약은 "대략 뭐가 문제인지" 감만 잡게 해주는 용도이고, 정확한 원인(어떤 값이 왜 다른지)은 여전히 원본 스택 트레이스를 읽어야 알 수 있기 때문입니다. `EXCEPTION_KO`에 없는 예외는 "테스트 중 오류가 발생했습니다"라는 기본 문구로 대체됩니다 — 모든 예외 종류를 미리 다 알 필요는 없습니다.

**멱등성**: 이미 처리된 JSON을 다시 돌려도 라벨이 중복되지 않고(`testClass`/`testMethod`가 이미 있으면 건너뜀) 요약도 두 번 안 붙습니다(`[실패 요약]`로 시작하면 건너뜀). pytest를 여러 번 나눠 돌리고 결과를 누적하는(위 `--clean-alluredir` 미적용 이유와 같은 맥락) 이 프로젝트 특성상, 스크립트를 여러 번 실행해도 안전해야 했습니다.

**실행 순서**:
```bash
pytest --alluredir=allure-results
python tools/postprocess_allure_results.py     # ← generate/open 하기 전에 실행
allure generate allure-results -o allure-report
```

## 리포트 생성 설정 — `allurerc.mjs`

프로젝트 루트에 이 파일을 두면 `allure generate`가 자동으로 읽습니다. 옵션을 매번 명령어에 붙일 필요가 없습니다.

```javascript
export default {
  name: "QA 자동화 테스트 리포트",
  plugins: {
    awesome: {
      options: {
        singleFile: true,          // 리포트를 index.html 하나로 묶어서 생성
        groupBy: ["feature"],      // 트리를 파일명(suite) 대신 화면(feature) 기준으로 묶음
        reportLanguage: "ko",
        theme: "auto",
      },
    },
  },
};
```

**`singleFile`은 CLI 옵션에 없습니다.** `allure generate --help`를 봐도 안 나와서 "Allure 3는 단일 HTML을 못 만든다"고 오판했었는데, 설치된 `@allurereport/plugin-awesome`의 타입 정의를 뒤져보니 옵션으로 존재했습니다. **설정 파일로만 켤 수 있습니다.**

| | 파일 수 | 크기 |
|---|---|---|
| 기본 | 90개 (JS 24 + JSON 57 + 폰트·CSS) | 2.7MB |
| `singleFile: true` | **1개 (`index.html`)** | 3.5MB |

파일 하나면 슬랙·메일로 그냥 보낼 수 있습니다(압축 불필요).

> **`import { defineConfig } from "allure"`를 쓰면 안 됩니다** — `allure`를 npm 전역(`-g`)으로 설치했다면 프로젝트에서 그 모듈을 못 찾아 모듈 해석 에러가 납니다. 위처럼 **순수 객체로 export**하면 문제없습니다.

## 함께 바꾼 것 — docstring에서 TC 요약 줄 제거

Allure는 함수의 docstring을 자동으로 description으로 씁니다. 이미 모든 테스트에 GIVEN/WHEN/THEN docstring이 있어서 그대로 리포트에 들어갔는데, **제목이 두 곳에 중복되는 문제**가 생겼습니다.

```python
@allure.title("TC-043 | 차량 등록 모달 파트너 항목(수정 불가) 노출 확인")   # ← 이것과
def test_TC043_...:
    """
    TC-043 | 차량 등록 시 파트너 항목 출력 확인                          # ← 이것이 중복
```

실제로 붙이자마자 **두 문구가 이미 미묘하게 달라진 상태**였습니다. 한쪽만 고치면 어긋난다는 게 바로 드러난 셈이라, **제목은 `@allure.title` 한 곳에만 두고 docstring 첫 줄의 TC 요약은 전부 제거**했습니다(19곳). docstring에는 GIVEN/WHEN/THEN과 그 아래 배경 설명만 남깁니다.

`CLAUDE.md`의 docstring 컨벤션도 이에 맞춰 갱신했습니다.

## 일부러 적용하지 않은 것

**`@allure.severity`** — TC 문서에 심각도 컬럼이 없습니다. 제가 임의로 "이건 critical, 저건 normal"로 정하면 `CLAUDE.md`의 *"TC/기획서에 명시되지 않은 정책이나 기대 결과를 임의로 추가하지 않는다"* 원칙에 어긋납니다. 팀에서 TC별 우선순위를 정하면 그때 근거를 갖고 붙이는 게 맞습니다.

**`@allure.testcase` / `@allure.issue`** — 지금 TC 문서가 엑셀 파일이라 연결할 URL이 없습니다. TestRail·Jira 같은 도구를 도입하면 그때 `--allure-link-pattern`과 함께 붙이면 됩니다.

**`@allure.epic` / `@allure.story`** — `feature` 하나로 화면 구분이 충분한 상태라, 계층을 더 쪼개면 오히려 리포트가 복잡해집니다. TC가 더 늘어나서 화면 안에서도 그룹이 필요해지면 그때 추가하는 게 낫습니다.

## 앞으로 활용할 수 있는 것

**히스토리 / 재시도 추적** — 같은 결과 디렉토리에 여러 번 쌓거나 CI에 붙이면, "이 테스트가 최근 10번 중 몇 번 실패했나"가 보입니다. 이 프로젝트는 dev 데이터가 실시간으로 바뀌어서 간헐적으로 실패하는 케이스(통합 탭 페이지네이션 등)가 있었는데, **진짜 회귀인지 환경 탓인지 구분**하는 데 이 기능이 직접적으로 도움이 됩니다.

---
관련 문서: `CLAUDE.md`(공통 설계 원칙) · `docs/notes/Playwright-pytest-함수-정리.md`(코드에 쓴 함수 정리)
