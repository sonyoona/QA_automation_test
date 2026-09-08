# GNB 경로: 차량관리 > 현장 서비스
#
# 전부 읽기 전용(화면 노출 확인) TC 다. 데이터를 만들거나 바꾸는 동작은 하지 않는다.
# ★ [신청 완료](fs-new__submit-button)는 절대 클릭하지 않는다 - dev 에 실제 신청 건이 생성된다.
#   팝업 검증은 "필드가 노출되는가 / 버튼이 있는가" 까지만 한다.
#
# 셀렉터(testid)는 이 파일에 나오지 않는다 - 전부 pages/field_service_page.py 가 안다.
# 왜 그렇게 했는지는 docs/notes/code-notes/현장서비스-테스트-노트.md 참고
# 각 줄이 무엇을 하는지는 docs/notes/code-notes/현장서비스-코드-한줄씩.md 참고

import allure
import pytest
from playwright.sync_api import Locator, Page, expect

from pages.field_service_page import FieldServicePage

# Allure 리포트에서 이 파일의 테스트들이 묶이는 기능 단위 (파일 상단 GNB 경로와 동일)
pytestmark = allure.feature("차량관리 > 현장 서비스  ·  test_field_service.py")

# TC ID 는 배포(예정)일자 접두어를 쓴다 (CLAUDE.md "TC ID 형식과 배포 단위 실행" 참고).
# TODO: 이 화면의 실제 배포일이 정해지면 260907 을 그 날짜로 일괄 치환할 것.
#       엑셀 TC 문서가 아직 없어서 번호도 여기서 임시로 001~005 를 붙였다 - 문서가 나오면 맞춘다.

# 결과 행마다 붙는 액션 버튼(fs-table__action-btn--{PK})의 화면 표시 라벨.
# 라벨이 한 가지가 아니라 행 상태에 따라 갈린다 - 2026-09-08 실측 스크립트로 상태 탭 5개를
# 하나씩 눌러 각 10행씩 총 50행을 확인했고, 상태마다 라벨이 하나로 일정했다.
#   진행 중(대기 · 배정완료) -> [수정]      종료(완료 · 취소 · 작업불가) -> [상세]
# "종료된 건은 더 고칠 수 없으니 [상세]" 로 읽히지만 그 규칙 자체는 기획서로 확인한 게
# 아니다 - 관찰이 일관될 뿐이다. 어긋나면 화면이 바뀐 것이니 실패하는 게 맞다.
ACTION_LABEL_BY_STATUS = {
    "대기": "수정",
    "배정완료": "수정",
    "완료": "상세",
    "취소": "상세",
    "작업불가": "상세",
}

# 상태 탭 이름. [전체] 를 뺀 5개이고, 대응표의 키와 같은 것이라 따로 적지 않고 뽑아 쓴다 -
# 따로 적으면 대응표에 상태를 추가할 때 한쪽만 고쳐진다.
STATUS_TABS = list(ACTION_LABEL_BY_STATUS)
ALL_TAB = "전체"

# 실측된 라벨 전체. 상태 탭 6개(전체 제외 5개)를 다 봤으므로 지금은 모든 상태가 위 표에 있고,
# 아래 집합은 **나중에 상태가 새로 생겼을 때**를 위한 그물이다 - 모르는 상태가 와도
# 라벨이 둘 중 하나이긴 한지까지는 본다.
ACTION_BUTTON_LABELS = set(ACTION_LABEL_BY_STATUS.values())

# 조회 필터 항목 - (화면에 보이는 이름, FieldServicePage 의 속성명)
# 속성명을 문자열로 두고 getattr 로 꺼내는 이유: 항목이 13개라 하나씩 나열하면 같은 줄이
# 13번 반복된다. testid 는 여전히 Page Object 안에만 있다.
FILTER_FIELDS = [
    ("리셀러", "reseller_select"),
    ("업체", "company_select"),
    ("서비스 유형", "service_type_select"),
    ("차량번호", "plate_input"),
    ("단말기 S/N", "device_sn_input"),
    ("담당자", "assignee_input"),
    ("신청자", "requester_input"),
    ("작업완료일 시작", "completed_from_date"),
    ("작업완료일 종료", "completed_to_date"),
    ("GPS 음영", "gps_shadow_checkbox"),
    ("임시등록만", "temp_only_checkbox"),
    ("작업완료만", "completed_only_checkbox"),
    ("조회 버튼", "search_button"),
]

