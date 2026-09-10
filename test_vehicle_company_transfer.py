# GNB 경로: 차량관리 > 차량관리 (수정 - 업체 변경)

from typing import Callable, Generator

import allure
import pytest
from playwright.sync_api import Page, expect

from test_vehicle_edit_reseller import (
    CAR_PARTNER_CONNECT,
    _find_list_col_index,
    _get_edit_field,
    _open_carmgmt_edit_modal,
    _read_settled,
)
from test_vehicle_register_reseller import COMPANY_PARTNERS

# Allure 리포트에서 이 파일의 테스트들이 묶이는 기능 단위 (파일 상단 GNB 경로와 동일)
pytestmark = allure.feature("차량관리 > 차량관리 (업체 변경)  ·  test_vehicle_company_transfer.py")

# 같은 모달(차량관리>차량관리 수정)을 다루므로 test_vehicle_edit_reseller.py의 헬퍼를 그대로 가져다 씀
# 업체→파트너 매핑도 test_vehicle_register_reseller.py의 COMPANY_PARTNERS를 그대로 재사용
# (같은 dev 환경 데이터라, 여기서 따로 문자열로 다시 적으면 나중에 한쪽만 바뀌었을 때 어긋날 수 있음)
# 자세한 설명은 docs/notes/code-notes/차량업체변경-테스트-노트.md 참고

# TC-059~066 전용 — 실제로 [수정] 저장까지 실행하는 이관 테스트라, TC-051~058이 쓰는 차량과
# 겹치면 위험해서(다른 TC의 전제 상태를 건드릴 수 있음) dev에 새로 등록해둔 전용 차량 4대.
# 각 차량은 "리셀러가 이 값이다"만 보장되면 되고, 원래 소속 업체가 어디든 코드가 현재 값을
# 읽어서 처리하므로 상관없다 (사용자 확인, 2026-09-04).
CAR_TRANSFER_CONNECT_FROM_IMS = "900용1001"   # IMS모빌리티(파트너 커넥트) 소속 · 리셀러 커넥트
CAR_TRANSFER_CONNECT_FROM_LG = "900용1002"    # LG업체입니다(파트너 LG U+) 소속 · 리셀러 커넥트
CAR_TRANSFER_LG_UPLUS = "900용1003"           # LG업체입니다(파트너 LG U+) 소속 · 리셀러 LG U+
CAR_TRANSFER_SMALLTICKET = "900용1004"        # 스몰티켓(지입)2(파트너 스몰티켓) 소속 · 리셀러 스몰티켓

# 이관 "목적지" 전용 업체 — COMPANY_PARTNERS(등록/수정 모달 공용)에는 파트너별 업체가 하나씩만
# 있어서, TC-061/063처럼 "같은 파트너의 다른 업체로 실제 이동"을 보여주려면 하나씩 더 필요했다.
TRANSFER_ONLY_COMPANY_PARTNERS = {
    "엘지테스트1": "LG U+",
    "스몰티켓(테스트)": "스몰티켓",
}


def _partner_of(company_name: str) -> str:
    """COMPANY_PARTNERS와 TRANSFER_ONLY_COMPANY_PARTNERS를 합쳐 업체명으로 파트너를 찾는다."""
    return COMPANY_PARTNERS.get(company_name) or TRANSFER_ONLY_COMPANY_PARTNERS[company_name]


# `_read_settled` 는 test_vehicle_edit_reseller.py 것을 import 해서 쓴다 — 같은 모달의 같은
# 필드를 읽는 것이라 구현이 두 벌이면 한쪽만 고쳐진다. 원래 여기에도 같은 함수가 있었다.


# 지점 드롭다운의 옵션을 브라우저 안에서 직접 읽는 JS. 닫혀 있어도 DOM 에는 있으므로
# `inner_text()`(안 보이면 빈 문자열)가 아니라 `evaluate` 로 읽어야 한다.
_BRANCH_OPTIONS_JS = """() => {
    const modal = [...document.querySelectorAll('section')]
        .find(s => s.querySelector('input[name="carNumber"]'));
    if (!modal) return null;
    const label = [...modal.querySelectorAll('label.form-label')]
        .find(l => l.innerText.trim() === '지점');
    if (!label || !label.nextElementSibling) return null;
    return [...label.nextElementSibling.querySelectorAll('[role=option]')]
        .map(o => o.innerText.trim()).join('|');
}"""


def _branch_options_fingerprint(page: Page) -> str | None:
    """지금 지점 드롭다운에 들어 있는 옵션 목록. 못 읽으면 None."""
    return page.evaluate(_BRANCH_OPTIONS_JS)


