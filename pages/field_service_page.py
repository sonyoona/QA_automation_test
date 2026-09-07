# GNB 경로: 차량관리 > 현장 서비스
#
# 이 화면은 프론트에서 data-testid 를 붙여둔 시범 페이지라, 셀렉터를 전부 testid 로 잡는다.
# testid 문자열이 적히는 곳은 이 파일 하나뿐이다 - 테스트 파일에는 testid 가 나오면 안 된다.
# (시범 단계라 이름이 바뀔 수 있어서, 바뀌면 여기만 고치면 되게 하려는 것)
#
# 자세한 배경은 docs/notes/code-notes/현장서비스-테스트-노트.md 참고

import os
import re

import allure
from playwright.sync_api import Locator, Page, expect

STAFF_URL = os.getenv("STAFF_URL")


class FieldServicePage:
    """차량관리 > 현장 서비스 - 현장서비스 현황 탭."""

    def __init__(self, page: Page) -> None:
        self.page = page

    # ------------------------------------------------------------------
    # 화면 요소 - testid 가 적히는 유일한 곳
    # ------------------------------------------------------------------

    @property
    def root(self) -> Locator:
        """화면 전체 컨테이너. 화면에 도착했는지 확인할 때 쓴다."""
        return self.page.get_by_test_id("fs-page__root")

    # ---- 상태 탭 ----

    @property
    def status_tabs(self) -> Locator:
        return self.page.get_by_test_id("fs-status-tabs__tabs")

    @property
    def new_service_button(self) -> Locator:
        return self.page.get_by_test_id("fs-status-tabs__new-service-btn")

    # ---- 조회 필터 ----

    @property
    def reseller_select(self) -> Locator:
        return self.page.get_by_test_id("fs-filter__reseller-select")

    @property
    def company_select(self) -> Locator:
        return self.page.get_by_test_id("fs-filter__company-select")

    @property
    def service_type_select(self) -> Locator:
        return self.page.get_by_test_id("fs-filter__service-type-select")

    @property
    def plate_input(self) -> Locator:
        return self.page.get_by_test_id("fs-filter__plate-input")

    @property
    def device_sn_input(self) -> Locator:
        return self.page.get_by_test_id("fs-filter__device-sn-input")

    @property
    def assignee_input(self) -> Locator:
        return self.page.get_by_test_id("fs-filter__assignee-input")

    @property
    def requester_input(self) -> Locator:
        return self.page.get_by_test_id("fs-filter__requester-input")

    @property
    def completed_from_date(self) -> Locator:
        return self.page.get_by_test_id("fs-filter__completed-from-date")

    @property
    def completed_to_date(self) -> Locator:
        return self.page.get_by_test_id("fs-filter__completed-to-date")

    @property
    def gps_shadow_checkbox(self) -> Locator:
        return self.page.get_by_test_id("fs-filter__gps-shadow-checkbox")

    @property
    def temp_only_checkbox(self) -> Locator:
        return self.page.get_by_test_id("fs-filter__temp-only-checkbox")

    @property
    def completed_only_checkbox(self) -> Locator:
        return self.page.get_by_test_id("fs-filter__completed-only-checkbox")

    @property
    def search_button(self) -> Locator:
        return self.page.get_by_test_id("fs-filter__search-btn")

    @property
    def excel_download_button(self) -> Locator:
        return self.page.get_by_test_id("fs-dashboard__excel-download-btn")

    # ---- 결과 테이블 ----

    # 결과가 0 건일 때 행 대신 나오는 안내 문구. 이 자리에는 testid 가 없어서 텍스트로 본다
    # (2026-09-07 실측 - 빈 결과에서는 tbody 자체가 그려지지 않는다).
    EMPTY_TEXT = "데이터가 없습니다"

    @property
    def table_root(self) -> Locator:
        return self.page.get_by_test_id("fs-table__root")

    @property
    def rows(self) -> Locator:
        """결과 행 전체. CSS 의 `^=` 는 "이 문자열로 시작하는" 이라는 뜻."""
        return self.page.locator('[data-testid^="fs-table__row--"]')

    def row(self, service_id: str) -> Locator:
        """PK 로 특정 행 하나를 잡는다 - 화면 텍스트가 겹쳐도 안전하다."""
        return self.page.get_by_test_id(f"fs-table__row--{service_id}")

    def row_action_button(self, service_id: str) -> Locator:
        return self.page.get_by_test_id(f"fs-table__action-btn--{service_id}")

    # ------------------------------------------------------------------
    # 동작
    # ------------------------------------------------------------------

    @allure.step("차량관리 > 현장 서비스 진입")
    def goto(self) -> None:
        """GNB 에서 차량관리 > 현장 서비스 순으로 눌러 화면에 진입한다.

        상위 메뉴 "차량관리" 를 `^...$` 로 고정하는 이유 - 하위에도 이름이 비슷한 항목이
        있어서 부분 일치로 잡으면 엉뚱한 걸 누를 수 있다 (test_monitor_reseller_filter.py 의
        `_goto_monitor` 와 같은 이유).

        하위 메뉴는 화면 실측 기준 "현장 서비스" 다 - 2026-09-07 에 "현장 서비스 관리" 로
        적혀 있어 5건 전부 진입 단계에서 30초 타임아웃(ERROR)이 났다. `exact=True` 는
        나중에 "현장 서비스 xxx" 같은 항목이 생겼을 때 부분 일치로 둘 다 잡혀
        strict mode 위반이 나는 것을 막는다.
        """
        self.page.goto(STAFF_URL)
        self.page.locator("a").filter(has_text=re.compile(r"^차량관리$")).click()
        self.page.get_by_role("link", name="현장 서비스", exact=True).click()
        self.wait_loaded()

    @allure.step("화면 로딩 완료 대기")
    def wait_loaded(self) -> None:
        """화면 도착 + 결과 목록이 다 그려질 때까지 기다린다.

        테이블 껍데기(`fs-table__root`)가 보이는 것과 결과가 채워지는 것은 다른 시점이다 -
        2026-09-07 실측으로 껍데기가 보인 뒤 0.14 초 더 지나서야 첫 행이 붙었고, 그 사이에
        읽은 TC 가 0 건을 보고 실패했다. 스피너 testid 가 없어서 결과 자체를 기다린다.

        나중에 스피너 testid 가 생기면 여기 한 줄만 추가하면 모든 TC 에 반영된다.
        """
        expect(self.root).to_be_visible()
        expect(self.table_root).to_be_visible()
        self.wait_table_settled()

    @allure.step("결과 목록이 안정될 때까지 대기")
    def wait_table_settled(self, timeout_ms: int = 30_000) -> None:
        """결과 목록이 "갱신 끝" 상태가 될 때까지 기다린다.

        행이 하나라도 생기는 것만 보면 안 되는 이유가 둘이다.
        - 빈 결과가 정상인 경우(조건에 맞는 건이 없는 검색)에는 행이 영원히 안 생긴다.
          이 화면은 그때 행 대신 EMPTY_TEXT 안내를 그리므로 그것도 완료로 인정한다.
        - 검색으로 목록을 다시 그릴 때는 옛 행이 남아 있는 순간이 있어서, 행 개수만 보면
          갱신 전 목록을 읽고 지나간다.

        그래서 "행 PK 목록(또는 빈 상태)이 연속 2회 같을 때"만 끝난 것으로 본다.
        `polling` 간격으로 두 번 재는 것이라 최소 그만큼은 걸리지만, 조건이 되면 즉시
        빠져나오므로 고정 대기와 달리 낭비가 쌓이지 않는다.

        한계 - 서버 응답이 polling 간격 두 번보다 느리면 옛 목록을 두 번 연속으로 읽어
        "안정됐다" 로 볼 수 있다. 이 대기는 그 창을 좁힐 뿐 없애지는 못한다. 갱신 전후를
        구분해야 하는 TC 는 여기에 기대지 말고 본문에서 직접 대조한다.
        """
        # 직전 호출이 남긴 값과 대조해 첫 샘플에 곧바로 통과해 버리는 것을 막는다
        # (화면 이동은 페이지가 새로 뜨지만 검색은 그렇지 않다).
        self.page.evaluate("() => { window.__fsTableSnapshot = undefined; }")
        self.page.wait_for_function(
            """(emptyText) => {
                const ids = [...document.querySelectorAll('[data-testid^="fs-table__row--"]')]
                    .map(e => e.getAttribute('data-testid')).join(',');
                const root = document.querySelector('[data-testid="fs-table__root"]');
                const isEmpty = !!(root && root.innerText.includes(emptyText));
                // 행도 없고 빈 상태 안내도 없으면 아직 그리는 중이다
                if (!ids && !isEmpty) { window.__fsTableSnapshot = undefined; return false; }
                const snapshot = isEmpty ? '__EMPTY__' : ids;
                const settled = window.__fsTableSnapshot === snapshot;
                window.__fsTableSnapshot = snapshot;
                return settled;
            }""",
            arg=self.EMPTY_TEXT,
            polling=300,
            timeout=timeout_ms,
        )

    def is_empty_result(self) -> bool:
        """결과가 0 건이라 "데이터가 없습니다" 안내가 떠 있는 상태인가.

        행이 0 개인 것만으로 판정하면 안 된다 - 아직 그리는 중일 때도 0 개다.
        """
        return self.EMPTY_TEXT in self.table_root.inner_text()

    @allure.step("차량번호 {plate} 로 검색")
    def search_by_plate(self, plate: str) -> None:
        self.plate_input.fill(plate)
        self.search()

    @allure.step("조회 버튼 클릭")
    def search(self) -> None:
        self.search_button.click()
        self.wait_loaded()

    def row_ids(self) -> list[str]:
        """현재 화면에 보이는 행들의 PK 목록. 예: ['10679', '10677', ...]

        표시 텍스트가 아니라 PK 로 비교해야 "같은 날 같은 업체 건이라 글자가 똑같은"
        경우에도 행을 정확히 구분할 수 있다.
        """
        return [
            el.get_attribute("data-testid").split("--")[1]
            for el in self.rows.all()
        ]

    @allure.step("신규 서비스 신청 팝업 열기")
    def open_new_service_popup(self) -> "NewServicePopup":
        self.new_service_button.click()
        popup = NewServicePopup(self.page)
        expect(popup.dialog).to_be_visible()
        return popup


