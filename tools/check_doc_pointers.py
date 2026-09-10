"""코드 주석이 가리키는 문서 경로·섹션이 실제로 있는지 검사한다.

왜 필요한가 - 2026-09-10 에 긴 주석을 문서로 옮기면서 코드에 `파일 "섹션"` 형태의 참조
40여 개가 생겼다. 참조는 **글자로 박혀 있어서** 문서 이름이나 제목이 바뀌면 조용히 거짓이
된다. 코드는 멀쩡히 돌고 테스트도 전부 통과하므로 눈으로는 못 잡는다.

    python tools/check_doc_pointers.py

문서 이름·제목을 바꾼 뒤, 그리고 주석에 새 참조를 넣은 뒤 돌린다.
"""

from __future__ import annotations

import pathlib
import re
import sys

# `docs/…/xxx.md "섹션 제목"` 또는 `CLAUDE.md "장 제목"`. 섹션은 없어도 된다.
REF = re.compile(r'((?:docs/[\w/\-.가-힣]+\.md|CLAUDE\.md))(?:\s*"([^"]+)")?')

# 마크다운 강조 기호는 제목 비교에서 무시한다 (`**굵게**`·`` `코드` ``)
_MARKUP = str.maketrans("", "", "*`")


def _headings(md: pathlib.Path) -> list[str]:
    return [
        line.translate(_MARKUP)
        for line in md.read_text(encoding="utf-8").splitlines()
        if line.lstrip().startswith("#")
    ]


def main() -> int:
    root = pathlib.Path(__file__).resolve().parent.parent
    sources = sorted(root.glob("*.py")) + sorted(root.glob("pages/*.py"))

    checked = 0
    problems: list[str] = []
    for src in sources:
        rel = src.relative_to(root)
        for lineno, line in enumerate(src.read_text(encoding="utf-8").splitlines(), 1):
            for path, section in REF.findall(line):
                checked += 1
                target = root / path
                if not target.exists():
                    problems.append(f"[없는 파일] {rel}:{lineno} -> {path}")
                    continue
                if section and not any(
                    section.translate(_MARKUP) in h for h in _headings(target)
                ):
                    problems.append(f'[없는 섹션] {rel}:{lineno} -> {path} "{section}"')

    for p in problems:
        print(p)
    print(f"\n검사한 참조 {checked}건 - 문제 {len(problems)}건")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