def _wait_branch_options_refreshed(page: Page, before: str | None, timeout_ms: int = 15_000) -> None:
    """지점 목록이 **새 업체 것으로 갈리고 안정될 때까지** 기다린다.

    업체를 바꿔도 지점 드롭다운은 즉시 안 갈린다. 라벨도 `aria-selected` 도 갈리기 전에 이미
    채워져 있어 신호가 못 되고, **"목록이 바뀌었다" 가 유일하게 남는 신호**다.

    ★ 두 업체의 지점 이름이 완전히 같으면 갈린 것을 알 수 없다 - 그때는 **실패시키지 않고**
      안정되기만 기다린 뒤 진행한다. 잘못 골랐으면 저장할 때 드러나고
      `_save_with_branch_retry` 가 받는다.
    경위: docs/notes/code-notes/차량업체변경-테스트-노트.md "② 업체를 바꿔도 지점 드롭다운이 즉시 안 갈린다"
    """
    page.evaluate("() => { window.__branchSnapshot = undefined; }")
    try:
        page.wait_for_function(
            """(args) => {
                const modal = [...document.querySelectorAll('section')]
                    .find(s => s.querySelector('input[name="carNumber"]'));
                if (!modal) return false;
                const label = [...modal.querySelectorAll('label.form-label')]
                    .find(l => l.innerText.trim() === '지점');
                if (!label || !label.nextElementSibling) return false;
                const cur = [...label.nextElementSibling.querySelectorAll('[role=option]')]
                    .map(o => o.innerText.trim()).join('|');
                if (!cur) { window.__branchSnapshot = undefined; return false; }
                if (cur === args.before) { window.__branchSnapshot = undefined; return false; }
                const settled = window.__branchSnapshot === cur;
                window.__branchSnapshot = cur;
                return settled;
            }""",
            arg={"before": before},
            polling=300,
            timeout=timeout_ms,
        )
    except Exception:
        # 갈린 것을 확인하지 못했다. 목록이 같은 업체일 수 있으므로 여기서 끊지 않고,
        # "안정되기만" 기다린 뒤 넘긴다. 잘못 골랐다면 저장에서 드러난다.
        page.evaluate("() => { window.__branchSnapshot = undefined; }")
        try:
            page.wait_for_function(
                """() => {
                    const modal = [...document.querySelectorAll('section')]
                        .find(s => s.querySelector('input[name="carNumber"]'));
                    if (!modal) return false;
                    const label = [...modal.querySelectorAll('label.form-label')]
                        .find(l => l.innerText.trim() === '지점');
                    if (!label || !label.nextElementSibling) return false;
                    const cur = [...label.nextElementSibling.querySelectorAll('[role=option]')]
                        .map(o => o.innerText.trim()).join('|');
                    if (!cur) { window.__branchSnapshot = undefined; return false; }
                    const settled = window.__branchSnapshot === cur;
                    window.__branchSnapshot = cur;
                    return settled;
                }""",
                polling=300,
                timeout=5_000,
            )
        except Exception:
            pass


@allure.step("인수받을 업체로 {company_name} 선택")
def _select_transfer_company(page: Page, company_name: str) -> None:
    """"업체"(인수받을 업체) 검색 드롭다운에서 이름으로 검색해 정확히 일치하는 업체를 선택한다.

    고른 뒤 **지점 목록이 새 업체 것으로 갈릴 때까지 기다린다** - 그 전에 지점을 고르면
    이전 업체의 지점을 고르게 된다 (`_wait_branch_options_refreshed` 참고).
    """
    before = _branch_options_fingerprint(page)

    company_field = _get_edit_field(page, "업체")
    company_field.click()
    company_field.locator("input.search").fill(company_name)

    option = company_field.get_by_role("option", name=company_name, exact=True)
    expect(option).to_be_visible()
    option.click()

    _wait_branch_options_refreshed(page, before)


@allure.step("지점 아무거나 선택")
def _select_any_branch(page: Page, retries: int = 3) -> None:
    """"지점" 드롭다운에서 플레이스홀더("선택")가 아닌 옵션을 아무거나 고른다.
    업체를 막 바꾼 직후라 지점 목록이 비동기로 채워지는 도중일 수 있고, 실측 중 클릭 자체가
    씹혀서 값이 "선택"에 그대로 남는 경우도 봤다(간헐적). 대기를 늘려도 안 풀리는 종류라
    — 안 눌렸으면 다시 열어서 재시도한다."""
    branch_field = _get_edit_field(page, "지점")
    branch_text = branch_field.locator(".text").first

    for attempt in range(retries):
        branch_field.click()
        option = branch_field.get_by_role("option").first
        expect(option).to_be_visible(timeout=5_000)
        picked = option.inner_text().strip()
        option.click()
        try:
            # 라벨이 "선택" 이 아닌 것만 보면 안 된다 - 업체를 바꾸기 전 지점 이름이 그대로
            # 남아 있어도 통과해서, 클릭이 씹혀도 실패할 수 없는 가드가 된다(2026-09-09 실측).
            # **방금 고른 그 지점**이 찍혔는지까지 본다.
            expect(branch_text).to_have_text(picked, timeout=3_000)
            return
        except AssertionError:
            if attempt == retries - 1:
                raise


