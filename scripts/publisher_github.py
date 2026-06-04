"""
GitHub Pages (Hugo) Publisher
Notion 글(마크다운)을 Hugo content/post 포스트로 만들고 git push 한다.
디스패치 일관성을 위해 글당 commit/push (AUTO_PUBLISH_MAX가 작아 비용 무시 가능).
"""

import re
import subprocess
from datetime import datetime
from pathlib import Path

from config import BLOG_REPO_PATH, BLOG_URL
from utils import setup_logger
from publisher_base import PublishResult, PLATFORM_GITHUB

logger = setup_logger(__name__, "auto-publish-approved.log")

blog_path = Path(BLOG_REPO_PATH)
posts_dir = blog_path / "content" / "post"


def sanitize_filename(title: str) -> str:
    """파일명/슬러그로 사용 가능한 문자열로 변환 (auto_publish_approved와 동일 규칙)."""
    filename = re.sub(r"[^\w\s-]", "", title)
    filename = re.sub(r"[\s]+", "-", filename)
    return filename[:100]


def post_exists(article: dict) -> bool:
    """이미 동일 슬러그의 Hugo 포스트가 있는지."""
    slug = sanitize_filename(article["title"])
    return (posts_dir / article["category"] / slug / "index.md").exists()


def _create_hugo_post(article: dict, markdown: str) -> str:
    """Hugo 포스트 파일 생성 → 저장소 기준 상대경로(content/post/...) 반환."""
    date_str = datetime.now().strftime("%Y-%m-%d")
    time_str = datetime.now().strftime("%H:%M:%S")
    slug = sanitize_filename(article["title"])
    category = article["category"]

    post_dir = posts_dir / category / slug
    post_dir.mkdir(parents=True, exist_ok=True)
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
    _git(["add", rel_path])
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
