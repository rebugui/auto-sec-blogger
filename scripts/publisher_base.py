"""
Publisher Base
멀티플랫폼 발행을 위한 공통 결과 타입과 상수.
각 퍼블리셔(publisher_github / publisher_naver / publisher_tistory)는
publish(article: dict, markdown: str, html: str) -> PublishResult 시그니처를 구현한다.
"""

from dataclasses import dataclass

# Notion '플랫폼' multi-select 옵션명 (정규 명칭)
PLATFORM_GITHUB = "GitHub"
PLATFORM_NAVER = "Naver"
PLATFORM_TISTORY = "Tistory"
ALL_PLATFORMS = (PLATFORM_GITHUB, PLATFORM_NAVER, PLATFORM_TISTORY)


@dataclass
class PublishResult:
    """단일 (글 × 플랫폼) 발행 결과"""
    platform: str
    ok: bool
    url: str = ""
    error: str = ""