@allure.step("[수정] 저장 + 변경 확인 팝업 [OK] 클릭")
def _click_save_and_confirm(page: Page) -> None:
    """[수정] 버튼을 누르고, 뒤이어 뜨는 "수정작업을 변경할까요?" 확인 팝업의 [OK]까지 클릭한다.
    그 뒤 팝업은 이관 성공/실패에 따라 갈리므로 호출부가 담당한다.

    ★ 확인 팝업 대신 **유효성 검사 팝업**이 뜰 수 있다(둘 다 [OK] 가 있다). 문구를 먼저 읽고
      유효성 팝업이면 그 자리에서 그 문구 그대로 실패시킨다 - 안 그러면 원인이 지점인데
      메시지는 이관 정책을 가리켜 매번 헛다리를 짚는다.
    ★★ 그 문구를 **못 읽어도 그냥 진행한다.** 진단용 곁가지가 본류를 막으면 안 된다
       (정상 팝업에는 heading 이 없어 30초 타임아웃으로 죽은 적이 있다).
    경위: docs/notes/code-notes/차량업체변경-테스트-노트.md "실측으로 뒤집힌 것 두 가지"
    """
    save_button = page.locator('button[id="2"]', has_text="수정")
    save_button.click()

    ok_button = page.get_by_role("button", name="OK", exact=True)
    expect(ok_button).to_be_visible(timeout=5_000)

    try:
        popup_text = page.get_by_role("dialog").first.inner_text(timeout=1_000)
    except Exception:
        popup_text = ""
    if "선택해주세요" in popup_text or "입력해주세요" in popup_text:
        first_line = popup_text.strip().splitlines()[0]
        raise AssertionError(
            f"[FAIL] 저장이 유효성 검사에서 막혔다: {first_line!r} - "
            "이관 정책과 무관하며, 저장 요청은 서버에 나가지 않았다"
        )
    ok_button.click()


@allure.step("이관 완료 팝업 [OK] 클릭")
def _confirm_transfer_complete(page: Page) -> None:
    """이관이 허용된 조합이면 뒤이어 뜨는 "변경을 완료하였습니다" 완료 팝업의 [OK]를 클릭한다."""
    complete_ok = page.get_by_role("button", name="OK", exact=True)
    expect(complete_ok).to_be_visible(timeout=8_000)
    complete_ok.click()


@allure.step("이관 불가 알럿 확인 후 닫기")
def _expect_transfer_blocked(page: Page) -> None:
    """이관이 정책상 불가능한 조합이면 뜨는 차단 알럿의 문구를 확인하고 닫는다."""
    alert = page.get_by_text("인수 업체의 파트너가 해당 차량의 리셀러를 허용하지 않습니다")
    expect(alert).to_be_visible(timeout=8_000)

    close_button = page.get_by_role("button", name="OK", exact=True)
    expect(close_button).to_be_visible()
    close_button.click()


def _save_with_branch_retry(page: Page, retries: int = 2) -> None:
    """지점을 고르고 저장한다. 지점 때문에 막히면 **다시 고르고 다시 저장한다.**

    "고르기 전에 완벽히 기다린다" 로는 못 막는 경우가 남는다(`_wait_branch_options_refreshed`
    의 ★). 대신 틀리면 "지점을 선택해주세요" 로 확실히 드러나므로 그 신호를 받아 재시도한다.

    ★ 유효성 팝업이 뜨면 `_click_save_and_confirm` 이 [OK]를 안 누르고 예외를 던지므로
      재시도 전에 여기서 닫아준다 - 안 닫으면 다음 클릭이 가려 막힌다.
    """
    for attempt in range(retries):
        _select_any_branch(page)
        try:
            _click_save_and_confirm(page)
            return
        except AssertionError as e:
            if "유효성 검사" not in str(e) or attempt == retries - 1:
                raise
            page.get_by_role("button", name="OK", exact=True).click()


