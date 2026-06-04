#!/usr/bin/env python3
"""
오리지널 딥다이브 생성기
뉴스에 매이지 않는 에버그린 전문 글(방법론/튜토리얼/심층분석)을 생성해
Notion에 '검토중' 초안으로 발행한다. 사람이 Notion에서 검토 후 발행하면
기존 auto_publish_approved 흐름으로 블로그에 게시된다.

사용:
    python3 generate_original.py --topic "주제" --category 보안
    python3 generate_original.py --seed          # 전문성 기반 시드 토픽 일괄 생성
    python3 generate_original.py --seed -n 3      # 시드 중 앞 3개만
"""

import argparse
import asyncio

from writer import BlogWriter
from notion_publisher import NotionPublisher
from utils import setup_logger

logger = setup_logger(__name__, "writer.log")

# 운영자 전문성(취약점 진단·논리적 취약점·진단 자동화·LLM 보안) 기반 에버그린 시드 토픽
SEED_TOPICS = [
    ("인증 로직의 논리적 취약점 분석 방법론: 인증 우회와 권한 상승 실전 패턴", "보안"),
    ("KISA 주요정보통신기반시설 기술적 취약점 진단 자동화: 스크립트 설계와 운영 노하우", "보안"),
    ("LLM을 활용한 취약점 분석 워크플로우: 프롬프트 설계부터 오탐 관리까지", "AI"),
    ("웹 애플리케이션 침투테스트 체크리스트: 진단가 관점의 우선순위와 사고 과정", "보안"),
    ("취약점 진단 보고서 작성법: 위험도(CVSS) 산정과 실무 대응 가이드", "보안"),
]


async def _generate_and_publish(writer: BlogWriter, notion: NotionPublisher,
                                topic: str, category: str) -> bool:
    try:
        article = await writer.generate_original(topic, category)
    except Exception as e:  # noqa: BLE001
        logger.error(f"생성 실패: {topic[:40]} — {e}")
        return False
    if not article.get("content") or len(article["content"]) < 300:
        logger.warning(f"본문 과소로 발행 보류: {topic[:40]}")
        return False
    try:
        result = notion.create_article(article)
    except Exception as e:  # noqa: BLE001
        logger.error(f"Notion 발행 예외: {topic[:40]} — {e}")
        return False
    if result and result.get("id"):
        logger.info(f"✅ Notion 검토중 발행: {article['title'][:50]} ({len(article['content'])}자)")
        print(f"✅ {article['title']}  [{category}, {len(article['content'])}자]")
        return True
    logger.error(f"Notion 발행 실패(응답 비정상): {topic[:40]}")
    print(f"❌ 발행 실패: {topic[:40]}")
    return False


async def main_async(topics):
    writer = BlogWriter()
    notion = NotionPublisher()
    ok = 0
    for topic, category in topics:
        if await _generate_and_publish(writer, notion, topic, category):
            ok += 1
    print(f"\n완료: {ok}/{len(topics)}건 Notion 검토중 발행. Notion에서 검토 후 '검토 완료'로 올리면 게시됩니다.")


def main():
    p = argparse.ArgumentParser(description="오리지널 딥다이브 생성 → Notion 검토중 발행")
    p.add_argument("--topic", help="단일 주제")
    p.add_argument("--category", default="보안", help="카테고리(보안/AI/DevOps/CVE)")
    p.add_argument("--seed", action="store_true", help="전문성 기반 시드 토픽 일괄 생성")
    p.add_argument("-n", type=int, default=0, help="시드 중 앞 N개만 (0=전체)")
    args = p.parse_args()

    if args.seed:
        topics = SEED_TOPICS[: args.n] if args.n > 0 else SEED_TOPICS
    elif args.topic:
        topics = [(args.topic, args.category)]
    else:
        p.error("--topic 또는 --seed 중 하나가 필요합니다.")
        return

    asyncio.run(main_async(topics))


if __name__ == "__main__":
    main()
