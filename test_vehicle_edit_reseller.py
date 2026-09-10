# GNB 경로: 차량관리 > 차량관리 (수정)

import os
import re
from typing import Callable, Generator

import allure
import pytest
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


def _read_settled(field_text: Locator) -> str:
    """모달이 열린 직후엔 값이 비동기로 채워지는 도중이라, 곧바로 `inner_text()`로 읽으면
    플레이스홀더("선택")를 실제 값으로 착각할 수 있다(실측으로 확인 — 원복 대상 값을 "선택"으로
    잘못 캡처했다). 값이 "선택"에서 벗어날 때까지 기다린 뒤 읽는다.

    같은 모달을 쓰는 test_vehicle_company_transfer.py도 이 함수를 import해서 쓴다 —
    같은 것을 읽는 방법이 파일마다 갈리면 한쪽만 고쳐지고 조용히 어긋난다."""
    expect(field_text).not_to_have_text("선택", timeout=10_000)
    return field_text.inner_text()


@allure.step("차량 {car_number} 의 리셀러를 {original_reseller} 로 원복")
def _restore_reseller(page: Page, car_number: str, original_reseller: str) -> None:
    """차량의 리셀러를 원래 값으로 되돌린다. 이미 원래 값이면 아무것도 하지 않는다.

    `_open_carmgmt_edit_modal`이 `page.goto()`로 시작하므로, 테스트가 모달이나 알럿을 열어둔
    채 깨졌어도 그 상태를 신경 쓰지 않고 부를 수 있다.

    이미 원래 값이면 저장을 누르지 않는다 — 되돌릴 게 없는데 [수정]을 누르는 것 자체가
    규칙이 막는 동작이다. 되돌린 뒤에는 목록에서 실제로 반영됐는지 확인한다. "예외가 안 났다"는
    "되돌렸다"가 아니기 때문이다(이관 TC에서 이걸로 한 번 속았다).
    """
    _open_carmgmt_edit_modal(page, car_number)
    reseller_text = _get_edit_field(page, "리셀러 선택").locator(".text").first
    if _read_settled(reseller_text) == original_reseller:
        return

    _select_reseller(page, original_reseller)
    _save_edit_modal(page)

    reseller_col = _find_list_col_index(page, "리셀러")
    row = page.locator("table").first.locator("tbody tr").filter(has_text=car_number)
    expect(row.locator("td").nth(reseller_col)).to_have_text(original_reseller, timeout=10_000)


@pytest.fixture
def reseller_guard(logged_in_page: Page) -> Generator[Callable[[str, str], None], None, None]:
    """리셀러 값을 바꾸는 TC가 바꾼 값을, **테스트가 어떻게 끝나든** 원래대로 되돌린다.

    전에는 원복이 테스트 본문 마지막 줄에 있었다. 그러면 중간에서 실패했을 때 그 줄에 도달하지
    못해 **값이 바뀐 채로 남는다** — 다음 실행은 다른 전제로 시작하게 되고, 그 뒤의 실패는 원인
    찾기가 어렵다. 이관 TC의 `company_guard`와 같은 형태다.

    쓰는 법 — 원래 값을 읽은 직후에 등록해 둔다. 그 다음부터는 무슨 일이 나도 teardown이 책임진다.

    원복에 실패하면 **예외를 삼키지 않는다** — teardown에서 그대로 터져 pytest가 그 테스트를
    ERROR로 표시한다. 정리 실패를 조용히 넘기면 "통과했는데 데이터는 바뀐 채"가 된다.
    """
    page = logged_in_page
    original: dict[str, str] = {}

    def guard(car_number: str, original_reseller: str) -> None:
        original[car_number] = original_reseller

    yield guard

    for car_number, original_reseller in original.items():
        _restore_reseller(page, car_number, original_reseller)


@allure.title("TC-051 | 차량 수정 모달 파트너 항목(수정 불가) 노출 확인")
@allure.label("testcase", "TC-051")
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
@allure.label("testcase", "TC-052")
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


@pytest.mark.mutating
@allure.title("TC-053 | 리셀러 값 변경(LG U+↔커넥트) 및 저장 반영 확인")
@allure.label("testcase", "TC-053")
def test_TC053_vehicle_edit_reseller_change_and_revert_when_partner_lg_uplus(
    logged_in_page: Page, reseller_guard: Callable[[str, str], None]
) -> None:
    """
    GIVEN  STAFF 웹에 로그인된 상태에서 차량관리>차량관리 화면에 진입해,
           파트너와 리셀러가 모두 [LG U+]인 차량의 [수정] 버튼을 클릭하면
    WHEN   1. 리셀러를 LG U+에서 커넥트로 변경 후 저장하고
           2. 차량 수정 화면에 재진입해 리셀러를 커넥트에서 LG U+로 다시 변경 후 저장하면
    THEN   각 저장 직후 재진입했을 때 리셀러 값이 정확히 반영되어 있고,
           그 과정 내내 파트너는 LG U+로 유지된다

    ★ 이 파일에서 **유일하게 [수정] 저장을 실제로 실행하는 TC** 다 (`@pytest.mark.mutating`).
      그래서 `--allow-mutating` 없이는 돌지 않고, 허용된 dev 접속처가 아니면 막힌다
      (conftest.py 의 `_mutating_gate`).

    본문 2단계(커넥트 -> LG U+)는 정리가 아니라 **검증 시나리오의 일부**다 — 양방향 변경이
    다 반영되는지를 보는 것이라 지우면 안 된다. `reseller_guard` 는 그 위에 덧대는 안전망이라,
    1단계 저장 뒤 어디서 깨지든 값을 되돌린다(이미 원래 값이면 아무것도 하지 않는다).

    전용 차량(CAR_PARTNER_LG_UPLUS_RESELLER_LG)만 쓰므로 다른 테스트에 영향이 없다.
    """
    page = logged_in_page
    car = CAR_PARTNER_LG_UPLUS_RESELLER_LG
    partner_field_selector = "파트너 선택"

    # 1. LG U+ -> 커넥트로 변경 + 저장
    _open_carmgmt_edit_modal(page, car)
    partner_text = _get_edit_field(page, partner_field_selector).locator(".text").first
    expect(partner_text).to_have_text("LG U+")
    reseller_text = _get_edit_field(page, "리셀러 선택").locator(".text").first
    # 앞선 실행이 원복에 실패해 커넥트로 남아 있으면 여기서 즉시 실패한다 — 전제가 깨진 채로
    # 진행하면 "LG U+ -> 커넥트" 가 제자리 저장이 되어 검증이 공허해진다.
    expect(reseller_text).to_have_text("LG U+")
    reseller_guard(car, _read_settled(reseller_text))

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
@allure.label("testcase", "TC-054")
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
@allure.label("testcase", "TC-055")
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
@allure.label("testcase", "TC-056")
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