class NewServicePopup:
    """신규 서비스 신청 팝업.

    팝업은 페이지가 아니라 "현장서비스 현황 탭 안에서 열리는 것" 이라 별도 클래스로 둔다.

    ★ submit_button([신청 완료])은 누르지 않는다 - dev 에 실제 신청 건이 생성된다.
      유효성 검사에서 막힐 거라고 가정하고 눌렀다가 안 막혀서 데이터가 생긴 사례가 있다.
      검증은 "필드가 있는가 / 버튼이 활성화됐는가" 까지만 한다.
    """

    def __init__(self, page: Page) -> None:
        self.page = page

    @property
    def dialog(self) -> Locator:
        return self.page.get_by_test_id("fs-new__dialog")

    # ---- 서비스 정보 ----

    @property
    def service_type_select(self) -> Locator:
        return self.dialog.get_by_test_id("fs-new__svc-type-select")

    @property
    def work_date_field(self) -> Locator:
        return self.dialog.get_by_test_id("fs-new__work-date-field")

    @property
    def digital_key_select(self) -> Locator:
        return self.dialog.get_by_test_id("fs-new__digital-key-select")

    @property
    def ignition_lock_select(self) -> Locator:
        return self.dialog.get_by_test_id("fs-new__ignition-lock-select")

    @property
    def address_input(self) -> Locator:
        return self.dialog.get_by_test_id("fs-new__address-input")

    @property
    def address_search_button(self) -> Locator:
        return self.dialog.get_by_test_id("fs-new__address-search-button")

    @property
    def contact_input(self) -> Locator:
        return self.dialog.get_by_test_id("fs-new__contact-input")

    @property
    def installer_walk_in_checkbox(self) -> Locator:
        return self.dialog.get_by_test_id("fs-new__installer-walk-in-checkbox")

    @property
    def assignee_trigger(self) -> Locator:
        return self.dialog.get_by_test_id("fs-new__assignee-trigger")

    @property
    def memo_textarea(self) -> Locator:
        return self.dialog.get_by_test_id("fs-new__memo-textarea")

    # ---- 차량 선택 ----

    @property
    def temp_reg_checkbox(self) -> Locator:
        return self.dialog.get_by_test_id("fs-new__temp-reg-checkbox")

    @property
    def company_select(self) -> Locator:
        return self.dialog.get_by_test_id("fs-new__company-select")

    @property
    def branch_select(self) -> Locator:
        return self.dialog.get_by_test_id("fs-new__branch-select")

    @property
    def vehicle_select(self) -> Locator:
        return self.dialog.get_by_test_id("fs-new__vehicle-select")

    @property
    def add_to_list_button(self) -> Locator:
        """[목록에 추가] - 팝업 안에서만 일어나는 동작이라 눌러도 안전하다."""
        return self.dialog.get_by_test_id("fs-new__add-to-list-button")

    @property
    def request_rows(self) -> Locator:
        """담긴 신청 목록의 행들.

        TODO: 목록에 1건 담은 뒤 실제 testid 를 확인할 것 (아직 미실측).
        """
        return self.dialog.locator('[data-testid^="fs-new__request-list-row--"]')

    # ---- 푸터 ----

    @property
    def close_button(self) -> Locator:
        return self.dialog.get_by_test_id("fs-new__close-button")

    @property
    def cancel_button(self) -> Locator:
        return self.dialog.get_by_test_id("fs-new__cancel-button")

    @property
    def submit_button(self) -> Locator:
        """[신청 완료] - ★ 존재/활성 상태 확인용. click() 하지 말 것."""
        return self.dialog.get_by_test_id("fs-new__submit-button")

    @allure.step("팝업 닫기")
    def close(self) -> None:
        self.close_button.click()
        expect(self.dialog).to_be_hidden()
