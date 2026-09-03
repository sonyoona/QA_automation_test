# GNB 경로: 단말기 > 모니터

import os
import re

import allure
import pytest
from playwright.sync_api import Locator, Page, expect

STAFF_URL = os.getenv("STAFF_URL")

# Allure 리포트에서 이 파일의 테스트들이 묶이는 기능 단위 (파일 상단 GNB 경로와 동일)
pytestmark = allure.feature("단말기 > 모니터  ·  test_monitor_reseller_filter.py")

MONITOR_TABS = ["통신", "구독끊김", "RT사망", "FaultINFO", "좌표누락", "지하음영", "통합"]
# pytest가 parametrize 테스트 ID를 만들 때 한글을 \uXXXX로 이스케이프해버려서,
# 터미널에서 알아보기 쉽게 영문 id를 따로 지정 (탭 이름과 순서를 그대로 맞춤)
MONITOR_TAB_IDS = ["comm", "sub_disconnect", "rt_death", "fault_info", "coord_missing", "underground_shadow", "integrated"]

# dev 환경 기준 실제 리셀러 목록 (TC 문서의 "전체/커넥트/LG U+/스몰티켓"과 다름 — dev 테스트 데이터 기준)
# "전체"는 화면에서 실제로 확인해보니 존재해서 추가함
RESELLER_OPTIONS = ["전체", "LG U+", "스몰티켓", "스몰티켓222", "인프라업뎃_파트너변경", "커넥트"]

# 자세한 설명은 docs/notes/code-notes/모니터-리셀러-필터-테스트-노트.md 참고


@allure.step("단말기>모니터 진입 후 {tab_name} 탭으로 이동")
def _goto_monitor(page: Page, tab_name: str = "통신") -> None:
    """단말기>모니터 화면으로 이동해 지정한 탭까지 전환하고, 로딩 스피너가 사라질 때까지 기다린다.
    "검색일부터 일주일 전까지" 날짜 필터가 있는 탭이면 오늘 날짜로 맞추고 다시 조회한다
    (기본값이 최근 데이터를 놓치는 범위라 그대로 두면 실제로 있는 데이터도 0건으로 보임)."""
    page.goto(STAFF_URL)
    page.locator("a").filter(has_text=re.compile(r"^단말기$")).click()
    page.get_by_role("link", name="모니터").click()
    page.locator("a").filter(has_text=re.compile(f"^{re.escape(tab_name)}$")).click()
    page.locator(".spinner").first.wait_for(state="hidden", timeout=60_000)

    date_column = page.locator("div.column", has_text="검색일부터")
    if date_column.count() > 0:
        date_column.locator("input, [role=combobox]").first.click()
        page.get_by_text("오늘", exact=True).click()
        page.get_by_role("button", name="조회").click()
        page.locator(".spinner").first.wait_for(state="hidden", timeout=60_000)


@allure.step("리셀러 드롭다운 열기")
def _open_reseller_dropdown(page: Page) -> Locator:
    """"리셀러" 콤보박스를 열고 그 Locator를 돌려준다."""
    reseller_column = page.locator("div.column", has_text="리셀러")
    reseller_dropdown = reseller_column.get_by_role("combobox")
    reseller_dropdown.click()
    return reseller_dropdown


@allure.step("헤더에서 '리셀러' 컬럼 위치 찾기")
def _find_reseller_col_index(page: Page) -> int:
    """현재 테이블에서 "리셀러" 컬럼의 위치(0-based)를 헤더에서 계산해 돌려준다. 탭마다 위치가 달라 매번 계산한다."""
    header_cells = page.locator("table").first.locator("thead tr").first.locator("th")
    count = header_cells.count()
    leaf_index = 0
    for i in range(count):
        cell = header_cells.nth(i)
        if cell.inner_text().strip() == "리셀러":
            return leaf_index
        span = cell.get_attribute("colspan")
        leaf_index += int(span) if span else 1
    raise AssertionError("헤더에서 '리셀러' 컬럼을 찾지 못했습니다")


def _get_total_pages(page: Page) -> int:
    """현재 조회 결과의 전체 페이지 수. 페이지네이션이 없으면(=1페이지) 1을 돌려준다."""
    pagination = page.locator(".pagination")
    if pagination.count() == 0:
        return 1
    last_item = pagination.first.locator('a[type="lastItem"]')
    if last_item.count() == 0:
        return 1
    return int(last_item.get_attribute("value"))