# 신규 서비스 신청 팝업의 입력 항목 - (화면에 보이는 이름, NewServicePopup 의 속성명)
NEW_POPUP_FIELDS = [
    ("서비스 유형", "service_type_select"),
    ("작업 희망일", "work_date_field"),
    ("디지털키", "digital_key_select"),
    ("시동잠금", "ignition_lock_select"),
    ("주소", "address_input"),
    ("주소 검색 버튼", "address_search_button"),
    ("연락처", "contact_input"),
    ("설치기사 방문", "installer_walk_in_checkbox"),
    ("담당자 지정", "assignee_trigger"),
    ("메모", "memo_textarea"),
    ("임시등록", "temp_reg_checkbox"),
    ("업체", "company_select"),
    ("지점", "branch_select"),
    ("차량", "vehicle_select"),
    ("목록에 추가 버튼", "add_to_list_button"),
]


@pytest.fixture
def fs(logged_in_page: Page) -> FieldServicePage:
    """화면 진입까지 끝난 상태의 Page Object 를 돌려준다.

    진입은 검증 대상이 아니라 사전 조건이라 fixture 로 뺀다 - 여기서 실패하면 pytest 가
    ERROR 로 표시해 기능 검증 실패(FAIL)와 구분된다.
    """
    page_object = FieldServicePage(logged_in_page)
    page_object.goto()
    return page_object


def _expect_rendered(locator: Locator, what: str) -> None:
    """대표 요소 하나를 기다려 렌더가 끝난 것을 확인한다.

    is_visible()·inner_text() 같은 조회 메서드는 재시도가 없어서, 아직 안 그려진 화면을
    읽으면 전부 "없음" 으로 나온다. 여러 요소를 한 번에 훑기 전에 이걸 먼저 부른다.

    expect 의 기본 실패 메시지는 셀렉터만 보여줘서, 리포트만 봐서는 그게 어느 항목인지
    알 수 없다 - 나머지 항목은 이름으로 보고되는데 대표 요소 하나만 예외가 된다.
    그래서 한글 이름을 담아 다시 던진다.
    """
    try:
        expect(locator).to_be_visible()
    except AssertionError as e:
        raise AssertionError(
            f"[FAIL] {what} 이(가) 끝내 노출되지 않아 나머지를 확인할 수 없다"
        ) from e


def _find_hidden(owner: object, fields: list[tuple[str, str]]) -> list[str]:
    """fields 중 화면에 안 보이는 항목의 이름을 모아서 돌려준다.

    첫 항목만 expect 로 기다리고 나머지는 is_visible() 로 즉시 확인한다 (위
    `_expect_rendered` 참고). 한 번에 훑으면 빠진 항목을 다 모아서 보고할 수 있다 -
    하나 발견하고 멈추는 것보다 원인 파악이 빠르다.
    """
    first_label, first_attr = fields[0]
    _expect_rendered(getattr(owner, first_attr), f"첫 항목 '{first_label}'")
    return [label for label, attr in fields if not getattr(owner, attr).is_visible()]


def _action_label_problems(fs: FieldServicePage, row_ids: list[str]) -> tuple[list[str], list[tuple[str, str]]]:
    """각 행의 액션 버튼을 보고 (문제 목록, 관찰된 (상태, 라벨) 목록)을 돌려준다.

    TC 두 개가 같은 검증을 하므로 여기 한 곳에 둔다 - 나뉘어 있으면 한쪽만 고쳐져
    "같은 것을 두 가지 방법으로 읽는" 상태가 된다 (CLAUDE.md 위양성 장).

    호출 전에 목록이 비어 있지 않은 것과 첫 행이 그려진 것을 확인해야 한다.
    """
    statuses = fs.row_statuses()
    problems: list[str] = []
    seen: list[tuple[str, str]] = []

    for row_id in row_ids:
        button = fs.row_action_button(row_id)
        if not button.is_visible():
            problems.append(f"{row_id}: 버튼이 없거나 숨겨져 있음")
            continue

        status = statuses[row_id]
        label = button.inner_text().strip()
        seen.append((status, label))
        expected = ACTION_LABEL_BY_STATUS.get(status)

        if expected and label != expected:
            problems.append(f"{row_id}: 상태 {status!r} 인데 라벨이 {label!r} (기대 {expected!r})")
        elif not expected and label not in ACTION_BUTTON_LABELS:
            problems.append(f"{row_id}: 대응표에 없는 상태 {status!r} 의 라벨이 {label!r}")

    return problems, seen


