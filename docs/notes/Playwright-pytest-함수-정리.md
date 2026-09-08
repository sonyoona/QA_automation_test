# 코드 속 함수 정리

`test_login.py`, `conftest.py`, `test_monitor_reseller_filter.py`, `test_vehicle_register_reseller.py`, `test_vehicle_edit_reseller.py`, `test_vehicle_company_transfer.py`, `test_field_service.py`, `pages/field_service_page.py`에서 실제로 쓴 함수·메서드·데코레이터만 모았습니다. `HTML-태그-정리.md`가 "화면의 태그"를 다뤘다면, 이 문서는 "그 태그를 조작·검증하는 코드"를 다룹니다. **여기 있는 것은 Playwright·pytest·파이썬이 원래 주는 도구들**이고, 우리가 직접 만든 함수(`_find_hidden` 등)는 16번에 어디를 보면 되는지만 적어두었습니다. 순서는 실제 테스트가 진행되는 흐름(import → 이동 → 찾기 → 조작 → 기다리기 → 검증)을 따라갑니다.

## 00. Import 정리 — 이 줄들이 왜 있나

파일 맨 위의 `import` 줄들은 "이 파일에서 이런 기능들을 갖다 쓰겠다"는 선언입니다. 어떤 import가 어떤 기능 때문에 필요한지 연결해서 보면 아래 챕터들이 더 잘 이해됩니다.

```python
import os
import re

import pytest
from playwright.sync_api import expect
```

**`import os`**
`os.getenv(...)`(11번), `os.path.exists(...)`(11번)를 쓰려고 가져옵니다. `.env` 값을 읽거나 파일 존재 여부를 확인할 때 씁니다.

**`import re`**
`re.compile(...)`, `re.escape(...)`(11번)를 쓰려고 가져옵니다. Locator를 정규식으로 정밀하게 좁힐 때(02번의 `.filter(has_text=re.compile(...))`) 필요합니다.

**`import pytest`**
`@pytest.fixture`, `@pytest.mark.parametrize`, `pytest.skip(...)`(09번)처럼 **pytest가 제공하는 기능**을 쓰려면 이 import가 있어야 합니다. 테스트 함수 자체(`def test_...`)는 pytest 프레임워크가 알아서 찾아 실행해주기 때문에 import 없이도 되지만, `parametrize`나 `skip`처럼 **직접 이름을 써서 불러야 하는 도구**는 import가 필요합니다. 그래서 parametrize·skip을 안 쓰는 파일(`test_vehicle_edit_reseller.py`, `test_vehicle_company_transfer.py`)에는 이 import 자체가 없습니다.

**`from playwright.sync_api import expect`**
말씀하신 대로 정확히 07번의 `expect(...)`를 쓰려고 가져오는 import입니다. Playwright가 제공하는 것 중에서도 "검증 전용 도구"만 콕 집어 가져오는 것이라, `page`나 `browser` 같은 다른 Playwright 객체들과는 달리 **직접 import해야만** 쓸 수 있습니다(`page`/`browser`는 pytest-playwright가 fixture로 자동 건네주지만, `expect`는 그런 fixture가 아니라 그냥 함수라서 직접 가져와야 합니다).

**`from dotenv import load_dotenv`** — `conftest.py`에서만 사용
`.env` 파일의 내용을 읽어서 환경변수로 등록해주는 외부 라이브러리 함수입니다. `conftest.py` 맨 위에서 딱 한 번(`load_dotenv()`) 호출하면, 그 뒤로는 어느 테스트 파일에서든 `os.getenv("STAFF_URL")`처럼 값을 꺼내 쓸 수 있게 됩니다.
```python
from dotenv import load_dotenv
load_dotenv()
```
자세한 설명은 `docs/notes/자동화-테스트-노트.md`의 ".env와 .env.example" 항목 참고.

**`import allure`** — 리포트 데코레이터를 쓰는 파일
`@allure.title`, `@allure.step`, `allure.attach(...)`(13번)를 쓰려면 필요합니다. pytest처럼 "프레임워크가 알아서 찾아주는" 게 아니라 **이름을 직접 써서 부르는 도구**라 import가 있어야 합니다.

**`from playwright.sync_api import Locator, Page, expect`** — 타입 어노테이션까지 쓰는 파일
`expect`는 검증용 함수(07번), `Page`·`Locator`는 **함수 시그니처에 타입을 적으려고** 가져옵니다(12번). 값을 만들려는 게 아니라 "이 자리에 오는 건 이런 타입이다"라고 적는 용도라, 가져와도 코드 동작은 달라지지 않습니다 — PyCharm 자동완성과 사람이 읽기 위한 것입니다.
```python
def _expect_rendered(locator: Locator, what: str) -> None:
```

**`from pages.field_service_page import FieldServicePage`** — 화면 객체를 쓰는 파일
`pages/` 폴더에 만들어둔 화면 객체(14번)를 가져옵니다. `pages.field_service_page`는 "pages 폴더 안의 field_service_page.py"라는 뜻이고, 그 안의 `FieldServicePage` 클래스를 꺼내옵니다. 폴더가 import 경로가 되려면 그 안에 `__init__.py`가 있어야 합니다(비어 있어도 됩니다).

