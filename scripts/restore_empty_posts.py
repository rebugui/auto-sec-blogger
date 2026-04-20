#!/usr/bin/env python3
"""
기존 "내용 없음" 포스트에 Notion 본문 채워넣기 (원회복 스크립트)
1회성 실행
"""

import os
import sys
import re
import json
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from dotenv import load_dotenv

load_dotenv('/Users/rebugui/.openclaw/workspace/.env')

notion_token = os.getenv('NOTION_API_KEY')
database_id = os.getenv('BLOG_DATABASE_ID')
blog_path = Path.home() / '.openclaw' / 'workspace' / 'blog'
posts_dir = blog_path / 'content' / 'post'


def notion_request(url, method='GET', body=None):
    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())


def extract_rich_text(block_data, key='rich_text'):
    parts = block_data.get(key, [])
    result = []
    for part in parts:
        text = part.get('plain_text', '')
        href = part.get('href', None)
        annotations = part.get('annotations', {})
        if href:
            result.append(f"[{text}]({href})")
        else:
            if annotations.get('code'): text = f"`{text}`"
            if annotations.get('bold'): text = f"**{text}**"
            if annotations.get('italic'): text = f"*{text}*"
            if annotations.get('strikethrough'): text = f"~~{text}~~"
            result.append(text)
    return ''.join(result)


def block_to_markdown(block):
    btype = block.get('type', '')
    if btype in ('paragraph', 'heading_1', 'heading_2', 'heading_3'):
        text = extract_rich_text(block.get(btype, {}))
        if not text.strip(): return ''
        if btype == 'heading_1': return f"\n# {text}\n"
        if btype == 'heading_2': return f"\n## {text}\n"
        if btype == 'heading_3': return f"\n### {text}\n"
        return f"\n{text}\n"
    elif btype == 'bulleted_list_item':
        return f"- {extract_rich_text(block.get(btype, {}))}\n"
    elif btype == 'numbered_list_item':
        return f"1. {extract_rich_text(block.get(btype, {}))}\n"
    elif btype == 'code':
        text = extract_rich_text(block.get(btype, {}))
        lang = block.get('code', {}).get('language', '')
        return f"\n```{lang}\n{text}\n```\n"
    elif btype == 'quote':
        text = extract_rich_text(block.get(btype, {}))
        return '\n'.join(f'> {line}' for line in text.split('\n')) + '\n'
    elif btype == 'callout':
        text = extract_rich_text(block.get(btype, {}))
        emoji = block.get('callout', {}).get('icon', {})
        emoji = emoji.get('emoji', '💡') if isinstance(emoji, dict) else '💡'
        return f"\n> {emoji} {text}\n"
    elif btype == 'divider':
        return "\n---\n"
    elif btype == 'table':
        table = block.get('table', {})
        rows = table.get('rows', [])
        has_header = table.get('has_row_header', False)
        if not rows: return ''
        md_lines = []
        for i, row in enumerate(rows):
            cells = row.get('cells', [])
            cell_texts = [extract_rich_text(c).replace('|', '\\|') for c in cells]
            md_lines.append('| ' + ' | '.join(cell_texts) + ' |')
            if i == 0 and has_header:
                md_lines.append('| ' + ' | '.join(['---'] * len(cells)) + ' |')
        return '\n'.join(md_lines) + '\n'
    elif btype == 'image':
        image = block.get('image', {})
        url = ''
        if image.get('type') == 'external': url = image['external'].get('url', '')
        elif image.get('type') == 'file': url = image['file'].get('url', '')
        if url:
            caption = extract_rich_text(image.get('caption', []))
            return f"\n![{caption or 'image'}]({url})\n"
        return ''
    elif btype == 'bookmark':
        url = block.get('bookmark', {}).get('url', '')
        if url:
            caption = extract_rich_text(block.get('bookmark', {}).get('caption', []))
            return f"\n[{caption or url}]({url})\n"
        return ''
    return ''