@allure.title("TC-260907-001 | 현장 서비스 화면 진입 시 주요 영역이 모두 노출된다")
@allure.label("testcase", "TC-260907-001")
def test_page_areas_visible(fs: FieldServicePage) -> None:
    """
    GIVEN  STAFF 웹에 로그인된 상태에서
    WHEN   차량관리 > 현장 서비스 화면에 진입하면
    THEN   상태 탭 · 신규 서비스 신청 버튼 · 결과 테이블 · 엑셀 다운로드 버튼이 모두 노출된다
    """
    expect(fs.root).to_be_visible()
    expect(fs.status_tabs).to_be_visible()
    expect(fs.new_service_button).to_be_visible()
    expect(fs.table_root).to_be_visible()
    expect(fs.excel_download_button).to_be_visible()


@allure.title("TC-260907-002 | 조회 필터 항목이 모두 노출된다")
@allure.label("testcase", "TC-260907-002")
def test_filter_fields_visible(fs: FieldServicePage) -> None:
    """
    GIVEN  현장 서비스 화면에 진입한 상태에서
    WHEN   조회 필터 영역을 확인하면
    THEN   리셀러 · 업체 · 서비스 유형 등 13개 항목이 모두 노출된다

    항목이 하나라도 빠지면 어느 것들이 빠졌는지 이름으로 전부 보고한다.
    """
    hidden = _find_hidden(fs, FILTER_FIELDS)

    assert not hidden, f"[FAIL] 노출되지 않은 조회 필터 항목: {hidden}"


@allure.title("TC-260907-003 | 결과 행마다 액션 버튼([수정]/[상세])이 하나씩 노출된다")
@allure.label("testcase", "TC-260907-003")
def test_table_rows_have_action_button(fs: FieldServicePage) -> None:
    """
    GIVEN  현장 서비스 화면에 진입해 결과 목록이 조회된 상태에서
    WHEN   각 행의 PK 로 대응하는 액션 버튼을 찾으면
    THEN   모든 행이 자기 PK 를 가진 액션 버튼을 하나씩 노출한다

    행 식별을 표시 텍스트가 아니라 testid 안의 PK(fs-table__row--10679)로 한다 -
    같은 날 같은 업체 건이면 행 텍스트가 글자까지 같을 수 있어 텍스트로는 구분이 안 된다.

    ★ 버튼을 누르지 않는다 - [수정] 은 수정 화면으로 들어가는 입구라, 노출·라벨까지만 본다.

    testid 존재만 보면 안 되는 이유 - testid 는 화면에 안 보이는 속성이라 `display:none`
    이어도 잡히고, 라벨이 통째로 바뀌어도 그대로 통과한다. 그래서 노출과 라벨을 함께 본다.

    라벨은 행 상태에 따라 갈린다 - 진행 중이면 [수정], 종료된 건이면 [상세]
    (ACTION_LABEL_BY_STATUS 주석 참고). 이 TC 는 [전체] 탭만 보므로 그때그때 1페이지에
    올라온 상태만 검증한다 - 상태별로 빠짐없이 보려면 탭을 도는 TC 가 따로 있어야 한다.
    """
    total = fs.status_tab_count(ALL_TAB)
    row_ids = fs.row_ids()

    if total == 0:
        pytest.skip(f"[{ALL_TAB}] 탭에 건이 0건 - 검증할 행이 없다 (탭 배지 기준)")

    assert row_ids, (
        f"[FAIL] [{ALL_TAB}] 탭 배지는 {total}건인데 조회된 행이 0건이다 - "
        "데이터가 없는 게 아니라 목록을 못 읽은 것이다\n"
        f"        {fs.state_summary()}"
    )

    _expect_rendered(fs.row_action_button(row_ids[0]), f"첫 행({row_ids[0]})의 액션 버튼")

    broken, seen = _action_label_problems(fs, row_ids)

    assert not broken, (   # broken 이 빈 리스트([])면 통과 - 문제 행이 하나도 없다는 뜻
        f"[FAIL] 액션 버튼이 정상이 아닌 행: {broken} / 전체 {len(row_ids)}행 "
        f"(상태별 기대 라벨: {ACTION_LABEL_BY_STATUS})"
    )
    print(f"[검증] {len(row_ids)}개 행 전부 액션 버튼 노출 확인 완료 - 관찰된 (상태, 라벨): "
          f"{sorted(set(seen))}")


