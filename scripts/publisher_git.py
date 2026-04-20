"""
Git Publisher - 사용자 승인 후 Git Push → GitHub Actions 배포
"""

import os
import subprocess
import time
import re
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path

from notion_publisher import NotionPublisher
from config import BLOG_REPO_PATH, BLOG_URL, NOTION_API_KEY, NOTION_DATABASE_ID
from utils import setup_logger

logger = setup_logger(__name__, "publisher_git.log")

class GitPublisher:
    """Git 기반 블로그 퍼블리셔"""

    def __init__(
        self,
        blog_repo_path: Path = None,
        blog_url: str = None,
        notion_publisher: NotionPublisher = None
    ):
        self.blog_repo_path = blog_repo_path or BLOG_REPO_PATH
        self.blog_url = blog_url or BLOG_URL
        self.notion_publisher = notion_publisher or NotionPublisher()

        # 유효성 검사
        if not self.blog_repo_path.exists():
            raise ValueError(f"블로그 저장소 경로가 존재하지 않습니다: {self.blog_repo_path}")

        git_dir = self.blog_repo_path / ".git"
        if not git_dir.exists():
            raise ValueError(f"Git 저장소가 아닙니다: {self.blog_repo_path}")

    def monitor_and_publish(self, interval_seconds: int = 300) -> None:
        logger.info(f"Starting monitor (interval: {interval_seconds}s)")
        print("💡 사용자가 Notion에서 상태를 '검토 완료'로 변경하면 자동 배포됩니다.")

        while True:
            try:
                publish_articles = self.notion_publisher.get_review_done_articles()

                if publish_articles:
                    logger.info(f"Found {len(publish_articles)} articles to publish.")
                    for article in publish_articles:
                        self.publish_article(article)
                else:
                    # logger.debug("No articles to publish.")
                    pass

                time.sleep(interval_seconds)

            except KeyboardInterrupt:
                logger.info("Monitoring stopped.")
                break
            except Exception as e:
                logger.error(f"Error during monitoring: {e}")
                time.sleep(interval_seconds)

    def publish_article(self, article: Dict) -> None:
        try:
            page_id = article.get('id', '')
            # Extract title (safe navigation)
            props = article.get('properties', {})
            title_prop = props.get('내용', {}).get('title', [])
            title = title_prop[0].get('text', {}).get('content', 'N/A') if title_prop else 'N/A'

            logger.info(f"Publishing: {title}")

            # 1. Create Post
            slug = self._create_blog_post(article, title)

            # 2. Git Commit
            self._git_commit(title)

            # 3. Git Push
            self._git_push()

            # 4. Update Notion
            blog_url = f"{self.blog_url}p/{slug}/"
            self.notion_publisher.update_published_url(page_id, blog_url)
            self.notion_publisher.update_status(page_id, "게시 완료")

            logger.info(f"Published successfully: {blog_url}")

        except Exception as e:
            logger.error(f"Failed to publish '{title}': {e}")
            try:
                self.notion_publisher.update_status(article.get('id', ''), "검토중")
            except:
                pass

    def _create_blog_post(self, article: Dict, title: str) -> str:
        page_id = article.get('id', '')
        props = article.get('properties', {})
        
        category = props.get('카테고리', {}).get('select', {}).get('name', '보안')
        tags_objs = props.get('테그', {}).get('multi_select', [])
        tags_list = [tag.get('name', '') for tag in tags_objs]

        content = self.notion_publisher.get_page_content(page_id)
        if not content:
            content = "이 글은 LLM을 기반으로 작성되었습니다."

        slug = self._slugify(title)
        post_dir = self.blog_repo_path / "content" / "post" / category / slug
        post_dir.mkdir(parents=True, exist_ok=True)
        
        md_file = post_dir / "index.md"
        
        front_matter = f"""---
title: "{title}"
date: {datetime.now().strftime("%Y-%m-%dT%H:%M:%S+09:00")}
draft: false
tags:
{chr(10).join(f'  - "{tag}"' for tag in tags_list)}
categories:
  - "{category}"
---

{content}
"""
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(front_matter)
        
        return slug

    def _git_commit(self, title: str) -> None:
        # cwd 변경 대신 subprocess의 cwd 파라미터 사용 권장
        cmd = ['git', 'add', '.']
        subprocess.run(cmd, cwd=self.blog_repo_path, check=True, capture_output=True)
        
        cmd = ['git', 'commit', '-m', f"feat: 블로그 글 추가 - {title}"]
        subprocess.run(cmd, cwd=self.blog_repo_path, check=True, capture_output=True)

    def _git_push(self) -> None:
        # Pull with rebase first to avoid conflicts
        cmd = ['git', 'pull', '--rebase', 'origin', 'main']
        subprocess.run(cmd, cwd=self.blog_repo_path, check=True, capture_output=True)
        # Then push
        cmd = ['git', 'push', 'origin', 'main']
        subprocess.run(cmd, cwd=self.blog_repo_path, check=True, capture_output=True)

    def _slugify(self, text: str) -> str:
        if re.search(r'[가-힣]', text):
            slug = text.replace(' ', '-')
        else:
            slug = text.lower().replace(' ', '-')
        return re.sub(r'[^\w\-]', '', slug)

    def publish_all_pending(self) -> List[Dict]:
        results = []
        publish_articles = self.notion_publisher.get_review_done_articles()
        
        logger.info(f"Publishing all {len(publish_articles)} pending articles...")

        for article in publish_articles:
            try:
                self.publish_article(article)
                results.append({"success": True, "id": article.get('id')})
            except Exception as e:
                results.append({"success": False, "error": str(e)})
        return results

if __name__ == "__main__":
    if not NOTION_API_KEY or not NOTION_DATABASE_ID:
        print("Set NOTION_API_KEY and NOTION_DATABASE_ID in .env")
    else:
        pub = GitPublisher()
        pub.publish_all_pending()