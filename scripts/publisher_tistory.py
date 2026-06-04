"""
Tistory Publisher (Playwright 브라우저 자동화 전용)
티스토리 Open API는 2024.2 종료 → 저장된 로그인 세션을 재사용해 글쓰기 자동화.

일회성 셋업 (헤드풀 1회 로그인 → 세션 저장):
    python3 publisher_tistory.py login
이후 자동 발행은 TISTORY_STATE_PATH의 storage_state를 재사용한다.

best-effort: 에디터 UI 변경에 취약 → 실패 시 PublishResult(ok=False)로 graceful 처리.
"""

import os
import sys

from config import TISTORY_BLOG_NAME, TISTORY_STATE_PATH
from utils import setup_logger
from publisher_base import PublishResult, PLATFORM_TISTORY
import browser_session

logger = setup_logger(__name__, "auto-publish-approved.log")


def _blog_base() -> str:
    return f"https://{TISTORY_BLOG_NAME}.tistory.com"


def capture_login() -> None:
    browser_session.capture_login(
        TISTORY_STATE_PATH,
        f"{_blog_base()}/manage/posts/",
        hint="티스토리(카카오) 로그인을 완료",
    )


def publish(article: dict, markdown: str, html: str) -> PublishResult:
    if not TISTORY_BLOG_NAME:
        return PublishResult(PLATFORM_TISTORY, ok=False, error="TISTORY_BLOG_NAME 미설정")
    if not os.path.exists(TISTORY_STATE_PATH):
        return PublishResult(
            PLATFORM_TISTORY, ok=False,
            error=f"로그인 세션 없음({TISTORY_STATE_PATH}). `python3 publisher_tistory.py login` 먼저 실행",
        )
    try:
        sync_playwright = browser_session.require_playwright()
    except RuntimeError as e:
        return PublishResult(PLATFORM_TISTORY, ok=False, error=str(e))

    title = article["title"]
    tags = ",".join(article.get("tags", []) or [])
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(storage_state=TISTORY_STATE_PATH)
            page = context.new_page()
            page.goto(f"{_blog_base()}/manage/newpost/", wait_until="networkidle")

            # 로그인 만료 감지 (카카오/티스토리 로그인 페이지로 튕김)
            if "kakao.com" in page.url or "/auth/" in page.url or "login" in page.url:
                browser.close()
                return PublishResult(PLATFORM_TISTORY, ok=False,
                                     error="로그인 세션 만료 → `publisher_tistory.py login` 재실행 필요")

            # 제목 입력
            page.fill("#post-title-inp", title, timeout=15000)

            # 에디터를 HTML 모드로 전환 후 본문 주입
            try:
                page.click("#editor-mode-layer-btn-open", timeout=5000)
                page.click("#editor-mode-html", timeout=5000)
                # HTML 모드 확인 다이얼로그가 뜰 수 있음
                try:
                    page.click("button:has-text('확인')", timeout=2000)
                except Exception:
                    pass
                page.click(".CodeMirror", timeout=5000)
                page.keyboard.insert_text(html)
            except Exception:
                # 폴백: 본문 iframe contenteditable에 직접 HTML 주입
                page.evaluate(
                    """(html)=>{const f=document.querySelector('iframe[id*="editor"]');
                    if(f&&f.contentDocument){f.contentDocument.body.innerHTML=html;}}""",
                    html,
                )

            # 태그 입력 (있으면)
            if tags:
                try:
                    page.fill("#tagText", tags, timeout=3000)
                except Exception:
                    pass

            # 발행: 완료 → 공개 발행
            page.click("#publish-layer-btn", timeout=15000)
            page.click("#publish-btn", timeout=15000)
            page.wait_for_load_state("networkidle", timeout=20000)

            posted_url = page.url
            browser.close()
            logger.info(f"[Tistory] 게시 완료: {posted_url}")
            return PublishResult(PLATFORM_TISTORY, ok=True, url=posted_url)

    except Exception as e:  # noqa: BLE001
        logger.error(f"[Tistory] 실패: {e}")
        return PublishResult(PLATFORM_TISTORY, ok=False, error=str(e)[:200])


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "login":
        capture_login()
    else:
        print("usage: python3 publisher_tistory.py login")
