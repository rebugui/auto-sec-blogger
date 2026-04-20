#!/usr/bin/env python3
"""
최근에 발행된 블로그 글을 '검토 완료' 상태로 변경하여 GitHub Pages 자동 발행을 준비
"""

import os
import sys
from pathlib import Path
from notion_publisher import NotionPublisher
from dotenv import load_dotenv

# .env 로드
load_dotenv('/Users/rebugui/.openclaw/workspace/.env')

def main():
    print("🔍 최근 발행된 글을 '검토 완료' 상태로 변경합니다...")
    
    # Notion Publisher 초기화
    notion = NotionPublisher()
    
    # 최근 10개의 글 조회 (최신순)
    recent_posts = notion._query_database({
        "property": "상태",
        "status": {"equals": "검토중"}
    })
    
    print(f"📝 '검토중' 상태인 글: {len(recent_posts)}개 발견")
    
    if not recent_posts:
        print("✅ 발행할 글이 없습니다.")
        return
    
    updated_count = 0
    
    for post in recent_posts:
        page_id = post['id']
        title = post['properties']['내용']['title'][0]['text']['content']
        
        print(f"📄 '{title}' -> '검토 완료' 상태로 변경...")
        
        # 상태 업데이트
        if notion.update_status(page_id, "검토 완료"):
            print(f"✅ {title} 업데이트 완료")
            updated_count += 1
        else:
            print(f"❌ {title} 업데이트 실패")
    
    print(f"\n🎉 완료! {updated_count}개의 글이 GitHub Pages 자동 발행을 위해 준비되었습니다.")
    
    # 이제 자동 발행 스크립트 실행
    print("\n🚀 GitHub Pages 자동 발행을 시작합니다...")
    from auto_publish_approved import main as auto_publish_main
    auto_publish_main()

if __name__ == "__main__":
    main()