# QA-친화적 리포트 생성 가이드

## 개요

이 프로젝트의 리포트는 **두 단계**로 만들어집니다.

1. **공식 Allure 리포트** (기본) — `postprocess_allure_results.py`가 결과 JSON을 정리해
   Labels 탭에서 `feature`(화면명) · `testClass`(파일명) · `testMethod`(함수명)가 겹치지 않고
   명확히 분리되게 만듭니다. 스크린샷·콘솔 로그·단계별 실행 기록까지 담긴 가장 상세한 리포트입니다.
2. **QA 커스텀 리포트** (추가) — 공식 리포트 위에, 코드를 안 짠 사람도 서버 없이 파일 하나
   더블클릭으로 결과를 훑을 수 있도록 `generate_qa_report.py`가 별도 HTML(`qa-report.html`)을
   더 만듭니다.

이 가이드는 두 번째(QA 커스텀 리포트)의 사용법을 설명합니다.
공식 리포트의 Labels 정리에 대한 배경은 `CLAUDE.md`의 "Labels 정리" 섹션을 참고하세요.

## 한 줄로 실행

### Windows
```bash
run_tests_and_report.bat
```

### Mac / Linux
```bash
bash run_tests_and_report.sh
```

이 명령이 다음을 자동으로 수행합니다:
1. pytest 테스트 실행
2. Allure JSON 후처리 (Labels 정리: feature/testClass/testMethod 분리, 한글 요약 추가)
3. **공식 Allure 리포트 생성** (기본 산출물)
4. **QA-친화적 HTML 리포트 생성** (추가 산출물)

## 단계별 실행 (커스텀 옵션)

### 1단계: pytest 실행

```bash
# 전체 테스트 실행
pytest -v --alluredir=allure-results

# 특정 파일만 실행
pytest test_monitor_reseller_filter.py -v --alluredir=allure-results

# 특정 테스트만 실행
pytest -k "TC086" -v --alluredir=allure-results

# 지난번 실패한 것만 다시 실행
pytest --lf -v --alluredir=allure-results
```

### 2단계: Allure JSON 후처리

```bash
python tools/postprocess_allure_results.py allure-results
```

이 단계에서:
- `testClass` 라벨 추가 (파일명)
- `testMethod` 라벨 추가 (함수명)
- `feature` 라벨에서 파일명 부분(`· xxx.py`)을 잘라내 화면명만 남김
- 실패 메시지 앞에 한글 요약 추가

**이 단계를 건너뛰면** 공식 Allure 리포트의 Labels 탭에 `feature`가
`"로그인 · 권한 · test_login.py"`처럼 화면명·파일명이 섞여 나오고, `testClass`/`testMethod`
라벨도 없는 상태로 생성됩니다 — 반드시 `allure generate`보다 먼저 실행하세요.

### 3단계: 공식 Allure 리포트 생성

PowerShell 기준:
```powershell
Remove-Item -Recurse -Force allure-report -ErrorAction SilentlyContinue   # 기존 리포트 삭제
allure generate allure-results --output allure-report
allure open allure-report
```
bash라면 삭제 명령만 `rm -rf allure-report`로 바꿉니다.

`allure open`이 로컬 서버를 띄우고 기본 브라우저를 자동으로 엽니다.
`allure-report/index.html`을 파일 탐색기에서 직접 더블클릭하면 정상 표시되지 않으니
꼭 `allure open`(또는 별도 로컬 서버)으로 열어야 합니다.

> Allure 3(Node 기반)에는 예전 Java 버전의 `--single-file`·`--clean` 옵션이 없습니다.
> `--output`만 지정하고, 재생성 전 기존 폴더는 직접 지웁니다.

### 4단계: QA 커스텀 리포트 생성

```bash
# 기본값 (qa-report.html로 생성)
python tools/generate_qa_report.py allure-results

# 다른 이름으로 생성
python tools/generate_qa_report.py allure-results -o my-report.html
```

**생성 결과: `qa-report.html`**

```
📊 요약 탭
├─ 성공/실패/건너뜀/오류 통계
└─ 총 테스트 개수

📂 화면/기능별 탭
├─ feature1 (화면1)
│  ├─ TC-001 | file1.py | func1 | ✓ | 2.3s
│  └─ TC-002 | file1.py | func2 | ✗ | 5.1s
└─ feature2 (화면2)
   └─ TC-003 | file2.py | func3 | ✓ | 1.8s

📋 상태별 탭
├─ 성공 (5건)
├─ 실패 (2건)
├─ 건너뜀 (1건)
└─ 오류 (0건)

📑 전체 목록 탭
└─ 모든 테스트 한 테이블로 표시
```

## 리포트에서 보는 정보

### 기본 정보

| 컬럼 | 내용 | 예시 |
|---|---|---|
| **상태** | ✓(성공) ✗(실패) ⊙(건너뜀) ⚠(오류) | ✓ |
| **TC ID** | 테스트 케이스 번호 | TC-086 |
| **화면/기능** | @allure.feature 값 | 단말기 > 모니터 |
| **파일명** | 테스트 파일명 | test_monitor_reseller_filter.py |
| **함수명** | 테스트 함수명 | test_TC086_monitor_reseller_filter_query_result |
| **실행시간** | 테스트 소요 시간 | 2.3s |

### 실패 정보

테스트가 실패하면 그 행 바로 아래에 **실패 메시지**가 표시됩니다:

```
[실패 요약] 예상한 값과 실제 결과가 다릅니다.
[실패 유형] AssertionError
[실패 위치] test_monitor_reseller_filter.py > test_TC086_...
----------------------------------------
실제 오류 메시지...
```

## 각 탭 활용법

### 1. 📊 요약 탭 (빠른 파악)

