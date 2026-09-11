import json
import os
import re
import time
from typing import Generator
from urllib.parse import urlparse

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

# 데이터를 바꾸는 테스트를 돌려도 되는 곳. 여기 없는 주소면 무조건 차단한다.
# dev 주소가 바뀌면 여기를 고친다 - 안 고쳐도 "안 돌아감" 쪽으로 틀리므로 안전하다.
# 블랙리스트가 아니라 화이트리스트인 이유: CLAUDE.md "변경성(mutating) 테스트 준비" 참고.
MUTATING_ALLOWED_HOSTS = {"fms-dev-staff.carbom.co.kr"}


def _staff_host() -> str:
    """`STAFF_URL` 의 호스트명. 못 읽으면 빈 문자열 - 그러면 화이트리스트에 없으니 차단된다."""
    return (urlparse(STAFF_URL or "").hostname or "").lower()


def pytest_addoption(parser: pytest.Parser) -> None:
    """데이터를 바꾸는 테스트를 **이번 실행에서만** 허용하는 플래그를 추가한다."""
    parser.addoption(
        "--allow-mutating",
        action="store_true",
        default=False,
        help="데이터를 바꾸는 테스트(@pytest.mark.mutating)를 이번 실행에서만 허용한다",
    )


def _mutating_allowed(config: pytest.Config) -> bool:
    """데이터를 바꾸는 테스트를 돌려도 되는가. `--allow-mutating` 플래그 또는
    `ALLOW_MUTATING_TESTS=true` 로 켠다 - **플래그를 권장한다**(그 명령 한 줄에만 살아서
    끄는 것을 잊을 수가 없다). 켜는 법 셋의 수명 비교와 환경변수를 매번 읽는 이유:
    CLAUDE.md "변경성(mutating) 테스트 준비" 참고.
    """
    if config.getoption("--allow-mutating"):
        return True
    return os.getenv("ALLOW_MUTATING_TESTS", "").strip().lower() == "true"


@pytest.fixture(autouse=True)
def _mutating_gate(request: pytest.FixtureRequest) -> None:
    """`@pytest.mark.mutating` 이 붙은 테스트는 명시적으로 켜야만 돈다 (옵트인).

    마커는 "고를 수 있게" 할 뿐이라 `-m` 이 안 붙는 경로(`pytest -v`·파일 지정·PyCharm
    실행 버튼)를 못 막는다. 그래서 기본값을 "안 함" 으로 둔다. 검사는 **허용 -> 접속처**
    순이고, 접속처는 `skip` 이 아니라 `fail` 이다(사고 직전이라 빨간불이 나야 한다).

    왜 이 순서인지 · 화이트리스트인 이유 · 이 fixture 가 `auth_state` 보다 **뒤에** 돈다는
    2026-09-10 정정: CLAUDE.md "변경성(mutating) 테스트 준비" 참고.
    """
    if request.node.get_closest_marker("mutating") is None:
        return

    if not _mutating_allowed(request.config):
        pytest.skip(
            "데이터를 바꾸는 TC 라 기본적으로 실행하지 않는다 - "
            "돌리려면 --allow-mutating 을 붙인다"
        )

    host = _staff_host()
    if host not in MUTATING_ALLOWED_HOSTS:
        pytest.fail(
            f"[FAIL] 데이터를 바꾸는 TC 를 허용되지 않은 접속처에서 돌리려 했다: {host or '(주소 없음)'}\n"
            f"        허용된 곳: {sorted(MUTATING_ALLOWED_HOSTS)}\n"
            "        .env 의 STAFF_URL 을 확인한다. 운영(prod) 이라면 절대 돌리지 않는다.\n"
            "        dev 주소가 바뀐 것이라면 conftest.py 의 MUTATING_ALLOWED_HOSTS 를 고친다",
            pytrace=False,
        )


def _auth_state_is_fresh(path: str) -> bool:
    """auth.json 이 있고 쿠키가 아직 만료 전인지 확인하는 **값싼 예비 검사**.

    ★ 이것만으로는 로그인 상태를 판정할 수 없다 - 서버가 끊었는지 알 수 없고, 세션
      쿠키(`expires == -1`)에는 영원히 "신선함" 이라 답한다. 진짜 판정은 `_session_alive()`.
    """
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
    """테스트가 실패하면 그 자리에서 화면·콘솔 로그를 Allure 리포트에 첨부한다.

    fixture teardown 이 아니라 훅인 이유, `setup` 단계도 함께 보는 이유:
    docs/notes/Allure-적용-노트.md "실패 증거 자동 첨부" 참고.
    """
    rep = yield
    if rep.when in ("setup", "call") and rep.failed:
        # funcargs 가 아니라 fixture 가 달아둔 값을 쓴다 (2026-09-07 실측 - 같은 노트 참고)
        page = getattr(item, "_page", None)
        if page is not None:
            _attach_page_evidence(page, getattr(item, "_console_logs", []), rep.when)
    return rep


def _attach_page_evidence(page: Page, console_logs: list[str], when: str = "call") -> None:
    """실패 시점의 화면 스크린샷·주소와 브라우저 콘솔 로그를 Allure 리포트에 첨부한다.

    첨부 이름에 단계를 적는 이유, 예외를 삼키는 이유:
    docs/notes/Allure-적용-노트.md "실패 증거 자동 첨부" 참고.
    """
    label = "사전조건(setup) 실패 시점" if when == "setup" else "실패 시점"
    try:
        allure.attach(
            page.screenshot(full_page=True),
            name=f"{label} 화면",
            attachment_type=allure.attachment_type.PNG,
        )
        allure.attach(page.url, name=f"{label} 주소", attachment_type=allure.attachment_type.TEXT)
    except Exception:
        pass

    if console_logs:
        allure.attach(
            "\n".join(console_logs),
            name="브라우저 콘솔 로그",
            attachment_type=allure.attachment_type.TEXT,
        )


