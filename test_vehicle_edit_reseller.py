# GNB 경로: 차량관리 > 차량관리 (수정)

import os
import re

import allure
from playwright.sync_api import Locator, Page, expect

STAFF_URL = os.getenv("STAFF_URL")

# Allure 리포트에서 이 파일의 테스트들이 묶이는 기능 단위 (파일 상단 GNB 경로와 동일)
pytestmark = allure.feature("차량관리 > 차량관리 (수정)  ·  test_vehicle_edit_reseller.py")

# 사용자가 직접 등록해둔 dev 환경 테스트 차량 (업체→파트너 매핑은
# test_vehicle_register_reseller.py의 COMPANY_PARTNERS와 동일한 3개 업체 기준)
CAR_PARTNER_CONNECT = "054용1111"       # IMS모빌리티 → 파트너 커넥트
CAR_PARTNER_LG_UPLUS = "055용1111"      # LG업체입니다 → 파트너 LG U+, 리셀러 커넥트로 등록됨
CAR_PARTNER_LG_UPLUS_RESELLER_LG = "035용1111"  # LG업체입니다 → 파트너 LG U+, 리셀러도 LG U+로 등록됨
CAR_PARTNER_SMALLTICKET = "056용1111"   # 스몰티켓(지입)2 → 파트너 스몰티켓

# 자세한 설명은 docs/notes/code-notes/차량수정-파트너리셀러-테스트-노트.md 참고


@allure.step("차량 {car_number}의 [수정] 버튼을 눌러 모달 열기")
def _open_carmgmt_edit_modal(page: Page, car_number: str) -> None:
    """차량관리>차량관리로 이동해 지정한 차량번호 행의 [수정] 버튼을 눌러 상세 모달을 연다.
    모달 데이터는 비동기로 채워지므로, 차량 번호 입력값이 실제로 그 차량 걸로 찰 때까지 기다린 뒤 돌려준다."""
    page.goto(STAFF_URL)
    page.locator("a").filter(has_text=re.compile(r"^차량관리$")).click()
    page.get_by_role("link", name="차량 관리", exact=True).click()

    row = page.locator("table").first.locator("tbody tr").filter(has_text=car_number)
    row.get_by_role("button", name="수정", exact=True).click()

    car_number_input = page.locator('input[name="carNumber"]')
    expect(car_number_input).to_have_value(car_number, timeout=15_000)


def _get_modal(page: Page) -> Locator:
    """지금 열려있는 차량 수정 모달(section) 자체를 가리키는 Locator."""
    return page.locator("section").filter(has=page.locator('input[name="carNumber"]'))


def _get_edit_field(page: Page, label_text: str) -> Locator:
    """모달 안에서 라벨 텍스트로 그 바로 다음 형제 요소(입력/드롭다운)를 찾아 돌려준다.
    목록 화면 필터 영역에도 같은 이름의 라벨(예: "업체")이 있을 수 있어서,
    지금 열려있는 모달 안으로 범위를 좁힌 뒤 찾는다."""
    label = _get_modal(page).locator("label.form-label").filter(has_text=re.compile(f"^{re.escape(label_text)}$"))
    return label.locator("xpath=./following-sibling::*[1]")


@allure.step("리셀러를 {value}로 변경")
def _select_reseller(page: Page, value: str) -> None:
    """"리셀러 선택" 드롭다운을 열고 정확히 일치하는 옵션을 클릭한다."""
    reseller_field = _get_edit_field(page, "리셀러 선택")
    reseller_field.click()
    option = reseller_field.get_by_role("option", name=value, exact=True)
    expect(option).to_be_visible()
    option.click()


@allure.step("[수정] 저장 + 확인 팝업 [OK] 클릭")
def _save_edit_modal(page: Page) -> None:
    """모달의 [수정](저장) 버튼을 누르고, 뒤이어 뜨는 저장 확인 팝업의 [OK]까지 클릭한다.
    이 확인 팝업을 안 누르면 저장 자체가 조용히 무시된다 — 자세한 경위는 code-notes 참고."""
    save_button = page.locator('button[id="2"]', has_text="수정")
    save_button.click()

    ok_button = page.get_by_role("button", name="OK", exact=True)
    expect(ok_button).to_be_visible(timeout=5_000)
    ok_button.click()