def _assert_not_already_there(page: Page, destination: str) -> None:
    """이관하려는 업체에 **이미 소속돼 있으면** 즉시 실패시킨다.

    목적지가 하드코딩이고 원래 업체는 화면에서 읽으므로, 차량이 이미 목적지에 있으면 이관이
    **제자리 저장**이 된다. 그러면 이관·검증·teardown 이 전부 초록불인데 **정책을 하나도
    검증하지 않는다**(CLAUDE.md 위양성 "자기충족"). 실제로 3대가 그 상태로 7건을 통과시켰다.

    전제가 깨진 것이라 skip 이 아니라 **fail** 이다 - skip 으로 두면 노란불 뒤에
    "검증이 한 번도 안 돌았다" 가 숨는다.
    경위: docs/notes/code-notes/차량업체변경-테스트-노트.md "① 차량 4대 중 3대가 원 소속이 아니었다"
    """
    current = _read_settled(_get_edit_field(page, "업체").locator(".text").first)
    assert current != destination, (
        f"[FAIL] 이미 {destination!r} 소속이라 이관을 검증할 수 없다 (전제 붕괴) - "
        "앞선 실행이 원복에 실패해 차량이 목적지에 남아 있는 상태다. "
        "원래 업체로 되돌린 뒤 다시 돌린다"
    )


@allure.step("차량 {car_number}를 {destination}로 이관 (성공 기대)")
def _transfer_company_and_save(page: Page, car_number: str, destination: str) -> None:
    """모달이 열려있는 상태에서 업체를 destination으로 바꾸고 저장 + 완료 팝업까지 처리한다.
    저장하면 모달이 닫히므로, 곧장 재진입하는 대신 목록에서 업체 컬럼이 실제로 바뀐 걸 먼저
    확인해 저장이 끝났다는 신호로 삼는다 (재진입 직후엔 이전 값이 잠깐 남아있을 수 있음 —
    TC-053에서 같은 이유로 겪었던 문제와 동일)."""
    _assert_not_already_there(page, destination)
    _select_transfer_company(page, destination)
    _save_with_branch_retry(page)
    _confirm_transfer_complete(page)

    company_col = _find_list_col_index(page, "업체명")
    row = page.locator("table").first.locator("tbody tr").filter(has_text=car_number)
    expect(row.locator("td").nth(company_col)).to_have_text(destination, timeout=10_000)


@allure.step("차량을 {destination}로 이관 시도 (차단 기대)")
def _attempt_transfer_and_expect_blocked(page: Page, destination: str) -> None:
    """모달이 열려있는 상태에서 업체를 destination으로 바꾸고 저장을 시도한다.
    정책상 차단되는 조합이라 완료 팝업 대신 차단 알럿이 떠야 한다."""
    _assert_not_already_there(page, destination)
    _select_transfer_company(page, destination)
    _save_with_branch_retry(page)
    _expect_transfer_blocked(page)


@allure.step("차량 {car_number} 의 소속 업체를 {original_company} 로 원복")
def _restore_company(page: Page, car_number: str, original_company: str) -> None:
    """차량 소속 업체를 원래 값으로 되돌린다. 이미 원래 값이면 아무것도 하지 않는다.

    `_open_carmgmt_edit_modal` 이 `page.goto()` 로 시작하므로 모달·알럿이 열린 채 깨졌어도
    그냥 부를 수 있다. 현재 값을 먼저 읽는 이유 - 되돌릴 게 없는데 [수정]을 누르는 것 자체가
    규칙이 막는 동작이다(차단 TC 는 정상이라면 안 바뀐다).
    """
    _open_carmgmt_edit_modal(page, car_number)
    current = _read_settled(_get_edit_field(page, "업체").locator(".text").first)
    if current == original_company:
        return
    _transfer_company_and_save(page, car_number, original_company)


@pytest.fixture
def company_guard(logged_in_page: Page) -> Generator[Callable[[str, str], None], None, None]:
    """이관 TC 가 바꾼 차량 소속 업체를, **테스트가 어떻게 끝나든** 원래대로 되돌린다.

    쓰는 법 - 원래 값을 읽은 **직후에** 등록한다. 그 뒤로는 무슨 일이 나도 teardown 이 맡는다.

        original_company = _read_settled(...)
        company_guard(car, original_company)

    ★ **차단(blocked) TC 도 등록한다** - 막아주는 그것이 검증 대상이라, 정책이 회귀해 있으면
      저장이 실제로 통과한다. 원복 실패는 삼키지 않고 그대로 터뜨려 ERROR 로 남긴다.
    본문 마지막 줄에서 teardown 으로 옮긴 경위: docs/notes/code-notes/차량업체변경-테스트-노트.md "원복을 fixture teardown 으로 옮겼다"
    """
    page = logged_in_page
    original: dict[str, str] = {}

    def guard(car_number: str, original_company: str) -> None:
        original[car_number] = original_company

    yield guard

    for car_number, original_company in original.items():
        _restore_company(page, car_number, original_company)


