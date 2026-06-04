"""
Content HTML
Notion에서 받은 마크다운 본문을 네이버/티스토리용 HTML로 변환한다.
- markdown2로 표/코드/링크 변환
- ```mermaid 블록은 mermaid.ink 이미지(<img>)로 치환 (네이버/티스토리는 Mermaid 미렌더).
  변환 실패 시 <pre> 코드블록으로 폴백.
"""

import base64
import re

import markdown2
from utils import setup_logger

logger = setup_logger(__name__, "auto-publish-approved.log")

_MERMAID_RE = re.compile(r"```mermaid\s*\n(.*?)\n```", re.DOTALL)


def _mermaid_to_img(graph: str) -> str:
    """Mermaid 그래프 정의 → mermaid.ink <img> 태그.

    mermaid.ink는 그래프 정의를 base64url 인코딩한 경로를 이미지로 렌더한다.
    (독자 브라우저가 이미지를 로드하므로 네이버/티스토리에서도 표시됨)
    """
    try:
        b64 = base64.urlsafe_b64encode(graph.encode("utf-8")).decode("ascii")
        src = f"https://mermaid.ink/img/{b64}"
        return f'<p><img src="{src}" alt="diagram" style="max-width:100%;"></p>'
    except Exception as e:  # noqa: BLE001 - 폴백 보장
        logger.warning(f"Mermaid 이미지 변환 실패, 코드블록 폴백: {e}")
        safe = graph.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return f"<pre><code>{safe}</code></pre>"


def to_html(markdown_text: str) -> str:
    """마크다운 → HTML. Mermaid 블록은 먼저 이미지로 치환."""
    if not markdown_text:
        return ""

    # 1) Mermaid 블록을 플레이스홀더 없이 직접 <img>로 치환
    def _sub(m: re.Match) -> str:
        return "\n\n" + _mermaid_to_img(m.group(1).strip()) + "\n\n"

    pre = _MERMAID_RE.sub(_sub, markdown_text)

    # 2) 나머지 마크다운 변환
    html = markdown2.markdown(
        pre,
        extras=[
            "fenced-code-blocks",
            "tables",
            "code-friendly",
            "cuddled-lists",
            "break-on-newline",
        ],
    )
    return html