@allure.step("목록 헤더에서 {header_text} 컬럼 위치 찾기")
def _find_list_col_index(page: Page, header_text: str) -> int:
    """차량관리 목록에서 header_text와 정확히 일치하는 컬럼의 인덱스(0-based)를 헤더에서 찾는다."""
    headers = page.locator("table").first.locator("thead th").all_inner_texts()
    return headers.index(header_text)


@allure.title("TC-051 | 차량 수정 모달 파트너 항목(수정 불가) 노출 확인")
def test_TC051_vehicle_edit_partner_field_visible(logged_in_page: Page) -> None:
    """
    GIVEN  STAFF 웹에 로그인된 상태에서 차량관리>차량관리 화면에 진입해, 임의의 차량 [수정] 버튼을 클릭하면
    WHEN   차량 수정 모달에 진입하면
    THEN   수정 불가능한 파트너 항목이 노출된다 (지점 항목 아래)
    """
    page = logged_in_page
    _open_carmgmt_edit_modal(page, CAR_PARTNER_CONNECT)

    partner_label = page.locator("label.form-label").filter(has_text=re.compile(r"^파트너 선택$"))
    expect(partner_label).to_be_visible()

    partner_field = _get_edit_field(page, "파트너 선택")
    expect(partner_field).to_be_visible()
    expect(partner_field).to_have_attribute("aria-disabled", "true")


@allure.title("TC-052 | 차량 수정 모달 리셀러 항목 노출 확인")
def test_TC052_vehicle_edit_reseller_field_visible(logged_in_page: Page) -> None:
    """
    GIVEN  STAFF 웹에 로그인된 상태에서 차량관리>차량관리 화면에 진입해, 임의의 차량 [수정] 버튼을 클릭하면
    WHEN   차량 수정 모달에 진입하면
    THEN   리셀러 항목이 노출된다 (파트너 항목 아래)
    """
    page = logged_in_page
    _open_carmgmt_edit_modal(page, CAR_PARTNER_CONNECT)

    reseller_label = page.locator("label.form-label").filter(has_text=re.compile(r"^리셀러 선택$"))
    expect(reseller_label).to_be_visible()

    reseller_field = _get_edit_field(page, "리셀러 선택")
    expect(reseller_field).to_be_visible()


@allure.title("TC-053 | 리셀러 값 변경(LG U+↔커넥트) 및 저장 반영 확인")
def test_TC053_vehicle_edit_reseller_change_and_revert_when_partner_lg_uplus(logged_in_page: Page) -> None:
    """
    GIVEN  STAFF 웹에 로그인된 상태에서 차량관리>차량관리 화면에 진입해,
           파트너와 리셀러가 모두 [LG U+]인 차량의 [수정] 버튼을 클릭하면
    WHEN   1. 리셀러를 LG U+에서 커넥트로 변경 후 저장하고
           2. 차량 수정 화면에 재진입해 리셀러를 커넥트에서 LG U+로 다시 변경 후 저장하면
    THEN   각 저장 직후 재진입했을 때 리셀러 값이 정확히 반영되어 있고,
           그 과정 내내 파트너는 LG U+로 유지된다

    ※ 이 TC는 실제로 값을 저장하는 차량이라, 마지막에 원래 값(LG U+)으로 복원하는 것까지가
      테스트 시나리오의 일부다 (CAR_PARTNER_LG_UPLUS_RESELLER_LG 전용 차량이라 다른 테스트에
      영향 없음).
    """
    page = logged_in_page
    car = CAR_PARTNER_LG_UPLUS_RESELLER_LG
    partner_field_selector = "파트너 선택"

    # 1. LG U+ -> 커넥트로 변경 + 저장
    _open_carmgmt_edit_modal(page, car)
    partner_text = _get_edit_field(page, partner_field_selector).locator(".text").first
    expect(partner_text).to_have_text("LG U+")
    reseller_text = _get_edit_field(page, "리셀러 선택").locator(".text").first
    expect(reseller_text).to_have_text("LG U+")

    _select_reseller(page, "커넥트")
    _save_edit_modal(page)

    # 저장 직후 목록에서 먼저 실제 반영을 확인한다 — 모달을 곧장 재진입하면 이전 값이 잠깐
    # 그대로 보일 수 있어서(상세 데이터가 새로 안 불려온 것으로 보임), 목록에서 갱신된 걸
    # 먼저 확인해 저장이 실제로 끝났다는 신호로 삼는다.
    reseller_col = _find_list_col_index(page, "리셀러")
    row = page.locator("table").first.locator("tbody tr").filter(has_text=car)
    expect(row.locator("td").nth(reseller_col)).to_have_text("커넥트", timeout=10_000)

    # 재진입해서 반영 확인
    _open_carmgmt_edit_modal(page, car)
    expect(_get_edit_field(page, partner_field_selector).locator(".text").first).to_have_text("LG U+")
    expect(_get_edit_field(page, "리셀러 선택").locator(".text").first).to_have_text("커넥트")

    # 2. 커넥트 -> LG U+로 다시 변경 + 저장 (원래 값으로 복원)
    _select_reseller(page, "LG U+")
    _save_edit_modal(page)

    row = page.locator("table").first.locator("tbody tr").filter(has_text=car)
    expect(row.locator("td").nth(reseller_col)).to_have_text("LG U+", timeout=10_000)

    # 재진입해서 원복 확인
    _open_carmgmt_edit_modal(page, car)
    expect(_get_edit_field(page, partner_field_selector).locator(".text").first).to_have_text("LG U+")
    expect(_get_edit_field(page, "리셀러 선택").locator(".text").first).to_have_text("LG U+")


