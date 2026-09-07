# GNB 경로: 차량관리 > 현장 서비스
#
# 전부 읽기 전용(화면 노출 확인) TC 다. 데이터를 만들거나 바꾸는 동작은 하지 않는다.
# ★ [신청 완료](fs-new__submit-button)는 절대 클릭하지 않는다 - dev 에 실제 신청 건이 생성된다.
#   팝업 검증은 "필드가 노출되는가 / 버튼이 있는가" 까지만 한다.
#
# 셀렉터(testid)는 이 파일에 나오지 않는다 - 전부 pages/field_service_page.py 가 안다.
# 자세한 설명은 docs/notes/code-notes/현장서비스-테스트-노트.md 참고

import allure
import pytest
from playwright.sync_api import Page, expect

from pages.field_service_page import FieldServicePage

# Allure 리포트에서 이 파일의 테스트들이 묶이는 기능 단위 (파일 상단 GNB 경로와 동일)
pytestmark = allure.feature("차량관리 > 현장 서비스  ·  test_field_service.py")

# TC ID 는 배포(예정)일자 접두어를 쓴다 (CLAUDE.md "TC ID 형식과 배포 단위 실행" 참고).
# TODO: 이 화면의 실제 배포일이 정해지면 260907 을 그 날짜로 일괄 치환할 것.
#       엑셀 TC 문서가 아직 없어서 번호도 여기서 임시로 001~005 를 붙였다 - 문서가 나오면 맞춘다.

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


def _find_hidden(owner: object, fields: list[tuple[str, str]]) -> list[str]:
    """fields 중 화면에 안 보이는 항목의 이름을 모아서 돌려준다.

    첫 항목만 expect 로 기다리고 나머지는 is_visible() 로 즉시 확인하는 이유 -
    is_visible() 은 재시도를 안 해서 아직 안 그려진 화면을 읽으면 전부 "없음" 으로 나온다.
    먼저 하나를 expect 로 기다려 렌더가 끝난 걸 확인한 뒤 나머지를 훑으면, 빠진 항목을
    한 번에 다 모아서 보고할 수 있다 (하나 발견하고 멈추는 것보다 원인 파악이 빠르다).
    """
    first_label, first_attr = fields[0]
    expect(getattr(owner, first_attr)).to_be_visible()
    return [label for label, attr in fields if not getattr(owner, attr).is_visible()]


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


@allure.title("TC-260907-003 | 결과 행마다 상세 버튼이 하나씩 있다")
@allure.label("testcase", "TC-260907-003")
def test_table_rows_have_action_button(fs: FieldServicePage) -> None:
    """
    GIVEN  현장 서비스 화면에 진입해 결과 목록이 조회된 상태에서
    WHEN   각 행의 PK 로 대응하는 상세 버튼을 찾으면
    THEN   모든 행이 자기 PK 를 가진 상세 버튼을 하나씩 가지고 있다

    행 식별을 표시 텍스트가 아니라 testid 안의 PK(fs-table__row--10679)로 한다 -
    같은 날 같은 업체 건이면 행 텍스트가 글자까지 같을 수 있어 텍스트로는 구분이 안 된다.
    """
    row_ids = fs.row_ids()
    assert row_ids, "[FAIL] 조회된 행이 0건입니다 - 목록이 실제로 비었는지, 로딩이 실패한 건지 확인 필요"

    missing = [row_id for row_id in row_ids if fs.row_action_button(row_id).count() == 0]

    assert not missing, f"[FAIL] 상세 버튼이 없는 행(PK): {missing} / 전체 {len(row_ids)}행"
    print(f"[검증] {len(row_ids)}개 행 전부 상세 버튼 확인 완료")


@allure.title("TC-260907-004 | 신규 서비스 신청 팝업의 입력 항목이 모두 노출된다")
@allure.label("testcase", "TC-260907-004")
def test_new_service_popup_fields_visible(fs: FieldServicePage) -> None:
    """
    GIVEN  현장 서비스 화면에 진입한 상태에서
    WHEN   [신규 서비스 신청] 버튼을 눌러 팝업을 열면
    THEN   서비스 정보 · 차량 선택 영역의 15개 입력 항목이 모두 노출된다

    ★ 값을 채우거나 제출하지 않는다 - 노출 여부만 확인하고 팝업을 닫는다.
    """
    popup = fs.open_new_service_popup()

    hidden = _find_hidden(popup, NEW_POPUP_FIELDS)
    popup.close()

    assert not hidden, f"[FAIL] 노출되지 않은 팝업 입력 항목: {hidden}"


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
