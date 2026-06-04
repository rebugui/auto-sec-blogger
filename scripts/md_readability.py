"""Notion 왕복 변환으로 한 줄에 뭉친 표/번호목록을 여러 줄 마크다운으로 복구한다.

Notion `_convert_to_blocks`는 마크다운 표·번호목록을 인식하지 못해 연속 줄을 한
문단으로 합친다(예: `| h | h | |---|---| | a | b |`). Hugo(goldmark)는 한 줄
표/목록을 렌더하지 못해 생마크다운이 노출된다. 이 모듈은 발행 직전 본문을 정규화한다.

좌상단 빈 헤더 셀이 있는 비교 매트릭스 등 모호한 표는 안전하게 건너뛴다(원형 유지).
코드펜스(```)·front matter는 절대 변형하지 않는다.
"""
import re

_SEP = re.compile(r":?-{2,}:?")
_TABLE_LINE = re.compile(r"^\s*\|.*\|\s*:?-{2,}")
_MARK = re.compile(r"(?<![\d.])(\d+)\.\s")


def _reconstruct_table(line: str):
    """'| h | h | |---|---| | a | b | ...' → 여러 줄 표. 모호하면 None."""
    cells = [c.strip() for c in line.strip().split("|")]
    sep_pos = [i for i, c in enumerate(cells) if _SEP.fullmatch(c)]
    if not sep_pos or sep_pos != list(range(sep_pos[0], sep_pos[0] + len(sep_pos))):
        return None
    n = len(sep_pos)
    aligns = [cells[i] for i in sep_pos]
    header = [c for c in cells[:sep_pos[0]] if c]
    data = [c for c in cells[sep_pos[-1] + 1:] if c]
    if len(header) != n:
        return None  # 빈 헤더 셀 등 모호 → 건너뜀
    out = ["| " + " | ".join(header) + " |", "| " + " | ".join(aligns) + " |"]
    for i in range(0, len(data), n):
        row = data[i:i + n]
        row += [""] * (n - len(row))
        out.append("| " + " | ".join(row) + " |")
    return "\n".join(out)


def _split_ordered(line: str):
    """'pre 1. a 2. b 3. c' → pre + 줄별 번호목록. 1..k 연속일 때만. 아니면 None."""
    marks = [(m.start(), int(m.group(1))) for m in _MARK.finditer(line)]
    if len(marks) < 2 or [n for _, n in marks] != list(range(1, len(marks) + 1)):
        return None
    out = []
    pre = line[:marks[0][0]].strip()
    if pre:
        out.append(pre)
    for j, (pos, _) in enumerate(marks):
        end = marks[j + 1][0] if j + 1 < len(marks) else len(line)
        out.append(line[pos:end].strip())
    return "\n".join(out)


def restore(markdown: str) -> str:
    """본문 마크다운을 정규화해 반환. 코드펜스 내부는 보존."""
    out, in_fence = [], False
    for ln in markdown.split("\n"):
        if ln.lstrip().startswith("```"):
            in_fence = not in_fence
            out.append(ln)
            continue
        if in_fence:
            out.append(ln)
            continue
        if _TABLE_LINE.match(ln):
            t = _reconstruct_table(ln)
            if t:
                out.append(t)
                continue
        o = _split_ordered(ln)
        out.append(o if o else ln)
    return "\n".join(out)
