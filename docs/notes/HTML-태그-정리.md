# 코드 속 HTML 태그 정리

`test_login.py`, `conftest.py`, `test_monitor_reseller_filter.py`에서 실제로 참조한 HTML 태그·속성만 모았습니다. 전부 화면을 조사하면서 실제로 마주쳤던 것들입니다.

## 01. 태그(요소)

코드가 `.locator("...")`나 `get_by_role("...")`로 직접 가리킨 HTML 요소들입니다.

**`<a>` — 링크**
클릭해서 다른 화면/상태로 이동시키는 요소. GNB 메뉴·탭·페이지네이션 버튼도 전부 `<a>`였습니다.
```python
page.locator("a").filter(has_text=re.compile(r"^단말기$")).click()
```
쓰인 곳: GNB "단말기" 메뉴, 모니터 탭 7개, 페이지네이션 번호 버튼

**`<label>` — 폼 캡션**
입력창·드롭다운 위에 붙는 이름표. 클릭해도 아무 동작이 없는 경우가 많습니다 — 실제 동작은 옆에 붙은 별도 요소(콤보박스 등)가 담당하는 게 이 사이트의 패턴이었습니다.
```python
page.locator("label").filter(has_text="리셀러")
```
쓰인 곳: "리셀러"/"파트너" 필터 캡션 노출 여부 확인(TC-084)

**`<div>` — 범용 컨테이너**
특별한 의미 없이 다른 요소들을 묶는 상자. 필터 하나(라벨+입력요소)를 `div.column`으로, 드롭다운 전체를 `div[role="combobox"]`로 묶어뒀습니다.
```python
page.locator("div.column", has_text="리셀러")
```
쓰인 곳: 필터 열 범위 좁히기, 날짜 필터 열 찾기

**`<input>` — 입력창**
글자를 직접 타이핑하는 요소. 아이디·비밀번호 입력, 드롭다운 안의 검색창, 날짜 선택 입력창까지 전부 이 태그입니다.
```python
page.get_by_placeholder("아이디").fill(ADMIN_EMAIL)
```
쓰인 곳: 로그인 아이디·비밀번호, 날짜 필터

**`<button>` — 버튼**
클릭해서 즉시 어떤 동작(제출·조회 등)을 일으키는 요소. `get_by_role("button", ...)`로 찾을 때 실제로 매치되는 태그입니다.
```python
page.get_by_role("button", name="조회").click()
```
쓰인 곳: 로그인, 2FA 확인, 조회 버튼

**`<table><thead><tbody><tr><th><td>` — 표**
`table`이 전체, `thead`는 헤더 영역, `tbody`는 실제 데이터 영역, `tr`은 한 행, `th`는 헤더 셀, `td`는 데이터 셀입니다.
```python
page.locator("table").first.locator("tbody tr")
```
쓰인 곳: 모니터 조회 결과 테이블 전체 (TC-086/087의 핵심)

**`<span>` — 인라인 텍스트 상자**
줄바꿈 없이 글자 일부만 감싸는 태그. 드롭다운 옵션 안의 글자(`<span class="text">커넥트</span>`)가 이 형태였습니다.

> **왜 굳이 줄바꿈 없이 감싸나**
>
> HTML 태그는 크게 두 종류입니다 — **block 요소**(`<div>`, `<table>` 등)는 항상 새 줄에서 시작하고 가로 폭을 꽉 채우고, **inline 요소**(`<span>`, `<a>` 등)는 줄 흐름 안에 그대로 끼어들고 자기 내용물만큼만 차지합니다.
>
> `<span>`은 그중에서도 **아무 의미·기본 스타일이 없는 "빈 상자"**입니다. 문장 하나 중 일부 글자에만 스타일을 주거나, CSS/자동화 코드가 그 글자 부분만 콕 집어 가리킬 수 있게 class를 붙이고 싶을 때 씁니다. 드롭다운 예시에서 바깥 `<div role="option">`은 옵션 한 줄 전체(block)고, 안쪽 `<span class="text">`는 그 안의 글자 부분만 따로 감싼 것입니다.