**다른 테스트 파일에서 직접 가져오기** — `test_vehicle_company_transfer.py`에서 새로 쓴 방식
```python
from test_vehicle_edit_reseller import CAR_PARTNER_CONNECT, _get_edit_field, _open_carmgmt_edit_modal
```
파이썬은 "테스트 파일"과 "그냥 파이썬 모듈"을 구분하지 않습니다 — `test_vehicle_edit_reseller.py`도 결국 평범한 `.py` 파일이라, 다른 파일에서 `import`로 그 안의 함수·변수를 그대로 가져다 쓸 수 있습니다. 두 파일이 완전히 같은 모달(차량관리>차량관리 수정)을 다루기 때문에, 헬퍼 함수를 복사해서 새로 만드는 대신 원본을 그대로 재사용한 것입니다. 밑줄로 시작하는 이름(`_get_edit_field` 등)이나 `test_`로 시작 안 하는 이름만 가져왔기 때문에, pytest가 이 파일을 수집할 때 `test_vehicle_edit_reseller.py`의 테스트 함수를 중복으로 다시 실행하는 일은 없습니다.

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

**`page.get_by_test_id(값)`**
`data-testid` 속성값으로 찾습니다. 프론트가 **테스트용으로 일부러 붙여준 이름**이라, 화면 문구나 class가 바뀌어도 안 깨집니다. 현장 서비스 화면이 이 방식을 쓰고 있습니다(testid 59개).
```python
self.page.get_by_test_id("fs-page__root")
self.dialog.get_by_test_id("fs-new__submit-button")   # 팝업 안으로 범위를 좁혀서
```
**주의 — testid로 찾았다는 것이 "보인다"를 뜻하지는 않습니다.** `data-testid`는 화면에 안 보이는 속성이라 `display:none`인 요소도 그대로 잡힙니다. 노출 검증은 `expect(...).to_be_visible()`로 따로 해야 합니다(`CLAUDE.md`의 Locator 우선순위 표 참고).

기본 속성명은 `data-testid`인데, 회사가 `data-qa` 같은 다른 이름을 쓰면 제품 코드를 고치는 게 아니라 Playwright 쪽을 한 줄로 맞춥니다.
```python
playwright.selectors.set_test_id_attribute("data-qa")
```

**`[속성^="값"]` — "이 문자열로 시작하는" 속성 셀렉터**
`^=`는 CSS에서 "~로 시작한다"는 뜻입니다. testid에 PK가 붙어 있는 행들을 **한꺼번에** 잡을 때 씁니다.
```python
# fs-table__row--10679, fs-table__row--10677 ... 을 전부 잡는다
self.page.locator('[data-testid^="fs-table__row--"]')
```
`get_by_test_id()`는 값이 정확히 일치해야 해서 이건 못 합니다. PK가 뒤에 붙는 구조라 앞부분만 고정해야 하므로 `locator()` + `^=`를 씁니다.

| 표기 | 뜻 |
|---|---|
| `[data-testid="x"]` | 정확히 `x` |
| `[data-testid^="x"]` | `x`로 **시작** |
| `[data-testid$="x"]` | `x`로 **끝남** |
| `[data-testid*="x"]` | `x`를 **포함** |

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

**`locator.filter(has=다른_locator)`**
`has_text=`가 "글자"로 좁히는 거라면, `has=`는 **"이 Locator를 자식으로 갖고 있는 것"**으로 좁힙니다. 값이 문자열이 아니라 또 다른 Locator라는 게 다른 점입니다.
```python
page.locator("section").filter(has=page.locator('input[name="carNumber"]'))
```
차량 수정 모달은 기존 목록 화면 위에 겹쳐서 뜨는데, 페이지에 `<section>`이 여러 개 있을 수 있어서 "그 안에 `carNumber` 입력창을 갖고 있는 `<section>`"으로 정확히 지금 열린 모달만 골라낼 때 씁니다.

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

**`.all()`**
매칭된 요소들을 **파이썬 리스트로** 펼칩니다. `.first`/`.nth(i)`가 하나를 고르는 것이라면, 이건 전부를 하나씩 다루려고 꺼내는 것입니다.
```python
[el.get_attribute("data-testid").split("--")[1] for el in self.rows.all()]
# ['10679', '10677', ...]
```
**주의 — `.all()`은 그 순간의 DOM을 그대로 펼칩니다.** `expect()`처럼 재시도하지 않아서, 아직 안 그려진 표에 대고 부르면 **빈 리스트가 그냥 나옵니다**(에러가 아닙니다). 그래서 표가 다 그려진 뒤에 불러야 합니다 — 현장 서비스 화면은 `wait_table_settled()`로 그것을 보장한 다음에 `row_ids()`가 `.all()`을 씁니다.

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

**`.is_visible()`**
그 요소가 지금 화면에 보이는지를 `True`/`False`로 돌려줍니다. **재시도가 없습니다** — 그 순간의 DOM을 그대로 읽습니다.
```python
return [label for label, attr in fields if not getattr(owner, attr).is_visible()]
```
`expect(...).to_be_visible()`과 목적이 비슷해 보이지만 성격이 완전히 다릅니다.