@allure.title("TC-054 | 파트너가 커넥트인 경우 리셀러 자동선택(비활성화) 확인")
def test_TC054_vehicle_edit_reseller_auto_selected_when_partner_connect(logged_in_page: Page) -> None:
    """
    GIVEN  STAFF 웹에 로그인된 상태에서 차량관리>차량관리 화면에 진입해,
           파트너가 [커넥트]인 차량의 [수정] 버튼을 클릭하면
    WHEN   차량 수정 모달에 진입하면
    THEN   리셀러는 [커넥트]로 자동 선택되고, 리셀러 항목이 비활성화되어 있다
    """
    page = logged_in_page
    _open_carmgmt_edit_modal(page, CAR_PARTNER_CONNECT)

    reseller_field = _get_edit_field(page, "리셀러 선택")
    reseller_text = reseller_field.locator(".text").first
    expect(reseller_field).to_have_attribute("aria-disabled", "true")
    expect(reseller_text).to_have_text("커넥트")


@allure.title("TC-055 | 파트너가 LG U+인 경우 리셀러 필수 선택 확인")
def test_TC055_vehicle_edit_reseller_required_when_partner_lg_uplus(logged_in_page: Page) -> None:
    """
    GIVEN  STAFF 웹에 로그인된 상태에서 차량관리>차량관리 화면에 진입해,
           파트너가 [LG U+]인 차량의 [수정] 버튼을 클릭하면
    WHEN   리셀러 토글을 클릭하면
    THEN   [커넥트 또는 LG U+] 항목이 노출되고 선택 가능한 상태다 (필수 선택 항목)
    """
    page = logged_in_page
    _open_carmgmt_edit_modal(page, CAR_PARTNER_LG_UPLUS)

    reseller_field = _get_edit_field(page, "리셀러 선택")
    expect(reseller_field).not_to_have_attribute("aria-disabled", "true")

    reseller_field.click()
    reseller_options = reseller_field.locator('[role="option"] .text')
    expect(reseller_options).to_have_count(2)
    assert set(reseller_options.all_inner_texts()) == {"커넥트", "LG U+"}, (
        f"[FAIL] 리셀러 선택지가 [커넥트/LG U+]가 아닙니다: {reseller_options.all_inner_texts()}"
    )


@allure.title("TC-056 | 파트너가 스몰티켓인 경우 리셀러 자동선택(비활성화) 확인")
def test_TC056_vehicle_edit_reseller_auto_selected_when_partner_smallticket(logged_in_page: Page) -> None:
    """
    GIVEN  STAFF 웹에 로그인된 상태에서 차량관리>차량관리 화면에 진입해,
           파트너가 [스몰티켓]인 차량의 [수정] 버튼을 클릭하면
    WHEN   차량 수정 모달에 진입하면
    THEN   리셀러는 [스몰티켓]으로 자동 선택되고, 리셀러 항목이 비활성화되어 있다
    """
    page = logged_in_page
    _open_carmgmt_edit_modal(page, CAR_PARTNER_SMALLTICKET)

    reseller_field = _get_edit_field(page, "리셀러 선택")
    reseller_text = reseller_field.locator(".text").first
    expect(reseller_field).to_have_attribute("aria-disabled", "true")
    expect(reseller_text).to_have_text("스몰티켓")
