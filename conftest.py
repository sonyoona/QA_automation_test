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

# 데이터를 바꾸는 테스트를 돌려도 되는 곳. **여기 없는 주소면 무조건 차단한다.**
#
# 화이트리스트인 이유 - "운영이면 막는다" 로 만들려면 운영 도메인이 어떻게 생겼는지
# 알아야 하는데 지금 모른다. 추측해서 적으면 두 방향으로 틀린다. 너무 좁으면(`"prod" in url`)
# 운영이 그렇게 안 생겼을 때 **안 막히고**, 너무 넓으면 dev 까지 막혀 못 돌린다.
# 뒤집어서 "아는 곳이 아니면 막는다" 로 두면 **운영 주소를 몰라도 되고**, 나중에 스테이징이나
# 새 환경이 생겨도 처음 보는 주소는 자동으로 막힌다. 옵트인 게이트와 같은 원칙이다 -
# 기본값을 안전한 쪽으로 두고, 틀리더라도 "안 돌아감" 쪽으로 틀리게 한다.
#
# dev 주소가 바뀌면 여기를 고쳐야 한다. 안 고치면 mutating 이 안 돌 뿐이라 안전하다.
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
    """데이터를 바꾸는 테스트를 돌려도 되는가. 켜는 방법이 둘이다.

        pytest -m mutating --allow-mutating -v     <- 권장. 이번 실행에만 산다
        .env 또는 셸에 ALLOW_MUTATING_TESTS=true   <- CI·반복 실행용

    **플래그를 권장하는 이유는 "끄는 것을 잊을 수가 없어서"** 다. `.env` 에 적으면
    지울 때까지 남고, 셸 환경변수는 그 터미널 탭이 닫힐 때까지 남는다. 둘 다 켜둔 채
    잊으면 게이트가 없는 것과 같아진다. 플래그는 그 명령 한 줄에만 살고, 무엇을
    허용했는지가 명령과 리포트에 그대로 보인다.

    환경변수를 읽을 때마다 확인하는 이유 - 모듈 상수로 굳혀두면 실행 중에 바꿔도
    안 먹혀서 "왜 아직 skip 되지" 를 한참 찾게 된다. `load_dotenv()` 는 기본이
    `override=False` 라 **셸에 이미 있는 값이 `.env` 를 이긴다** (2026-09-09 실측).
    """
    if config.getoption("--allow-mutating"):
        return True
    return os.getenv("ALLOW_MUTATING_TESTS", "").strip().lower() == "true"


@pytest.fixture(autouse=True)
def _mutating_gate(request: pytest.FixtureRequest) -> None:
    """`@pytest.mark.mutating` 이 붙은 테스트는 명시적으로 켜야만 돈다 (옵트인).

    **마커만으로는 부족하기 때문에 있다.** 마커는 "고를 수 있게" 해주는 것이지
    "모르고 돌리는 것을 막는" 장치가 아니다. `-m "not mutating"` 이 안 붙는 경로가
    이만큼 있고, 전부 dev 데이터를 실제로 바꾼다.

        pytest -v · pytest --lf · pytest test_vehicle_company_transfer.py
        PyCharm 의 실행 버튼 · 새로 온 사람 · 6개월 뒤의 나

    그래서 기본값을 "안 함" 으로 두고, 켠 사람만 돌 수 있게 한다. 켜는 방법과
    각각이 얼마나 오래 사는지는 `_mutating_allowed()` 참고 - **플래그를 권장한다.**

    `autouse=True` 라 모든 테스트가 이걸 거치지만, 마커가 없으면 즉시 돌려보내므로
    읽기 전용 TC 에는 비용이 없다. 이 fixture 는 의존이 없어서 `logged_in_page` 보다
    **먼저** 돌고, 그래서 차단될 때는 브라우저가 아예 안 뜬다.

    **접속처 검사가 허용보다 먼저다** (2026-09-09 추가). 옵트인은 "모르고 도는 것" 은
    막지만 "알고 돌렸는데 대상이 운영인 것" 은 못 막는다. 각각은 멀쩡한 판단인데
    조합이 사고가 되는 경로가 있다.

        ① 운영 화면을 볼 일이 있어 `.env` 의 STAFF_URL 을 운영으로 바꿔 둔다
        ② 며칠 뒤 이관 TC 를 돌리려고 --allow-mutating 을 붙인다
        ③ 실제 고객 차량의 소속 업체가 바뀐다

    그래서 `MUTATING_ALLOWED_HOSTS` 에 없는 주소면 **허용을 켰든 말든 막는다.**
    `skip` 이 아니라 `fail` 인 이유 - skip 은 "조건이 안 맞아 안 했다" 는 정상 상태인데,
    이건 정상이 아니라 **사고 직전**이라 빨간불이 나야 사람이 알아챈다.

    ★ 검사 순서가 "허용 -> 접속처" 인 것은 일부러다. 접속처를 먼저 보면, 허용을 켜지도
      않은 평범한 `pytest -v` 가 낯선 환경에서 **8건 전부 빨간불**이 된다 - 어차피 안 돌
      테스트인데 시끄럽고, 그러면 사람이 이 가드를 약하게 만들려 든다. 안전성은 같다:
      허용이 꺼져 있으면 mutating 은 애초에 안 돈다. **정말 돌 뻔한 순간에만** 끊는다.
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
    """auth.json이 있고, 안에 든 쿠키가 아직 만료 전인지 확인.

    ★ 이것만으로는 "로그인 상태" 를 판정할 수 없다. 파일에 적힌 만료 시각을 보는 것뿐이라
      서버가 세션을 이미 끊었는지는 알 수 없고, 세션 쿠키(`expires == -1`)는 이 함수가
      **영원히 살아 있다고 답한다.** 실제 판정은 `_session_alive()` 가 화면에 물어서 한다 -
      이 함수는 그 앞의 값싼 예비 검사다 (2026-09-10 실측, 그쪽 docstring 참고).
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


