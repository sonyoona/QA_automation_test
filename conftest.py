import json
import os
import time

import pytest
from dotenv import load_dotenv
from playwright.sync_api import expect

load_dotenv()

STAFF_URL = os.getenv("STAFF_URL", "https://<STAFF_URL_REDACTED>/")
ADMIN_EMAIL = os.getenv("STAFF_ADMIN_EMAIL")
ADMIN_PASSWORD = os.getenv("STAFF_ADMIN_PASSWORD")

AUTH_STATE_PATH = "auth.json"
OTP_WAIT_SEC = int(os.getenv("OTP_WAIT_SEC", "180"))


def _auth_state_is_fresh(path: str) -> bool:
    """auth.json이 있고, 안에 든 쿠키가 아직 만료 전인지 확인."""
    if not os.path.exists(path):
        return False
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    cookies = data.get("cookies", [])
    if not cookies:
        return False
    now = time.time()
    # expires가 -1(세션 쿠키)이면 만료 판정에서 제외, 나머지는 지금 시각과 비교
    return all(c.get("expires", -1) in (-1, None) or c["expires"] > now for c in cookies)


def _login_and_save(browser_type) -> None:
    """아이디·비밀번호는 자동 입력, 인증번호는 사람이 직접 입력 → auth.json 저장.

    다른 테스트가 쓰는 기본 browser fixture는 headless라 화면이 안 보이므로,
    로그인 전용으로만 headed 브라우저를 따로 띄운다.
    """
    login_browser = browser_type.launch(headless=False)
    context = login_browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    try:
        page.goto(STAFF_URL)
        page.get_by_placeholder("아이디").fill(ADMIN_EMAIL)
        page.get_by_placeholder("비밀번호").fill(ADMIN_PASSWORD)
        page.get_by_role("button", name="로그인").click()

        # TODO: 실제 화면 문구/셀렉터로 교체
        expect(page.get_by_text("인증번호")).to_be_visible()
        print(f"\n[로그인] 인증번호를 직접 입력해주세요. 최대 {OTP_WAIT_SEC}초 기다립니다.")

        # ↓↓↓ 여기서부터 사람이 직접: 뜬 브라우저 창에서 인증번호 입력 + [확인] 클릭 ↓↓↓
        expect(page.get_by_role("button", name="확인")).to_be_hidden(timeout=OTP_WAIT_SEC * 1000)

        context.storage_state(path=AUTH_STATE_PATH)
    finally:
        context.close()
        login_browser.close()


@pytest.fixture(scope="session")
def auth_state(browser_type) -> str:
    """세션당 최대 1번만 로그인. auth.json이 살아있으면 그대로 재사용."""
    if not _auth_state_is_fresh(AUTH_STATE_PATH):
        _login_and_save(browser_type)
    return AUTH_STATE_PATH


@pytest.fixture
def logged_in_page(browser, auth_state):
    """테스트마다: 저장된 세션으로 새 탭만 연다 (재로그인 없음)."""
    context = browser.new_context(storage_state=auth_state)
    page = context.new_page()
    yield page
    context.close()
