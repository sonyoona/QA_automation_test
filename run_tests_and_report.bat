@echo off
REM ★ 이 파일은 CRLF 줄바꿈 + cp949(ANSI) 인코딩으로 저장한다. UTF-8 로 바꾸지 말 것.
REM   LF 로 저장하면 cmd 가 줄 위치를 놓쳐 명령이 중간에서 잘린다
REM   ('ing'/'ure-results' 가 명령으로 실행되는 오류 - 2026-09-10 실측).
REM   UTF-8 로 저장하면 한글이 깨진다. chcp 65001 로도 못 고친다 -
REM   파일 중간에 코드페이지를 바꾸면 파서가 어긋나 REM 줄까지 실행된다 (같은 날 실측).
REM   .sh 쪽은 반대로 LF 여야 한다 - .gitattributes 가 둘을 따로 고정한다.
REM QA 테스트 실행 및 리포트 생성 통합 스크립트 (Windows)
REM
REM   run_tests_and_report.bat                    읽기 전용 61건만 (기본)
REM   run_tests_and_report.bat --allow-mutating   저장하는 8건까지 69건 전부
REM
REM 붙인 인자는 %* 로 pytest 에 그대로 넘어간다. 데이터를 바꾸는 8건
REM (@pytest.mark.mutating) 은 게이트가 기본적으로 skip 하므로, 플래그 없이
REM 돌리면 결과에 8 skipped 가 뜬다 - 고장이 아니다.
REM 자세한 것은 README '데이터를 바꾸는 테스트는 기본적으로 실행되지 않습니다' 참고.

REM 지연확장(enabledelayedexpansion)은 켜지 않는다 - echo 의 [!] 가 사라진다.
setlocal

echo ============================================
echo [*] QA E2E 테스트 실행 및 리포트 생성
echo ============================================

REM 1. pytest 실행 및 Allure 결과 수집
echo.
echo [1/4] pytest 테스트 실행 중...
echo %* | findstr /C:"--allow-mutating" >nul
if %errorlevel% equ 0 (
    echo       [!] --allow-mutating 켜짐 - 데이터를 바꾸는 8건이 함께 돕니다.
    echo           dev 차량 4대의 소속 업체가 실제로 바뀌었다 돌아옵니다.
) else (
    echo       데이터를 바꾸는 8건은 건너뜁니다 ^(게이트 기본값 - 8 skipped 는 정상^).
    echo       함께 돌리려면: run_tests_and_report.bat --allow-mutating
)
pytest -v --alluredir=allure-results %*
if %errorlevel% neq 0 (
    REM pytest가 실패해도 계속 진행 (이미 일부 결과가 있을 수 있음)
)

REM 2. Allure JSON 후처리
echo.
echo [2/4] Allure 결과 후처리 중...
python tools\postprocess_allure_results.py allure-results

REM 3. 공식 Allure 리포트 생성 (기본 산출물)
echo.
echo [3/4] 공식 Allure 리포트 생성 중...
where allure >nul 2>nul
if %errorlevel% equ 0 (
    if exist allure-report rmdir /s /q allure-report
    allure generate allure-results --output allure-report
    echo [OK] Allure 리포트: allure-report\index.html
) else (
    echo [--] Allure CLI가 없어 공식 리포트를 건너뜁니다: npm i -g allure
)

REM 4. QA-친화적 커스텀 HTML 리포트 생성 (추가 산출물)
echo.
echo [4/4] QA 친화적 커스텀 리포트 생성 중...
python tools\generate_qa_report.py allure-results -o qa-report.html
if %errorlevel% neq 0 (
    echo [--] 커스텀 리포트 생성 실패 - 공식 Allure 리포트는 위에서 이미 생성됨
)

echo.
echo ============================================
echo [OK] 리포트 생성 완료!
echo ============================================
echo.
echo 공식 Allure 리포트 (기본):
echo    allure-report\index.html
echo    열기: allure open allure-report
echo.
echo QA-친화적 커스텀 리포트 (추가):
echo    qa-report.html
echo.

pause