| | `expect(...).to_be_visible()` | `.is_visible()` |
|---|---|---|
| 재시도 | **한다**(기본 5초까지) | 안 한다 |
| 결과 | 안 보이면 **실패로 끝냄** | `False`를 돌려줄 뿐 |
| 쓰는 곳 | 검증 그 자체 | 여러 요소를 훑어 **빠진 것을 모을 때** |

13개 항목을 전부 `expect`로 감싸면 없는 항목마다 타임아웃을 다 기다리고, 첫 번째에서 멈춰서 나머지가 어떤 상태인지 알 수 없습니다. 그래서 **대표 요소 하나만 `expect`로 기다려 렌더 완료를 확인한 뒤**, 나머지는 `.is_visible()`로 즉시 훑어 빠진 것을 한 번에 보고합니다(`test_field_service.py`의 `_expect_rendered` + `_find_hidden`).
이 순서를 지키지 않으면 **화면이 안 그려졌을 뿐인데 "13개가 다 없다"**고 나옵니다.

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

**`page.evaluate(js식)`** — 요소가 아니라 **페이지 전체**에 대고 실행
`locator.evaluate()`가 "이 요소를 넘겨서 실행"이라면, 이건 그냥 브라우저 안에서 코드를 돌립니다. 현장 서비스에서는 대기용 스냅샷 값을 지우는 데 씁니다.
```python
self.page.evaluate("() => { window.__fsTableSnapshot = undefined; }")
```

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

**`page.wait_for_function(js식, arg=..., polling=..., timeout=...)`**
`wait_for(state=...)`로 표현할 수 없는 조건을 기다릴 때 씁니다. 조건을 **브라우저 안에서** 평가하기 때문에 파이썬↔브라우저 왕복이 없습니다.
```python
self.page.wait_for_function(
    """(emptyText) => {
        const ids = [...document.querySelectorAll('[data-testid^="fs-table__row--"]')]
            .map(e => e.getAttribute('data-testid')).join(',');
        ...
    }""",
    arg=self.EMPTY_TEXT,   # 파이썬 값을 js 함수의 인자로 넘긴다
    polling=300,           # 300ms 간격으로 다시 평가
    timeout=30_000,
)
```

| 인자 | 뜻 |
|---|---|
| `arg=` | 파이썬 쪽 값을 js 함수의 **인자로** 넘긴다. js 문자열 안에 값을 직접 이어붙이면 따옴표·이스케이프가 깨지기 쉬워서 이 통로를 쓴다 |
| `polling=` | 다시 평가하는 간격(ms). 안 주면 화면 갱신 주기(약 16ms)마다 평가한다 |
| `timeout=` | 최대 대기. 넘으면 에러 |

**`polling` 값을 일부러 300ms로 준 이유** — 현장 서비스의 `wait_table_settled()`는 "행 목록이 **연속 2회 같을 때**"를 완료로 봅니다. 기본값(16ms)이면 두 번이 거의 같은 순간이라 "안정됐다"는 근거가 못 됩니다. 300ms 간격으로 두 번 같아야 갱신이 끝났다고 볼 수 있습니다.

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

**`expect(locator).to_have_attribute(속성명, 값)`** / **`.not_to_have_attribute(속성명, 값)`**
그 요소의 HTML 속성이 특정 값인지 / 아닌지 확인합니다. `.get_attribute()`(04번, 그 순간 값만 읽음)의 "재시도 버전"이라고 보면 됩니다.
```python
expect(partner_field).to_have_attribute("aria-disabled", "true")
expect(reseller_field).not_to_have_attribute("aria-disabled", "true")
```
`not_to_have_attribute`가 필요했던 이유: 차량 수정 모달에서는 필드가 활성화됐을 때 `aria-disabled` 속성이 `"false"`로 채워지는 게 아니라 **속성 자체가 아예 없어집니다.** "정확히 `"false"`인지"를 확인하면 이 경우를 놓치지만, "`"true"`가 아닌지"를 확인하면 속성이 없는 경우까지 정확히 잡아냅니다.

**`expect(locator).to_have_value(값)`**
`<input>`의 현재 입력값이 정확히 그 값인지 확인합니다(반복 재확인됨). 텍스트 요소를 보는 `to_have_text`와 달리, 실제 폼 입력창(`<input>`)의 `value` 속성을 봅니다.
```python
expect(car_number_input).to_have_value(car_number, timeout=15_000)
```
차량 수정 모달은 열리자마자 상세 데이터를 비동기로 받아오기 때문에, "차량 번호 입력값이 실제로 그 차량 걸로 찼는지"를 이걸로 확인해서 "이제 이 차량의 데이터 로딩이 끝났다"는 신호로 씁니다.