def _get_real_row_count(page: Page) -> int:
    """실제 데이터 행 개수. "조회 결과가 없습니다" 같은 안내 문구 행(colspan 처리됨)은 0으로 취급한다."""
    rows = page.locator("table").first.locator("tbody tr")
    count = rows.count()
    if count == 1 and rows.first.locator("td").first.get_attribute("colspan"):
        return 0
    return count


def _get_sample_pages(total_pages: int) -> list[int]:
    """전체 페이지 중 첫 페이지·중간 페이지·마지막 페이지를 표본으로 뽑는다.
    페이지 수가 적으면(1~2개) 자동으로 중복 없이 있는 것만 남는다."""
    return sorted({1, total_pages, (1 + total_pages) // 2})


@allure.step("{target_page}페이지로 이동")
def _go_to_page(page: Page, target_page: int) -> None:
    """조회 결과에서 target_page 번째 페이지로 이동한다(1부터 시작). 페이지가 1개뿐이면 아무것도 안 하고 끝난다.
    이동 시도 후 실제로 target_page에 도착했는지 마지막에 확인한다 — 확인 안 하면, 이동이 조용히
    실패해도(예: next 버튼이 비활성 상태) 엉뚱한 페이지를 검사하고 지나칠 수 있다."""
    pagination = page.locator(".pagination")
    if pagination.count() == 0:
        return

    pagination = pagination.first
    direct_link = pagination.locator(f'a[type="pageItem"][value="{target_page}"]')
    if direct_link.count() > 0:
        direct_link.click()
        page.locator(".spinner").first.wait_for(state="hidden", timeout=60_000)
    else:
        next_button = pagination.locator('a[type="nextItem"]')
        for _ in range(target_page + 5):  # 무한루프 방지용 안전장치
            active_value = int(pagination.locator('a[type="pageItem"].active').get_attribute("value"))
            if active_value >= target_page:
                break
            next_button.click()
            page.locator(".spinner").first.wait_for(state="hidden", timeout=60_000)

    active_value = int(pagination.locator('a[type="pageItem"].active').get_attribute("value"))
    assert active_value == target_page, (
        f"[FAIL] {target_page}페이지로 이동하지 못했습니다 (현재 {active_value}페이지)"
    )


@allure.step("[마지막] 버튼으로 마지막 페이지 이동")
def _go_to_last_page(page: Page) -> None:
    """[마지막] 버튼을 눌러 실제 마지막 페이지로 이동한다.

    이 화면은 실시간으로 갱신되는 모니터링 데이터라, _get_total_pages()로 미리 계산해둔
    총 페이지 수가 그 뒤(특히 통합 탭처럼 느린 탭에서 여러 페이지를 거쳐가는 사이)
    실제 값과 달라질 수 있다. 그래서 미리 계산해둔 페이지 번호로 이동을 시도하고
    "그 번호에 도착했는지"를 확인하는 대신, [마지막] 버튼이 실제로 데려다주는 곳을
    그대로 마지막 페이지로 받아들인다 — 그 순간의 진짜 마지막 페이지가 어디든, 그곳이
    검증해야 할 표본이라는 뜻이다."""
    pagination = page.locator(".pagination")
    if pagination.count() == 0:
        return

    last_link = pagination.first.locator('a[type="lastItem"]')
    last_link.click()
    page.locator(".spinner").first.wait_for(state="hidden", timeout=60_000)


@allure.step("현재 페이지 전체 행의 리셀러가 {target_reseller}인지 확인")
def _assert_all_rows_have_reseller(page: Page, col_index: int, target_reseller: str) -> None:
    """현재 화면(한 페이지)의 모든 행에 대해 리셀러 컬럼 값이 target_reseller와 정확히 같은지 전수 확인한다."""
    rows = page.locator("table").first.locator("tbody tr")
    row_count = rows.count()
    for i in range(row_count):
        cell_text = rows.nth(i).locator("td").nth(col_index).inner_text()
        assert cell_text == target_reseller, (
            f"[FAIL] 리셀러가 {target_reseller!r}가 아닌 행 발견: {cell_text!r} (행 {i})"
        )


@allure.title("TC-084 | 리셀러 필터 노출 확인 ({tab_name} 탭)")
@allure.label("testcase", "TC-084")
@pytest.mark.parametrize("tab_name", MONITOR_TABS, ids=MONITOR_TAB_IDS)
def test_TC084_monitor_reseller_filter_visible(logged_in_page: Page, tab_name: str) -> None:
    """
    GIVEN  STAFF 웹에 로그인된 상태에서 단말기>모니터 화면에 진입해, 검증 대상 탭으로 이동하면
    WHEN   화면을 확인하면
    THEN   파트너 필터 대신 리셀러 필터가 노출된다 (7개 탭 모두 동일하게 적용되어야 함)
    """
    page = logged_in_page
    _goto_monitor(page, tab_name)

    reseller_filter = page.locator("label").filter(has_text="리셀러")
    partner_filter = page.locator("label").filter(has_text="파트너")

    expect(reseller_filter).to_be_visible()
    expect(partner_filter).not_to_be_visible()


@allure.title("TC-085 | 리셀러 필터 선택 항목 확인 ({tab_name} 탭)")
@allure.label("testcase", "TC-085")
@pytest.mark.parametrize("tab_name", MONITOR_TABS, ids=MONITOR_TAB_IDS)
def test_TC085_monitor_reseller_filter_options(logged_in_page: Page, tab_name: str) -> None:
    """
    GIVEN  STAFF 웹에 로그인된 상태에서 단말기>모니터 화면에 진입해, 검증 대상 탭으로 이동하면
    WHEN   리셀러 필터를 클릭하면
    THEN   전체, LG U+, 스몰티켓, 스몰티켓222, 인프라업뎃_파트너변경, 커넥트 항목이 노출된다
           (7개 탭 모두 동일하게 적용되어야 함)
    """
    page = logged_in_page
    _goto_monitor(page, tab_name)

    reseller_dropdown = _open_reseller_dropdown(page)

    for option in RESELLER_OPTIONS:
        expect(reseller_dropdown.get_by_role("option", name=option, exact=True)).to_be_visible()


@allure.title("TC-086 | 리셀러 필터 조회 결과 확인 ({tab_name} 탭)")
@allure.label("testcase", "TC-086")
@pytest.mark.parametrize("tab_name", MONITOR_TABS, ids=MONITOR_TAB_IDS)
def test_TC086_monitor_reseller_filter_query_result(logged_in_page: Page, tab_name: str) -> None:
    """
    GIVEN  STAFF 웹에 로그인된 상태에서 단말기>모니터 화면에 진입해, 검증 대상 탭으로 이동하면
           (탭에 데이터가 아예 없으면 검증할 게 없으므로 skip)
    WHEN   리셀러 필터에서 특정 리셀러(커넥트)를 선택하고 [조회]를 클릭하면
    THEN   표본으로 뽑은 첫/중간/마지막 페이지의 모든 행이 그 리셀러(커넥트) 값을 가진다
           (컬럼 위치는 탭마다 달라 매번 새로 계산)
    """
    page = logged_in_page
    _goto_monitor(page, tab_name)

    target_reseller = "커넥트"

    if _get_real_row_count(page) == 0:
        pytest.skip(f"{tab_name} 탭에 조회할 데이터가 아예 없어 리셀러 필터를 검증할 수 없음")

    col_index = _find_reseller_col_index(page)

    reseller_dropdown = _open_reseller_dropdown(page)
    reseller_dropdown.get_by_role("option", name=target_reseller, exact=True).click()

    page.get_by_role("button", name="조회").click()
    page.locator(".spinner").first.wait_for(state="hidden", timeout=60_000)

    filtered_row_count = _get_real_row_count(page)
    assert filtered_row_count > 0, "조회 결과가 0건입니다 — 필터가 제대로 적용됐는지 먼저 확인하세요"

    total_pages = _get_total_pages(page)
    sample_pages = _get_sample_pages(total_pages)

    for target_page in sample_pages:
        if target_page == total_pages:
            _go_to_last_page(page)
        else:
            _go_to_page(page, target_page)
        _assert_all_rows_have_reseller(page, col_index, target_reseller)


@allure.title("TC-087 | 컬럼 구성 확인 ({tab_name} 탭)")
@allure.label("testcase", "TC-087")
@pytest.mark.parametrize("tab_name", MONITOR_TABS, ids=MONITOR_TAB_IDS)
def test_TC087_monitor_column_composition(logged_in_page: Page, tab_name: str) -> None:
    """
    GIVEN  STAFF 웹에 로그인된 상태에서 단말기>모니터 화면에 진입해, 검증 대상 탭으로 이동하면
    WHEN   테이블 헤더를 확인하면
    THEN   "파트너" 컬럼은 제거되고 "리셀러" 컬럼이 노출된다 (7개 탭 모두 동일하게 적용되어야 함)
    """
    page = logged_in_page
    _goto_monitor(page, tab_name)

    header_texts = page.locator("table").first.locator("thead th").all_inner_texts()

    assert "리셀러" in header_texts, f"[FAIL] '리셀러' 컬럼이 헤더에 없습니다: {header_texts}"
    assert "파트너" not in header_texts, f"[FAIL] '파트너' 컬럼이 아직 남아있습니다: {header_texts}"