**언제 봐:** 전체 테스트 결과를 빠르게 확인하고 싶을 때

```
성공: 18건 (90%)
실패: 2건 (10%)
건너뜀: 0건
오류: 0건
```

### 2. 📂 화면/기능별 탭 (화면별 확인)

**언제 봐:** 특정 화면(모니터, 차량관리 등)의 테스트 결과만 보고 싶을 때

```
단말기 > 모니터 ✓3 ✗1 ⊙0 ⚠0
├─ TC-084 | test_monitor... | 성공
├─ TC-085 | test_monitor... | 성공
├─ TC-086 | test_monitor... | 실패  ← [메시지 표시]
└─ TC-087 | test_monitor... | 성공
```

### 3. 📋 상태별 탭 (문제 집중)

**언제 봐:** 실패한 테스트만 모아서 보고 싶을 때

```
실패 (2건)
├─ TC-086 | 단말기 > 모니터 | test_monitor_reseller_filter.py | test_TC086... | 5.2s
└─ TC-090 | 차량관리 > 차량 수정 | test_vehicle_edit_reseller.py | test_TC090... | 3.1s
```

### 4. 📑 전체 목록 탭 (완전 상세)

**언제 봐:** 모든 테스트를 한 테이블로 보고 싶을 때

한 화면에 전체 결과를 표시하므로 Ctrl+F로 검색하거나 스프레드시트로 내보낼 수도 있습니다.

## 색상 코드

| 색상 | 의미 |
|---|---|
| 🟢 초록 | 성공 (PASS) |
| 🔴 빨강 | 실패 (FAIL) |
| 🟠 주황 | 건너뜀 (SKIP) — 검증 대상 데이터 없음 |
| 🩷 핑크 | 오류 (ERROR) — 테스트 코드 문제 |

## 공식 Allure 리포트는 어디 있나요?

`run_tests_and_report.bat`/`.sh`를 실행했다면 위 3단계에서 **이미 `allure-report/`에
생성되어 있습니다** — QA 커스텀 리포트(`qa-report.html`)는 그 위에 얹는 추가 산출물입니다.

```bash
# 열기 (반드시 이 명령으로 — index.html 더블클릭은 정상 표시 안 됨)
allure open allure-report
```

**공식 Allure 리포트가 QA 리포트보다 더 보여주는 정보:**
- 실패 시점의 스크린샷
- 브라우저 콘솔 로그
- 테스트 단계별 상세 실행 기록
- 실행 환경 정보 (브라우저, OS 등)
- Retries·History 등 Allure 표준 기능

TC 상세의 **Labels 탭**에서도 `feature`(화면명)·`testClass`(파일명)·`testMethod`(함수명)가
분리되어 나옵니다 — 이건 `postprocess_allure_results.py`가 만든 것으로, `CLAUDE.md`의
"Labels 정리" 섹션에 배경이 정리되어 있습니다.

## FAQ

### Q: "건너뜀" 탭에 테스트가 너무 많습니다

A: 검증 대상 데이터가 없어서 테스트를 건너뛴 것입니다.
- `docs/code-notes/` 파일에 "검증 불가 이유" 가 적혀 있는지 확인하세요
- dev 환경 데이터를 확인해서 실제로 검증할 수 있는지 검토해주세요

### Q: 실패한 테스트의 정확한 원인을 알고 싶습니다

A: 두 가지 방법이 있습니다:

1. **QA 리포트의 메시지 읽기** (권장)
   - 실패 행 아래에 "[실패 요약]" 메시지가 있습니다
   - 이걸로 대부분의 원인을 파악할 수 있습니다

2. **공식 Allure 리포트 확인**
   - 스크린샷, 콘솔 로그, 단계별 기록을 봅니다
   - 더 자세한 진단이 필요할 때만 씁니다

### Q: 리포트를 파일로 저장하거나 공유하고 싶습니다

A: `qa-report.html` 파일 자체가 스스로 완결된 HTML입니다.
- 이메일로 보내기: 바로 첨부해서 보낼 수 있습니다 (내부 링크만 있어 인터넷 불필요)
- 공유 폴더에 저장: 그대로 복사해서 저장소에 두면 됩니다
- 버전 관리: 날짜를 붙여서 저장하면 추적 가능합니다
  ```
  qa-report-2026-01-15.html
  qa-report-2026-01-16.html
  ```

### Q: 리포트에 내가 원하는 정보를 추가하고 싶습니다

A: `tools/generate_qa_report.py` 파일을 수정하면 됩니다.
- HTML 템플릿 부분을 고쳐서 새 컬럼 추가
- CSS 스타일을 고쳐서 색상·레이아웃 변경
- 테이블 생성 로직을 고쳐서 필터링·정렬 기능 추가

변경 후: `python tools/generate_qa_report.py allure-results` 다시 실행

## 트러블슈팅

### 리포트가 생성되지 않습니다

```powershell
# 1. Allure 결과가 있는지 확인
Get-ChildItem allure-results

# 2. 후처리 단계 실행 확인
python tools/postprocess_allure_results.py allure-results

# 3. 리포트 생성 실행
python tools/generate_qa_report.py allure-results
```

### 한글이 깨져서 나옵니다

A: Windows의 경우, 콘솔 인코딩을 UTF-8로 설정하세요 (PowerShell):
```powershell
$env:PYTHONIOENCODING = "utf-8"
python tools/generate_qa_report.py allure-results
```

### 파일명이 이상하게 나옵니다

A: 리포트가 생성된 직후 `qa-report.html`을 바로 열기보다,
파일 이름을 확인해주세요. 특수 문자나 공백이 있으면 문제가 될 수 있습니다.

---

**더 자세한 내용은 `CLAUDE.md` 의 "Allure 리포트 컨벤션" 섹션을 참고하세요.**
