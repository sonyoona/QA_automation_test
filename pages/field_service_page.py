# GNB 경로: 차량관리 > 현장 서비스
#
# 프론트가 data-testid 를 붙여둔 시범 페이지라 셀렉터를 전부 testid 로 잡는다.
# testid 문자열이 적히는 곳은 이 파일 하나뿐 - 테스트 파일에는 나오면 안 된다.
# 배경: docs/notes/code-notes/현장서비스-테스트-노트.md "이 화면만 다른 점"

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

    def status_tab(self, name: str) -> Locator:
        """상태 탭 하나. 2026-09-08 실측 - `button[role="tab"]` 6개, testid 는 없다.

        **시작 앵커 정규식이 필수다** - `완료` 로 찾으면 `배정완료` 까지 잡힌다.
        탭 텍스트에는 건수 배지가 붙어 있어서(`완료 226`) `exact=True` 는 쓸 수 없고,
        건수를 이름에 넣으면 데이터가 바뀔 때마다 깨진다.
        """
        return self.status_tabs.get_by_role(
            "tab", name=re.compile(rf"^{re.escape(name)}")
        )

    def status_tab_count(self, name: str) -> int:
        """상태 탭 배지의 건수. 텍스트가 `완료 226` 형태라 숫자만 뽑는다.

        "행이 0건" 일 때 **그 상태에 건이 없는 것**과 **못 읽은 것**을 가르는 근거다.
        배지가 0 이면 없는 게 맞고, 배지가 있는데 행이 0 이면 읽기가 실패한 것이다.
        """
        text = self.status_tab(name).inner_text()
        match = re.search(r"(\d[\d,]*)", text)
        assert match, f"[FAIL] [{name}] 탭에서 건수를 읽지 못했다: {text!r}"
        return int(match.group(1).replace(",", ""))

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

    def column_index(self, header: str) -> int:
        """헤더 텍스트로 컬럼 위치를 찾는다. 인덱스를 박으면 컬럼이 하나 끼워질 때
        **예외가 아니라 빈 문자열**이 읽혀 조용히 지나간다.

        정렬 헤더는 아이콘 텍스트가 붙어 오므로 첫 줄만 쓴다 (2026-09-08 실측 - 헤더 17개).
        """
        headers = [
            text.split("\n")[0].strip()
            for text in self.table_root.locator("th").all_inner_texts()
        ]
        assert header in headers, f"[FAIL] 표 헤더에 {header!r} 이 없다: {headers}"
        return headers.index(header)

    def row_statuses(self) -> dict[str, str]:
        """행 PK -> 상태 컬럼 값.

        상태를 읽는 방법을 여기 하나만 두는 이유는 `row_ids()` 와 같다 - TC 마다 다른
        방법으로 읽으면 그중 하나가 위양성이 되어도 셀렉터 이름은 멀쩡해 아무도 못 잡는다.
        """
        index = self.column_index("상태")
        return {
            service_id: self.row(service_id).locator("td").nth(index).inner_text().strip()
            for service_id in self.row_ids()
        }

    def row_action_button(self, service_id: str) -> Locator:
        """행의 액션 컬럼에 있는 [수정] 버튼 (2026-09-08 라벨 실측).

        ★ 누르지 않는다 - 수정 화면으로 들어가는 입구라, 노출·라벨 확인까지만 쓴다.
        """
        return self.page.get_by_test_id(f"fs-table__action-btn--{service_id}")

    # ------------------------------------------------------------------
    # 동작
    # ------------------------------------------------------------------

    @allure.step("차량관리 > 현장 서비스 진입")
    def goto(self) -> None:
        """GNB 에서 차량관리 > 현장 서비스 순으로 눌러 화면에 진입한다.

        상위 메뉴를 `^...$` 로, 하위를 `exact=True` 로 고정한다 - 이름이 비슷한 항목에
        부분 일치로 걸리는 것을 막는다. 하위 메뉴명이 "현장 서비스 관리" 가 아니라는
        실측 경위: docs/notes/code-notes/현장서비스-테스트-노트.md "겪은 문제 ①"
        """
        self.page.goto(STAFF_URL)
        self.page.locator("a").filter(has_text=re.compile(r"^차량관리$")).click()
        self.page.get_by_role("link", name="현장 서비스", exact=True).click()
        self.wait_loaded()

    @allure.step("화면 로딩 완료 대기")
    def wait_loaded(self) -> None:
        """화면 도착 + 결과 목록이 다 그려질 때까지 기다린다.

        테이블 껍데기가 보이는 것과 결과가 채워지는 것은 다른 시점이다 (2026-09-07 실측
        0.14초). 스피너 testid 가 없어 결과 자체를 기다린다 - 생기면 여기 한 줄만 고친다.
        경위: docs/notes/code-notes/현장서비스-테스트-노트.md "겪은 문제 ②"
        """
        expect(self.root).to_be_visible()
        expect(self.table_root).to_be_visible()
        self.wait_status_counts()
        self.wait_table_settled()

    @allure.step("상태 탭 건수 배지가 채워질 때까지 대기")
    def wait_status_counts(self, timeout_ms: int = 15_000) -> None:
        """상태 탭 배지(`전체 591`)에 숫자가 들어올 때까지 기다린다.

        배지는 서버 응답이 와야 채워지므로 **데이터가 도착했다는 유일한 신호**다. 안 기다리면
        미도착 화면을 "결과 0건" 으로 오독한다. 끝내 안 오면 여기서 실패하는 게 맞다.
        591건을 0건으로 읽은 경위: docs/notes/code-notes/현장서비스-테스트-노트.md "그 한계가 정확히 그대로 터졌다"
        """
        try:
            self.page.wait_for_function(
                """(selector) => {
                    const el = document.querySelector(selector);
                    return !!el && /\\d/.test(el.innerText);
                }""",
                arg='[data-testid="fs-status-tabs__tabs"]',
                polling=300,
                timeout=timeout_ms,
            )
        except Exception as e:
            raise AssertionError(
                "[FAIL] 상태 탭 건수 배지가 끝내 채워지지 않았다 - 데이터가 도착하지 않은 "
                "화면이라 결과를 읽을 수 없다 (세션 끊김·API 실패 의심)\n"
                f"        {self.state_summary()}"
            ) from e

    @allure.step("결과 목록이 안정될 때까지 대기")
    def wait_table_settled(self, timeout_ms: int = 30_000, allow_empty: bool = True) -> None:
        """결과 목록이 "갱신 끝" 상태가 될 때까지 기다린다.

        "행 PK 목록(또는 빈 상태)이 **연속 2회 같을 때**" 만 끝난 것으로 본다. 행이 생기는
        것만 보면 빈 결과가 정상인 검색에서 영원히 못 빠져나오고, 개수만 보면 갱신 전 옛
        목록을 읽는다.

        ★ `allow_empty=False` 는 "여기서 빈 상태는 결과가 아니라 아직 안 온 것" 이라고 아는
          자리에서만 쓴다. 연속 2회 규칙은 옛 목록에 속는 것은 막아도 **빈 상태에 속는 것은
          못 막는다.** 이 대기의 한계와 2026-09-09 사례:
          docs/notes/code-notes/현장서비스-테스트-노트.md "행이 하나라도 생기면 통과" 이하
        """
        # 직전 호출이 남긴 값과 대조해 첫 샘플에 곧바로 통과해 버리는 것을 막는다
        # (화면 이동은 페이지가 새로 뜨지만 검색은 그렇지 않다).
        self.page.evaluate("() => { window.__fsTableSnapshot = undefined; }")
        try:
            self.page.wait_for_function(
                """({emptyText, allowEmpty}) => {
                    const ids = [...document.querySelectorAll('[data-testid^="fs-table__row--"]')]
                        .map(e => e.getAttribute('data-testid')).join(',');
                    const root = document.querySelector('[data-testid="fs-table__root"]');
                    const isEmpty = !!(root && root.innerText.includes(emptyText));
                    // 행도 없고 빈 상태 안내도 없으면 아직 그리는 중이다
                    if (!ids && !isEmpty) { window.__fsTableSnapshot = undefined; return false; }
                    // 행이 있어야 하는 것을 아는 자리에서는 빈 상태를 완료로 인정하지 않는다
                    if (!ids && !allowEmpty) { window.__fsTableSnapshot = undefined; return false; }
                    const snapshot = isEmpty ? '__EMPTY__' : ids;
                    const settled = window.__fsTableSnapshot === snapshot;
                    window.__fsTableSnapshot = snapshot;
                    return settled;
                }""",
                arg={"emptyText": self.EMPTY_TEXT, "allowEmpty": allow_empty},
                polling=300,
                timeout=timeout_ms,
            )
        except Exception as e:
            reason = (
                "행이 있어야 하는 자리인데 끝내 안 붙었다"
                if not allow_empty
                else "목록이 끝내 안정되지 않았다"
            )
            raise AssertionError(
                f"[FAIL] {reason} ({timeout_ms / 1000:.0f}초 대기) - "
                "데이터가 도착하지 않은 화면일 수 있다 (세션 끊김·API 실패 의심)\n"
                f"        {self.state_summary()}"
            ) from e

    # 요약을 만들다가 화면 읽기가 막히면 짧게 포기한다. 여기서 오래 끄는 것은
    # "왜 실패했는지" 를 늦게 알려주는 것뿐이라 이득이 없다.
    SUMMARY_READ_TIMEOUT_MS = 2_000

    def _peek(self, locator: Locator, limit: int = 200) -> str | None:
        """요약용 텍스트 읽기. 못 읽으면 None 을 돌려주고 **예외를 내지 않는다**."""
        try:
            return locator.inner_text(timeout=self.SUMMARY_READ_TIMEOUT_MS)[:limit]
        except Exception:
            return None

    def state_summary(self) -> str:
        """행이 0건일 때 원인을 가르기 위한 화면 상태 요약. 실패 메시지에 담는다.

        ★ 이 함수는 **예외를 던지지 않는다.** `wait_status_counts()` 의 except 안에서 불리는데
          여기서 터지면 정작 알려주려던 원인이 통째로 가려진다. 못 읽은 항목은 `<못 읽음>`.
        읽는 넷과 판별법: docs/notes/code-notes/현장서비스-테스트-노트.md "0건일 때 원인을 가르는 요약"
        """
        tabs = self._peek(self.status_tabs)
        table = self._peek(self.table_root, limit=150)
        try:
            row_count: object = len(self.rows.all())
        except Exception:
            row_count = None

        unknown = "<못 읽음>"
        return (
            f"행수={unknown if row_count is None else row_count} / "
            f"빈결과안내={unknown if table is None else (self.EMPTY_TEXT in table)} / "
            # 배지 텍스트는 줄바꿈으로 와서 그대로 두면 메시지가 세로로 늘어진다
            f"상태탭={unknown if tabs is None else repr(' | '.join(tabs.split(chr(10))))} / "
            f"표={unknown if table is None else repr(table)}"
        )

    @allure.step("[{name}] 상태 탭 클릭")
    def click_status_tab(self, name: str) -> None:
        """상태 탭을 누르고 목록이 다시 그려질 때까지 기다린다.

        건수 배지는 탭을 눌러도 이미 채워져 있으므로 표만 기다린다. **그 배지를 "행이 있어야
        하는가" 의 근거로 같이 쓴다** - 0보다 크면 표의 "데이터가 없습니다" 는 결과가 아니라
        아직 응답이 안 온 것이다(전제: 탭을 누르는 시점이 1페이지).
        경위: docs/notes/code-notes/현장서비스-테스트-노트.md "같은 구멍이 상태 탭 클릭에서 또 열렸다"
        """
        self.status_tab(name).click()
        expected = self.status_tab_count(name)
        self.wait_table_settled(allow_empty=(expected == 0))

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
    """신규 서비스 신청 팝업. 페이지가 아니라 "탭 안에서 열리는 것" 이라 별도 클래스다.

    ★ submit_button([신청 완료])은 누르지 않는다 - dev 에 실제 신청 건이 생성된다.
      "유효성 검사에서 막히겠지" 로 눌렀다가 안 막혀서 데이터가 생긴 사례가 있다.
      검증은 "필드가 있는가 / 버튼이 활성화됐는가" 까지만.
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
        """팝업 안 "담긴 신청 목록" 의 행들. 팝업을 막 열면 비어서 DOM 에 없다 - 1건을 담아야 생긴다.

        ★ 접두어는 표 행과 같아 보여도 뒤에 붙는 값이 **신원(id)이 아니라 위치(0부터)** 다.
          중간 행을 지우면 뒤 번호가 당겨지므로, 개수를 세거나 "N번째" 를 가리키는 데까지만
          쓰고 조작 전후로 같은 행을 다시 찾는 데는 쓰지 않는다 (CLAUDE.md "행 식별" 4순위).
        2026-09-08 실측: docs/notes/code-notes/현장서비스-테스트-노트.md "접두어는 맞았고"
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