def fetch_page_content(page_id):
    url = f"https://api.notion.com/v1/blocks/{page_id}/children?page_size=100"
    data = notion_request(url)
    parts = []
    for block in data.get('results', []):
        md = block_to_markdown(block)
        if md: parts.append(md)
    while data.get('has_more'):
        cursor = data.get('next_cursor')
        url = f"https://api.notion.com/v1/blocks/{page_id}/children?page_size=100&start_cursor={cursor}"
        data = notion_request(url)
        for block in data.get('results', []):
            md = block_to_markdown(block)
            if md: parts.append(md)
    content = ''.join(parts).strip()
    return re.sub(r'\n{3,}', '\n\n', content)


def find_empty_posts():
    """내용 없음 포스트 찾기"""
    empty = []
    for f in posts_dir.rglob('index.md'):
        content = f.read_text(encoding='utf-8')
        if '내용 없음' in content and content.strip().count('\n') < 15:
            # front matter 이후 내용이 거의 없음
            empty.append(f)
    return empty


def main():
    empty_posts = find_empty_posts()
    print(f"내용 없음 포스트: {len(empty_posts)}개\n")

    if not empty_posts:
        print("복원할 포스트가 없습니다.")
        return

    # Notion DB에서 전체 글 로드 (제목 → page_id 매핑)
    all_articles = {}
    has_more = True
    cursor = None
    while has_more:
        body = {'page_size': 100}
        if cursor: body['start_cursor'] = cursor
        data = notion_request(
            f"https://api.notion.com/v1/databases/{database_id}/query",
            method='POST', body=body
        )
        for page in data.get('results', []):
            title_prop = page['properties'].get('내용')
            if title_prop and title_prop.get('title'):
                title = title_prop['title'][0]['plain_text']
                all_articles[title] = page['id']
        has_more = data.get('has_more', False)
        cursor = data.get('next_cursor')

    print(f"Notion DB 글: {len(all_articles)}개 로드됨\n")

    fixed = 0
    failed = 0
    for filepath in empty_posts:
        # 파일에서 제목 추출 (front matter)
        content = filepath.read_text(encoding='utf-8')
        title_match = re.search(r'title:\s*"(.+?)"', content)
        if not title_match:
            print(f"  ❌ 제목 추출 실패: {filepath.parent.name}")
            failed += 1
            continue

        title = title_match.group(1)
        page_id = all_articles.get(title)

        if not page_id:
            print(f"  ⚠️ Notion에서 못 찾음: {title[:40]}")
            failed += 1
            continue

        # 본문 가져오기
        try:
            notion_content = fetch_page_content(page_id)
            if not notion_content:
                print(f"  ⚠️ 본문 비어있음: {title[:40]}")
                failed += 1
                continue

            # 출처 URL 추출 (기존)
            source_match = re.search(r'\*\*출처\*\*:\s*\[.*?\]\((.*?)\)', content)

            # 새 front matter 유지 + 본문 교체
            fm_end = content.index('---\n', content.index('---') + 4) + 4
            front_matter = content[:fm_end]

            source = ""
            if source_match:
                source = f"\n\n---\n\n**출처**: [{source_match.group(1)}]({source_match.group(1)})"

            new_content = front_matter + "\n" + notion_content + source
            filepath.write_text(new_content, encoding='utf-8')
            fixed += 1
            print(f"  ✅ 복원 ({len(notion_content)}자): {title[:50]}")

        except Exception as e:
            print(f"  ❌ 실패: {title[:40]} - {e}")
            failed += 1

    print(f"\n결과: {fixed}개 복원, {failed}개 실패")

    if fixed > 0:
        print("\ngit commit & push 실행...")
        import subprocess
        subprocess.run(['git', 'add', '-A'], cwd=blog_path, check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', f'fix: "내용 없음" 포스트 복원 - {fixed}개'], cwd=blog_path, check=True, capture_output=True)
        subprocess.run(['git', 'pull', '--rebase', 'origin', 'main'], cwd=blog_path, check=True, capture_output=True)
        subprocess.run(['git', 'push', 'origin', 'main'], cwd=blog_path, check=True, capture_output=True)
        print("✅ push 완료")


if __name__ == "__main__":
    main()
