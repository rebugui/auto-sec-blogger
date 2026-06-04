"""
Browser Session Helper (Playwright)
네이버/티스토리 발행을 위한 공통 브라우저 세션 유틸.
- 일회성 로그인으로 storage_state(쿠키/세션) JSON 저장 → 이후 헤드리스 재사용.
- 로그인 성공을 쿠키로 자동 감지 (터미널 Enter 불필요).
"""

import os
import time


def require_playwright():
    """playwright sync_api 로더. 미설치 시 명확한 에러."""
    try:
        from playwright.sync_api import sync_playwright
        return sync_playwright
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(
            "playwright 미설치. `pip install playwright && python3 -m playwright install chromium` 필요"
        ) from e


def capture_login(state_path: str, start_url: str, success_cookies, hint: str = "",
                  timeout_s: int = 300, poll_s: int = 3) -> bool:
    """헤드풀 브라우저로 로그인 → 성공 쿠키 감지 시 세션을 state_path에 자동 저장.

    success_cookies: 로그인 성공을 나타내는 쿠키 이름 목록(하나라도 값이 있으면 성공).
    반환: 감지 성공 여부.
    """
    sync_playwright = require_playwright()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto(start_url)
        print(f">> {hint} — 열린 브라우저 창에서 로그인하세요. "
              f"로그인 감지 시 자동 저장됩니다 (최대 {timeout_s}s 대기).", flush=True)

        ok = False
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            try:
                names = {c["name"] for c in context.cookies() if c.get("value")}
            except Exception:
                names = set()
            if any(n in names for n in success_cookies):
                ok = True
                break
            time.sleep(poll_s)

        os.makedirs(os.path.dirname(state_path), exist_ok=True)
        context.storage_state(path=state_path)
        browser.close()

    if ok:
        print(f">> ✅ 로그인 감지 → 세션 저장: {state_path}", flush=True)
    else:
        print(f">> ⚠️ 타임아웃: 로그인 미감지. 현재 상태 저장(불완전할 수 있음): {state_path}", flush=True)
    return ok
