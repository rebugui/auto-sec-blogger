"""
Browser Session Helper (Playwright)
네이버/티스토리 발행을 위한 공통 브라우저 세션 유틸.
- 일회성 로그인으로 storage_state(쿠키/세션) JSON 저장 → 이후 헤드리스 재사용.
"""

import os


def require_playwright():
    """playwright sync_api 로더. 미설치 시 명확한 에러."""
    try:
        from playwright.sync_api import sync_playwright
        return sync_playwright
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(
            "playwright 미설치. `pip install playwright && python3 -m playwright install chromium` 필요"
        ) from e


def capture_login(state_path: str, start_url: str, hint: str = "") -> None:
    """헤드풀 브라우저로 직접 로그인 후 세션을 state_path에 저장 (일회성)."""
    sync_playwright = require_playwright()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto(start_url)
        print(f">> {hint or '브라우저에서 로그인을 완료'}한 뒤, 이 터미널에서 Enter를 누르세요...")
        input()
        os.makedirs(os.path.dirname(state_path), exist_ok=True)
        context.storage_state(path=state_path)
        print(f">> 세션 저장됨: {state_path}")
        browser.close()
