#!/usr/bin/env python3
"""
Notion 데이터베이스에 있는 글들의 상태를 확인하는 간단한 스크립트
"""

import os
import sys
import json
from pathlib import Path
from notion_publisher import NotionPublisher
from dotenv import load_dotenv

# .env 로드
load_dotenv('/Users/rebugui/.openclaw/workspace/.env')

def main():
    print("🔍 Notion 데이터베이스 상태 확인...")
    
    # Notion Publisher 초기화
    notion = NotionPublisher()
    
    # 특정 상태로 글 조회 테스트
    print("\n🔍 테스트: '검토중' 상태 글 조회...")
    try:
        review_posts = notion._query_database({"property": "상태", "status": {"equals": "검토중"}})
        print(f"✅ '검토중' 상태 글: {len(review_posts)}개")
        for post in review_posts[:3]:
            title = post['properties']['내용']['title'][0]['text']['content'] if '내용' in post['properties'] and post['properties']['내용']['title'] else '제목 없음'
            print(f"  - {title}")
    except Exception as e:
        print(f"❌ '검토중' 조회 오류: {e}")
        
    print("\n🔍 테스트: '검토 완료' 상태 글 조회...")
    try:
        done_posts = notion._query_database({"property": "상태", "status": {"equals": "검토 완료"}})
        print(f"✅ '검토 완료' 상태 글: {len(done_posts)}개")
        for post in done_posts[:3]:
            title = post['properties']['내용']['title'][0]['text']['content'] if '내용' in post['properties'] and post['properties']['내용']['title'] else '제목 없음'
            print(f"  - {title}")
    except Exception as e2:
        print(f"❌ '검토 완료' 조회 오류: {e2}")
        return
    
    # 전체 글 수 계산
    total_posts = len(review_posts) + len(done_posts)
    print(f"📄 총 글 수: {total_posts}")
    
    # 상태별로 그룹화
    status_counts = {"검토중": len(review_posts), "검토 완료": len(done_posts)}
    
    # 최근 글 출력 (검토중 상태의 글들)
    print(f"\n🆕 최근 {min(5, len(review_posts))}개 '검토중' 글:")
    for post in review_posts[:5]:
        title = post['properties']['내용']['title'][0]['text']['content'] if '내용' in post['properties'] and post['properties']['내용']['title'] else '제목 없음'
        post_id = post['id']
        url = post.get('url', 'N/A')
        print(f"  - {title}")
        print(f"    상태: 검토중")
        print(f"    URL: {url}")
        print(f"    ID: {post_id}")
        print()

if __name__ == "__main__":
    main()