_TC_ID_RE = re.compile(r"^TC-(\d{6})-(\d+)")


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """@allure.label("testcase", ...) 값에서 배포일자 기준 pytest 마커를 자동 생성한다.

    TC ID(`TC-260904-001`)는 함수명이 아니라 이 데코레이터가 정본이다(CLAUDE.md 참고).
    마커를 손으로 붙이면 데코레이터와 어긋날 수 있으므로, 여기서 파싱해 자동으로만 붙인다.
    `TC-YYMMDD-001` 형식이 아닌 기존 TC(`TC-001` 등)는 그냥 건너뛴다.
    """
    for item in items:
        for marker in item.iter_markers("allure_label"):
            # allure.label(label_type, *labels) -> pytest.mark.allure_label(*labels, label_type=label_type)
            # label_type은 키워드 인자로만 들어오고, TC ID는 args[0]이다.
            if marker.kwargs.get("label_type") != "testcase" or not marker.args:
                continue
            match = _TC_ID_RE.match(marker.args[0])
            if match:
                date, seq = match.groups()
                item.add_marker(f"tc_{date}")
                item.add_marker(f"tc_{date}_{seq}")


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

        # 2단계 인증 화면이 떴는지 확인 (실측 문구, 2026-09-10 기준)
        expect(page.get_by_text("인증번호")).to_be_visible()
        print(f"\n[로그인] 인증번호를 직접 입력해주세요. 최대 {OTP_WAIT_SEC}초 기다립니다.")

        # ↓↓↓ 여기서부터 사람이 직접: 뜬 브라우저 창에서 인증번호 입력 + [확인] 클릭 ↓↓↓
        expect(page.get_by_role("button", name="확인")).to_be_hidden(timeout=OTP_WAIT_SEC * 1000)

        context.storage_state(path=AUTH_STATE_PATH)
    finally:
        context.close()
        login_browser.close()


def _session_alive(browser_type: BrowserType, path: str) -> bool:
    """저장된 세션으로 **실제로 로그인이 되는지** 화면에 물어본다.

    쿠키 만료 시각만 믿으면 안 된다 - 서버가 세션을 이미 끊었는지는 파일에 안 적혀 있다.
    판정 기준은 GNB 상위 메뉴이고, 이는 **테스트가 실제로 의존하는 신호와 같아서** 새로
    단정하는 것이 없다. 비용 3~5초로 20분짜리 전체 ERROR 실행을 막는다.
    2026-09-10 경위: docs/notes/실행-트러블슈팅-노트.md "04. 전 테스트 ERROR" 참고.
    """
    browser = browser_type.launch()
    context = browser.new_context(storage_state=path)
    page = context.new_page()
    try:
        page.goto(STAFF_URL)
        expect(
            page.locator("a").filter(has_text=re.compile(r"^차량관리$")).first
        ).to_be_visible(timeout=15000)
        return True
    except Exception:
        return False
    finally:
        context.close()
        browser.close()


@pytest.fixture(scope="session")
def auth_state(browser_type: BrowserType, pytestconfig: pytest.Config) -> str:
    """세션당 최대 1번만 로그인. 저장된 세션이 **실제로 살아 있을 때만** 재사용한다.

    검사가 둘이다 - 파일만 보는 예비 검사(`_auth_state_is_fresh`) 뒤에 화면에 묻는 진짜
    판정(`_session_alive`). 로그인 구간에만 pytest 출력 가로채기를 껐다 켜는 이유:
    docs/notes/실행-트러블슈팅-노트.md "05. pytest 가 출력을 가둔다" 참고.
    """
    if _auth_state_is_fresh(AUTH_STATE_PATH) and _session_alive(browser_type, AUTH_STATE_PATH):
        return AUTH_STATE_PATH

    # 낡은 세션 파일은 남겨두지 않는다 - `_login_and_save` 가 새로 덮어쓰지만, 로그인이
    # 중간에 실패하면 이 파일이 다음 실행에서 또 "예비 검사 통과" 로 시간을 버리게 한다.
    if os.path.exists(AUTH_STATE_PATH):
        os.remove(AUTH_STATE_PATH)

    # getplugin 은 캡처를 시작시키는 게 아니라 이미 일하고 있는 그 객체를 받아온다.
    # in_=True 는 지금 효과가 없다 - 관례를 따른 것이지 위험해서가 아니다.
    capman = pytestconfig.pluginmanager.getplugin("capturemanager")
    if capman is not None:
        capman.suspend_global_capture(in_=True)
    try:
        _login_and_save(browser_type)
    finally:
        if capman is not None:
            capman.resume_global_capture()
    return AUTH_STATE_PATH


@pytest.fixture
def logged_in_page(browser: Browser, auth_state: str, request) -> Generator[Page, None, None]:
    """테스트마다: 저장된 세션으로 새 탭만 연다 (재로그인 없음).

    page 와 콘솔 로그를 테스트 객체에 달아둔다 - 실패하면 `pytest_runtest_makereport`
    훅이 꺼내 리포트에 첨부한다. 왜 실패한 것만 첨부하는지, funcargs 를 안 쓰는 이유:
    docs/notes/Allure-적용-노트.md "실패 증거 자동 첨부" 참고.
    """
    context = browser.new_context(storage_state=auth_state)
    page = context.new_page()

    console_logs: list[str] = []
    page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
    page.on("pageerror", lambda exc: console_logs.append(f"[pageerror] {exc}"))
    request.node._console_logs = console_logs
    request.node._page = page

    yield page

    context.close()
