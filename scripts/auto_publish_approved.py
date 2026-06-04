#!/usr/bin/env python3
"""
Auto-Sec-Blogger 자동 발행 스크립트
3시간마다 Notion에서 "검토 완료" 상태인 글을 찾아 블로그에 발행
"""

import os
import sys
import re
import json
import urllib.request
from pathlib import Path
from datetime import datetime

# 설정은 config.py로 단일화 (config가 ~/.hermes/.skills.env까지 폴백 로드).
# 스크립트 자신의 디렉토리(scripts/)가 sys.path[0]이므로 직접 import 가능.
from config import NOTION_API_KEY, NOTION_DATABASE_ID, BLOG_REPO_PATH, LOG_DIR

# 멀티플랫폼 퍼블리셔
import content_html
import publisher_github
import publisher_naver
import publisher_tistory
from publisher_base import (
    PublishResult, PLATFORM_GITHUB, PLATFORM_NAVER, PLATFORM_TISTORY,
)

# 플랫폼명 → 퍼블리셔 함수
PUBLISHERS = {
    PLATFORM_GITHUB: publisher_github.publish,
    PLATFORM_NAVER: publisher_naver.publish,
    PLATFORM_TISTORY: publisher_tistory.publish,
}

notion_token = NOTION_API_KEY
database_id = NOTION_DATABASE_ID          # 파이프라인과 동일 DB (INTELLIGENCE_BLOG_DATABASE_ID)
blog_path = Path(BLOG_REPO_PATH)          # 하드코딩 제거 → .skills.env의 BLOG_REPO_PATH 사용
posts_dir = blog_path / 'content' / 'post'

# 발행 대상 상태: 기본 '검토 완료'(사람이 Notion에서 검토 후 승인한 글만 발행).
#   파이프라인은 새 글을 '검토중'까지만 만들고, 사람이 '검토 완료'로 올린 것만 게시됨.
#   (완전 자동발행을 원하면 .skills.env에 AUTO_PUBLISH_STATUS="검토중" 설정)
PUBLISH_STATUS = os.getenv('AUTO_PUBLISH_STATUS', '검토 완료')

# 1회 실행당 발행 상한 (백로그 대량 일괄 발행/중복 게시 방지). 최신순으로 N건만.
AUTO_PUBLISH_MAX = int(os.getenv('AUTO_PUBLISH_MAX', '5'))

# 로그 파일 (스킬 logs 디렉토리로 통일)
log_file = LOG_DIR / 'auto-publish-approved.log'