def _session_alive(browser_type: BrowserType, path: str) -> bool:
    """저장된 세션으로 **실제로 로그인이 되는지** 화면에 물어본다.

    ★ 쿠키 만료 시각만 믿으면 안 된다 - 2026-09-10 실측. auth.json 의 쿠키는 11:54 까지
      유효했는데 10:01 에 시작한 전체 실행이 **전부 ERROR** 였다. 서버가 그 세션을 이미
      무효화했기 때문이다(계정당 단일 세션 - 사람이 브라우저로 같은 계정에 로그인하거나
      pytest 를 두 개 돌리면 앞 세션이 끊긴다. `CLAUDE.md` "스택 & 실행" 참고).

      로컬 파일만 보는 `_auth_state_is_fresh` 는 그걸 알 수가 없어서 "살아 있다" 고 답했고,
      그래서 **재로그인이 일어나지 않았다.** 사람은 2FA 입력 창이 뜨기를 기다렸는데 화면은
      안 뜨고, 모든 TC 가 로그인 화면에서 GNB 를 기다리다 30초씩 타임아웃했다 -
      증상이 '전부 실패' 라 코드 버그로 보이지만 원인은 세션이다.

    그래서 파일이 아니라 화면에 묻는다. **테스트가 실제로 의존하는 것과 같은 신호**(GNB 상위
    메뉴)를 보므로 새로 단정하는 것이 없다 - 로그인 화면에는 이 링크가 없어서 타임아웃되고,
    그것을 '세션 죽음' 으로 읽는다.

    비용은 headless 브라우저 1회(약 3~5초)이고, 막는 것은 20분짜리 전체 ERROR 실행이다.
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

    검사가 둘인 이유 - `_auth_state_is_fresh` 는 파일만 보는 값싼 예비 검사고(브라우저를
    안 띄운다), `_session_alive` 가 화면에 물어보는 진짜 판정이다. 앞것이 통과해도
    뒷것이 막을 수 있고, 그때는 2FA 로그인 창이 뜬다.

    **로그인 동안에는 pytest 의 출력 가로채기를 잠시 끈다.** `pytest -v` 는 기본적으로
    stdout 을 가둬두므로, 끄지 않으면 `_login_and_save` 의 "인증번호를 직접 입력해주세요"
    안내가 사람에게 안 보인다 - 창만 덩그러니 뜨고 얼마나 기다려주는지 알 수가 없다.
    `-s` 로 전체를 여는 것과 달리 이 구간만 열어서, 다른 TC 의 리포트는 깨끗하게 둔다.
    """
    if _auth_state_is_fresh(AUTH_STATE_PATH) and _session_alive(browser_type, AUTH_STATE_PATH):
        return AUTH_STATE_PATH

    # 낡은 세션 파일은 남겨두지 않는다 - `_login_and_save` 가 새로 덮어쓰지만, 로그인이
    # 중간에 실패하면 이 파일이 다음 실행에서 또 "예비 검사 통과" 로 시간을 버리게 한다.
    if os.path.exists(AUTH_STATE_PATH):
        os.remove(AUTH_STATE_PATH)

    # `getplugin` 은 캡처를 시작시키는 게 아니라 **이미 일하고 있는 그 객체**를 받아온다.
    # import 로 새로 만들면 지금까지 가둬둔 출력을 모르는 딴 객체가 되어 아무 일도 안 한다.
    # None 은 `-p no:capture` 로 캡처 플러그인 자체를 뺐을 때만 나온다 (`-s` 여도 객체는 있다).
    capman = pytestconfig.pluginmanager.getplugin("capturemanager")
    if capman is not None:
        # in_=True 는 stdin 도 함께 연다. 지금은 인증번호를 터미널이 아니라 브라우저 창에
        # 치므로 **효과가 없다** - pytest 의 대화형 예제가 이렇게 쓰므로 관례를 따른 것이다
        # (CLAUDE.md "관례이고 비용이 0이면" 참고). 안 열어도 멈추지 않고 OSError 로 즉시
        # 죽으므로, 이걸 근거로 '위험해서 넣었다' 고 읽지 말 것.
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
