"""
GitHub Pages (Hugo) Publisher
Notion 글(마크다운)을 Hugo content/post 포스트로 만들고 git push 한다.
디스패치 일관성을 위해 글당 commit/push (AUTO_PUBLISH_MAX가 작아 비용 무시 가능).
"""

import re
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import requests

from config import BLOG_REPO_PATH, BLOG_URL
from utils import setup_logger
from publisher_base import PublishResult, PLATFORM_GITHUB

logger = setup_logger(__name__, "auto-publish-approved.log")

blog_path = Path(BLOG_REPO_PATH)
posts_dir = blog_path / "content" / "post"

# 표준 카테고리 폴더/분류 일관성: 영문·변형 → 표준 한글, 빈 값 → 보안
CATEGORY_NORMALIZE = {
    "security": "보안", "Security": "보안", "보안": "보안",
    "vulnerability": "보안", "Vulnerability": "보안",
    "AI": "AI", "ai": "AI",
    "DevOps": "DevOps", "devops": "DevOps", "Dev": "DevOps",
    "인프라": "DevOps", "System": "DevOps",
    "CVE": "CVE", "cve": "CVE",
    "IT": "IT",
    "가이드라인": "가이드라인",
}


def _norm_category(cat) -> str:
    cat = (cat or "").strip()
    return CATEGORY_NORMALIZE.get(cat, cat or "보안")


def sanitize_filename(title: str) -> str:
    """파일명/슬러그로 사용 가능한 문자열로 변환 (auto_publish_approved와 동일 규칙)."""
    filename = re.sub(r"[^\w\s-]", "", title)
    filename = re.sub(r"[\s]+", "-", filename)
    return filename[:100]


def post_exists(article: dict) -> bool:
    """이미 동일 슬러그의 Hugo 포스트가 있는지."""
    slug = sanitize_filename(article["title"])
    return (posts_dir / _norm_category(article["category"]) / slug / "index.md").exists()


_IMG_MD = re.compile(r'!\[([^\]]*)\]\((https?://[^)\s]+)\)')
_CT_EXT = {"image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif",
           "image/webp": ".webp", "image/svg+xml": ".svg", "image/bmp": ".bmp"}


def _guess_ext(url: str, content_type: str) -> str:
    path = urlparse(url).path.lower()
    for e in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp"):
        if path.endswith(e):
            return ".jpg" if e == ".jpeg" else e
    return _CT_EXT.get((content_type or "").split(";")[0].strip(), ".png")


def _localize_images(markdown: str, post_dir: Path) -> str:
    """본문의 원격 이미지(![](http...))를 다운로드해 <post_dir>/images/에 저장하고
    마크다운을 로컬 상대경로(images/..)로 치환. Hugo 페이지 번들 리소스로 영구 보존.
    (Notion 업로드 이미지의 임시 서명 URL이 만료되어 깨지는 문제 해결)
    """
    images_dir = post_dir / "images"
    counter = [0]

    def repl(m):
        alt, url = m.group(1), m.group(2)
        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            counter[0] += 1
            ext = _guess_ext(url, r.headers.get("content-type", ""))
            images_dir.mkdir(parents=True, exist_ok=True)
            fname = f"img_{counter[0]}{ext}"
            (images_dir / fname).write_bytes(r.content)
            return f"![{alt}](images/{fname})"
        except Exception as e:  # noqa: BLE001
            logger.warning(f"이미지 다운로드 실패, 원본 URL 유지: {url[:60]} ({e})")
            return m.group(0)

    return _IMG_MD.sub(repl, markdown)


def _create_hugo_post(article: dict, markdown: str) -> str:
    """Hugo 포스트 파일 생성 → 저장소 기준 상대경로(content/post/...) 반환."""
    date_str = datetime.now().strftime("%Y-%m-%d")
    time_str = datetime.now().strftime("%H:%M:%S")
    slug = sanitize_filename(article["title"])
    category = _norm_category(article["category"])

    post_dir = posts_dir / category / slug
    post_dir.mkdir(parents=True, exist_ok=True)
    # 원격/Notion 이미지를 번들 내 images/로 다운로드 + 경로 치환
    markdown = _localize_images(markdown, post_dir)
    filepath = post_dir / "index.md"

    front_matter = (
        f"---\n"
        f'title: "{article["title"]}"\n'
        f"date: {date_str}T{time_str}+09:00\n"
        f"draft: false\n"
        f'categories: ["{category}"]\n'
        f'tags: ["{category}"]\n'
        f'author: "Intelligence Agent"\n'
        f"---\n\n"
    )
    source = ""
    if article.get("url"):
        source = f"\n\n---\n\n**출처**: [{article['url']}]({article['url']})"

    filepath.write_text(front_matter + markdown + source, encoding="utf-8")
    return f"content/post/{category}/{slug}/index.md"


def _git(args: list) -> None:
    subprocess.run(["git", *args], cwd=blog_path, check=True, capture_output=True)


def _commit_and_push(rel_path: str, title: str) -> None:
    # 번들 디렉터리째 add → index.md + images/ 모두 포함
    _git(["add", str(Path(rel_path).parent)])
    _git(["commit", "-m", f"feat: 블로그 글 추가 - {title[:50]} ({datetime.now():%Y-%m-%d %H:%M})"])
    _git(["pull", "--rebase", "origin", "main"])
    _git(["push", "origin", "main"])


def _public_url(article: dict) -> str:
    slug = sanitize_filename(article["title"])
    return BLOG_URL.rstrip("/") + "/" + slug + "/"


def publish(article: dict, markdown: str, html: str) -> PublishResult:
    """Hugo 포스트 생성 + git push. (html은 사용 안 함 — GitHub은 마크다운)"""
    title = article["title"]
    try:
        if post_exists(article):
            # 파일은 있는데 미push 였을 수 있으나, 일반적으로 이미 게시된 것으로 간주.
            logger.info(f"[GitHub] 이미 존재: {title[:50]}")
            return PublishResult(PLATFORM_GITHUB, ok=True, url=_public_url(article))

        rel = _create_hugo_post(article, markdown)
        _commit_and_push(rel, title)
        logger.info(f"[GitHub] push 완료: {rel}")
        return PublishResult(PLATFORM_GITHUB, ok=True, url=_public_url(article))

    except subprocess.CalledProcessError as e:
        err = (e.stderr or b"").decode("utf-8", "ignore")[:200]
        logger.error(f"[GitHub] git 실패: {err}")
        return PublishResult(PLATFORM_GITHUB, ok=False, error=f"git: {err}")
    except Exception as e:  # noqa: BLE001
        logger.error(f"[GitHub] 실패: {e}")
        return PublishResult(PLATFORM_GITHUB, ok=False, error=str(e)[:200])
