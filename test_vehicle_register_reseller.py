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
    assert partner_field.get_attribute("aria-disabled") == "true", (
        "[FAIL] 파트너 항목이 수정 가능한 상태입니다 (수정 불가여야 함)"
    )


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
