import os
import re

from playwright.sync_api import expect

STAFF_URL = os.getenv("STAFF_URL")

# 자세한 설명은 docs/notes/code-notes/차량등록-파트너리셀러-테스트-노트.md 참고


def _open_carspec_register_modal(page):
    """차량관리>차스펙관리로 이동해 목록 첫 행의 [등록] 버튼을 눌러 차량 등록 모달을 연다."""
    page.goto(STAFF_URL)
    page.locator("a").filter(has_text=re.compile(r"^차량관리$")).click()
    page.get_by_role("link", name="차스펙관리", exact=True).click()
    page.locator(".spinner").first.wait_for(state="hidden", timeout=60_000)
    page.get_by_role("button", name="등록", exact=True).first.click()


def _get_form_field(page, label_text):
    """"파트너"/"리셀러" 같은 폼 라벨(label.form-label) 텍스트로, 그 바로 다음에 오는
    입력/드롭다운 요소(형제 요소)를 찾아 돌려준다."""
    label = page.locator("label.form-label").filter(has_text=re.compile(f"^{re.escape(label_text)}$"))
    return label.locator("xpath=./following-sibling::*[1]")


def _select_company(page, company_name):
    """"업체" 검색 드롭다운에서 이름으로 검색해 정확히 일치하는 업체를 선택한다."""
    company_field = _get_form_field(page, "업체")
    company_field.click()
    company_field.locator("input.search").fill(company_name)

    option = company_field.get_by_role("option", name=company_name, exact=True).first
    expect(option).to_be_visible()
    option.click()


def test_TC043_vehicle_register_partner_field_visible(logged_in_page):
    """
    TC-043 | 차량 등록 시 파트너 항목 출력 확인

    GIVEN  STAFF 웹에 로그인된 상태에서 차량관리>차스펙관리 화면에 진입해, 목록의 [등록] 버튼을 클릭하면
    WHEN   차량 등록 모달에 진입하면
    THEN   수정 불가능한 파트너 항목이 노출된다 (업체 항목 아래)
    """
    page = logged_in_page
    _open_carspec_register_modal(page)

    partner_label = page.locator("label.form-label").filter(has_text=re.compile(r"^파트너$"))
    expect(partner_label).to_be_visible()

    partner_field = _get_form_field(page, "파트너")
    expect(partner_field).to_be_visible()
    expect(partner_field).to_have_attribute("aria-disabled", "true")


def test_TC044_vehicle_register_reseller_field_visible(logged_in_page):
    """
    TC-044 | 차량 등록 시 리셀러 항목 출력 확인

    GIVEN  STAFF 웹에 로그인된 상태에서 차량관리>차스펙관리 화면에 진입해, 목록의 [등록] 버튼을 클릭하면
    WHEN   차량 등록 모달에 진입하면
    THEN   리셀러 항목이 노출된다 (지점 항목 아래, 파트너 항목 오른쪽)
    """
    page = logged_in_page
    _open_carspec_register_modal(page)

    reseller_label = page.locator("label.form-label").filter(has_text=re.compile(r"^리셀러$"))
    expect(reseller_label).to_be_visible()

    reseller_field = _get_form_field(page, "리셀러")
    expect(reseller_field).to_be_visible()


def test_TC045_vehicle_register_partner_reseller_switch_by_company(logged_in_page):
    """
    TC-045 | 차량 등록 시 업체 선택 변경에 따른 파트너 및 리셀러 상태 전환 확인

    GIVEN  STAFF 웹에 로그인된 상태에서 차량관리>차스펙관리 화면에 진입해, 목록의 [등록] 버튼을 클릭하면
    WHEN   1. 파트너가 [커넥트]인 업체를 선택하면
           2. 파트너가 [LG U+]인 업체로 변경하면
           3. 파트너가 [스몰티켓]인 업체로 변경하면
    THEN   1. 파트너·리셀러가 커넥트로 자동 선택된다
           2. 파트너는 LG U+로 자동 선택되고, 리셀러는 [커넥트/LG U+] 중 선택 가능한 상태로 활성화된다
           3. 파트너·리셀러가 스몰티켓으로 자동 선택된다

    dev 환경에서 실제로 각 파트너에 매핑되는 업체를 직접 선택해보고 확인한 값입니다
    (업체 이름이 파트너명을 그대로 담고 있지 않은 경우도 있어서, 실제 동작으로 확인 후 골랐습니다).
    """
    page = logged_in_page
    _open_carspec_register_modal(page)

    partner_field = _get_form_field(page, "파트너")
    reseller_field = _get_form_field(page, "리셀러")
    partner_text = partner_field.locator(".text").first
    reseller_text = reseller_field.locator(".text").first

    # 1. 파트너가 커넥트인 업체
    _select_company(page, "IMS모빌리티")
    expect(partner_field).to_have_attribute("aria-disabled", "true")
    expect(partner_text).to_have_text("커넥트")
    expect(reseller_field).to_have_attribute("aria-disabled", "true")
    expect(reseller_text).to_have_text("커넥트")

    # 2. 파트너가 LG U+인 업체로 변경
    _select_company(page, "LG업체입니다")
    expect(partner_field).to_have_attribute("aria-disabled", "true")
    expect(partner_text).to_have_text("LG U+")
    expect(reseller_field).to_have_attribute("aria-disabled", "false")
    reseller_options = reseller_field.locator('[role="option"] .text').all_inner_texts()
    assert set(reseller_options) == {"커넥트", "LG U+"}, (
        f"[FAIL] 리셀러 선택지가 [커넥트/LG U+]가 아닙니다: {reseller_options}"
    )

    # 3. 파트너가 스몰티켓인 업체로 변경
    _select_company(page, "스몰티켓(지입)2")
    expect(partner_field).to_have_attribute("aria-disabled", "true")
    expect(partner_text).to_have_text("스몰티켓")
    expect(reseller_field).to_have_attribute("aria-disabled", "true")
    expect(reseller_text).to_have_text("스몰티켓")
