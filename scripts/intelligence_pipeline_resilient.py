#!/usr/bin/env python3
"""
Modified Intelligence Pipeline - Rate Limit Resilient
arXiv rate limit 오류를 처리하기 위해 수정된 버전
"""

import sys
import argparse
import asyncio
from collections import defaultdict
from utils import setup_logger
from collector import NewsCollector
from writer import BlogWriter
from notion_publisher import NotionPublisher
from selector import ArticleSelector

logger = setup_logger(__name__, "pipeline_resilient.log")

async def run_pipeline_async_resilient(max_articles: int = 5):
    logger.info("=== Intelligence Pipeline (Resilient) Started ===")

    try:
        # 1. 뉴스 수집 (Collector) - 실패한 소스 건너뛰기
        logger.info("[1/4] Collecting news from available sources...")
        collector = NewsCollector()
        raw_articles = []
        
        # Google News 수집
        logger.info("  - Fetching Google News...")
        try:
            for keyword in ["Vulnerability", "Security", "Cybersecurity"]:
                articles = collector.fetch_google_news(keyword, max_results_per_source=15)
                raw_articles.extend(articles)
            logger.info(f"  → Google News: {len(articles)} articles")
        except Exception as e:
            logger.error(f"  ❌ Google News failed: {e}")
        
        # arXiv 수집 (rate limit 시 건너뛰기)
        logger.info("  - Fetching arXiv papers...")
        try:
            arxiv_articles = collector.fetch_arxiv(max_results=15)
            raw_articles.extend(arxiv_articles)
            logger.info(f"  → arXiv: {len(arxiv_articles)} articles")
        except Exception as e:
            logger.warning(f"  ⚠️ arXiv skipped due to rate limit: {e}")
        
        # HackerNews 수집
        logger.info("  - Fetching HackerNews...")
        try:
            hn_articles = collector.fetch_hackernews(max_results=15)
            raw_articles.extend(hn_articles)
            logger.info(f"  → HackerNews: {len(hn_articles)} articles")
        except Exception as e:
            logger.error(f"  ❌ HackerNews failed: {e}")
        
        # Hada.io 수집
        logger.info("  - Fetching Hada.io...")
        try:
            hada_articles = collector.fetch_hadaio(max_results=10)
            raw_articles.extend(hada_articles)
            logger.info(f"  → Hada.io: {len(hada_articles)} articles")
        except Exception as e:
            logger.error(f"  ❌ Hada.io failed: {e}")
        
        # Geeknews 수집
        logger.info("  - Fetching Geeknews...")
        try:
            geek_articles = collector.fetch_geeknews(max_results=10)
            raw_articles.extend(geek_articles)
            logger.info(f"  → Geeknews: {len(geek_articles)} articles")
        except Exception as e:
            logger.error(f"  ❌ Geeknews failed: {e}")

        if not raw_articles:
            logger.warning("No articles collected from any source. Terminating pipeline.")
            return

        logger.info(f"Total candidates collected: {len(raw_articles)}")

        # 2. AI 기반 기사 선별 (Async Selector)
        logger.info(f"[2/4] AI evaluating and selecting best {max_articles} articles (Async)...")
        selector = ArticleSelector()
        selected_articles = await selector.evaluate_and_select(
            raw_articles, 
            max_articles=max_articles,
            min_score=6  # 품질 관리 (6점 미만 탈락)
        )

        if not selected_articles:
            logger.warning("No articles passed the selection criteria (Score >= 6).")
            return

        # 3. 블로그 글 작성 (Async Writer)
        logger.info(f"[3/4] Writing blog posts for {len(selected_articles)} articles (Parallel)...")
        writer = BlogWriter()
        
        # 병렬 실행
        blog_posts_results = await writer.generate_article_batch(selected_articles)
        
        valid_posts = []
        for res in blog_posts_results:
            if isinstance(res, dict) and 'title' in res:
                valid_posts.append(res)
                logger.info(f"   ✅ Done: {res['title'][:40]}")
            elif isinstance(res, Exception):
                logger.error(f"   ❌ Writing failed: {res}")

        # 4. Notion 저장 (Publisher)
        # Notion API는 순차적으로 호출 (Rate Limit 고려)
        logger.info(f"[4/4] Publishing {len(valid_posts)} posts to Notion...")
        notion_pub = NotionPublisher()
        
        success_count = 0
        for i, post in enumerate(valid_posts, 1):
            try:
                logger.info(f"   ({i}/{len(valid_posts)}) Sending to Notion: {post['title'][:40]}...")
                result = notion_pub.create_article(post)
                if result.get('id'):
                    success_count += 1
                    logger.info(f"   ✅ Success: {result.get('url')}")
            except Exception as e:
                logger.error(f"   ❌ Failed to publish to Notion: {e}")
        
        logger.info(f"=== Pipeline Completed: {success_count}/{len(valid_posts)} articles published successfully ===")

    except Exception as e:
        logger.error(f"Critical Pipeline Error: {e}", exc_info=True)
        raise

def main():
    parser = argparse.ArgumentParser(description='Intelligence Agent Pipeline (Resilient)')
    parser.add_argument('--max-articles', type=int, default=5, help='최종 생성할 블로그 글 수')
    args = parser.parse_args()

    asyncio.run(run_pipeline_async_resilient(max_articles=args.max_articles))

if __name__ == "__main__":
    main()