**`expect(locator).to_have_count(개수)`**
매칭된 요소의 **개수**가 정확히 그 숫자인지 확인합니다(반복 재확인됨). `.count()`(03번)가 그 순간의 스냅샷이라면, 이건 그 개수가 될 때까지 기다려주는 버전입니다.
```python
reseller_options = reseller_field.locator('[role="option"] .text')
expect(reseller_options).to_have_count(2)
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

**`page.on(이벤트명, 콜백)`**
그 탭에서 특정 일이 생길 때마다 함수를 부르도록 등록합니다. 브라우저 콘솔 로그를 계속 모아두는 데 씁니다 — 테스트가 실패했을 때 리포트에 첨부하려는 것입니다.
```python
console_logs: list[str] = []
page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
page.on("pageerror", lambda exc: console_logs.append(f"[pageerror] {exc}"))
```
등록해두면 그 뒤로 알아서 쌓입니다 — 테스트 쪽에서 따로 부를 필요가 없습니다. `"console"`은 사이트가 찍은 콘솔 출력, `"pageerror"`는 사이트에서 터진 자바스크립트 에러입니다.

**`page.screenshot(full_page=True)`**
그 순간 화면을 PNG **바이트**로 돌려줍니다(파일로 저장하려면 `path=`를 줍니다). `full_page=True`면 스크롤을 내려야 보이는 부분까지 전부 담습니다.
```python
allure.attach(page.screenshot(full_page=True), name="실패 시점 화면", ...)
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

**`리스트.index(값)`**
리스트 안에서 그 값이 몇 번째(0부터)에 있는지 찾아줍니다. 값이 없으면 에러가 납니다.
```python
headers = page.locator("table").first.locator("thead th").all_inner_texts()
return headers.index(header_text)
```
`all_inner_texts()`(04번)로 헤더 글자들을 리스트로 뽑아온 다음, 원하는 헤더 글자가 몇 번째 컬럼인지 찾을 때 씁니다 — 컬럼 위치를 숫자로 하드코딩하지 않고 헤더 텍스트로 찾아내는 패턴의 핵심 부분입니다.

**`getattr(객체, "속성명")`**
객체의 속성을 **이름 문자열로** 꺼냅니다. `owner.reseller_select`라고 직접 쓰는 것과 결과는 같은데, 속성명이 변수에 담겨 있을 때 쓸 수 있다는 게 다릅니다.
```python
FILTER_FIELDS = [("리셀러", "reseller_select"), ("업체", "company_select"), ...]

for label, attr in fields:
    getattr(owner, attr).is_visible()      # owner.reseller_select.is_visible() 와 같다
```
필터 항목이 13개라 하나씩 나열하면 같은 모양의 줄이 13번 반복되는데, (화면에 보이는 이름, 속성명) 짝을 표로 두고 이렇게 돌리면 한 줄로 끝납니다. **화면에 보이는 이름을 같이 들고 다니는 게 요점**입니다 — 그래야 빠진 항목을 `['GPS 음영', '임시등록만']`처럼 사람이 읽는 이름으로 보고할 수 있습니다.

세 번째 인자로 기본값을 주면 속성이 없을 때 에러 대신 그 값을 돌려줍니다.
```python
page = getattr(item, "_page", None)        # 없으면 None
```

**`raise ... from e` — 원인을 붙여서 다시 던지기**
예외를 잡아 더 친절한 메시지로 바꿔 던지되, **원래 예외도 같이 남깁니다**.
```python
try:
    expect(locator).to_be_visible()
except AssertionError as e:
    raise AssertionError(f"[FAIL] {what} 이(가) 끝내 노출되지 않아 ...") from e
```
`expect`의 기본 실패 메시지는 셀렉터만 보여줘서 리포트만 봐서는 그게 어느 항목인지 알 수 없습니다. 한글 이름을 담아 다시 던지되 `from e`를 붙이면 원래 메시지(어느 셀렉터가 몇 초 만에 실패했는지)도 함께 남아, 둘 다 볼 수 있습니다. `from e`를 빼면 원래 예외가 사라집니다.

## 12. 타입 어노테이션 (type annotation)

지금까지 나온 함수들은 전부 **"무슨 기능을 하는가"**였다면, 이건 조금 다릅니다 — 그 함수에 **"어떤 타입의 값이 들어오고 나가는지"**를 코드 자체에 적어두는 문법입니다. 새 기능이 아니라, 이미 있는 함수들 위에 "타입 표시"를 얹는 것이라 이 문서 맨 뒤에 따로 뺐습니다.

```python
def _get_edit_field(page: Page, label_text: str) -> Locator:
    ...
```

**매개변수 뒤의 `: 타입`** — `page: Page`는 "page라는 매개변수엔 Page 타입의 값이 들어온다"는 뜻입니다.
**화살표 뒤의 `-> 타입`** — `-> Locator`는 "이 함수는 끝나면 Locator 타입의 값을 돌려준다"는 뜻입니다.

**왜 쓰는가**

- **PyCharm 자동완성이 정확해집니다.** `page: Page`라고 타입을 명시해두면, 그 이후 `page.`을 입력할 때 실제로 `Page` 객체가 갖고 있는 메서드(`.goto`, `.locator`, `.get_by_role`...) 목록이 정확히 뜹니다. 타입이 없으면 PyCharm이 이 값이 뭔지 몰라서 자동완성이 부정확하거나 아예 안 뜹니다.
- **실수를 실행 전에 잡아줍니다.** 문자열이 들어와야 할 자리에 실수로 다른 타입을 넘기면 PyCharm이 코드를 돌려보기도 전에 밑줄로 경고해줍니다.
- **함수 자체가 설명서가 됩니다.** `def _select_reseller(page, value):`만 보면 `value`에 뭘 넣어야 하는지 함수 안을 읽어봐야 알 수 있는데, `def _select_reseller(page: Page, value: str) -> None:`라고 적혀 있으면 "리셀러 이름 문자열을 넣으면 되는구나"가 코드만 보고 바로 보입니다.

