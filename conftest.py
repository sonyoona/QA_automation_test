import json
import os
import time
from typing import Generator

import allure
import pytest
from dotenv import load_dotenv
from playwright.sync_api import Browser, BrowserType, Page, expect

load_dotenv()

STAFF_URL = os.getenv("STAFF_URL")
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


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    """테스트 본문이 실패하면 그 자리에서 화면·콘솔 로그를 Allure 리포트에 첨부한다.

    **왜 fixture teardown이 아니라 여기인가** — teardown에서 `allure.attach`를 부르면
    그 첨부는 fixture의 컨테이너에 붙어서 리포트의 "Tear down" 안쪽에 숨는다.
    테스트 본문이 실패한 이 시점(아직 테스트가 열려 있는 동안)에 붙여야
    테스트의 **Attachments 탭**에 바로 보인다.

    이 시점엔 fixture teardown이 아직 안 돌았으므로 page도 살아있다.
    """
    rep = yield
    if rep.when == "call" and rep.failed:
        page = item.funcargs.get("logged_in_page")
        if page is not None:
            _attach_page_evidence(page, getattr(item, "_console_logs", []))
    return rep


def _attach_page_evidence(page: Page, console_logs: list[str]) -> None:
    """실패 시점의 화면 스크린샷·주소와 브라우저 콘솔 로그를 Allure 리포트에 첨부한다.

    첨부 자체가 실패해도(이미 닫힌 페이지 등) 테스트 결과를 덮어쓰면 안 되므로
    예외는 삼키고 넘어간다 — 여기서 에러가 나면 정작 원래 실패 원인이 가려진다.
    """
    try:
        allure.attach(
            page.screenshot(full_page=True),
            name="실패 시점 화면",
            attachment_type=allure.attachment_type.PNG,
        )
        allure.attach(page.url, name="실패 시점 주소", attachment_type=allure.attachment_type.TEXT)
    except Exception:
        pass

    if console_logs:
        allure.attach(
            "\n".join(console_logs),
            name="브라우저 콘솔 로그",
            attachment_type=allure.attachment_type.TEXT,
        )


def _login_and_save(browser_type: BrowserType) -> None:
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
def auth_state(browser_type: BrowserType) -> str:
    """세션당 최대 1번만 로그인. auth.json이 살아있으면 그대로 재사용."""
    if not _auth_state_is_fresh(AUTH_STATE_PATH):
        _login_and_save(browser_type)
    return AUTH_STATE_PATH


@pytest.fixture
def logged_in_page(browser: Browser, auth_state: str, request) -> Generator[Page, None, None]:
    """테스트마다: 저장된 세션으로 새 탭만 연다 (재로그인 없음).

    브라우저 콘솔 로그를 계속 모아 테스트 객체에 달아둔다 — 테스트가 실패하면
    pytest_runtest_makereport 훅이 이걸 꺼내 화면 스크린샷과 함께 리포트에 첨부한다.
    실패 원인이 코드 문제인지 dev 데이터가 바뀐 건지 판단하려면 "그때 화면이
    실제로 어땠는지"가 필요하기 때문이다. 통과한 테스트까지 첨부하면 리포트만
    무거워져서(테스트당 풀페이지 PNG 약 200KB) 실패 케이스에만 남긴다.
    """
    context = browser.new_context(storage_state=auth_state)
    page = context.new_page()

    console_logs: list[str] = []
    page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
    page.on("pageerror", lambda exc: console_logs.append(f"[pageerror] {exc}"))
    request.node._console_logs = console_logs

    yield page

    context.close()
