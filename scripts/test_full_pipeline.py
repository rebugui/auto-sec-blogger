"""
Full Pipeline Test - Create test article → Upload to Notion → Download → Verify
"""

import sys
import os
import importlib.util
from pathlib import Path
from dotenv import load_dotenv

# Load .env
env_path = Path.home() / '.openclaw' / 'workspace' / '.env'
load_dotenv(str(env_path), override=True)

# Load NotionPublisher directly
scripts_dir = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "notion_publisher",
    str(scripts_dir / "notion_publisher.py")
)
notion_publisher_module = importlib.util.module_from_spec(spec)

class MockLogger:
    def info(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass

class MockUtils:
    @staticmethod
    def setup_logger(name, log_file):
        return MockLogger()

sys.modules['modules'] = type(sys)('modules')
sys.modules['modules.intelligence'] = type(sys)('intelligence')
sys.modules['modules.intelligence.config'] = type('Config', (), {
    'NOTION_API_KEY': os.getenv('NOTION_API_KEY', ''),
    'NOTION_DATABASE_ID': os.getenv('NOTION_DATABASE_ID') or os.getenv('BLOG_DATABASE_ID', ''),
    'BLOG_REPO_PATH': Path(os.getenv('BLOG_REPO_PATH', '~/Documents/OpenClaw/rebugui.github.io')).expanduser(),
    'BLOG_URL': os.getenv('BLOG_URL', 'https://rebugui.github.io/hate-coding-turtle/'),
})
sys.modules['modules.intelligence.utils'] = MockUtils

import requests
spec.loader.exec_module(notion_publisher_module)
NotionPublisher = notion_publisher_module.NotionPublisher

def create_test_article_with_mermaid():
    """Create a test article with Mermaid diagram"""
    return {
        'title': '🧪 파이프라인 테스트: Mermaid 다이어그램',
        'summary': '이 글은 인텔리전스 에이전트 파이프라인 테스트를 위해 자동으로 생성되었습니다.',
        'category': '보안',
        'tags': ['Test', 'Mermaid', 'Pipeline', '자동화'],
        'content': '''
## 서론

이 글은 인텔리전스 에이전트 파이프라인의 Mermaid 다이어그램 변환 기능을 테스트하기 위해 생성되었습니다.

## 파이프라인 아키텍처

아래 다이어그램은 전체 파이프라인의 흐름을 보여줍니다.

```mermaid
graph TD
    A[AI Writer] -->|Generate Markdown| B[Notion Publisher]
    B -->|Convert to Callout| C[Notion Database]
    C -->|Export| D[Git Publisher]
    D -->|Convert to Mermaid| E[Git Repository]
    E -->|Build| F[Hugo Blog]
    F -->|Render| G[Published Blog]

    style A fill:#e1f5ff
    style B fill:#fff4e1
    style C fill:#f0e1ff
    style D fill:#fff4e1
    style E fill:#e1ffe1
    style F fill:#ffe1f0
    style G fill:#e1ffe1
```

## 테스트 코드 예시

파이프라인 테스트를 위한 Python 코드입니다.

~~~python
def test_mermaid_conversion():
    test_markdown = '~~~mermaid\\ngraph LR\\n    A[Start] --> B[End]\\n~~~'

    publisher = NotionPublisher()
    blocks = publisher._convert_to_blocks(test_markdown)
    restored = publisher._block_to_text(blocks[0])

    assert '```mermaid' in restored
    print("✓ Mermaid conversion test passed!")
~~~

## 테스트 결과

| 항목 | 예상 | 실제 | 상태 |
|:---|:---|:---|:---|
| Mermaid 변환 | Callout → Mermaid | Callout → Mermaid | ✅ |
| 코드 블록 | 정상 유지 | 정상 유지 | ✅ |
| 테이블 | 정상 렌더링 | 정상 렌더링 | ✅ |

## 결론

이 테스트는 다음을 검증합니다:

1. ✅ AI Writer가 생성한 ```mermaid 블록이 Notion에 업로드될 때 Callout(📊)으로 변환됨
2. ✅ Git Publisher가 Notion에서 내려받을 때 Callout(📊)을 ```mermaid로 복원함
3. ✅ Hugo가 ```mermaid를 정상적으로 렌더링함

파이프라인이 정상 작동합니다!
'''
    }

def test_full_pipeline():
    """Test complete pipeline: Create → Upload → Download → Verify"""
    print("=" * 70)
    print("Full Pipeline Test: Create → Upload → Download → Verify")
    print("=" * 70)

    try:
        publisher = NotionPublisher()

        # Step 1: Create test article
        print("\n[Step 1] Creating test article with Mermaid diagram...")
        article_data = create_test_article_with_mermaid()
        print(f"  Title: {article_data['title']}")
        print(f"  Tags: {', '.join(article_data['tags'])}")
        print(f"  Content length: {len(article_data['content'])} characters")

        # Count Mermaid blocks in original
        original_mermaid_count = article_data['content'].count('```mermaid')
        print(f"  Mermaid blocks: {original_mermaid_count}")

        # Step 2: Upload to Notion
        print("\n[Step 2] Uploading to Notion...")
        result = publisher.create_article(article_data)

        if not result:
            print("  ✗ Failed to upload to Notion")
            return False

        page_id = result.get('id')
        page_url = result.get('url')
        print(f"  ✓ Uploaded successfully!")
        print(f"  Page ID: {page_id}")
        print(f"  URL: {page_url}")

        # Step 3: Download from Notion
        print("\n[Step 3] Downloading from Notion...")
        downloaded_content = publisher.get_page_content(page_id)
        print(f"  Downloaded content length: {len(downloaded_content)} characters")

        # Step 4: Verify Mermaid conversion
        print("\n[Step 4] Verifying Mermaid conversion...")

        downloaded_mermaid_count = downloaded_content.count('```mermaid')
        print(f"  Original Mermaid blocks: {original_mermaid_count}")
        print(f"  Downloaded Mermaid blocks: {downloaded_mermaid_count}")

        if downloaded_mermaid_count == original_mermaid_count:
            print("  ✓ Mermaid blocks preserved!")
        else:
            print(f"  ✗ Mermaid block count mismatch!")
            return False

        # Extract and display a Mermaid block
        if '```mermaid' in downloaded_content:
            start_idx = downloaded_content.find('```mermaid')
            end_idx = downloaded_content.find('```', start_idx + 10)
            if end_idx > start_idx:
                mermaid_sample = downloaded_content[start_idx:end_idx + 3]
                print("\n  Sample Mermaid block from Notion:")
                print("  " + "-" * 50)
                lines = mermaid_sample.split('\n')[:15]
                for line in lines:
                    print(f"  {line}")
                if len(mermaid_sample.split('\n')) > 15:
                    print("  ...")
                print("  " + "-" * 50)

        # Update status to 검토 완료 for Git Publisher test
        print("\n[Step 5] Updating status to '검토 완료'...")
        publisher.update_status(page_id, "검토 완료")
        print("  ✓ Status updated!")

        print("\n" + "=" * 70)
        print("✅ Full Pipeline Test PASSED!")
        print("=" * 70)
        print("\nNext steps:")
        print("1. Check the article in Notion:")
        print(f"   {page_url}")
        print("2. Run Git Publisher to download to Git repository:")
        print("   python3 publisher_git.py")
        print("3. Verify the generated markdown file has Mermaid diagrams")
        print("4. Build Hugo site to verify rendering:")
        print("   cd ~/Documents/OpenClaw/rebugui.github.io && hugo")

        return True

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\n🚀 Starting Full Pipeline Test...\n")
    success = test_full_pipeline()

    if success:
        print("\n✅ Test completed successfully!")
    else:
        print("\n❌ Test failed. Please check the errors above.")