> **주의 — 파이썬은 이 타입을 강제로 검사하지 않습니다**
>
> `page: Page`라고 적어놔도, 실행 시점에 파이썬이 "진짜 Page 타입 맞아?"라고 검사하지는 않습니다(자바·타입스크립트 같은 언어와 다른 점). 어디까지나 **PyCharm 같은 에디터와 사람이 읽으라고 남기는 힌트**입니다. 강제로 검사하고 싶다면 `mypy`·`pyright` 같은 별도 도구를 돌려야 하는데, 이 프로젝트에서는 아직 그 단계까지는 안 쓰고 "에디터 자동완성 + 문서화" 용도로만 쓰고 있습니다.

**어디서 타입을 가져오나** — Playwright가 제공하는 타입은 `playwright.sync_api`에서 그대로 import합니다.
```python
from playwright.sync_api import Page, Locator, Browser, BrowserType, expect
```
`page`(탭), `Locator`(찾은 요소), `browser`(브라우저 프로그램), `browser_type`(브라우저 엔진 발사대) — 이미 02·03·10번에서 다룬 그 객체들이 각각 이 타입입니다.

**`Generator[...]` — `yield`가 있는 함수의 반환 타입**

`logged_in_page` fixture는 `yield`를 쓰기 때문에(06번의 "fixture는 준비→건네주고→정리" 패턴), 보통 함수와는 반환 타입 표기가 다릅니다.

```python
from typing import Generator

@pytest.fixture
def logged_in_page(browser: Browser, auth_state: str) -> Generator[Page, None, None]:
    context = browser.new_context(storage_state=auth_state)
    page = context.new_page()
    yield page          # ← 1번째 자리(Page): 여기서 밖으로 내보내는 값의 타입
    context.close()
```

`Generator[YieldType, SendType, ReturnType]` 세 자리는 각각 다릅니다:

| 자리 | 이름 | 뜻 | 이 프로젝트에서 |
|---|---|---|---|
| 1번째 | YieldType | `yield`로 내보내는 값의 타입 | `Page` — `yield page` |
| 2번째 | SendType | 제너레이터에 `.send(값)`으로 넣어줄 값의 타입 | `None` — 아무도 `.send()` 안 씀 |
| 3번째 | ReturnType | 함수가 끝날 때 `return`으로 내보내는 값의 타입 | `None` — 별도 return 값 없음 |

**`_login_and_save(browser_type: BrowserType) -> None:`처럼 그냥 `None`인 함수와의 차이**는, 함수 안에 `yield`가 있냐 없냐입니다. `yield`가 하나라도 있으면 그 함수는 "제너레이터 함수"가 되어 반환 타입을 `Generator[...]`로 적어야 하고, `yield` 없이 `return`만 쓰거나 아무것도 안 돌려주면 그냥 `None`이나 `str` 같은 단순한 타입 하나로 충분합니다.

### 세 자리를 실제로 다 써보면 — 방향과 타이밍 비교

이 프로젝트의 fixture는 YieldType만 실제로 쓰이고 나머지 둘은 `None`이라 감이 잘 안 올 수 있습니다. 세 개를 전부 쓰는 가상의 예시로 비교하면 역할이 뚜렷해집니다.

```python
def counter() -> Generator[int, str, str]:
    total = 0
    while True:
        cmd = yield total      # ① YieldType(int): total을 밖으로 내보냄
                                # ③ SendType(str): 밖에서 .send()로 넣어준 값이 cmd에 들어옴
        if cmd == "stop":
            return "done"       # ② ReturnType(str): 완전히 끝날 때 딱 한 번
        total += 1
```

| | YieldType | SendType | ReturnType |
|---|---|---|---|
| 방향 | 함수 **밖으로** 나감 | 함수 **안으로** 들어감 | 함수 **밖으로** 나감 (마지막 1번) |
| 트리거 | `yield 값` | `제너레이터.send(값)` | `return 값` |
| 몇 번 | `yield`가 있는 만큼 여러 번 | `.send()` 호출한 만큼 여러 번 | 딱 1번(끝날 때) |

### "누가 받고 누가 보내는지"는 코드 어디에도 안 적혀 있는데 어떻게 정해지나

**순수 제너레이터라면 코드에 그대로 보입니다** — `next()`나 `.send()`를 직접 호출하는 그 코드가 "받는 쪽"/"보내는 쪽"입니다.

```python
g = gen()
value = next(g)     # ← 여기가 "받는 쪽" (이 줄이 코드로 명시되어 있음)
g.send("안녕")       # ← 여기가 "보내는 쪽"
```

**근데 pytest fixture 코드엔 `next()`도 `.send()`도 안 보입니다.** 이건 pytest가 그 호출을 대신 해주기 때문입니다. 실제로 벌어지는 일을 풀어보면 이렇습니다.

```python
# pytest가 테스트 실행 전에 뒤에서 대신 해주는 일 (의사코드)
gen = logged_in_page(browser, auth_state)   # fixture 함수 호출 → 제너레이터 객체 생성
page = next(gen)                             # yield까지 실행시켜 값을 받음
test_TC051_...(logged_in_page=page)          # 이름이 같은 매개변수에 그 값을 넣어 테스트 호출
# 테스트가 끝나면
next(gen)   # 다시 진행시켜 yield 뒤(context.close())까지 마저 실행 → StopIteration
```

