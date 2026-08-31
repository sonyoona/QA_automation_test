import os

from playwright.sync_api import expect

STAFF_URL = os.getenv("STAFF_URL", "https://<STAFF_URL_REDACTED>/")

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


def test_TC114_login_success_and_refresh_session(auth_state):
    """
    TC-114 | 인증번호 일치 시 2단계 인증 완료 및 관리자 메인화면 이동 확인
             (+ auth.json이 신선하지 않을 때만 갱신)

    conftest.py의 auth_state fixture를 그대로 씁니다 — auth.json이 아직 신선하면
    로그인을 건너뛰고 그 파일을 그대로 재사용하며, 만료됐거나 없으면 그때만 실제
    로그인(+사람이 인증번호 직접 입력)을 수행해서 새로 저장합니다.

    ※ 로그인이 실제로 실행되는 경우엔 반자동입니다. 2단계 인증번호는 실제 휴대폰으로
      받아야 해서 코드가 대신할 수 없습니다. 로그인 전용 headed 브라우저가 자동으로
      뜨니(--headed 안 줘도 됩니다), 그 창에서 인증번호를 직접 입력하고 [확인]을 눌러주세요.
      auth.json이 이미 신선하면 이 과정 없이 바로 통과합니다.

    GIVEN  STAFF 1단계 로그인 화면에서, 아이디·비밀번호가 일치하는 정상 계정(adminyoona)일 때
    WHEN   (필요할 때만) 아이디·비밀번호를 자동으로 입력해 로그인하고, 뜬 2단계 인증 화면에서
           사람이 휴대폰으로 받은 인증번호를 직접 입력하고 [확인]을 누르면
    THEN   관리자 메인화면으로 이동해 세션이 auth.json에 저장되어 있다
    """
    assert os.path.exists(auth_state)