@allure.title("TC-057 | 업체 변경 시 파트너 값 노출 확인")
@allure.label("testcase", "TC-057")
def test_TC057_vehicle_transfer_partner_updates_to_selected_company(logged_in_page: Page) -> None:
    """
    GIVEN  STAFF 웹에 로그인된 상태에서 차량관리>차량관리 화면에 진입해, 임의의 차량 [수정] 버튼을 클릭하면
    WHEN   인수받을 업체를 선택하면
    THEN   그 업체의 파트너가 비활성화 상태로 출력된다 (선택한 업체 기준으로 전환됨)
    """
    page = logged_in_page
    _open_carmgmt_edit_modal(page, CAR_PARTNER_CONNECT)

    transfer_company = "LG업체입니다"
    _select_transfer_company(page, transfer_company)

    partner_field = _get_edit_field(page, "파트너 선택")
    partner_text = partner_field.locator(".text").first
    expect(partner_text).to_have_text(COMPANY_PARTNERS[transfer_company])
    expect(partner_field).to_have_attribute("aria-disabled", "true")


@allure.title("TC-058 | 업체 변경 시 리셀러 값 유지 확인")
@allure.label("testcase", "TC-058")
def test_TC058_vehicle_transfer_reseller_unchanged(logged_in_page: Page) -> None:
    """
    GIVEN  STAFF 웹에 로그인된 상태에서 차량관리>차량관리 화면에 진입해,
           파트너가 [커넥트]인 차량(리셀러도 커넥트)의 [수정] 버튼을 클릭하면
    WHEN   인수받을 업체를 파트너가 다른(LG U+) 업체로 변경하면
    THEN   현재 차량의 리셀러 값(커넥트)은 변동 없이 그대로 출력된다
    """
    page = logged_in_page
    _open_carmgmt_edit_modal(page, CAR_PARTNER_CONNECT)

    # 이 차량의 리셀러가 정확히 뭔지는 몰라도 된다 — 지금 실제 표시된 값을 그대로
    # "변경 전 기준값"으로 읽어서, 업체를 바꿔도 그 값이 유지되는지만 확인한다.
    reseller_field = _get_edit_field(page, "리셀러 선택")
    reseller_text = reseller_field.locator(".text").first
    expect(reseller_text).not_to_have_text("-")
    original_reseller = reseller_text.inner_text()

    _select_transfer_company(page, "LG업체입니다")

    # 파트너 기준 업체가 바뀌어도, 리셀러 값 자체는 그대로 유지되어야 한다
    expect(reseller_text).to_have_text(original_reseller)


@pytest.mark.mutating
@allure.title("TC-059 | 리셀러 [커넥트] 차량을 파트너 [LG U+] 업체로 이관 성공")
@allure.label("testcase", "TC-059")
def test_TC059_vehicle_transfer_allowed_reseller_connect_to_lg_uplus(logged_in_page: Page, company_guard: Callable[[str, str], None]) -> None:
    """
    GIVEN  리셀러가 [커넥트]인 차량(900용1001)의 수정 화면에 진입한 상태
    WHEN   파트너가 [LG U+]인 업체(LG업체입니다)로 변경하고 지점을 선택한 뒤 저장하면
    THEN   업체 변경이 저장되고, 파트너는 LG U+로 전환되며, 리셀러는 커넥트로 그대로 유지된다

    이관 테스트 전용 차량(900용1001)이라, 검증 후 원래 업체로 되돌려 반복 실행 가능하게 한다.
    "원래 업체"는 하드코딩하지 않고 모달 진입 시 실제 표시된 값을 읽어서 쓴다.
    """
    page = logged_in_page
    car = CAR_TRANSFER_CONNECT_FROM_IMS
    destination = "LG업체입니다"

    _open_carmgmt_edit_modal(page, car)
    reseller_text = _get_edit_field(page, "리셀러 선택").locator(".text").first
    expect(reseller_text).to_have_text("커넥트")
    original_company = _read_settled(_get_edit_field(page, "업체").locator(".text").first)
    company_guard(car, original_company)

    _transfer_company_and_save(page, car, destination)

    # 재진입해서 파트너 전환·리셀러 유지를 직접 확인한다
    _open_carmgmt_edit_modal(page, car)
    partner_text = _get_edit_field(page, "파트너 선택").locator(".text").first
    expect(partner_text).to_have_text(_partner_of(destination))
    reseller_text = _get_edit_field(page, "리셀러 선택").locator(".text").first
    expect(reseller_text).to_have_text("커넥트")


