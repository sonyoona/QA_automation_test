import os

from playwright.sync_api import expect

STAFF_URL = os.getenv("STAFF_URL", "https://<STAFF_URL_REDACTED>/")

ADMIN_EMAIL = os.getenv("STAFF_ADMIN_EMAIL")
ADMIN_PASSWORD = os.getenv("STAFF_ADMIN_PASSWORD")

NOAUTH_EMAIL = os.getenv("STAFF_NOAUTH_EMAIL")
NOAUTH_PASSWORD = os.getenv("STAFF_NOAUTH_PASSWORD")


def test_TC103_login_fail_no_permission(page):
    """
    TC-103 | 계정 일치하나 시스템관리자·설치관리자 권한이 아닌 계정 로그인 시 안내 알럿 표시 확인

    GIVEN  STAFF 1단계 로그인 화면에서, 아이디·비밀번호는 일치하지만
           시스템관리자·설치관리자 권한이 아닌 계정(testyoona)일 때
    WHEN   아이디·비밀번호를 입력하고 로그인하면
    THEN   '권한이 없는 계정입니다. 관리자에게 문의해 주세요.' 안내 알럿이 표시된다
    """
    page.goto(STAFF_URL)
    page.get_by_placeholder("아이디").fill(NOAUTH_EMAIL)
    page.get_by_placeholder("비밀번호").fill(NOAUTH_PASSWORD)
    page.get_by_role("button", name="로그인").click()

    # TODO: 실제 알럿 문구/셀렉터는 화면 보면서 Pick Locator로 확인 후 교체
    expect(page.get_by_text("권한이 없는 계정입니다")).to_be_visible()


def test_TC114_login_success_and_refresh_session(page):
    """
    TC-114 | 인증번호 일치 시 2단계 인증 완료 및 관리자 메인화면 이동 확인
             (+ 세션을 auth.json으로 갱신 — 이후 다른 기능 테스트가 로그인 없이 바로 시작하도록)

    ※ 반자동 테스트입니다. 2단계 인증번호는 실제 휴대폰으로 받아야 해서 코드가 대신할 수 없습니다.
      아이디·비밀번호까지는 자동으로 입력되고, 그 다음은 사람이 직접 이어서 진행합니다.
      반드시 --headed 로 실행해서 뜬 브라우저 창에서 직접 조작하세요.

    GIVEN  STAFF 1단계 로그인 화면에서, 아이디·비밀번호가 일치하는 정상 계정(adminyoona)일 때
    WHEN   아이디·비밀번호를 자동으로 입력해 로그인하고, 뜬 2단계 인증 화면에서
           사람이 휴대폰으로 받은 인증번호를 직접 입력하고 [확인]을 누르면
    THEN   관리자 메인화면으로 이동한다 → 이 시점의 세션을 auth.json으로 저장한다
    """
    page.goto(STAFF_URL)
    page.get_by_placeholder("아이디").fill(ADMIN_EMAIL)
    page.get_by_placeholder("비밀번호").fill(ADMIN_PASSWORD)
    page.get_by_role("button", name="로그인").click()

    # 여기까지는 자동 — 2단계 인증 화면으로 넘어갔는지만 확인
    # TODO: 실제 화면 문구/셀렉터로 교체
    expect(page.get_by_text("인증번호")).to_be_visible()

    # ↓↓↓ 여기서부터 사람이 직접: 뜬 브라우저 창에서 인증번호 입력 + [확인] 클릭 ↓↓↓
    # 로그인 버튼이 화면에서 사라질 때까지(=로그인 화면을 완전히 벗어날 때까지) 최대 2분 기다립니다.
    expect(page.get_by_role("button", name="확인")).to_be_hidden(timeout=120_000)

    # THEN: 메인화면 진입 성공 → 세션 저장
    page.context.storage_state(path="auth.json")
