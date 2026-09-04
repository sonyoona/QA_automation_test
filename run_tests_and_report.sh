#!/bin/bash
# QA 테스트 실행 및 리포트 생성 통합 스크립트

set -e

echo "============================================"
echo "🧪 QA E2E 테스트 실행 및 리포트 생성"
echo "============================================"

# 1. pytest 실행 및 Allure 결과 수집
echo ""
echo "[1/4] pytest 테스트 실행 중..."
pytest -v --alluredir=allure-results "$@" || true

# 2. Allure JSON 후처리 (testClass/testMethod 라벨 추가, 한글 요약)
echo ""
echo "[2/4] Allure 결과 후처리 중..."
python tools/postprocess_allure_results.py allure-results

# 3. 공식 Allure 리포트 생성 (기본 산출물)
echo ""
echo "[3/4] 공식 Allure 리포트 생성 중..."
if command -v allure &> /dev/null; then
    rm -rf allure-report
    allure generate allure-results --output allure-report
    echo "✓ Allure 리포트: allure-report/index.html"
else
    echo "⊙ Allure CLI가 없어 공식 리포트를 건너뜁니다: npm i -g allure"
fi

# 4. QA-친화적 커스텀 HTML 리포트 생성 (추가 산출물)
echo ""
echo "[4/4] QA 친화적 커스텀 리포트 생성 중..."
python tools/generate_qa_report.py allure-results -o qa-report.html || echo "⊙ 커스텀 리포트 생성 실패 — 공식 Allure 리포트는 위에서 이미 생성됨"

echo ""
echo "============================================"
echo "✓ 리포트 생성 완료!"
echo "============================================"
echo ""
echo "📋 공식 Allure 리포트 (기본):"
echo "   allure-report/index.html"
echo "   열기: allure open allure-report"
echo ""
echo "📊 QA-친화적 커스텀 리포트 (추가):"
echo "   qa-report.html"
echo ""
