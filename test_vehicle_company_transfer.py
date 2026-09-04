# GNB 경로: 차량관리 > 차량관리 (수정 - 업체 변경)

import allure
from playwright.sync_api import Locator, Page, expect

from test_vehicle_edit_reseller import (
    CAR_PARTNER_CONNECT,
    _find_list_col_index,
    _get_edit_field,
    _open_carmgmt_edit_modal,
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


def _read_settled(field_text: Locator) -> str:
    """모달이 열린 직후엔 "업체"/"파트너 선택" 값이 비동기로 채워지는 도중이라, 곧바로
    inner_text()로 읽으면 플레이스홀더("선택")를 실제 값으로 착각할 수 있다(실측으로 확인 —
    TC-065/066에서 "선택"을 원래 업체명으로 잘못 캡처해 원복 검색이 "No results found"로
    실패했다). 값이 "선택"에서 벗어날 때까지 기다린 뒤 읽는다."""
    expect(field_text).not_to_have_text("선택", timeout=10_000)
    return field_text.inner_text()


@allure.step("인수받을 업체로 {company_name} 선택")
def _select_transfer_company(page: Page, company_name: str) -> None:
    """"업체"(인수받을 업체) 검색 드롭다운에서 이름으로 검색해 정확히 일치하는 업체를 선택한다."""
    company_field = _get_edit_field(page, "업체")
    company_field.click()
    company_field.locator("input.search").fill(company_name)

    option = company_field.get_by_role("option", name=company_name, exact=True)
    expect(option).to_be_visible()
    option.click()


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
        option.click()
        try:
            expect(branch_text).not_to_have_text("선택", timeout=3_000)
            return
        except AssertionError:
            if attempt == retries - 1:
                raise


@allure.step("[수정] 저장 + 변경 확인 팝업 [OK] 클릭")
def _click_save_and_confirm(page: Page) -> None:
    """[수정] 버튼을 누르고, 뒤이어 뜨는 "수정작업을 변경할까요?" 확인 팝업의 [OK]까지 클릭한다.
    이 다음은 이관 성공/실패에 따라 뜨는 팝업이 갈리므로, 그 뒤 처리는 호출부가 담당한다."""
    save_button = page.locator('button[id="2"]', has_text="수정")
    save_button.click()

    ok_button = page.get_by_role("button", name="OK", exact=True)
    expect(ok_button).to_be_visible(timeout=5_000)
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


@allure.step("차량 {car_number}를 {destination}로 이관 (성공 기대)")
def _transfer_company_and_save(page: Page, car_number: str, destination: str) -> None:
    """모달이 열려있는 상태에서 업체를 destination으로 바꾸고 저장 + 완료 팝업까지 처리한다.
    저장하면 모달이 닫히므로, 곧장 재진입하는 대신 목록에서 업체 컬럼이 실제로 바뀐 걸 먼저
    확인해 저장이 끝났다는 신호로 삼는다 (재진입 직후엔 이전 값이 잠깐 남아있을 수 있음 —
    TC-053에서 같은 이유로 겪었던 문제와 동일)."""
    _select_transfer_company(page, destination)
    _select_any_branch(page)
    _click_save_and_confirm(page)
    _confirm_transfer_complete(page)

    company_col = _find_list_col_index(page, "업체명")
    row = page.locator("table").first.locator("tbody tr").filter(has_text=car_number)
    expect(row.locator("td").nth(company_col)).to_have_text(destination, timeout=10_000)


@allure.step("차량을 {destination}로 이관 시도 (차단 기대)")
def _attempt_transfer_and_expect_blocked(page: Page, destination: str) -> None:
    """모달이 열려있는 상태에서 업체를 destination으로 바꾸고 저장을 시도한다.
    정책상 차단되는 조합이라 완료 팝업 대신 차단 알럿이 떠야 한다."""
    _select_transfer_company(page, destination)
    _select_any_branch(page)
    _click_save_and_confirm(page)
    _expect_transfer_blocked(page)


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


@allure.title("TC-059 | 리셀러 [커넥트] 차량을 파트너 [LG U+] 업체로 이관 성공")
@allure.label("testcase", "TC-059")
def test_TC059_vehicle_transfer_allowed_reseller_connect_to_lg_uplus(logged_in_page: Page) -> None:
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

    _transfer_company_and_save(page, car, destination)

    # 재진입해서 파트너 전환·리셀러 유지를 직접 확인한다
    _open_carmgmt_edit_modal(page, car)
    partner_text = _get_edit_field(page, "파트너 선택").locator(".text").first
    expect(partner_text).to_have_text(_partner_of(destination))
    reseller_text = _get_edit_field(page, "리셀러 선택").locator(".text").first
    expect(reseller_text).to_have_text("커넥트")

    # 원복 — 다음 실행에서도 같은 전제로 시작할 수 있게
    _transfer_company_and_save(page, car, original_company)


@allure.title("TC-060 | 리셀러 [커넥트] 차량을 파트너 [스몰티켓] 업체로 이관 시도 시 차단")
@allure.label("testcase", "TC-060")
def test_TC060_vehicle_transfer_blocked_reseller_connect_to_smallticket(logged_in_page: Page) -> None:
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
    original_partner = _read_settled(_get_edit_field(page, "파트너 선택").locator(".text").first)

    _attempt_transfer_and_expect_blocked(page, destination)

    _open_carmgmt_edit_modal(page, car)
    expect(_get_edit_field(page, "업체").locator(".text").first).to_have_text(original_company)
    expect(_get_edit_field(page, "파트너 선택").locator(".text").first).to_have_text(original_partner)
    expect(_get_edit_field(page, "리셀러 선택").locator(".text").first).to_have_text("커넥트")


@allure.title("TC-061 | 리셀러 [LG U+] 차량을 파트너 [LG U+] 다른 업체로 이관 성공")
@allure.label("testcase", "TC-061")
def test_TC061_vehicle_transfer_allowed_reseller_lg_uplus_to_lg_uplus(logged_in_page: Page) -> None:
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

    _transfer_company_and_save(page, car, destination)

    _open_carmgmt_edit_modal(page, car)
    partner_text = _get_edit_field(page, "파트너 선택").locator(".text").first
    expect(partner_text).to_have_text(_partner_of(destination))
    reseller_text = _get_edit_field(page, "리셀러 선택").locator(".text").first
    expect(reseller_text).to_have_text("LG U+")

    _transfer_company_and_save(page, car, original_company)


@allure.title("TC-062 | 리셀러 [LG U+] 차량을 파트너 [커넥트] 업체로 이관 시도 시 차단")
@allure.label("testcase", "TC-062")
def test_TC062_vehicle_transfer_blocked_reseller_lg_uplus_to_connect(logged_in_page: Page) -> None:
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
    original_partner = _read_settled(_get_edit_field(page, "파트너 선택").locator(".text").first)

    _attempt_transfer_and_expect_blocked(page, destination)

    _open_carmgmt_edit_modal(page, car)
    expect(_get_edit_field(page, "업체").locator(".text").first).to_have_text(original_company)
    expect(_get_edit_field(page, "파트너 선택").locator(".text").first).to_have_text(original_partner)
    expect(_get_edit_field(page, "리셀러 선택").locator(".text").first).to_have_text("LG U+")


@allure.title("TC-063 | 리셀러 [스몰티켓] 차량을 파트너 [스몰티켓] 다른 업체로 이관 성공")
@allure.label("testcase", "TC-063")
def test_TC063_vehicle_transfer_allowed_reseller_smallticket_to_smallticket(logged_in_page: Page) -> None:
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

    _transfer_company_and_save(page, car, destination)

    _open_carmgmt_edit_modal(page, car)
    partner_text = _get_edit_field(page, "파트너 선택").locator(".text").first
    expect(partner_text).to_have_text(_partner_of(destination))
    reseller_text = _get_edit_field(page, "리셀러 선택").locator(".text").first
    expect(reseller_text).to_have_text("스몰티켓")

    _transfer_company_and_save(page, car, original_company)


@allure.title("TC-064 | 리셀러 [스몰티켓] 차량을 파트너 [커넥트] 업체로 이관 시도 시 차단")
@allure.label("testcase", "TC-064")
def test_TC064_vehicle_transfer_blocked_reseller_smallticket_to_connect(logged_in_page: Page) -> None:
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
    original_partner = _read_settled(_get_edit_field(page, "파트너 선택").locator(".text").first)

    _attempt_transfer_and_expect_blocked(page, destination)

    _open_carmgmt_edit_modal(page, car)
    expect(_get_edit_field(page, "업체").locator(".text").first).to_have_text(original_company)
    expect(_get_edit_field(page, "파트너 선택").locator(".text").first).to_have_text(original_partner)
    expect(_get_edit_field(page, "리셀러 선택").locator(".text").first).to_have_text("스몰티켓")


@allure.title("TC-065 | 업체 이관 성공 후 재진입 시 파트너·리셀러 정합성 확인")
@allure.label("testcase", "TC-065")
def test_TC065_vehicle_transfer_partner_reseller_consistent_after_reentry(logged_in_page: Page) -> None:
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

    _transfer_company_and_save(page, car, destination)

    # 재진입해서 업체·파트너·리셀러가 정확히 반영됐는지 직접 확인
    _open_carmgmt_edit_modal(page, car)
    company_text = _get_edit_field(page, "업체").locator(".text").first
    expect(company_text).to_have_text(destination)
    partner_text = _get_edit_field(page, "파트너 선택").locator(".text").first
    expect(partner_text).to_have_text(_partner_of(destination))
    reseller_text = _get_edit_field(page, "리셀러 선택").locator(".text").first
    expect(reseller_text).to_have_text("커넥트")

    _transfer_company_and_save(page, car, original_company)


@allure.title("TC-066 | 업체 이관 차단 후 재진입해도 기존 정보 유지 확인")
@allure.label("testcase", "TC-066")
def test_TC066_vehicle_transfer_blocked_data_unchanged_after_reentry(logged_in_page: Page) -> None:
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
    original_partner = _read_settled(_get_edit_field(page, "파트너 선택").locator(".text").first)

    _attempt_transfer_and_expect_blocked(page, destination)

    # 재진입 — _open_carmgmt_edit_modal이 페이지를 새로 열어서 시작하므로 모달을 따로 닫을 필요 없음
    _open_carmgmt_edit_modal(page, car)
    expect(_get_edit_field(page, "업체").locator(".text").first).to_have_text(original_company)
    expect(_get_edit_field(page, "파트너 선택").locator(".text").first).to_have_text(original_partner)
    expect(_get_edit_field(page, "리셀러 선택").locator(".text").first).to_have_text("커넥트")
