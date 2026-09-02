# 코드 속 함수 정리

`test_login.py`, `conftest.py`, `test_monitor_reseller_filter.py`, `test_vehicle_register_reseller.py`에서 실제로 쓴 함수·메서드만 모았습니다. `HTML-태그-정리.md`가 "화면의 태그"를 다뤘다면, 이 문서는 "그 태그를 조작·검증하는 코드"를 다룹니다. 순서는 실제 테스트가 진행되는 흐름(이동 → 찾기 → 조작 → 기다리기 → 검증)을 따라갑니다.

## 01. 페이지 이동

**`page.goto(url)`**
브라우저 탭을 그 주소로 이동시킵니다. 사람이 주소창에 URL 치고 엔터 치는 것과 같습니다.
```python
page.goto(STAFF_URL)
```
쓰인 곳: 모든 테스트의 첫 줄 — 로그인 화면 또는 STAFF 메인으로 이동

## 02. 요소 찾기 — Locator 만들기

여기 나오는 함수들은 전부 **"화면의 이 요소를 가리키는 위치 정보"**(Locator)를 만들 뿐, 아직 아무 동작도 하지 않습니다. 실제 클릭·입력은 03번에서 다룹니다.

**`page.locator(셀렉터)`**
CSS 셀렉터로 요소를 찾는 가장 기본적인 방법. 태그명·클래스·속성 뭐든 CSS 문법이면 다 됩니다.
```python
page.locator(".spinner").first
page.locator('a[type="lastItem"]')
page.locator("div.column", has_text="검색일부터")
```
`has_text=` 옵션을 주면 "이 셀렉터에 매칭되면서, 이 글자도 포함하는 것"으로 더 좁힐 수 있습니다.

> **`a[type="lastItem"]`이 뭔가**
>
> `[속성="값"]`은 CSS의 **속성 셀렉터**입니다 — "이 태그이면서, 이 속성이 이 값인 것"을 찾습니다. `a[type="lastItem"]`은 "`<a>` 태그 중, `type` 속성값이 정확히 `"lastItem"`인 것"이라는 뜻입니다. 여기서 `type`은 표준 HTML 속성이 아니라 이 사이트가 페이지네이션 버튼 종류를 구분하려고 자체적으로 붙인 값이라, class 대신 이 속성으로 페이지네이션 버튼(`pageItem`·`nextItem`·`lastItem` 등)을 정확히 골라낼 수 있습니다.
> ```html
> <a type="lastItem" value="116">»</a>
> <a type="pageItem" value="5">5</a>
> ```

**`page.get_by_role(role, name=...)`**
CSS 대신 **접근성 역할(role)**로 찾습니다. `role="button"`, `role="link"`, `role="option"`처럼 화면이 실제로 갖고 있는 role 속성(또는 `<button>`/`<a>`처럼 브라우저가 자동 부여하는 역할)을 기준으로 찾는 방식이라, class 이름이 바뀌어도 잘 안 깨집니다. `name=`은 그 요소의 **눈에 보이는 글자**를 가리킵니다(`HTML-태그-정리.md`의 "accessible name" 설명 참고).
```python
page.get_by_role("button", name="로그인")
page.get_by_role("option", name="커넥트", exact=True)
```
`exact=True`를 주면 "글자를 포함"이 아니라 "글자가 정확히 일치"만 찾습니다.

**`page.get_by_text(text)`**
화면에 보이는 텍스트 그대로 찾습니다. role이 애매하거나 그냥 안내 문구를 찾을 때 씁니다.
```python
page.get_by_text("인증번호")
page.get_by_text("오늘", exact=True)
```

**`page.get_by_placeholder(text)`**
`<input placeholder="...">`의 placeholder 글자로 입력창을 찾습니다.
```python
page.get_by_placeholder("아이디")
```

**`locator.filter(has_text=...)`**
이미 찾은 Locator(보통 여러 개 걸린 상태)를, 그중에서도 특정 글자를 포함하는 것으로 다시 좁힙니다. `has_text=` 값에 그냥 문자열을 주면 "포함"으로 걸리고, `re.compile(...)`을 주면 정규식으로 정밀하게 걸립니다.
```python
page.locator("a").filter(has_text=re.compile(r"^차량관리$"))
page.locator("label").filter(has_text="리셀러")
```
`^...$`를 쓴 이유는 `CLAUDE.md`의 "부분 일치 함정" 항목 참고 — `has_text="완료"`라고만 하면 "배정완료"도 걸립니다.

