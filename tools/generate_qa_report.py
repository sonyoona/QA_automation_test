"""QA-친화적 커스텀 Allure 리포트 생성 도구.

Allure JSON 결과를 읽어 feature/testClass/testMethod를 명확하게 분리하고,
QA가 한눈에 알아보기 쉬운 HTML 리포트를 생성한다.

사용법:
    pytest --alluredir=allure-results
    python tools/postprocess_allure_results.py allure-results
    python tools/generate_qa_report.py allure-results -o qa-report.html
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class TestResult:
    """테스트 결과 정보."""

    tc_id: str  # TC-XXX
    feature: str  # 화면/기능 분류
    test_class: str  # 파일명
    test_method: str  # 함수명
    status: str  # "passed", "failed", "skipped", "broken"
    duration_ms: float
    message: str = ""

    @property
    def status_ko(self) -> str:
        """상태를 한글로."""
        return {
            "passed": "성공",
            "failed": "실패",
            "skipped": "건너뜀",
            "broken": "오류",
        }.get(self.status, self.status)

    @property
    def status_emoji(self) -> str:
        """상태를 emoji로."""
        return {
            "passed": "✓",
            "failed": "✗",
            "skipped": "⊙",
            "broken": "⚠",
        }.get(self.status, "?")

    @property
    def status_class(self) -> str:
        """CSS class name."""
        return f"status-{self.status}"


def _extract_test_info(data: dict) -> TestResult | None:
    """Allure JSON 데이터에서 테스트 정보를 추출한다."""
    full_name = data.get("fullName", "")
    if "#" not in full_name:
        return None

    test_class, test_method = full_name.rsplit("#", 1)
    test_class = f"{test_class}.py"

    # feature 추출: @allure.feature 라벨에서 가져오기
    # (형식: "화면명 · 파일명" → "화면명" 부분만 취하기)
    feature = ""
    labels = data.get("labels", [])
    for label in labels:
        if label.get("name") == "feature":
            feature_full = label.get("value", "")
            # "단말기 > 모니터  ·  test_monitor_reseller_filter.py" 형식 → "단말기 > 모니터" 취하기
            if "·" in feature_full:
                feature = feature_full.split("·")[0].strip()
            else:
                feature = feature_full.strip()
            break

    # TC ID 추출: @allure.label("testcase", "TC-XXX")
    tc_id = ""
    for label in labels:
        if label.get("name") == "testcase":
            tc_id = label.get("value", "")
            break
    if not tc_id:
        tc_id = "N/A"

    # 상태와 메시지
    status = data.get("status", "unknown")
    status_details = data.get("statusDetails", {})
    message = status_details.get("message", "")

    # 실행 시간 (ms)
    duration_ms = data.get("stop", 0) - data.get("start", 0)

    return TestResult(
        tc_id=tc_id,
        feature=feature or "분류없음",
        test_class=test_class,
        test_method=test_method,
        status=status,
        duration_ms=duration_ms,
        message=message,
    )


def load_results(results_dir: str) -> list[TestResult]:
    """allure-results 디렉토리에서 모든 결과를 로드한다."""
    results = []
    pattern = os.path.join(results_dir, "*-result.json")
    for path in glob.glob(pattern):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            if info := _extract_test_info(data):
                results.append(info)
        except Exception as e:
            print(f"[경고] {path} 처리 중 오류: {e}")
    return results


def _format_duration(ms: float) -> str:
    """ms 단위 시간을 읽기 좋게 포맷."""
    if ms < 1000:
        return f"{ms:.0f}ms"
    return f"{ms / 1000:.1f}s"


def _html_escape(text: str) -> str:
    """HTML 특수문자 이스케이프."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def generate_html(results: list[TestResult]) -> str:
    """HTML 리포트를 생성한다."""

    # 상태별·feature별 그룹화
    by_status = defaultdict(list)
    by_feature = defaultdict(list)
    for r in results:
        by_status[r.status].append(r)
        by_feature[r.feature].append(r)

    # 통계
    total = len(results)
    passed = len(by_status.get("passed", []))
    failed = len(by_status.get("failed", []))
    broken = len(by_status.get("broken", []))
    skipped = len(by_status.get("skipped", []))

    # 상태별 색상
    status_colors = {
        "passed": "#4caf50",
        "failed": "#f44336",
        "skipped": "#ff9800",
        "broken": "#e91e63",
    }

    # HTML 생성
    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QA 테스트 리포트 - {datetime.now().strftime('%Y-%m-%d %H:%M')}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Roboto, sans-serif;
            background: #f5f5f5;
            padding: 20px;
            color: #333;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}

        header {{
            background: white;
            padding: 30px;
            border-radius: 8px;
            margin-bottom: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}

        h1 {{
            font-size: 28px;
            margin-bottom: 20px;
            color: #1a1a1a;
        }}

        .timestamp {{
            color: #666;
            font-size: 14px;
        }}

        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }}

        .stat-card {{
            background: #f9f9f9;
            padding: 15px;
            border-radius: 6px;
            border-left: 4px solid #ddd;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .stat-card.passed {{ border-left-color: #4caf50; }}
        .stat-card.failed {{ border-left-color: #f44336; }}
        .stat-card.skipped {{ border-left-color: #ff9800; }}
        .stat-card.broken {{ border-left-color: #e91e63; }}

        .stat-value {{
            font-size: 24px;
            font-weight: bold;
        }}

        .stat-label {{
            font-size: 13px;
            color: #666;
        }}

        .tabs {{
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            border-bottom: 2px solid #ddd;
        }}

        .tab-button {{
            padding: 12px 20px;
            border: none;
            background: transparent;
            cursor: pointer;
            font-size: 14px;
            border-bottom: 3px solid transparent;
            color: #666;
            transition: all 0.3s ease;
        }}

        .tab-button:hover {{
            color: #1a1a1a;
            border-bottom-color: #ddd;
        }}

        .tab-button.active {{
            color: #1a1a1a;
            border-bottom-color: #2196f3;
            font-weight: 600;
        }}

        .tab-content {{
            display: none;
        }}

        .tab-content.active {{
            display: block;
        }}

        table {{
            width: 100%;
            background: white;
            border-collapse: collapse;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }}

        thead {{
            background: #2c3e50;
            color: white;
        }}

        th {{
            padding: 15px;
            text-align: left;
            font-weight: 600;
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border-bottom: 2px solid #34495e;
        }}

        td {{
            padding: 12px 15px;
            border-bottom: 1px solid #ecf0f1;
            font-size: 13px;
        }}

        tbody tr {{
            transition: background-color 0.2s ease;
        }}

        tbody tr:hover {{
            background-color: #f9f9f9;
        }}

        .status-badge {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 12px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 12px;
        }}

        .status-passed {{
            background-color: #e8f5e9;
            color: #2e7d32;
        }}

        .status-failed {{
            background-color: #ffebee;
            color: #c62828;
        }}

        .status-skipped {{
            background-color: #fff3e0;
            color: #e65100;
        }}

        .status-broken {{
            background-color: #fce4ec;
            color: #880e4f;
        }}

        .feature-group {{
            margin-bottom: 20px;
        }}

        .feature-header {{
            background: #ecf0f1;
            padding: 12px 15px;
            border-left: 4px solid #3498db;
            margin-bottom: 10px;
            border-radius: 4px;
            font-weight: 600;
            font-size: 14px;
        }}

        .feature-group table {{
            margin-bottom: 15px;
        }}

        .message {{
            background: #f5f5f5;
            padding: 10px;
            border-left: 3px solid #ff9800;
            border-radius: 4px;
            font-family: 'Monaco', 'Courier New', monospace;
            font-size: 12px;
            color: #555;
            word-break: break-word;
            white-space: pre-wrap;
            max-width: 100%;
            overflow-x: auto;
        }}

        .message.failed {{
            border-left-color: #f44336;
        }}

        .time {{
            color: #999;
            font-size: 12px;
        }}

        .empty {{
            text-align: center;
            padding: 40px;
            color: #999;
            font-size: 14px;
        }}

        footer {{
            text-align: center;
            padding: 20px;
            color: #999;
            font-size: 12px;
        }}

        .tc-id {{
            background: #e3f2fd;
            padding: 2px 8px;
            border-radius: 3px;
            font-weight: 600;
            color: #1976d2;
            font-size: 11px;
            font-family: 'Monaco', 'Courier New', monospace;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🧪 QA 테스트 리포트</h1>
            <div class="timestamp">
                생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            </div>

            <div class="stats">
                <div class="stat-card passed">
                    <div>
                        <div class="stat-label">성공</div>
                        <div class="stat-value">{passed}</div>
                    </div>
                </div>
                <div class="stat-card failed">
                    <div>
                        <div class="stat-label">실패</div>
                        <div class="stat-value">{failed}</div>
                    </div>
                </div>
                <div class="stat-card skipped">
                    <div>
                        <div class="stat-label">건너뜀</div>
                        <div class="stat-value">{skipped}</div>
                    </div>
                </div>
                <div class="stat-card broken">
                    <div>
                        <div class="stat-label">오류</div>
                        <div class="stat-value">{broken}</div>
                    </div>
                </div>
                <div class="stat-card">
                    <div>
                        <div class="stat-label">총계</div>
                        <div class="stat-value">{total}</div>
                    </div>
                </div>
            </div>
        </header>

        <div class="tabs">
            <button class="tab-button active" onclick="showTab(event, 'summary')">
                📊 요약
            </button>
            <button class="tab-button" onclick="showTab(event, 'by-feature')">
                📂 화면/기능별
            </button>
            <button class="tab-button" onclick="showTab(event, 'by-status')">
                📋 상태별
            </button>
            <button class="tab-button" onclick="showTab(event, 'all')">
                📑 전체 목록
            </button>
        </div>

        <!-- 요약 탭 -->
        <div id="summary" class="tab-content active">
            {_generate_summary_table(results, status_colors)}
        </div>

        <!-- 화면/기능별 탭 -->
        <div id="by-feature" class="tab-content">
            {_generate_by_feature_table(results, by_feature)}
        </div>

        <!-- 상태별 탭 -->
        <div id="by-status" class="tab-content">
            {_generate_by_status_table(results, by_status)}
        </div>

        <!-- 전체 목록 탭 -->
        <div id="all" class="tab-content">
            {_generate_all_table(results)}
        </div>

        <footer>
            <p>© QA Test Report Generator</p>
        </footer>
    </div>

    <script>
        function showTab(event, tabName) {{
            // 모든 탭 콘텐츠 숨기기
            const contents = document.querySelectorAll('.tab-content');
            contents.forEach(c => c.classList.remove('active'));

            // 모든 탭 버튼 비활성화
            const buttons = document.querySelectorAll('.tab-button');
            buttons.forEach(b => b.classList.remove('active'));

            // 선택된 탭만 표시
            document.getElementById(tabName).classList.add('active');
            event.target.classList.add('active');
        }}
    </script>
</body>
</html>"""

    return html


def _generate_summary_table(results: list[TestResult], status_colors: dict) -> str:
    """요약 테이블 생성."""
    status_summary = defaultdict(int)
    for r in results:
        status_summary[r.status] += 1

    html = '<table><thead><tr>'
    html += '<th>상태</th><th>건수</th><th>비율</th>'
    html += '</tr></thead><tbody>'

    total = len(results)
    status_order = ["passed", "failed", "skipped", "broken"]

    for status in status_order:
        count = status_summary.get(status, 0)
        if total > 0:
            percent = (count / total) * 100
        else:
            percent = 0

        status_ko_map = {
            "passed": "성공",
            "failed": "실패",
            "skipped": "건너뜀",
            "broken": "오류",
        }

        html += f'''<tr>
            <td>
                <span class="status-badge status-{status}">
                    {status_ko_map.get(status, status)}
                </span>
            </td>
            <td><strong>{count}</strong></td>
            <td>{percent:.1f}%</td>
        </tr>'''

    html += '</tbody></table>'
    return html


def _generate_by_feature_table(results: list[TestResult], by_feature: dict) -> str:
    """화면/기능별 테이블 생성."""
    if not results:
        return '<div class="empty">테스트 결과가 없습니다.</div>'

    html = ''
    for feature in sorted(by_feature.keys()):
        feature_results = by_feature[feature]
        status_count = defaultdict(int)
        for r in feature_results:
            status_count[r.status] += 1

        html += f'''<div class="feature-group">
            <div class="feature-header">
                {_html_escape(feature)}
                <span style="float: right; font-size: 12px; font-weight: normal;">
                    ✓ {status_count['passed']} |
                    ✗ {status_count['failed']} |
                    ⊙ {status_count['skipped']} |
                    ⚠ {status_count['broken']}
                </span>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>TC ID</th>
                        <th>파일명</th>
                        <th>함수명</th>
                        <th>상태</th>
                        <th>실행시간</th>
                    </tr>
                </thead>
                <tbody>'''

        for r in sorted(feature_results, key=lambda x: x.test_class):
            html += f'''<tr>
                <td><span class="tc-id">{_html_escape(r.tc_id)}</span></td>
                <td><code>{_html_escape(r.test_class)}</code></td>
                <td><code style="font-size: 12px;">{_html_escape(r.test_method)}</code></td>
                <td><span class="status-badge status-{r.status}">
                    {r.status_ko}
                </span></td>
                <td><span class="time">{_format_duration(r.duration_ms)}</span></td>
            </tr>'''

            if r.message and r.status in ("failed", "broken"):
                html += f'''<tr>
                    <td colspan="5">
                        <div class="message failed">
                            {_html_escape(r.message[:500])}
                        </div>
                    </td>
                </tr>'''

        html += '''</tbody></table></div>'''

    return html


def _generate_by_status_table(results: list[TestResult], by_status: dict) -> str:
    """상태별 테이블 생성."""
    html = ''
    status_order = [("passed", "성공 ✓"), ("failed", "실패 ✗"),
                    ("skipped", "건너뜀 ⊙"), ("broken", "오류 ⚠")]

    for status, status_label in status_order:
        status_results = by_status.get(status, [])
        if not status_results:
            continue

        html += f'''<div class="feature-group">
            <div class="feature-header">
                {status_label} ({len(status_results)}건)
            </div>
            <table>
                <thead>
                    <tr>
                        <th>TC ID</th>
                        <th>화면/기능</th>
                        <th>파일명</th>
                        <th>함수명</th>
                        <th>실행시간</th>
                    </tr>
                </thead>
                <tbody>'''

        for r in sorted(status_results, key=lambda x: (x.feature, x.test_class)):
            html += f'''<tr>
                <td><span class="tc-id">{_html_escape(r.tc_id)}</span></td>
                <td>{_html_escape(r.feature)}</td>
                <td><code>{_html_escape(r.test_class)}</code></td>
                <td><code style="font-size: 12px;">{_html_escape(r.test_method)}</code></td>
                <td><span class="time">{_format_duration(r.duration_ms)}</span></td>
            </tr>'''

            if r.message:
                html += f'''<tr>
                    <td colspan="5">
                        <div class="message {'' if status != 'failed' else 'failed'}">
                            {_html_escape(r.message[:500])}
                        </div>
                    </td>
                </tr>'''

        html += '''</tbody></table></div>'''

    if not html:
        html = '<div class="empty">테스트 결과가 없습니다.</div>'

    return html


def _generate_all_table(results: list[TestResult]) -> str:
    """전체 목록 테이블 생성."""
    if not results:
        return '<div class="empty">테스트 결과가 없습니다.</div>'

    html = '''<table>
        <thead>
            <tr>
                <th>상태</th>
                <th>TC ID</th>
                <th>화면/기능</th>
                <th>파일명</th>
                <th>함수명</th>
                <th>실행시간</th>
            </tr>
        </thead>
        <tbody>'''

    for r in sorted(results, key=lambda x: (x.status != "failed", x.feature, x.test_class)):
        html += f'''<tr>
            <td><span class="status-badge status-{r.status}">
                {r.status_ko}
            </span></td>
            <td><span class="tc-id">{_html_escape(r.tc_id)}</span></td>
            <td>{_html_escape(r.feature)}</td>
            <td><code>{_html_escape(r.test_class)}</code></td>
            <td><code style="font-size: 12px;">{_html_escape(r.test_method)}</code></td>
            <td><span class="time">{_format_duration(r.duration_ms)}</span></td>
        </tr>'''

        if r.message and r.status in ("failed", "broken"):
            html += f'''<tr>
                <td colspan="6">
                    <div class="message failed">
                        {_html_escape(r.message[:500])}
                    </div>
                </td>
            </tr>'''

    html += '''</tbody></table>'''
    return html


def main():
    parser = argparse.ArgumentParser(
        description="QA-친화적 Allure 리포트 생성"
    )
    parser.add_argument(
        "results_dir",
        nargs="?",
        default="allure-results",
        help="Allure 결과 디렉토리 (기본값: allure-results)"
    )
    parser.add_argument(
        "-o",
        "--output",
        default="qa-report.html",
        help="출력 파일명 (기본값: qa-report.html)"
    )

    args = parser.parse_args()

    if not os.path.isdir(args.results_dir):
        print(f"[오류] {args.results_dir} 디렉토리를 찾을 수 없습니다.")
        return 1

    print(f"[진행] {args.results_dir}에서 테스트 결과를 로드 중...")
    results = load_results(args.results_dir)

    if not results:
        print("[알림] 처리할 테스트 결과가 없습니다.")
        return 0

    print(f"[진행] {len(results)}건의 테스트 결과를 발견했습니다.")
    print(f"[진행] HTML 리포트를 생성 중...")

    html = generate_html(results)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[완료] 리포트 생성 완료: {output_path}")
    print(f"       총 {len(results)}건 | "
          f"성공 {sum(1 for r in results if r.status == 'passed')} | "
          f"실패 {sum(1 for r in results if r.status == 'failed')}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