**"어떤 함수가 받는지"를 정하는 규칙은 "이름이 똑같은지" 딱 하나입니다.** `@pytest.fixture`로 등록된 함수 이름이 `logged_in_page`고, 테스트 함수의 매개변수 이름도 `logged_in_page`면, pytest가 테스트를 실행하기 전에 그 이름을 보고 자동으로 연결해줍니다 — `자동화-테스트-노트.md`의 "conftest.py를 pytest가 왜 자동으로 불러오나"와 같은 종류의 이름 기반 자동 연결입니다.

**`send`가 왜 항상 `None`인가도 같은 이유**: 위 의사코드의 `next(gen)`은 내부적으로 `gen.send(None)`과 동일합니다(`next()`는 "보낼 값 없이 그냥 진행시켜라"의 축약형). pytest는 fixture를 재개시킬 때 항상 `None`만 보내고, 테스트 함수가 fixture 안으로 값을 밀어 넣을 통로 자체를 열어주지 않습니다. 그래서 pytest fixture에서는 `SendType`이 `None`이 아닌 경우가 거의 없습니다 — pytest 설계상 그 기능 자체를 안 쓰기 때문입니다.

## 13. Allure 데코레이터 — 리포트에 남기는 것들

여기 나오는 것들은 **테스트 동작을 바꾸지 않습니다.** 전부 "리포트에 이렇게 적어라"는 표시일 뿐이라, 떼어내도 테스트는 똑같이 돌고 똑같이 통과합니다. 대신 결과 보고서를 사람이 읽을 수 없게 됩니다.

적용 배경과 리포트 화면 설명은 `docs/notes/Allure-적용-노트.md`, 지킬 규칙은 `CLAUDE.md`의 "Allure 리포트 컨벤션" 참고. 여기는 **각각이 문법적으로 무엇인지**만 정리합니다.

**`pytestmark = allure.feature("...")`**
파일 맨 위에 한 줄 두면 **그 파일의 모든 테스트**에 적용됩니다. `pytestmark`는 pytest가 정해둔 특별한 변수 이름이라, 이 이름으로 두어야 알아서 읽어갑니다. 리포트에서 화면 단위로 묶는 값입니다.
```python
pytestmark = allure.feature("차량관리 > 현장 서비스  ·  test_field_service.py")
```

**`@allure.title("...")`**
리포트에 뜨는 **한 줄 제목**입니다. 안 붙이면 Allure가 함수명으로 대신 채워서, 리포트에 `test_table_rows_have_action_button[chromium]`이라고 찍힙니다 — 테스트는 통과하는데 보고서만 읽을 수 없게 됩니다.
```python
@allure.title("TC-260907-003 | 결과 행마다 [수정] 버튼이 하나씩 노출된다")
```
`@pytest.mark.parametrize`로 값을 갈아 끼우는 테스트라면 제목에 `{파라미터명}`을 넣습니다 — 값이 치환되어 케이스가 갈라 보입니다.

**`@allure.label("testcase", "TC-260907-003")`**
리포트 Labels 탭에 TC 번호를 **텍스트로** 남깁니다. 이 프로젝트에서는 이 값이 **TC ID의 유일한 정본**입니다(함수명에는 번호를 안 넣습니다). `conftest.py`의 훅이 이 값을 읽어 `tc_260907` 같은 실행용 마커도 자동으로 만듭니다.

> **`@allure.testcase(...)`를 쓰지 않는 이유** — 이름은 라벨처럼 보이지만 실제로는 링크(`tms`) 생성 함수라, **첫 인자를 URL로 취급**합니다. `@allure.testcase("TC-043")`이라고 쓰면 리포트에 클릭 가능한 링크로 뜨는데 실제 URL이 아니라서 눌러도 깨진 페이지로 갑니다.

**`@allure.step("...")`**
그 함수가 리포트에서 **하나의 단계**로 보이게 합니다. 실패했을 때 "어느 단계에서 깨졌는지"가 바로 드러납니다. 화면 객체의 조작 메서드에 붙입니다.
```python
@allure.step("차량관리 > 현장 서비스 진입")
def goto(self) -> None: ...

@allure.step("차량번호 {plate} 로 검색")      # 인자값이 그 자리에 치환된다
def search_by_plate(self, plate: str) -> None: ...
```
문구에 인자를 넣을 때 **따옴표를 직접 쓰지 않습니다** — Allure가 알아서 붙여줘서 `''값''`처럼 두 번 찍힙니다.
한 줄짜리 단순 조회 함수에까지 다 붙이지는 않습니다. 단계가 서너 개로 나뉘는 흐름에만 의미가 있습니다.

**`allure.attach(내용, name=..., attachment_type=...)`**
스크린샷·텍스트를 리포트에 **첨부**합니다. 데코레이터가 아니라 그 자리에서 부르는 함수입니다.
```python
allure.attach(page.screenshot(full_page=True), name="실패 시점 화면",
              attachment_type=allure.attachment_type.PNG)
allure.attach(page.url, name="실패 시점 주소",
              attachment_type=allure.attachment_type.TEXT)
```
`allure.attachment_type`은 첨부물의 종류를 고르는 목록입니다(`PNG`·`TEXT`·`JSON` 등). 이걸 알려줘야 리포트가 이미지로 그릴지 글로 보여줄지 정합니다.
이 프로젝트는 **실패한 테스트에만** 첨부합니다 — 통과한 것까지 붙이면 리포트가 무거워집니다(테스트당 PNG 약 150KB).