## 03. 여러 개 중에서 고르기

`locator()`나 `get_by_role()`은 조건에 맞는 요소가 여러 개면 그 여러 개를 **한꺼번에** 가리키는 상태가 됩니다(Playwright는 이걸 "strict mode"로 관리해서, 여러 개인 채로 클릭 같은 단일 액션을 시도하면 에러를 냅니다). 아래 함수들로 그중 하나를 콕 집거나, 개수 자체를 확인합니다.

**`.first`**
매칭된 것 중 첫 번째만 가리킵니다.
```python
page.locator(".spinner").first
```

**`.nth(i)`**
매칭된 것 중 `i`번째(0부터 시작)를 가리킵니다.
```python
header_cells.nth(i)
rows.nth(i).locator("td").nth(col_index)
```

**`.count()`**
매칭된 요소가 몇 개인지 **지금 이 순간** 세서 정수로 돌려줍니다. (`expect`처럼 기다려주지 않는, 그 즉시 값입니다 — 06번 참고)
```python
if pagination.count() == 0:
    return
```

## 04. 값 읽어오기

**`.inner_text()`**
요소 안에 사람 눈에 보이는 글자를 문자열로 읽어옵니다. 매칭된 게 정확히 1개일 때만 씁니다(아니면 에러).
```python
cell.inner_text().strip()
```

**`.all_inner_texts()`**
매칭된 요소가 **여러 개**일 때, 그 전부의 텍스트를 리스트로 읽어옵니다. `.inner_text()`가 단수용이면 이건 복수용입니다.
```python
header_texts = page.locator("table").first.locator("thead th").all_inner_texts()
reseller_options = reseller_field.locator('[role="option"] .text').all_inner_texts()
# 결과 예: ['커넥트', 'LG U+']
```

**`.get_attribute(속성명)`**
그 요소의 HTML 속성값을 문자열로 읽어옵니다(속성이 없으면 `None`).
```python
span.get_attribute("colspan")
partner_field.get_attribute("aria-disabled")   # "true" / "false"
```

**`.evaluate(js식)`**
그 요소를 자바스크립트 코드에 직접 넘겨서 실행합니다. Playwright의 다른 메서드로는 안 되는 걸(예: 부모 요소 통째로 HTML 읽기) 확인할 때 최후 수단으로 씁니다.
```python
label.evaluate('el => el.parentElement.outerHTML')
```
디버깅용 조사 스크립트에서만 썼고, 실제 테스트 코드에는 안 남겼습니다 — `HTML-태그-정리.md`에서 언급한 "스크린샷·evaluate로 직접 조사"가 이 메서드입니다.

## 05. 액션 — 화면 조작하기

**`.click()`**
그 요소를 마우스로 클릭합니다.
```python
page.get_by_role("button", name="로그인").click()
```

**`.fill(text)`**
입력창을 비우고 그 자리에 text를 채워 넣습니다(타이핑을 시뮬레이션하는 것보다 빠르고 안정적).
```python
page.get_by_placeholder("아이디").fill(ADMIN_EMAIL)
company_field.locator("input.search").fill(company_name)
```

## 06. 기다리기

**`.wait_for(state=...)`**
그 요소가 특정 상태(`"visible"`, `"hidden"` 등)가 될 때까지 **반복 확인하며** 기다립니다. `timeout`을 넘기면 그 시간 안에 상태가 안 되면 에러를 던집니다.
```python
page.locator(".spinner").first.wait_for(state="hidden", timeout=60_000)
```
`timeout=60_000`은 "무조건 60초 기다려라"가 아니라 "최대 60초까지 반복 확인, 되는 즉시 통과"라는 뜻입니다 — 자세한 설명은 `docs/notes/code-notes/모니터-리셀러-필터-테스트-노트.md`의 "`timeout=60_000`은 무조건 60초 기다리는 게 아니다" 참고.

