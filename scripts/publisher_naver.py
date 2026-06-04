"""
Naver Blog Publisher (Playwright 브라우저 자동화 전용)
네이버 공식 글쓰기 API는 제약이 많아 저장된 로그인 세션으로 글쓰기 자동화.

일회성 셋업 (헤드풀 1회 로그인 → 세션 저장):
    python3 publisher_naver.py login
이후 자동 발행은 NAVER_STATE_PATH의 storage_state를 재사용한다.

주의: 네이버 SmartEditor ONE은 iframe + 동적 DOM이라 매우 취약(best-effort).
실패 시 PublishResult(ok=False)로 graceful 처리.
"""

import os
import sys

from config import NAVER_BLOG_ID, NAVER_STATE_PATH
from utils import setup_logger
from publisher_base import PublishResult, PLATFORM_NAVER
import browser_session

logger = setup_logger(__name__, "auto-publish-approved.log")

WRITE_URL = "https://blog.naver.com/PostWriteForm.naver"


def capture_login() -> bool:
    # 로그인 성공 시 .naver.com에 NID_SES/NID_AUT 쿠키가 설정됨
    return browser_session.capture_login(
        NAVER_STATE_PATH,
        "https://nid.naver.com/nidlogin.login",
        success_cookies=["NID_SES", "NID_AUT"],
        hint="네이버 로그인",
    )


def publish(article: dict, markdown: str, html: str) -> PublishResult:
    if not NAVER_BLOG_ID:
        return PublishResult(PLATFORM_NAVER, ok=False, error="NAVER_BLOG_ID 미설정")
    if not os.path.exists(NAVER_STATE_PATH):
        return PublishResult(
            PLATFORM_NAVER, ok=False,
            error=f"로그인 세션 없음({NAVER_STATE_PATH}). `python3 publisher_naver.py login` 먼저 실행",
        )
    try:
        sync_playwright = browser_session.require_playwright()
    except RuntimeError as e:
        return PublishResult(PLATFORM_NAVER, ok=False, error=str(e))

    title = article["title"]
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(storage_state=NAVER_STATE_PATH)
            page = context.new_page()
            page.goto(f"https://blog.naver.com/{NAVER_BLOG_ID}?Redirect=Write",
                      wait_until="networkidle")

            if "nid.naver.com" in page.url or "nidlogin" in page.url:
                browser.close()
                return PublishResult(PLATFORM_NAVER, ok=False,
                                     error="로그인 세션 만료 → `publisher_naver.py login` 재실행 필요")

            # SmartEditor ONE은 mainFrame iframe 안에 있다.
            frame = page.frame(name="mainFrame") or page
            # '도움말/이전 글 이어쓰기' 팝업 닫기 (있으면)
            try:
                frame.click("button.se-popup-button-cancel", timeout=3000)
            except Exception:
                pass

            # 제목/본문: SmartEditor는 contenteditable 영역. 셀렉터는 환경에 따라 조정 필요.
            try:
                frame.click(".se-section-documentTitle .se-text-paragraph", timeout=10000)
                frame.keyboard.type(title)
                frame.click(".se-component.se-text .se-text-paragraph", timeout=10000)
                # 본문은 평문/마크다운으로 입력(SmartEditor는 HTML 직접 주입이 어려움).
                frame.keyboard.insert_text(markdown)
            except Exception as e:
                browser.close()
                return PublishResult(PLATFORM_NAVER, ok=False,
                                     error=f"에디터 입력 실패(SmartEditor 셀렉터 조정 필요): {str(e)[:120]}")

            # 발행 버튼 → 확인
            try:
                frame.click("button.publish_btn__m9KHH", timeout=10000)
                frame.click("button.confirm_btn__WEaBq", timeout=10000)
            except Exception:
                # 대체 셀렉터
                frame.click("text=발행", timeout=10000)

            page.wait_for_load_state("networkidle", timeout=20000)
            posted_url = page.url
            browser.close()
            logger.info(f"[Naver] 게시 완료: {posted_url}")
            return PublishResult(PLATFORM_NAVER, ok=True, url=posted_url)

    except Exception as e:  # noqa: BLE001
        logger.error(f"[Naver] 실패: {e}")
        return PublishResult(PLATFORM_NAVER, ok=False, error=str(e)[:200])


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "login":
        capture_login()
    else:
        print("usage: python3 publisher_naver.py login")
