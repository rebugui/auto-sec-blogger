"""
테스트용 임시 모듈 수정본
"""
# 필요한 모듈만 임포트
try:
    from notion_publisher import NotionPublisher
    __all__ = ["NotionPublisher"]
except ImportError:
    __all__ = []