**`page.wait_for_timeout(ms)`** — 이 코드에서는 안 씀, 참고로만
이름이 비슷해서 헷갈리기 쉬운데, 이건 조건과 무관하게 **무조건 그 시간만큼 그냥 잠드는** 함수입니다. 이 프로젝트는 전부 조건부로 반복 확인하는 `wait_for`/`expect` 방식만 쓰고, 이 함수는 의도적으로 안 씁니다(고정 sleep은 느리거나 불안정한 원인이 되기 쉬움).

## 07. 검증하기 — `expect(...)`

`expect()`는 Playwright가 제공하는 **재시도되는 검증 함수**입니다. 안에 Locator를 넣고, 뒤에 조건 메서드를 붙이는 구조입니다. 조건이 그 순간 안 맞아도 바로 실패시키지 않고, 기본 5초 동안 반복 확인하다가 맞으면 통과, 끝까지 안 맞으면 그때 실패시킵니다 — DOM처럼 **비동기로 늦게 뜨는 대상**은 항상 이걸 씁니다(`CLAUDE.md`의 "assert vs expect" 기준).

**`expect(locator).to_be_visible()` / `.not_to_be_visible()` / `.to_be_hidden()`**
그 요소가 보이는지 / 안 보이는지(공간은 차지할 수 있음, 예: `display:none` 아님) / 아예 숨었는지(`display:none` 등) 확인합니다.
```python
expect(reseller_filter).to_be_visible()
expect(partner_filter).not_to_be_visible()
expect(page.get_by_role("button", name="확인")).to_be_hidden(timeout=OTP_WAIT_SEC * 1000)
```

**`expect(locator).to_have_text(text)` / `.not_to_have_text(text)`**
그 요소의 텍스트가 정확히 그 값인지 / 아닌지 확인합니다(반복 재확인됨 — 값이 비동기로 바뀌는 걸 기다릴 때 특히 유용).
```python
expect(partner_text).to_have_text("커넥트")
expect(partner_text).not_to_have_text("-")
```

**`expect(locator).to_have_attribute(속성명, 값)`**
그 요소의 HTML 속성이 특정 값인지 확인합니다. `.get_attribute()`(04번, 그 순간 값만 읽음)의 "재시도 버전"이라고 보면 됩니다.
```python
expect(partner_field).to_have_attribute("aria-disabled", "true")
```

## 08. `assert` — 파이썬 자체 검증

DOM과 무관한 값(파이썬 변수·계산 결과)을 확인할 때 씁니다. 재시도 없이 **그 순간 딱 한 번**만 보고, 조건이 거짓이면 바로 `AssertionError`를 던집니다.
```python
assert os.path.exists(auth_state)
assert set(reseller_options) == {"커넥트", "LG U+"}, (
    f"[FAIL] 리셀러 선택지가 [커넥트/LG U+]가 아닙니다: {reseller_options}"
)
```
`assert 조건, "메시지"`에서 메시지는 조건이 거짓일 때만 계산되어 에러에 붙습니다 — 자세한 동작은 `docs/notes/자동화-테스트-노트.md`의 "10. `assert`는 조건을 통과하면 PASS를 만드는 건가" 참고.

## 09. 테스트 구조 — pytest

**`@pytest.fixture`**
함수를 "테스트에 필요한 걸 준비해서 건네주는" fixture로 등록합니다. `scope="session"`을 주면 전체 실행에서 1번만, 안 주면(기본값 `function`) 테스트마다 새로 실행됩니다.
```python
@pytest.fixture(scope="session")
def auth_state(browser_type) -> str:
    ...

@pytest.fixture
def logged_in_page(browser, auth_state):
    ...
```

**`@pytest.mark.parametrize("파라미터명", 값목록, ids=...)`**
같은 테스트 함수를 값목록 개수만큼 반복 실행합니다. `ids=`로 한글 대신 영문 테스트 ID를 지정하는 이유는 `CLAUDE.md`에 있는 그대로 — pytest가 한글을 `\uXXXX`로 이스케이프해서 터미널에서 못 알아보기 때문입니다.
```python
@pytest.mark.parametrize("tab_name", MONITOR_TABS, ids=MONITOR_TAB_IDS)
def test_TC084_monitor_reseller_filter_visible(logged_in_page, tab_name):
    ...
```