@pytest.mark.mutating
@allure.title("TC-060 | 리셀러 [커넥트] 차량을 파트너 [스몰티켓] 업체로 이관 시도 시 차단")
@allure.label("testcase", "TC-060")
def test_TC060_vehicle_transfer_blocked_reseller_connect_to_smallticket(logged_in_page: Page, company_guard: Callable[[str, str], None]) -> None:
    """
    GIVEN  리셀러가 [커넥트]인 차량(900용1001)의 수정 화면에 진입한 상태
    WHEN   파트너가 [스몰티켓]인 업체(스몰티켓(지입)2)로 변경하고 지점을 선택한 뒤 저장을 시도하면
    THEN   차단 알럿이 뜨고, 재진입해도 업체·파트너·리셀러 정보가 변경 전 그대로 유지된다

    차단된 뒤에도 모달의 "업체" 필드가 방금 시도한 값으로 남아있고 자동으로 되돌아가지 않는 걸
    실측으로 확인했다 — 그래서 알럿을 닫은 직후 그 자리에서 확인하지 않고, 모달을 닫고 재진입해
    실제로 저장된(persisted) 값을 기준으로 확인한다.
    """
    page = logged_in_page
    car = CAR_TRANSFER_CONNECT_FROM_IMS
    destination = "스몰티켓(지입)2"

    _open_carmgmt_edit_modal(page, car)
    reseller_text = _get_edit_field(page, "리셀러 선택").locator(".text").first
    expect(reseller_text).to_have_text("커넥트")
    original_company = _read_settled(_get_edit_field(page, "업체").locator(".text").first)
    company_guard(car, original_company)
    original_partner = _read_settled(_get_edit_field(page, "파트너 선택").locator(".text").first)

    _attempt_transfer_and_expect_blocked(page, destination)

    _open_carmgmt_edit_modal(page, car)
    expect(_get_edit_field(page, "업체").locator(".text").first).to_have_text(original_company)
    expect(_get_edit_field(page, "파트너 선택").locator(".text").first).to_have_text(original_partner)
    expect(_get_edit_field(page, "리셀러 선택").locator(".text").first).to_have_text("커넥트")


@pytest.mark.mutating
@allure.title("TC-061 | 리셀러 [LG U+] 차량을 파트너 [LG U+] 다른 업체로 이관 성공")
@allure.label("testcase", "TC-061")
def test_TC061_vehicle_transfer_allowed_reseller_lg_uplus_to_lg_uplus(logged_in_page: Page, company_guard: Callable[[str, str], None]) -> None:
    """
    GIVEN  리셀러가 [LG U+]인 차량(900용1003, 원 소속 LG업체입니다)의 수정 화면에 진입한 상태
    WHEN   파트너가 [LG U+]인 다른 업체(엘지테스트1)로 변경하고 지점을 선택한 뒤 저장하면
    THEN   업체 변경이 저장되고, 파트너는 LG U+로 유지되며, 리셀러도 LG U+로 그대로 유지된다

    파트너=LG U+인 업체가 원래 COMPANY_PARTNERS엔 "LG업체입니다" 하나뿐이라, 실제로 다른 업체로
    이동하는 걸 보여주기 위해 목적지를 "엘지테스트1"(파트너도 LG U+)로 잡았다.
    """
    page = logged_in_page
    car = CAR_TRANSFER_LG_UPLUS
    destination = "엘지테스트1"

    _open_carmgmt_edit_modal(page, car)
    reseller_text = _get_edit_field(page, "리셀러 선택").locator(".text").first
    expect(reseller_text).to_have_text("LG U+")
    original_company = _read_settled(_get_edit_field(page, "업체").locator(".text").first)
    company_guard(car, original_company)

    _transfer_company_and_save(page, car, destination)

    _open_carmgmt_edit_modal(page, car)
    partner_text = _get_edit_field(page, "파트너 선택").locator(".text").first
    expect(partner_text).to_have_text(_partner_of(destination))
    reseller_text = _get_edit_field(page, "리셀러 선택").locator(".text").first
    expect(reseller_text).to_have_text("LG U+")


