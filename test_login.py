import os

import allure
from playwright.sync_api import Page, expect

STAFF_URL = os.getenv("STAFF_URL")

NOAUTH_EMAIL = os.getenv("STAFF_NOAUTH_EMAIL")
NOAUTH_PASSWORD = os.getenv("STAFF_NOAUTH_PASSWORD")

# 로그인 후 헤더에 찍히는 계정 표시. 2026-09-10 실측 - 아이디 필드에는 이메일 전체를 넣는데
# 헤더에는 @ 앞부분만 나온다. 하드코딩하지 않고 .env 에서 끌어와 계정을 바꾸면 따라오게 한다.
EXPECTED_ACCOUNT = (os.getenv("STAFF_ADMIN_EMAIL") or "").split("@")[0]

# 이 화면에는 testid 가 없고 GNB 링크는 accessible name 도 안 잡힌다(2026-09-10 실측) - 클래스로 잡는다.
# TODO(testid): 헤더 계정 표시에 testid 를 붙여달라고 프론트에 요청할 것.
ACCOUNT_LABEL_SELECTOR = ".menu-userName"

# Allure 리포트에서 이 파일의 테스트들이 묶이는 기능 단위
pytestmark = allure.feature("로그인 · 권한  ·  test_login.py")

# 자세한 설명은 docs/notes/code-notes/로그인-테스트-노트.md 참고


@allure.title("TC-103 | 권한 없는 계정 로그인 시 안내 알럿 표시 확인")
@allure.label("testcase", "TC-103")
def test_TC103_login_fail_no_permission(page: Page) -> None:
    """
    GIVEN  STAFF 1단계 로그인 화면에서, 아이디·비밀번호는 일치하지만
           시스템관리자·설치관리자 권한이 아닌 계정(testyoona)일 때
    WHEN   아이디·비밀번호를 입력하고 로그인하면
    THEN   '권한이 없는 계정입니다. 관리자에게 문의해 주세요.' 안내 알럿이 표시된다
    """
    page.goto(STAFF_URL)
    page.get_by_placeholder("아이디").fill(NOAUTH_EMAIL)
    page.get_by_placeholder("비밀번호").fill(NOAUTH_PASSWORD)
    page.get_by_role("button", name="로그인").click()

    # 안내 알럿 문구는 화면에서 확인한 실측값이다 (2026-09-10 기준)
    expect(page.get_by_text("권한이 없는 계정입니다")).to_be_visible()


@allure.title("TC-114 | 2단계 인증 완료 및 세션 저장·갱신 확인")
@allure.label("testcase", "TC-114")
def test_TC114_login_success_and_refresh_session(logged_in_page: Page, auth_state: str) -> None:
    """
    GIVEN  STAFF 1단계 로그인 화면에서, 아이디·비밀번호가 일치하는 정상 계정(adminyoona)일 때
    WHEN   (필요할 때만) 로그인해 2단계 인증까지 마치고, 저장된 세션으로 메인화면을 열면
    THEN   세션이 auth.json 에 저장돼 있고, 그 세션으로 연 화면이 로그인 화면으로 튕기지 않으며,
           헤더에 .env 에 설정한 그 계정이 표시된다

    ※ 실제로 로그인이 필요할 때만 **반자동**입니다 - 인증번호는 코드가 대신 못 칩니다.
      전용 headed 브라우저가 자동으로 뜨니(`--headed` 불필요) 그 창에서 입력하면 됩니다.
      세션이 살아 있으면 이 과정 없이 통과합니다: docs/notes/code-notes/로그인-테스트-노트.md

    ★ 전에는 파일 존재만 봤습니다. 무엇을 신호로 골랐는지와 그때 밟은 함정 둘은 위 노트 참고.
    """
    page = logged_in_page

    assert os.path.exists(auth_state), f"[FAIL] 세션 파일이 저장되지 않았다: {auth_state}"

    # 긍정 검증을 부정보다 먼저 둔다 - [로그인] 버튼이 없다만 있으면 화면이 안 그려졌을 때도 통과한다
    page.goto(STAFF_URL)
    expect(page.get_by_text("로그아웃", exact=True)).to_be_visible()
    expect(page.get_by_role("button", name="로그인")).not_to_be_visible()

    # 비어 있으면 to_have_text("") 가 되어 무엇이든 통과하므로 먼저 끊는다
    assert EXPECTED_ACCOUNT, "[FAIL] .env 의 STAFF_ADMIN_EMAIL 이 비어 있어 계정을 대조할 수 없다"
    expect(page.locator(ACCOUNT_LABEL_SELECTOR)).to_have_text(EXPECTED_ACCOUNT)