**`pytest.skip(이유)`**
그 테스트를 "검증 불가"로 건너뜁니다. 언제 써야 하는지는 `CLAUDE.md`의 "pytest.skip 사용 기준" 참고 — "데이터가 아예 없어서 검증 자체가 불가능"할 때만 쓰고, "필터링 결과가 0건"처럼 실패일 수 있는 상황엔 안 씁니다.
```python
pytest.skip(f"{tab_name} 탭에 조회할 데이터가 아예 없어 리셀러 필터를 검증할 수 없음")
```

## 10. 브라우저 다루기

**`browser_type.launch(headless=False)`**
새 브라우저 프로세스를 직접 하나 켭니다. `headless=False`를 주면 창이 실제로 보입니다(사람이 OTP를 직접 입력해야 하는 로그인 전용 브라우저에 씀).
```python
login_browser = browser_type.launch(headless=False)
```

**`browser.new_context(...)`**
그 브라우저 안에 독립된 세션(쿠키가 서로 안 섞이는 "시크릿 창" 같은 것)을 하나 만듭니다. `storage_state=`를 주면 저장해둔 로그인 정보를 그 세션에 바로 적용합니다.
```python
context = browser.new_context(storage_state=auth_state)
```

**`context.new_page()`**
그 세션 안에 새 탭을 하나 엽니다.
```python
page = context.new_page()
```

**`context.storage_state(path=...)`**
지금 세션의 쿠키·로그인 상태를 파일로 저장합니다. `auth.json`이 이렇게 만들어집니다.
```python
context.storage_state(path=AUTH_STATE_PATH)
```

## 11. 그 외 자주 나오는 파이썬 기본 함수

**`os.getenv("KEY", 기본값)`**
환경변수(`.env`에서 읽어온 값)를 가져옵니다. 기본값은 생략 가능하며, 생략하면 없을 때 `None`을 돌려줍니다.
```python
STAFF_URL = os.getenv("STAFF_URL")
OTP_WAIT_SEC = int(os.getenv("OTP_WAIT_SEC", "180"))
```

**`os.path.exists(경로)`**
그 경로에 파일/폴더가 실제로 있는지 True/False로 확인합니다.
```python
if not os.path.exists(path):
```

**`re.compile(패턴)`** / **`re.escape(문자열)`**
`re.compile`은 정규식 패턴을 만들어서 `has_text=` 같은 곳에 넘길 때 씁니다. `re.escape`는 변수 안에 정규식에서 특별한 의미를 가진 문자(`.`, `(` 등)가 들어있어도 그냥 "글자 그대로"로 취급하게 이스케이프 처리해줍니다 — 업체 이름(`(주)...` 등)처럼 괄호가 실제로 들어있는 문자열을 안전하게 정규식에 끼워 넣을 때 필요합니다.
```python
re.compile(r"^차량관리$")
re.compile(f"^{re.escape(label_text)}$")
```

**`json.load(f)`**
열어둔 파일을 JSON으로 파싱해서 파이썬 dict/list로 돌려줍니다.
```python
data = json.load(f)
```

**`time.time()`**
지금 시각을 숫자(1970년 1월 1일부터 지난 초)로 돌려줍니다. 쿠키 만료 시각과 비교할 때 씁니다.
```python
now = time.time()
```

**`set(...)`**
리스트를 집합으로 바꿉니다 — 순서를 없애고 중복을 제거합니다. "정확히 이 값들만 있는지"를 순서 상관없이 비교하고 싶을 때 유용합니다.
```python
assert set(reseller_options) == {"커넥트", "LG U+"}
```

**`sorted(집합_또는_리스트)`**
정렬된 리스트로 돌려줍니다. 집합은 원래 순서가 없어서, 화면에 표시하거나 순서대로 순회하려면 정렬이 필요합니다.
```python
return sorted({1, total_pages, (1 + total_pages) // 2})
```

---
`test_login.py` · `conftest.py` · `test_monitor_reseller_filter.py` · `test_vehicle_register_reseller.py` 전체를 훑어서 정리했습니다. 개념 설명(fixture가 정확히 뭔지, scope 차이 등)은 `docs/notes/자동화-테스트-노트.md`에 더 자세히 있습니다.