@pytest.mark.parametrize("tab", STATUS_TABS)
@allure.title("TC-260907-006 | [{tab}] 탭 — 그 상태에 맞는 액션 버튼 라벨이 노출된다")
@allure.label("testcase", "TC-260907-006")
def test_action_label_by_status(fs: FieldServicePage, tab: str) -> None:
    """
    GIVEN  현장 서비스 화면에 진입한 상태에서
    WHEN   상태 탭을 하나씩 눌러 결과 행의 액션 버튼을 확인하면
    THEN   각 행이 자기 상태에 맞는 라벨([수정]/[상세])의 버튼을 노출한다

    TC-260907-003 은 [전체] 탭 1페이지만 보므로, 그날 그 페이지에 안 올라온 상태는
    검증되지 않는다. 이 TC 가 상태 5개를 매번 돌게 해서 그 구멍을 메운다.

    ★ 버튼을 누르지 않는다 - 탭 클릭은 조회라 데이터를 바꾸지 않는다.

    이 TC 는 "탭 필터가 제대로 걸렸는가"(결과 행이 전부 그 상태인가)는 보지 않는다 -
    그건 상태 탭 필터 TC 의 몫이다. 여기서는 행이 어떤 상태든 **그 상태에 맞는 라벨**인지만
    본다. 그래서 필터가 깨져도 이 TC 는 통과할 수 있고, 그게 의도한 범위다.
    """
    fs.click_status_tab(tab)

    total = fs.status_tab_count(tab)
    row_ids = fs.row_ids()

    if total == 0:
        pytest.skip(f"[{tab}] 탭에 건이 0건 - 검증할 행이 없다 (탭 배지 기준)")

    assert row_ids, (
        f"[FAIL] [{tab}] 탭 배지는 {total}건인데 조회된 행이 0건이다 - "
        "데이터가 없는 게 아니라 목록을 못 읽은 것이다\n"
        f"        {fs.state_summary()}"
    )

    _expect_rendered(fs.row_action_button(row_ids[0]), f"[{tab}] 탭 첫 행의 액션 버튼")

    broken, seen = _action_label_problems(fs, row_ids)

    assert not broken, (
        f"[FAIL] [{tab}] 탭에서 액션 버튼이 정상이 아닌 행: {broken} / 전체 {len(row_ids)}행 "
        f"(상태별 기대 라벨: {ACTION_LABEL_BY_STATUS})"
    )
    print(f"[검증] [{tab}] 탭 {len(row_ids)}행 - 관찰된 (상태, 라벨): {sorted(set(seen))}")


@pytest.mark.parametrize("tab", STATUS_TABS)
@allure.title("TC-260907-007 | [{tab}] 탭 — 그 상태의 건만, 빠짐없이 조회된다")
@allure.label("testcase", "TC-260907-007")
def test_status_tab_filters_rows(fs: FieldServicePage, tab: str) -> None:
    """
    GIVEN  [전체] 탭에서 1페이지 행들의 상태를 미리 읽어둔 상태에서
    WHEN   상태 탭을 누르면
    THEN   ① 결과 행이 전부 그 상태이고 ② [전체] 탭에 있던 그 상태 건이 빠지지 않았다

    **한 방향만 보면 반쪽이다** - ①만 보면 필터가 아무것도 안 돌려줘도(0건) 통과하고,
    ②만 보면 필터가 전부 돌려줘도 통과한다. 둘을 같이 걸어야 "그 상태만, 빠짐없이" 가 된다.

    ② 의 전제 - 두 목록이 같은 기준(작업신청일 내림차순)으로 정렬돼 있다는 것.
    그러면 "[전체] 1페이지에 있는 X 상태 행" 은 반드시 "[X] 탭 1페이지" 안에 있다.
    전체에서 그 행보다 위에 있는 행이 9개 이하이므로, X 중에서도 9번째 안이기 때문이다.
    정렬 기본값이 바뀌면 이 전제가 깨지고 ② 가 거짓 실패를 낸다 - 그때는 실패 메시지의
    "정렬 전제" 문구를 보고 여기부터 의심한다.

    ★ 아무것도 누르지 않는다 - 탭 클릭은 조회다.
    """
    with allure.step(f"[{ALL_TAB}] 탭에서 기준 목록 읽기"):
        fs.click_status_tab(ALL_TAB)
        all_ids = fs.row_ids()
        assert all_ids, (
            f"[FAIL] [{ALL_TAB}] 탭이 0건이라 기준 목록을 만들 수 없다\n"
            f"        {fs.state_summary()}"
        )
        _expect_rendered(fs.row_action_button(all_ids[0]), f"[{ALL_TAB}] 탭 첫 행")
        all_statuses = fs.row_statuses()
        expected_ids = [i for i in all_ids if all_statuses[i] == tab]

    fs.click_status_tab(tab)
    total = fs.status_tab_count(tab)
    row_ids = fs.row_ids()

    if total == 0:
        # 건이 없다는 배지를 그대로 믿지 않는다 - [전체] 탭에 그 상태가 보였다면 모순이다
        assert not expected_ids, (
            f"[FAIL] [{tab}] 탭 배지는 0건인데 [{ALL_TAB}] 탭에는 그 상태 행이 있다: {expected_ids}"
        )
        pytest.skip(f"[{tab}] 탭에 건이 0건 - 필터 결과를 검증할 행이 없다")

    assert row_ids, (
        f"[FAIL] [{tab}] 탭 배지는 {total}건인데 조회된 행이 0건이다 - "
        "필터가 걸러낸 게 아니라 목록을 못 읽은 것이다\n"
        f"        {fs.state_summary()}"
    )

    _expect_rendered(fs.row_action_button(row_ids[0]), f"[{tab}] 탭 첫 행")
    statuses = fs.row_statuses()

    with allure.step("① 결과에 다른 상태가 섞이지 않았는가 (오검출)"):
        wrong = {i: statuses[i] for i in row_ids if statuses[i] != tab}
        assert not wrong, (
            f"[FAIL] [{tab}] 탭 결과에 다른 상태가 섞였다 (행 PK: 상태): {wrong} "
            f"/ 전체 {len(row_ids)}행"
        )

    with allure.step("② 그 상태인데 결과에서 빠진 건이 없는가 (누락)"):
        missing = [i for i in expected_ids if i not in row_ids]
        assert not missing, (
            f"[FAIL] [{ALL_TAB}] 탭에서 상태가 {tab!r} 이던 행이 [{tab}] 탭 결과에 없다: {missing} "
            f"(기준 {len(expected_ids)}건 중) — 정렬 전제(작업신청일 내림차순)가 깨졌을 수도 있다"
        )

    print(f"[검증] [{tab}] 탭 {len(row_ids)}행 전부 상태 일치 · "
          f"[{ALL_TAB}] 탭 기준 {len(expected_ids)}건 누락 없음")