**실제 조사했던 구조 (드롭다운 예시)**
```html
<label>리셀러</label>
<div role="combobox">
  <input class="search">
  <div role="listbox">
    <div role="option"><span>전체</span></div>
    <div role="option"><span>커넥트</span></div>
  </div>
</div>
```

## 02. 속성(attribute)

태그 안에 붙어서 그 요소를 더 구체적으로 설명하거나, 코드가 골라내는 기준이 된 값들입니다.

**`class` — CSS 클래스**
스타일을 입히려고 붙이는 이름표인데, 자동화에서는 "이 요소가 뭔지 식별하는 용도"로도 자주 씁니다. 페이지에 딱 하나뿐인 이름(`.spinner`, `.pagination`)은 셀렉터로 아주 유용합니다.
```python
page.locator(".spinner").first.wait_for(state="hidden")
```
쓰인 곳: 로딩 스피너, 페이지네이션 영역, 현재 활성 탭(`.active`)

**`role` — ARIA 역할**
스크린리더 등 보조기술에게 "이 요소가 뭘 하는 물건인지" 알려주는 표준 속성. `get_by_role()`이 화면을 훑을 때 바로 이 속성(과 태그 종류)을 기준으로 찾습니다. `combobox`·`option`·`listbox`는 이 사이트의 커스텀 드롭다운이 직접 붙여둔 값이고, `link`·`button`은 `<a>`/`<button>` 태그면 브라우저가 자동으로 부여합니다.
```python
reseller_dropdown.get_by_role("option", name=target_reseller, exact=True)
```
쓰인 곳: 리셀러 드롭다운(combobox/option), GNB·버튼(link/button)

**`colspan` / `rowspan` — 셀 병합**
`colspan`은 그 셀이 가로로 몇 칸을 차지하는지, `rowspan`은 세로로 몇 칸을 차지하는지 나타냅니다. 이 사이트의 표 헤더가 "통신"처럼 큰 제목 아래 "여부·사유" 세부 헤더가 딸린 2단 구조라 `colspan`이 쓰였고, "조회 결과가 없습니다" 안내 행도 `colspan`으로 전체 폭을 차지하는 셀 하나로 되어 있었습니다.
```html
<th colspan="4">통신</th>  <!-- 여부·사유·발생일자 등 4칸을 차지 -->
```
쓰인 곳: 리셀러 컬럼 위치 계산(TC-086), "조회 결과 없음" 판별

**`type` — (이 사이트만의) 커스텀 속성**
표준 HTML 태그 중에도 `type`이 있는 게 있지만(`<input type="text">` 등), 여기서 본 `type="pageItem"`·`type="nextItem"`·`type="lastItem"`은 이 사이트가 페이지네이션 버튼 종류를 구분하려고 자체적으로 붙인 값입니다. 표준이 아니라 이 앱만의 규칙이라, 다른 사이트에서는 안 통합니다.
```python
pagination.locator('a[type="pageItem"][value="5"]')
```
쓰인 곳: 페이지네이션 버튼(1·5·10페이지 이동, TC-086)

**`value` — 값**
여기서는 `<input>`의 입력값이 아니라, 페이지네이션 버튼(`<a>`)에 붙은 "이 버튼이 몇 페이지로 가는 버튼인지"를 나타내는 값으로 쓰였습니다.
```python
int(last_item.get_attribute("value"))  # 마지막 페이지 번호 = 전체 페이지 수
```
쓰인 곳: 전체 페이지 수 계산, 현재 활성 페이지 확인

**`placeholder` — 입력창 안내 문구**
입력창에 아직 아무것도 안 썼을 때 흐리게 보이는 안내 텍스트. `get_by_placeholder(...)`가 이 값을 기준으로 입력창을 찾습니다.
```python
page.get_by_placeholder("비밀번호").fill(ADMIN_PASSWORD)
```
쓰인 곳: 로그인 아이디·비밀번호 입력창

