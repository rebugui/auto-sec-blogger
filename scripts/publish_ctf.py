#!/usr/bin/env python3
"""
CTF Judgement Day 전용 발행기
Notion '검토 완료' + 카테고리 'CTF/judgementday' 글을 블로그 페이지번들로 발행한다.
표준 auto_publish와 달리 **깨끗한 고정 슬러그(judgement-day-XX)**를 쓰고,
글간 .md 링크를 슬러그 URL로 변환하며, Notion 이미지를 번들로 다운로드한다.
발행 후 Notion 상태를 '게시 완료'로 갱신.

사용: python3 publish_ctf.py            # 검토완료 CTF 글 전부 발행
"""
import json
import re
import urllib.request
from pathlib import Path

import auto_publish_approved as ap
import publisher_github as pg
import md_readability
from config import NOTION_API_KEY, NOTION_DATABASE_ID, BLOG_REPO_PATH

CAT = "CTF/judgementday"
H = {"Authorization": f"Bearer {NOTION_API_KEY}", "Notion-Version": "2022-06-28",
     "Content-Type": "application/json"}
DEST = Path(BLOG_REPO_PATH) / "content" / "post" / "CTF" / "judgementday"
BLOG_URL = "https://rebugui.github.io"

# 제목 패턴 → 고정 슬러그 (시리즈 순서 유지)
SLUG_RULES = [
    (r"개관편", "judgement-day-00-overview"),
    (r"Track\s*1\.0", "judgement-day-01-triage"),
    (r"Track\s*1\.1", "judgement-day-02-robotics-door"),
    (r"Track\s*1\.2", "judgement-day-03-sports-var"),
    (r"Track\s*1\.3", "judgement-day-04-dam-flood"),
    (r"Track\s*2\.0", "judgement-day-05-soc"),
    (r"Track\s*2\.1", "judgement-day-06-aircraft"),
    (r"Track\s*2\.2", "judgement-day-07-outbreak"),
    (r"Track\s*2\.3", "judgement-day-08-deepfake"),
    (r"syntheses|프레임워크", "judgement-day-09-syntheses"),
    (r"마무리|회고|후기", "judgement-day-10-retrospective"),
]
# 본문 내 .md 링크 → 슬러그 URL
LINK_SLUG = {
    "00-overview.md": "judgement-day-00-overview", "01-t1-0-triage.md": "judgement-day-01-triage",
    "02-t1-1-robotics-door.md": "judgement-day-02-robotics-door", "03-t1-2-sports-var.md": "judgement-day-03-sports-var",
    "04-t1-3-dam-flood.md": "judgement-day-04-dam-flood", "05-t2-0-soc.md": "judgement-day-05-soc",
    "06-t2-1-aircraft.md": "judgement-day-06-aircraft", "07-t2-2-outbreak.md": "judgement-day-07-outbreak",
    "08-t2-3-deepfake.md": "judgement-day-08-deepfake", "09-syntheses-framework.md": "judgement-day-09-syntheses",
}


def slug_for(title):
    for pat, s in SLUG_RULES:
        if re.search(pat, title):
            return s
    return None


def rewrite_links(md):
    def r(m):
        fn, anc = m.group(1), m.group(2) or ""
        s = LINK_SLUG.get(fn)
        return f"](/{s}/{anc})" if s else m.group(0)
    return re.sub(r"\]\((\d\d[\w.-]*?\.md)(#[^)]*)?\)", r, md)


def notion_query_review_done():
    body = {"filter": {"and": [
        {"property": "상태", "status": {"equals": "검토 완료"}},
        {"property": "카테고리", "select": {"equals": CAT}}]}, "page_size": 30}
    req = urllib.request.Request(f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query",
                                 data=json.dumps(body).encode(), headers=H, method="POST")
    return json.loads(urllib.request.urlopen(req).read())["results"]


def notion_mark_published(pid, url):
    patch = {"properties": {
        "상태": {"status": {"name": "게시 완료"}},
        "게시된 플랫폼": {"multi_select": [{"name": "GitHub"}]},
        "배포 URL": {"url": url}}}
    urllib.request.urlopen(urllib.request.Request(
        f"https://api.notion.com/v1/pages/{pid}", data=json.dumps(patch).encode(),
        headers=H, method="PATCH")).read()


def main():
    rows = notion_query_review_done()
    if not rows:
        print("검토 완료된 CTF/judgementday 글이 없습니다.")
        return
    published = []
    for p in rows:
        t = p["properties"].get("내용", {}).get("title", [])
        title = t[0]["plain_text"] if t else ""
        slug = slug_for(title)
        if not slug:
            print(f"⏭️ 슬러그 매핑 없음, 건너뜀: {title[:50]}")
            continue
        idx = (idx_n.group(0) if (idx_n := re.search(r"\d\d", slug)) else "09")
        md = ap.fetch_page_content(p["id"])
        if not md:
            print(f"⚠️ 본문 없음: {title[:40]}")
            continue
        md = rewrite_links(md)
        md = md_readability.restore(md)  # Notion 왕복으로 뭉친 표/번호목록 복구
        post_dir = DEST / slug
        post_dir.mkdir(parents=True, exist_ok=True)
        md = pg._localize_images(md, post_dir)
        fm = (f'---\ntitle: "{title.replace(chr(34), chr(39))}"\nslug: "{slug}"\n'
              f"date: 2026-06-04T09:{idx}:00+09:00\ndraft: false\n"
              f'categories: ["{CAT}"]\ntags: ["CTF", "judgementday", "AI red-team", "LLM"]\n'
              f'author: "Rebugui"\n---\n\n')
        (post_dir / "index.md").write_text(fm + md, encoding="utf-8")
        nimg = len(list((post_dir / "images").glob("*"))) if (post_dir / "images").exists() else 0
        pg._git(["add", f"content/post/CTF/judgementday/{slug}"])
        published.append((p["id"], slug, title, nimg))
        print(f"✅ 빌드: {slug}  (이미지 {nimg}개)  ← {title[:45]}")

    if not published:
        print("발행할 글이 없습니다.")
        return
    pg._git(["commit", "-m", f"feat: CTF Judgement Day 발행 {len(published)}편"])
    pg._git(["pull", "--rebase", "--autostash", "origin", "main"])
    pg._git(["push", "origin", "main"])
    print(f"\n🚀 git push 완료: {len(published)}편")
    for pid, slug, title, _ in published:
        notion_mark_published(pid, f"{BLOG_URL}/{slug}/")
    print("✅ Notion 상태 → 게시 완료 갱신 완료")


if __name__ == "__main__":
    main()