def log(message):
    """로그 기록"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_message = f"[{timestamp}] {message}"
    print(log_message)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(log_message + '\n')


def notion_request(url, method='GET', body=None):
    """Notion API 요청 헬퍼"""
    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read())
    except Exception as e:
        log(f"❌ Notion API 오류: {e}")
        return None


def extract_rich_text(block_data, key='rich_text'):
    """rich_text 배열에서 일반 텍스트 추출 (inline bold/italic/code/링크 유지)"""
    parts = block_data.get(key, [])
    result = []
    for part in parts:
        text = part.get('plain_text', '')
        href = part.get('href', None)
        annotations = part.get('annotations', {})

        if href:
            result.append(f"[{text}]({href})")
        else:
            if annotations.get('code'):
                text = f"`{text}`"
            if annotations.get('bold'):
                text = f"**{text}**"
            if annotations.get('italic'):
                text = f"*{text}*"
            if annotations.get('strikethrough'):
                text = f"~~{text}~~"
            result.append(text)
    return ''.join(result)


def block_to_markdown(block):
    """Notion 블록 → 마크다운 변환"""
    btype = block.get('type', '')

    if btype in ('paragraph', 'heading_1', 'heading_2', 'heading_3'):
        text = extract_rich_text(block.get(btype, {}))
        if not text.strip():
            return ''
        if btype == 'heading_1':
            return f"\n# {text}\n"
        elif btype == 'heading_2':
            return f"\n## {text}\n"
        elif btype == 'heading_3':
            return f"\n### {text}\n"
        return f"\n{text}\n"

    elif btype == 'bulleted_list_item':
        text = extract_rich_text(block.get(btype, {}))
        return f"- {text}\n"

    elif btype == 'numbered_list_item':
        text = extract_rich_text(block.get(btype, {}))
        return f"1. {text}\n"

    elif btype == 'code':
        text = extract_rich_text(block.get(btype, {}))
        lang = block.get('code', {}).get('language', '')
        return f"\n```{lang}\n{text}\n```\n"

    elif btype == 'quote':
        text = extract_rich_text(block.get(btype, {}))
        lines = text.split('\n')
        return '\n'.join(f'> {line}' for line in lines) + '\n'

    elif btype == 'callout':
        text = extract_rich_text(block.get(btype, {}))
        emoji = block.get('callout', {}).get('icon', {})
        if isinstance(emoji, dict):
            emoji = emoji.get('emoji', '💡')
        return f"\n> {emoji} {text}\n"

    elif btype == 'divider':
        return "\n---\n"

    elif btype == 'table':
        return _table_to_markdown(block)

    elif btype == 'image':
        image = block.get('image', {})
        url = ''
        if image.get('type') == 'external':
            url = image.get('external', {}).get('url', '')
        elif image.get('type') == 'file':
            url = image.get('file', {}).get('url', '')
        caption = extract_rich_text(image.get('caption', []))
        alt = caption if caption else 'image'
        return f"\n![{alt}]({url})\n" if url else ''

    elif btype == 'bookmark':
        url = block.get('bookmark', {}).get('url', '')
        caption = extract_rich_text(block.get('bookmark', {}).get('caption', []))
        label = caption if caption else url
        return f"\n[{label}]({url})\n" if url else ''

    elif btype == 'toggle':
        text = extract_rich_text(block.get(btype, {}))
        return f"\n<details>\n<summary>{text}</summary>\n\n</details>\n"

    elif btype == 'table_of_contents':
        return "\n**목차**\n\n"

    elif btype == 'child_page':
        return ''

    return ''


def _table_to_markdown(block):
    """Notion 테이블 → 마크다운 테이블"""
    table = block.get('table', {})
    width = table.get('table_width', 0)
    has_header = table.get('has_row_header', False)
    rows = table.get('rows', [])

    if not rows:
        return ''

    md_lines = []
    for i, row in enumerate(rows):
        cells = row.get('cells', [])
        cell_texts = []
        for cell in cells:
            cell_texts.append(extract_rich_text(cell).replace('|', '\\|').replace('\n', ' '))
        line = '| ' + ' | '.join(cell_texts) + ' |'
        md_lines.append(line)

        if i == 0 and has_header:
            md_lines.append('| ' + ' | '.join(['---'] * len(cells)) + ' |')

    return '\n'.join(md_lines) + '\n'


def fetch_page_content(page_id):
    """Notion 페이지의 전체 블록을 마크다운으로 변환"""
    url = f"https://api.notion.com/v1/blocks/{page_id}/children?page_size=100"
    data = notion_request(url)
    if not data:
        return ''

    markdown_parts = []
    for block in data.get('results', []):
        md = block_to_markdown(block)
        if md:
            markdown_parts.append(md)

    # has_more인 경우 추가 페이지 로드
    while data.get('has_more'):
        cursor = data.get('next_cursor')
        url = f"https://api.notion.com/v1/blocks/{page_id}/children?page_size=100&start_cursor={cursor}"
        data = notion_request(url)
        if not data:
            break
        for block in data.get('results', []):
            md = block_to_markdown(block)
            if md:
                markdown_parts.append(md)

    content = ''.join(markdown_parts).strip()
    # 연속 빈줄 정리
    content = re.sub(r'\n{3,}', '\n\n', content)
    return content


def get_approved_articles():
    """Notion에서 발행 대상 상태(PUBLISH_STATUS)인 글 조회"""
    query_url = f"https://api.notion.com/v1/databases/{database_id}/query"
    payload = {
        "filter": {
            "property": "상태",
            "status": {"equals": PUBLISH_STATUS}
        },
        "sorts": [{"timestamp": "created_time", "direction": "descending"}],
        "page_size": 50
    }

    data = notion_request(query_url, method='POST', body=payload)
    if not data:
        return []

    results = data.get('results', [])
    log(f"📊 '{PUBLISH_STATUS}' 상태인 글: {len(results)}개 발견")

    articles = []
    for page in results:
        # 제목 추출
        title = "제목 없음"
        title_prop = page['properties'].get('내용')
        if title_prop and title_prop.get('title'):
            title = title_prop['title'][0]['plain_text']

        # 카테고리 추출
        category = "security"
        category_prop = page['properties'].get('카테고리')
        if category_prop and category_prop.get('select'):
            category = category_prop['select']['name']

        # URL 추출
        url = ""
        url_prop = page['properties'].get('URL')
        if url_prop and url_prop.get('url'):
            url = url_prop['url']

        # 태그 (multi_select '테그')
        tags = [t.get('name', '') for t in page['properties'].get('테그', {}).get('multi_select', [])]

        # 발행 대상 플랫폼 (multi_select '플랫폼') — 비어있으면 발행하지 않음
        platforms = [p.get('name', '') for p in page['properties'].get('플랫폼', {}).get('multi_select', [])]
        # 이미 게시된 플랫폼 (multi_select '게시된 플랫폼') — 중복 발행 방지
        published = [p.get('name', '') for p in page['properties'].get('게시된 플랫폼', {}).get('multi_select', [])]

        if not platforms:
            log(f"  ⏭️ '플랫폼' 미선택 → 건너뜀: {title[:40]}")
            continue

        articles.append({
            'title': title,
            'category': category,
            'url': url,
            'tags': [t for t in tags if t],
            'platforms': [p for p in platforms if p],
            'published_platforms': [p for p in published if p],
            'page_id': page['id'],
        })

    # 1회 발행 상한 적용 (최신순 상위 N건만)
    if len(articles) > AUTO_PUBLISH_MAX:
        log(f"발행 상한 적용: {len(articles)}건 중 최신 {AUTO_PUBLISH_MAX}건만 처리")
        articles = articles[:AUTO_PUBLISH_MAX]

    return articles


def update_published_platforms(page_id, platforms):
    """'게시된 플랫폼' multi_select 갱신 (idempotency 기록)."""
    url = f"https://api.notion.com/v1/pages/{page_id}"
    body = {
        "properties": {
            "게시된 플랫폼": {"multi_select": [{"name": p} for p in sorted(set(platforms))]}
        }
    }
    return notion_request(url, method='PATCH', body=body) is not None


def update_deploy_url(page_id, url_value):
    """'배포 URL' 기록 (best-effort — 속성 없으면 무시)."""
    if not url_value:
        return
    api = f"https://api.notion.com/v1/pages/{page_id}"
    notion_request(api, method='PATCH', body={"properties": {"배포 URL": {"url": url_value}}})


def update_notion_status(page_id, status_name="게시 완료"):
    """Notion 페이지 상태 업데이트"""
    url = f"https://api.notion.com/v1/pages/{page_id}"
    body = {
        "properties": {
            "상태": {"status": {"name": status_name}}
        }
    }
    data = notion_request(url, method='PATCH', body=body)
    return data is not None


def publish_article(article, idx, total):
    """단일 글을 선택된(미게시) 플랫폼들에 발행. (newly_published, all_done) 반환."""
    title = article['title']
    requested = [p for p in article['platforms'] if p in PUBLISHERS]
    already = set(article['published_platforms'])
    todo = [p for p in requested if p not in already]

    if not requested:
        log(f"  [{idx}/{total}] ⏭️ 지원 플랫폼 없음({article['platforms']}): {title[:40]}")
        return [], False
    if not todo:
        log(f"  [{idx}/{total}] ✅ 이미 모두 게시됨: {title[:40]}")
        return [], True

    log(f"  [{idx}/{total}] 📥 본문 수집: {title[:45]} → 대상 {todo}")
    markdown = fetch_page_content(article['page_id'])
    if not markdown:
        log(f"    ⚠️ 본문 없음, 스킵")
        return [], False

    # 네이버/티스토리용 HTML (Mermaid는 이미지로). GitHub은 markdown 사용.
    html = content_html.to_html(markdown)

    newly = []
    for platform in todo:
        result = PUBLISHERS[platform](article, markdown, html)
        if result.ok:
            newly.append(platform)
            log(f"    ✅ {platform} 게시: {result.url or '(URL 미반환)'}")
            update_deploy_url(article['page_id'], result.url)
        else:
            log(f"    ❌ {platform} 실패: {result.error}")

    if newly:
        update_published_platforms(article['page_id'], already | set(newly))

    all_done = set(requested) <= (already | set(newly))
    return newly, all_done


def main():
    log("=" * 70)
    log("🚀 Auto-Sec-Blogger 멀티플랫폼 발행 시작")
    log("=" * 70)

    articles = get_approved_articles()
    if not articles:
        log("📭 발행할 글이 없습니다.")
        return

    total = len(articles)
    published_count = 0
    for i, article in enumerate(articles, 1):
        newly, all_done = publish_article(article, i, total)
        published_count += len(newly)
        # 요청한 플랫폼 전부 게시 완료된 경우에만 상태 전환 (부분 실패는 다음 run 재시도)
        if all_done:
            update_notion_status(article['page_id'], "게시 완료")
            log(f"    🏁 상태 → 게시 완료")

    log("\n" + "=" * 70)
    log(f"✅ 자동 발행 완료 (신규 게시 {published_count}건)")
    log("=" * 70)


if __name__ == "__main__":
    main()