@pytest.mark.mutating
@allure.title("TC-062 | 리셀러 [LG U+] 차량을 파트너 [커넥트] 업체로 이관 시도 시 차단")
@allure.label("testcase", "TC-062")
def test_TC062_vehicle_transfer_blocked_reseller_lg_uplus_to_connect(logged_in_page: Page, company_guard: Callable[[str, str], None]) -> None:
    """
    GIVEN  리셀러가 [LG U+]인 차량(900용1003)의 수정 화면에 진입한 상태
    WHEN   파트너가 [커넥트]인 업체(IMS모빌리티)로 변경하고 지점을 선택한 뒤 저장을 시도하면
    THEN   차단 알럿이 뜨고, 재진입해도 업체·파트너·리셀러 정보가 변경 전 그대로 유지된다
    """
    page = logged_in_page
    car = CAR_TRANSFER_LG_UPLUS
    destination = "IMS모빌리티"

    _open_carmgmt_edit_modal(page, car)
    reseller_text = _get_edit_field(page, "리셀러 선택").locator(".text").first
    expect(reseller_text).to_have_text("LG U+")
    original_company = _read_settled(_get_edit_field(page, "업체").locator(".text").first)
    company_guard(car, original_company)
    original_partner = _read_settled(_get_edit_field(page, "파트너 선택").locator(".text").first)

    _attempt_transfer_and_expect_blocked(page, destination)

    _open_carmgmt_edit_modal(page, car)
    expect(_get_edit_field(page, "업체").locator(".text").first).to_have_text(original_company)
    expect(_get_edit_field(page, "파트너 선택").locator(".text").first).to_have_text(original_partner)
    expect(_get_edit_field(page, "리셀러 선택").locator(".text").first).to_have_text("LG U+")


@pytest.mark.mutating
@allure.title("TC-063 | 리셀러 [스몰티켓] 차량을 파트너 [스몰티켓] 다른 업체로 이관 성공")
@allure.label("testcase", "TC-063")
def test_TC063_vehicle_transfer_allowed_reseller_smallticket_to_smallticket(logged_in_page: Page, company_guard: Callable[[str, str], None]) -> None:
    """
    GIVEN  리셀러가 [스몰티켓]인 차량(900용1004, 원 소속 스몰티켓(지입)2)의 수정 화면에 진입한 상태
    WHEN   파트너가 [스몰티켓]인 다른 업체(스몰티켓(테스트))로 변경하고 지점을 선택한 뒤 저장하면
    THEN   업체 변경이 저장되고, 파트너는 스몰티켓으로 유지되며, 리셀러도 스몰티켓으로 그대로 유지된다
    """
    page = logged_in_page
    car = CAR_TRANSFER_SMALLTICKET
    destination = "스몰티켓(테스트)"

    _open_carmgmt_edit_modal(page, car)
    reseller_text = _get_edit_field(page, "리셀러 선택").locator(".text").first
    expect(reseller_text).to_have_text("스몰티켓")
    original_company = _read_settled(_get_edit_field(page, "업체").locator(".text").first)
    company_guard(car, original_company)

    _transfer_company_and_save(page, car, destination)

    _open_carmgmt_edit_modal(page, car)
    partner_text = _get_edit_field(page, "파트너 선택").locator(".text").first
    expect(partner_text).to_have_text(_partner_of(destination))
    reseller_text = _get_edit_field(page, "리셀러 선택").locator(".text").first
    expect(reseller_text).to_have_text("스몰티켓")


@pytest.mark.mutating
@allure.title("TC-064 | 리셀러 [스몰티켓] 차량을 파트너 [커넥트] 업체로 이관 시도 시 차단")
@allure.label("testcase", "TC-064")
def test_TC064_vehicle_transfer_blocked_reseller_smallticket_to_connect(logged_in_page: Page, company_guard: Callable[[str, str], None]) -> None:
    """
    GIVEN  리셀러가 [스몰티켓]인 차량(900용1004)의 수정 화면에 진입한 상태
    WHEN   파트너가 [커넥트]인 업체(IMS모빌리티)로 변경하고 지점을 선택한 뒤 저장을 시도하면
    THEN   차단 알럿이 뜨고, 재진입해도 업체·파트너·리셀러 정보가 변경 전 그대로 유지된다
    """
    page = logged_in_page
    car = CAR_TRANSFER_SMALLTICKET
    destination = "IMS모빌리티"

    _open_carmgmt_edit_modal(page, car)
    reseller_text = _get_edit_field(page, "리셀러 선택").locator(".text").first
    expect(reseller_text).to_have_text("스몰티켓")
    original_company = _read_settled(_get_edit_field(page, "업체").locator(".text").first)
    company_guard(car, original_company)
    original_partner = _read_settled(_get_edit_field(page, "파트너 선택").locator(".text").first)

    _attempt_transfer_and_expect_blocked(page, destination)

    _open_carmgmt_edit_modal(page, car)
    expect(_get_edit_field(page, "업체").locator(".text").first).to_have_text(original_company)
    expect(_get_edit_field(page, "파트너 선택").locator(".text").first).to_have_text(original_partner)
    expect(_get_edit_field(page, "리셀러 선택").locator(".text").first).to_have_text("스몰티켓")


