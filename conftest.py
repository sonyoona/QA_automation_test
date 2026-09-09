import json
import os
import re
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


def _mutating_allowed() -> bool:
    """`.env` 에 `ALLOW_MUTATING_TESTS=true` 가 있을 때만 참.

    값을 읽을 때마다 확인하는 이유 - 모듈 상수로 굳혀두면 실행 중에 바꿔도 안 먹혀서
    "왜 아직 skip 되지" 를 한참 찾게 된다.
    """
    return os.getenv("ALLOW_MUTATING_TESTS", "").strip().lower() == "true"


@pytest.fixture(autouse=True)
def _mutating_gate(request: pytest.FixtureRequest) -> None:
    """`@pytest.mark.mutating` 이 붙은 테스트는 명시적으로 켜야만 돈다 (옵트인).

    **마커만으로는 부족하기 때문에 있다.** 마커는 "고를 수 있게" 해주는 것이지
    "모르고 돌리는 것을 막는" 장치가 아니다. `-m "not mutating"` 이 안 붙는 경로가
    이만큼 있고, 전부 dev 데이터를 실제로 바꾼다.

        pytest -v · pytest --lf · pytest test_vehicle_company_transfer.py
        PyCharm 의 실행 버튼 · 새로 온 사람 · 6개월 뒤의 나

    그래서 기본값을 "안 함" 으로 두고, `.env` 에 `ALLOW_MUTATING_TESTS=true` 를 적은
    사람만 돌 수 있게 한다. `.env` 는 `.gitignore` 에 있어서 커밋되지 않으므로
    남의 컴퓨터·CI 에는 그 값이 없다 - 기본이 안전한 쪽으로 유지된다.

    `autouse=True` 라 모든 테스트가 이걸 거치지만, 마커가 없으면 즉시 돌려보내므로
    읽기 전용 TC 에는 비용이 없다. 이 fixture 는 의존이 없어서 `logged_in_page` 보다
    **먼저** 돌고, 그래서 차단될 때는 브라우저가 아예 안 뜬다.

    ★ 아직 없는 것 - 운영(prod) URL 하드 가드. 옵트인은 "실수로 도는 것" 은 막지만,
      `ALLOW_MUTATING_TESTS=true` 를 켜둔 채 `STAFF_URL` 만 운영으로 바꾼 경우는
      못 막는다. 운영 도메인 패턴이 확인되면 여기에 무조건 차단을 한 겹 더 건다
      (CLAUDE.md `변경성(mutating) 테스트 준비` ① 참고).
    """
    if request.node.get_closest_marker("mutating") is None:
        return
    if not _mutating_allowed():
        pytest.skip(
            "데이터를 바꾸는 TC 라 기본적으로 실행하지 않는다 - "
            "돌리려면 .env 에 ALLOW_MUTATING_TESTS=true 를 적는다"
        )


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
    """테스트가 실패하면 그 자리에서 화면·콘솔 로그를 Allure 리포트에 첨부한다.

    **왜 fixture teardown이 아니라 여기인가** — teardown에서 `allure.attach`를 부르면
    그 첨부는 fixture의 컨테이너에 붙어서 리포트의 "Tear down" 안쪽에 숨는다.
    실패한 이 시점(아직 테스트가 열려 있는 동안)에 붙여야 증거가 그 테스트에 남는다.

    이 시점엔 fixture teardown이 아직 안 돌았으므로 page도 살아있다.

    **setup 단계도 함께 보는 이유** — fixture 안에서 화면 진입이 실패하면 pytest 는
    ERROR(Allure 는 broken)로 끝내는데, `when == "call"` 만 보면 그 경우엔 증거가
    하나도 안 남는다. 2026-09-07 에 현장 서비스 5건이 진입 단계에서 전부 깨졌을 때
    리포트에 스크린샷이 없어서 브라우저를 따로 띄워 메뉴를 확인해야 했다.

    setup 실패 때 `logged_in_page` 가 아직 안 만들어졌으면(로그인 자체가 실패한 경우)
    붙일 화면이 없으므로 조용히 넘어간다.
    """
    rep = yield
    if rep.when in ("setup", "call") and rep.failed:
        # `item.funcargs` 가 아니라 fixture 가 달아둔 값을 쓴다 - funcargs 에는 테스트 함수가
        # 직접 요청한 fixture 만 올라와서, `logged_in_page` 를 다른 fixture(`fs` 등)가
        # 대신 받는 구조에서는 None 이 나온다 (2026-09-07 실측).
        page = getattr(item, "_page", None)
        if page is not None:
            _attach_page_evidence(page, getattr(item, "_console_logs", []), rep.when)
    return rep


def _attach_page_evidence(page: Page, console_logs: list[str], when: str = "call") -> None:
    """실패 시점의 화면 스크린샷·주소와 브라우저 콘솔 로그를 Allure 리포트에 첨부한다.

    첨부 이름에 단계를 적는 이유 — setup 실패는 "검증하다 틀린 것" 이 아니라
    "검증까지 가지도 못한 것" 이라, 스크린샷을 보는 사람이 그 차이를 알아야 한다.

    첨부 자체가 실패해도(이미 닫힌 페이지 등) 테스트 결과를 덮어쓰면 안 되므로
    예외는 삼키고 넘어간다 — 여기서 에러가 나면 정작 원래 실패 원인이 가려진다.
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

    page 와 브라우저 콘솔 로그를 테스트 객체에 달아둔다 — 테스트가 실패하면
    pytest_runtest_makereport 훅이 이걸 꺼내 화면 스크린샷과 함께 리포트에 첨부한다.
    훅에서 `item.funcargs` 로 page 를 찾지 않는 이유는 그 hook 쪽 주석에 적어 두었다.
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
    request.node._page = page

    yield page

    context.close()