## 14. Page Object를 이루는 파이썬 문법

셀렉터를 한 파일에 모으는 이유와 규칙은 `CLAUDE.md`의 "Page Object" 장에 있습니다. 여기는 **그걸 만드는 데 쓴 파이썬 문법**만 봅니다.

**`class` + `__init__` — 화면 하나를 객체로**
```python
class FieldServicePage:
    def __init__(self, page: Page) -> None:
        self.page = page
```
`__init__`은 객체를 만들 때 자동으로 한 번 불리는 함수입니다. `FieldServicePage(logged_in_page)`라고 쓰면 그 `page`가 `self.page`에 저장되고, 그 뒤 모든 메서드가 `self.page`로 그 탭을 조작합니다. `self`는 "지금 이 객체 자신"을 가리키며, 첫 번째 자리에 항상 있습니다(부를 때는 안 넘깁니다).

**`@property` — 괄호 없이 쓰는 속성**
메서드인데 **속성처럼** 쓰게 만듭니다.
```python
@property
def table_root(self) -> Locator:
    return self.page.get_by_test_id("fs-table__root")

fs.table_root          # 괄호 없이. 부를 때마다 위 함수가 실행된다
```
**왜 그냥 `self.table_root = ...`로 `__init__`에서 한 번 만들어두지 않나** — Locator를 한 번 만들어 들고 있으면, 화면이 다시 그려졌을 때 **없어진 예전 요소를 가리키는** 상태가 될 수 있습니다. `@property`는 쓸 때마다 새로 만들기 때문에 항상 지금 화면 기준입니다. 이게 이 파일에서 `@property`를 39번이나 쓴 이유입니다.

**요소는 `@property`, 동작은 메서드**로 나눕니다.

| | 예 | 부르는 법 |
|---|---|---|
| 요소(`@property`) | `table_root`, `submit_button` | `fs.table_root` |
| 동작(메서드) | `goto()`, `row_ids()`, `close()` | `fs.goto()` |

**문자열로 적는 반환 타입 — `-> "NewServicePopup"`**
```python
def open_new_service_popup(self) -> "NewServicePopup":
    ...

class NewServicePopup:      # 이 줄이 아래에 있다
```
`NewServicePopup` 클래스가 **아직 정의되기 전 줄**에서 그 이름을 쓰기 때문에, 따옴표로 감싸 "지금 말고 나중에 찾아라"라고 알려주는 것입니다. 따옴표를 빼면 `NameError`가 납니다.

**팝업은 별도 클래스로 두고 `self.dialog` 기준으로 좁힙니다.**
```python
class NewServicePopup:
    @property
    def dialog(self) -> Locator:
        return self.page.get_by_test_id("fs-new__dialog")

    @property
    def company_select(self) -> Locator:
        return self.dialog.get_by_test_id("fs-new__company-select")   # page 가 아니라 dialog
```
`page`에서 찾으면 팝업 뒤에 깔린 목록 화면의 같은 이름 요소까지 잡힐 수 있습니다(다른 화면에서 실제로 겪은 strict mode 에러 — `docs/notes/code-notes/차량업체변경-테스트-노트.md` 참고).

## 15. pytest 훅 — `conftest.py`에서만 쓰는 것

**훅(hook)은 "pytest가 정해둔 이름의 함수"**입니다. 그 이름으로 `conftest.py`에 만들어두면, 우리가 부르지 않아도 pytest가 정해진 순간에 알아서 부릅니다. fixture가 "테스트가 요청해서 받는 것"이라면, 훅은 "요청하지 않아도 실행 흐름에 끼어드는 것"입니다.

**`pytest_runtest_makereport(item, call)`**
테스트 한 건의 결과 보고서가 만들어질 때마다 불립니다. 실패했으면 그 자리에서 스크린샷을 첨부하는 데 씁니다.
```python
@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    rep = yield                                   # 원래 보고서를 받아온다
    if rep.when in ("setup", "call") and rep.failed:
        page = getattr(item, "_page", None)
        if page is not None:
            _attach_page_evidence(page, ...)
    return rep
```

| 이름 | 뜻 |
|---|---|
| `item` | 지금 실행 중인 테스트 하나 |
| `rep.when` | 어느 **단계**인지 — `"setup"`(fixture) · `"call"`(테스트 본문) · `"teardown"` |
| `rep.failed` | 그 단계가 실패했는지 |
| `wrapper=True` + `yield` | 원래 동작을 `yield`로 돌린 뒤 그 결과를 받아 **덧붙인다**(원래 동작을 대체하지 않는다) |

`rep.when`을 봐야 하는 이유는 한 테스트가 **세 번** 이 훅을 지나가기 때문입니다(setup·call·teardown). 구분 없이 첨부하면 같은 스크린샷이 여러 번 붙습니다.