@pytest.mark.mutating
@allure.title("TC-065 | 업체 이관 성공 후 재진입 시 파트너·리셀러 정합성 확인")
@allure.label("testcase", "TC-065")
def test_TC065_vehicle_transfer_partner_reseller_consistent_after_reentry(logged_in_page: Page, company_guard: Callable[[str, str], None]) -> None:
    """
    GIVEN  리셀러가 [커넥트]인 차량(900용1002, 원 소속 LG업체입니다)의 수정 화면에 진입한 상태
    WHEN   파트너가 [커넥트]인 업체(IMS모빌리티)로 변경하고 지점을 선택한 뒤 저장, 완료 팝업 [OK]
           클릭 후 변경된 차량의 수정 화면에 재진입하면
    THEN   업체는 선택한 인수 업체로 변경되어 있고, 파트너는 그 업체의 파트너(커넥트)로 바뀌어
           있으며, 기존 리셀러(커넥트)는 변경되지 않고 유지된다

    TC-059와 검증 로직 자체는 같은 조합(리셀러=커넥트, 목적지 파트너=커넥트/LG U+)이지만, TC
    문서가 "재진입 후 정합성"을 별도 TC로 명시하고 있어 다른 차량(900용1002)을 써서 독립적으로
    실행한다. 방향도 TC-059(커넥트→LG U+)와 반대(LG U+→커넥트)로 잡아 양방향을 다 검증한다.
    """
    page = logged_in_page
    car = CAR_TRANSFER_CONNECT_FROM_LG
    destination = "IMS모빌리티"

    _open_carmgmt_edit_modal(page, car)
    reseller_text = _get_edit_field(page, "리셀러 선택").locator(".text").first
    expect(reseller_text).to_have_text("커넥트")
    original_company = _read_settled(_get_edit_field(page, "업체").locator(".text").first)
    company_guard(car, original_company)

    _transfer_company_and_save(page, car, destination)

    # 재진입해서 업체·파트너·리셀러가 정확히 반영됐는지 직접 확인
    _open_carmgmt_edit_modal(page, car)
    company_text = _get_edit_field(page, "업체").locator(".text").first
    expect(company_text).to_have_text(destination)
    partner_text = _get_edit_field(page, "파트너 선택").locator(".text").first
    expect(partner_text).to_have_text(_partner_of(destination))
    reseller_text = _get_edit_field(page, "리셀러 선택").locator(".text").first
    expect(reseller_text).to_have_text("커넥트")


@pytest.mark.mutating
@allure.title("TC-066 | 업체 이관 차단 후 재진입해도 기존 정보 유지 확인")
@allure.label("testcase", "TC-066")
def test_TC066_vehicle_transfer_blocked_data_unchanged_after_reentry(logged_in_page: Page, company_guard: Callable[[str, str], None]) -> None:
    """
    GIVEN  리셀러가 [커넥트]인 차량(900용1002)의 수정 화면에 진입한 상태
    WHEN   파트너가 [스몰티켓]인 업체로 변경을 시도해 차단된 뒤, 차량 수정 화면에 재진입하면
    THEN   재진입해도 업체·파트너·리셀러 정보가 변경 전 그대로 유지된다

    TC-060은 알럿을 닫은 직후(모달을 다시 열지 않고) 확인하지만, 이 TC는 TC 문서 비고에
    "변경 차단 후 기존 데이터 유지 여부까지 확인"하라고 명시돼 있어 모달을 닫고(재진입 자체가
    _open_carmgmt_edit_modal 내부에서 새로 페이지를 로드하므로 별도 닫기 동작 없이도 됨)
    재진입까지 해서 한 번 더 확인한다.
    """
    page = logged_in_page
    car = CAR_TRANSFER_CONNECT_FROM_LG
    destination = "스몰티켓(지입)2"

    _open_carmgmt_edit_modal(page, car)
    reseller_text = _get_edit_field(page, "리셀러 선택").locator(".text").first
    expect(reseller_text).to_have_text("커넥트")
    original_company = _read_settled(_get_edit_field(page, "업체").locator(".text").first)
    company_guard(car, original_company)
    original_partner = _read_settled(_get_edit_field(page, "파트너 선택").locator(".text").first)

    _attempt_transfer_and_expect_blocked(page, destination)

    # 재진입 — _open_carmgmt_edit_modal이 페이지를 새로 열어서 시작하므로 모달을 따로 닫을 필요 없음
    _open_carmgmt_edit_modal(page, car)
    expect(_get_edit_field(page, "업체").locator(".text").first).to_have_text(original_company)
    expect(_get_edit_field(page, "파트너 선택").locator(".text").first).to_have_text(original_partner)
    expect(_get_edit_field(page, "리셀러 선택").locator(".text").first).to_have_text("커넥트")
