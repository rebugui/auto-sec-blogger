"""발행 직전 본문 정규화: ① Notion 왕복으로 한 줄에 뭉친 표/번호목록 복구,
② 깨진 mermaid 다이어그램 교정.

Notion `_convert_to_blocks`는 마크다운 표·번호목록을 인식하지 못해 연속 줄을 한
문단으로 합친다(예: `| h | h | |---|---| | a | b |`). Hugo(goldmark)는 한 줄
표/목록을 렌더하지 못해 생마크다운이 노출된다.

또한 LLM이 만든 mermaid는 라벨 속 괄호 `()`·기형 엣지(`X --|l|--> Y`)·미치환
placeholder(`{content}`)·비-다이어그램(ASCII 트리) 때문에 v11 파서에서 깨진다.
`sanitize_mermaid`가 이를 발행 시점에 자동 교정한다(괄호 라벨 따옴표, 엣지 정상화,
placeholder 제거, 비-다이어그램은 일반 코드펜스로 강등).

좌상단 빈 헤더 셀이 있는 비교 매트릭스 등 모호한 표는 안전하게 건너뛴다(원형 유지).
front matter는 절대 변형하지 않는다.
"""
import re

_SEP = re.compile(r":?-{2,}:?")
_TABLE_LINE = re.compile(r"^\s*\|.*\|\s*:?-{2,}")
_MARK = re.compile(r"(?<![\d.])(\d+)\.\s")

# --- mermaid 교정용 ---
_DIAG = re.compile(
    r"^\s*(graph|flowchart|sequenceDiagram|classDiagram|stateDiagram|erDiagram|"
    r"journey|gantt|pie|mindmap|timeline|gitGraph|quadrantChart|C4Context|"
    r"requirementDiagram|sankey|xychart|block)\b")
_BAD_EDGE = re.compile(r"--\|([^|]+)\|-->")               # 기형 엣지
# 라벨 컨테이너 (더블 델리미터는 룩비하인드/룩어헤드로 보호)
_BRACKET = re.compile(r"(?<![\[\(\{])\[([^\[\]]*?)\](?![\]\)\}])")
_BRACE = re.compile(r"(?<![\{\[\(])\{([^\{\}]*?)\}(?![\}\]\)])")
_PIPE = re.compile(r"\|([^|]*?)\|")


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


def _quote_if_paren(inner: str, open_c: str, close_c: str):
    """라벨 텍스트에 괄호가 있고 따옴표로 안 감싸졌으면 따옴표로 감싼 형태 반환, 아니면 None."""
    if "(" not in inner and ")" not in inner:
        return None
    if inner.lstrip().startswith('"'):
        return None
    return f'{open_c}"{inner}"{close_c}'


def _q_bracket(m):
    return _quote_if_paren(m.group(1), "[", "]") or m.group(0)


def _q_brace(m):
    return _quote_if_paren(m.group(1), "{", "}") or m.group(0)


def _q_pipe(m):
    return _quote_if_paren(m.group(1), "|", "|") or m.group(0)


def _fix_mermaid_body(code: str) -> str:
    """mermaid 본문 교정: 기형 엣지 정상화 + 괄호 라벨 따옴표 처리."""
    code = _BAD_EDGE.sub(r"-->|\1|", code)  # X --|l|--> Y → X -->|l| Y
    out = []
    for ln in code.split("\n"):
        ln = _BRACKET.sub(_q_bracket, ln)
        ln = _BRACE.sub(_q_brace, ln)
        ln = _PIPE.sub(_q_pipe, ln)
        out.append(ln)
    return "\n".join(out)


def sanitize_mermaid(markdown: str) -> str:
    """본문의 ```mermaid 블록을 교정한다(blocked-level).

    - 빈/placeholder 블록(`{content}` 등) → 제거
    - 유효 diagram 타입으로 시작 안 함(주석·ASCII 트리) → 일반 코드펜스로 강등(내용 보존)
    - 그 외 → 기형 엣지·괄호 라벨 교정
    """
    def handle(m):
        body = m.group(1)
        bt = body.strip()
        if bt == "" or (bt.startswith("{") and bt.endswith("}") and "\n" not in bt):
            return ""
        first = next((l for l in bt.splitlines() if l.strip()), "")
        if not _DIAG.match(first):
            return "```\n" + body + "```"
        return "```mermaid\n" + _fix_mermaid_body(body) + "```"

    return re.sub(r"```mermaid\n(.*?)```", handle, markdown, flags=re.S)


def restore(markdown: str) -> str:
    """본문 마크다운을 정규화해 반환. 코드펜스 내부는 보존(mermaid는 별도 교정)."""
    markdown = sanitize_mermaid(markdown)  # mermaid 블록 교정 (펜스 내부)
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