> **헷갈리기 쉬운 것 — `name=`은 진짜 HTML `name` 속성이 아닙니다**
>
> `get_by_role("button", name="조회")`처럼 자주 쓰는 `name=` 파라미터는, `<input name="...">`같은 실제 HTML `name` 속성을 읽는 게 아닙니다. Playwright가 그 요소의 **"접근성 이름"(accessible name)** — 보통 화면에 보이는 글자 자체, 또는 `aria-label` — 을 계산해서 비교하는 겁니다. 그래서 버튼 안의 보이는 글자를 그대로 `name=`에 적으면 되는 거예요.

## 03. ARIA와 role, 왜 필요한가

### ARIA란

**ARIA = "Accessible Rich Internet Applications"**, W3C가 정한 HTML 속성 규격입니다. 시각장애인이 쓰는 스크린리더 같은 보조기술에게 "이 요소가 뭐고 지금 어떤 상태인지" 알려주는 용도예요.

**왜 필요한가**: `<button>`이나 `<select>` 같은 원래 HTML 태그는 스크린리더가 자동으로 "이건 버튼이구나"를 압니다. 근데 요즘 웹사이트들은 디자인을 마음대로 꾸미려고 원래 태그 대신 그냥 `<div>`로 처음부터 다시 만드는 경우가 많습니다 — 이 사이트의 드롭다운이 정확히 그 경우였죠. 문제는 스크린리더 입장에서 그냥 `<div>`는 의미 없는 상자로만 보인다는 것입니다. ARIA 속성이 이 빈틈을 채웁니다:

- `role="combobox"` → "이 div를 드롭다운처럼 취급해라"
- `aria-expanded="true"` → "지금 열려있다"
- `aria-selected="true"` → "이 옵션이 지금 선택된 것이다"

### role이 필요한 진짜 이유

**핵심: 태그 이름과 "실제 하는 역할"이 다를 때, 그 간극을 메우는 게 role입니다.**

원래부터 의미가 있는 태그(`<button>`, `<a>`, `<select>`)는 role을 따로 안 붙여도 됩니다 — 태그 이름 자체가 이미 "나는 버튼이다"라고 말하고 있으니까요. 문제는 커스텀 드롭다운처럼 겉모습은 자유롭게 꾸미고 싶어서 `<div>`로 새로 만든 경우입니다.

```
겉모습/구현 방식 = <div>          (디자인 자유롭게 하려고)
실제 역할        = role="combobox" (기능은 그래도 드롭다운)
```

**그리고 "표준화된 값"이어야 하는 이유**: `type="pageItem"` 기억하시나요? 그건 이 사이트가 페이지네이션 버튼을 구분하려고 자기 마음대로 만든 이름이라, 이 사이트 코드를 직접 읽어보지 않으면 아무도 그 뜻을 모릅니다. 반면 `role="combobox"`·`role="option"`·`role="button"`은 W3C가 정해놓은 목록 중 하나라서, 어떤 사이트에서 만났든 스크린리더도 Playwright도 미리 알고 있습니다.

**한 줄로 정리**: role이 없으면 커스텀 요소는 "이름 없는 상자"일 뿐이라 아무도(보조기술도, 자동화 도구도) 그게 뭔지 알 방법이 없습니다. role은 모두가 알아듣는 공통 이름표를 붙여주는 것이고, 그 덕분에 `get_by_role()`이 사전 지식 없이도 정확히 찾아낼 수 있는 겁니다. ARIA는 원래 시각장애인을 위한 규격인데, **Playwright의 `get_by_role()`이 스크린리더와 똑같은 메커니즘을 쓰기 때문에** 이렇게 자동화에도 그대로 연결됩니다.

---
`test_login.py` · `conftest.py` · `test_monitor_reseller_filter.py` 전체를 훑어서 정리했습니다.
