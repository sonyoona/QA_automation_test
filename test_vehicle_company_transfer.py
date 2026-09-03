# GNB 경로: 차량관리 > 차량관리 (수정 - 업체 변경)

import allure
from playwright.sync_api import Page, expect

from test_vehicle_edit_reseller import CAR_PARTNER_CONNECT, _get_edit_field, _open_carmgmt_edit_modal
from test_vehicle_register_reseller import COMPANY_PARTNERS

# Allure 리포트에서 이 파일의 테스트들이 묶이는 기능 단위 (파일 상단 GNB 경로와 동일)
pytestmark = allure.feature("차량관리 > 차량관리 (업체 변경)  ·  test_vehicle_company_transfer.py")

# 같은 모달(차량관리>차량관리 수정)을 다루므로 test_vehicle_edit_reseller.py의 헬퍼를 그대로 가져다 씀
# 업체→파트너 매핑도 test_vehicle_register_reseller.py의 COMPANY_PARTNERS를 그대로 재사용
# (같은 dev 환경 데이터라, 여기서 따로 문자열로 다시 적으면 나중에 한쪽만 바뀌었을 때 어긋날 수 있음)
# 자세한 설명은 docs/notes/code-notes/차량업체변경-테스트-노트.md 참고


@allure.step("인수받을 업체로 {company_name} 선택")
def _select_transfer_company(page: Page, company_name: str) -> None:
    """"업체"(인수받을 업체) 검색 드롭다운에서 이름으로 검색해 정확히 일치하는 업체를 선택한다."""
    company_field = _get_edit_field(page, "업체")
    company_field.click()
    company_field.locator("input.search").fill(company_name)

    option = company_field.get_by_role("option", name=company_name, exact=True)
    expect(option).to_be_visible()
    option.click()


@allure.title("TC-057 | 업체 변경 시 파트너 값 노출 확인")
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