**`pytest_collection_modifyitems(items)`**
테스트를 다 수집한 뒤, 실행 직전에 목록을 손볼 수 있는 훅입니다. 이 프로젝트는 `@allure.label("testcase", ...)` 값을 읽어 `tc_260907` 같은 마커를 자동으로 붙이는 데 씁니다 — 덕분에 `pytest -m tc_260907`로 배포 단위 실행이 됩니다. 마커를 손으로도 붙이면 두 곳이 어긋나므로, 데코레이터 하나만 정본으로 두고 나머지는 여기서 만들어냅니다.

## 16. 우리가 만든 함수는 어디에 정리돼 있나

여기까지가 **라이브러리가 주는 도구**였다면, 이 프로젝트에는 그것들을 조합해 직접 만든 함수가 32개 있습니다.
**그 설명은 이 노트에 두지 않습니다** — 함수마다 "왜 이렇게 만들었나"가 화면 사정에 붙어 있어서, 화면별 노트(`docs/notes/code-notes/`)가 정본입니다. 같은 설명을 두 곳에 두면 한쪽만 고쳐져 어긋납니다.

여기는 **어디를 보면 되는지만** 가리키는 색인입니다.

**이름 앞의 `_`가 뜻하는 것** — "이 파일 안에서만 쓰는 것"이라는 파이썬 관례입니다. 문법적으로 막히는 건 아니지만, **pytest가 테스트로 수집하지 않게 하는 실질적인 효과**도 있습니다(pytest는 `test_`로 시작하는 함수만 실행합니다). 그래서 다른 파일에서 `import`해 가져다 써도(`test_vehicle_company_transfer.py`가 그렇게 합니다) 테스트가 중복 실행되지 않습니다.

**UI를 조작하는 헬퍼에는 `@allure.step`을 붙입니다**(13번) — 실패했을 때 어느 단계에서 깨졌는지 리포트에 드러나게 하기 위해서입니다.

### 현장 서비스 (`test_field_service.py` · `pages/field_service_page.py`)

정본: `docs/notes/code-notes/현장서비스-테스트-노트.md` (아래 표에서 "현장서비스 노트")

| 함수 | 하는 일 | 설명 |
|---|---|---|
| `_expect_rendered(locator, what)` | 대표 요소 하나를 기다려 렌더 완료를 보장. 실패 시 한글 이름을 담아 다시 던짐 | 현장서비스 노트 |
| `_find_hidden(owner, fields)` | 안 보이는 항목의 이름을 **모아서** 돌려줌 | 현장서비스 노트 |
| `FieldServicePage.goto()` | GNB로 화면 진입 | 현장서비스 노트 (메뉴 이름 함정) |
| `.wait_loaded()` / `.wait_table_settled()` | 결과 목록이 다 그려질 때까지 대기 | 현장서비스 노트 (껍데기 vs 행) |
| `.row_ids()` | 행 PK 목록 | 현장서비스 노트 |
| `.is_empty_result()` / `.state_summary()` | 0건일 때 원인 가르기 | 현장서비스 노트 |
| `.open_new_service_popup()` | 팝업을 열고 `NewServicePopup`을 돌려줌 | 14번 (Page Object 문법) |

### 모니터 리셀러 필터 (`test_monitor_reseller_filter.py`)

헬퍼 9개(`_goto_monitor` · `_get_real_row_count` · `_get_sample_pages` · `_assert_all_rows_have_reseller` 등)는
**모니터 노트에 표와 흐름도로 정리돼 있습니다** — `docs/notes/code-notes/모니터-리셀러-필터-테스트-노트.md`.

### 차량 등록·수정·업체 이관 (`test_vehicle_*.py`)

모달을 다루는 헬퍼들(`_open_carmgmt_edit_modal` · `_get_edit_field` · `_transfer_company_and_save` 등)은
`차량등록-파트너리셀러-테스트-노트.md` · `차량수정-파트너리셀러-테스트-노트.md` · `차량업체변경-테스트-노트.md` 세 개에 나뉘어 있습니다.
`_get_modal`이 왜 `filter(has=...)`로 모달 범위를 좁히는지는 차량업체변경 노트의 "겪은 문제" 참고(02번의 `filter(has=)` 항목과 짝).

### 공통 (`conftest.py`)

| 함수 | 하는 일 | 설명 |
|---|---|---|
| `_auth_state_is_fresh(path)` | `auth.json`의 쿠키가 아직 안 죽었는지 | `docs/notes/자동화-테스트-노트.md` |
| `_login_and_save(browser_type)` | OTP 로그인 후 세션 저장 (세션당 1회) | `docs/notes/자동화-테스트-노트.md` |
| `_attach_page_evidence(page, logs, when)` | 실패 시점 스크린샷·주소·콘솔 로그 첨부 | 15번 + 현장서비스 노트 |

---
`test_login.py` · `conftest.py` · `test_monitor_reseller_filter.py` · `test_vehicle_register_reseller.py` · `test_vehicle_edit_reseller.py` · `test_vehicle_company_transfer.py` · `test_field_service.py` · `pages/field_service_page.py` 전체를 훑어서 정리했습니다. 개념 설명(fixture가 정확히 뭔지, scope 차이 등)은 `docs/notes/자동화-테스트-노트.md`에 더 자세히 있습니다.
