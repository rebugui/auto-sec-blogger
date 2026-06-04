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


def capture_login() -> bool:
    # 티스토리 로그인(카카오) 성공 시 .tistory.com에 TSSESSION 쿠키가 설정됨
    return browser_session.capture_login(
        TISTORY_STATE_PATH,
        "https://www.tistory.com/auth/login",
        success_cookies=["TSSESSION"],
        hint="티스토리(카카오) 로그인",
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

    def _on_dialog(d):
        # '이어서 작성'(이전 임시저장)은 거부=새 글, '모드 변경' 등은 수락
        (d.dismiss() if ("이어" in d.message) else d.accept())

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(storage_state=TISTORY_STATE_PATH,
                                          viewport={"width": 1400, "height": 1000})
            page = context.new_page()
            page.on("dialog", _on_dialog)
            page.goto(f"{_blog_base()}/manage/newpost/", wait_until="networkidle")
            page.wait_for_timeout(2000)

            if "kakao.com" in page.url or "/auth/" in page.url or "login" in page.url:
                browser.close()
                return PublishResult(PLATFORM_TISTORY, ok=False,
                                     error="로그인 세션 만료 → `publisher_tistory.py login` 재실행 필요")

            # 제목
            page.fill("#post-title-inp", title, timeout=15000)

            # HTML 모드 전환 → CodeMirror에 HTML 주입
            page.click("#editor-mode-layer-btn-open", timeout=8000)
            page.wait_for_timeout(600)
            page.click("#editor-mode-html-text", timeout=5000)
            page.wait_for_timeout(1200)
            page.locator("#html-editor-container .CodeMirror").first.click()
            page.keyboard.insert_text(html)
            page.wait_for_timeout(600)

            # 태그
            if tags:
                try:
                    page.fill("#tagText", tags, timeout=3000)
                except Exception:
                    pass

            # 완료 → 공개 선택 → 공개 발행
            page.click("#publish-layer-btn", timeout=15000)
            page.wait_for_timeout(1200)
            page.get_by_text("공개", exact=True).click(timeout=5000)
            page.wait_for_timeout(500)
            page.click("#publish-btn", timeout=10000)

            # 자동등록방지(캡차) 감지 — 뜨면 자동화로는 완료 불가
            page.wait_for_timeout(3000)
            try:
                cap = page.locator(".capcha_layer, .recaptcha, iframe[src*='recaptcha']")
                if cap.count() > 0 and cap.first.is_visible():
                    browser.close()
                    return PublishResult(PLATFORM_TISTORY, ok=False,
                                         error="자동등록방지(캡차) 발생 → 자동 발행 불가(수동 발행 필요)")
            except Exception:
                pass

            # 발행 완료(에디터 이탈) 대기
            ok = False
            for _ in range(12):
                if "/manage/newpost" not in page.url:
                    ok = True
                    break
                page.wait_for_timeout(1000)
            posted_url = page.url
            browser.close()
            if not ok:
                return PublishResult(PLATFORM_TISTORY, ok=False,
                                     error="발행 미완료(캡차/검증 가능성) — 수동 확인 필요")
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