@allure.title("TC-260907-004 | 신규 서비스 신청 팝업의 입력 항목이 모두 노출된다")
@allure.label("testcase", "TC-260907-004")
def test_new_service_popup_fields_visible(fs: FieldServicePage) -> None:
    """
    GIVEN  현장 서비스 화면에 진입한 상태에서
    WHEN   [신규 서비스 신청] 버튼을 눌러 팝업을 열면
    THEN   서비스 정보 · 차량 선택 영역의 15개 입력 항목이 모두 노출된다

    ★ 값을 채우거나 제출하지 않는다 - 노출 여부만 확인한다.

    assert 를 close() 보다 먼저 두는 이유 - 실패하면 close() 에 도달하지 않아 팝업이 열린
    화면이 그대로 리포트에 첨부된다. 먼저 닫으면 "어느 필드가 안 보이는가" 로 실패했는데
    스크린샷에는 목록 화면만 남아 정작 봐야 할 것이 사라진다 (conftest 의 첨부 훅은
    fixture teardown 전에 그 시점 화면을 찍는다).

    통과했을 때 닫는 것도 정리 목적은 아니다 - logged_in_page 가 function scope 라
    테스트마다 컨텍스트를 새로 만들고 끝나면 닫으므로, 팝업이 열린 채 끝나도 다음 TC 에
    남지 않는다. 화면을 원래 상태로 돌려놓는다는 뜻만 남긴다.
    """
    popup = fs.open_new_service_popup()

    hidden = _find_hidden(popup, NEW_POPUP_FIELDS)

    assert not hidden, f"[FAIL] 노출되지 않은 팝업 입력 항목: {hidden}"
    popup.close()


@allure.title("TC-260907-005 | 팝업 하단 버튼이 노출되고 닫기로 화면이 복귀한다")
@allure.label("testcase", "TC-260907-005")
def test_new_service_popup_footer_and_close(fs: FieldServicePage) -> None:
    """
    GIVEN  현장 서비스 화면에서 [신규 서비스 신청] 팝업을 연 상태에서
    WHEN   하단 버튼을 확인하고 [닫기]를 누르면
    THEN   [신청 완료] · [취소] · [닫기]가 모두 노출되고, 닫으면 목록 화면으로 돌아온다

    ★ [신청 완료]는 노출 여부만 본다 - 클릭하면 dev 에 실제 신청 건이 생성된다.
      "유효성 검사에서 막히겠지" 하고 눌렀다가 안 막혀서 데이터가 생긴 사례가 있다.
    """
    popup = fs.open_new_service_popup()

    expect(popup.submit_button).to_be_visible()
    expect(popup.cancel_button).to_be_visible()
    expect(popup.close_button).to_be_visible()

    popup.close()

    expect(fs.table_root).to_be_visible()
