"""
Test script for Mermaid diagram conversion in Notion Publisher
Tests the bidirectional conversion of Mermaid diagrams
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Direct import to avoid package initialization issues
import importlib.util
scripts_dir = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("notion_publisher", os.path.join(scripts_dir, "notion_publisher.py"))
notion_publisher_module = importlib.util.module_from_spec(spec)

# Mock the config module to avoid import errors
class MockConfig:
    NOTION_API_KEY = "test_key"
    NOTION_DATABASE_ID = "test_db_id"

sys.modules['modules.intelligence.config'] = MockConfig()
sys.modules['modules'] = type(sys)('modules')
sys.modules['modules'].intelligence = type(sys)('intelligence')
sys.modules['modules'].intelligence.config = MockConfig()

# Mock logger
class MockLogger:
    def info(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass

class MockUtils:
    @staticmethod
    def setup_logger(name, log_file):
        return MockLogger()

sys.modules['modules.intelligence.utils'] = MockUtils()

# Now load the module
spec.loader.exec_module(notion_publisher_module)
NotionPublisher = notion_publisher_module.NotionPublisher

def test_mermaid_to_notion_blocks():
    """Test converting Mermaid markdown to Notion blocks"""
    print("=== Test 1: Markdown → Notion Blocks ===")

    publisher = NotionPublisher()

    # Sample markdown with Mermaid diagram
    markdown_content = """
## 서론

이것은 테스트입니다.

```mermaid
graph TD
    A[Start] --> B[End]
```

결론입니다.
"""

    blocks = publisher._convert_to_blocks(markdown_content)

    print(f"Total blocks created: {len(blocks)}")
    for i, block in enumerate(blocks):
        print(f"\nBlock {i+1}:")
        print(f"  Type: {block.get('type', 'unknown')}")
        if block.get('type') == 'callout':
            emoji = block.get('callout', {}).get('icon', {}).get('emoji', '')
            text = block.get('callout', {}).get('rich_text', [{}])[0].get('text', {}).get('content', '')
            print(f"  Emoji: {emoji}")
            print(f"  Text preview: {text[:50]}...")

            # Verify it's a Mermaid callout
            if emoji == '📊':
                print("  ✓ Mermaid correctly converted to Callout with 📊 emoji")
            else:
                print(f"  ✗ Expected 📊 emoji, got {emoji}")
        elif block.get('type') == 'heading_2':
            text = block.get('heading_2', {}).get('rich_text', [{}])[0].get('text', {}).get('content', '')
            print(f"  Text: {text}")

    return blocks

def test_notion_blocks_to_markdown():
    """Test converting Notion blocks back to Markdown"""
    print("\n=== Test 2: Notion Blocks → Markdown ===")

    publisher = NotionPublisher()

    # Simulate a Notion Callout block with Mermaid diagram
    mermaid_code = """graph TD
    A[Start] --> B[End]
    B --> C[Finish]"""

    notion_block = {
        "object": "block",
        "type": "callout",
        "callout": {
            "rich_text": [{"type": "text", "text": {"content": mermaid_code}}],
            "icon": {"emoji": "📊"}
        }
    }

    markdown = publisher._block_to_text(notion_block)
    print(f"Converted Markdown:\n{markdown}")

    # Verify it's a Mermaid code block
    if markdown.startswith("```mermaid") and markdown.endswith("```"):
        print("✓ Callout with 📊 emoji correctly converted back to ```mermaid code block")
        return True
    else:
        print(f"✗ Expected ```mermaid code block, got: {markdown[:50]}...")
        return False

def test_regular_callout():
    """Test that regular Callouts are not converted to Mermaid"""
    print("\n=== Test 3: Regular Callout (not Mermaid) ===")

    publisher = NotionPublisher()

    # Regular callout with different emoji
    notion_block = {
        "object": "block",
        "type": "callout",
        "callout": {
            "rich_text": [{"type": "text", "text": {"content": "This is a regular callout"}}],
            "icon": {"emoji": "💡"}
        }
    }

    markdown = publisher._block_to_text(notion_block)
    print(f"Converted Markdown: {markdown}")

    # Verify it's NOT a Mermaid code block
    if not markdown.startswith("```mermaid"):
        print("✓ Regular callout preserved as regular callout")
        return True
    else:
        print("✗ Regular callout incorrectly converted to Mermaid")
        return False

def test_roundtrip_conversion():
    """Test full roundtrip: Markdown → Notion → Markdown"""
    print("\n=== Test 4: Roundtrip Conversion ===")

    publisher = NotionPublisher()

    original_markdown = """```mermaid
graph LR
    A[Attacker] --> B[Victim]
    B --> C[Compromise]
```"""

    # Step 1: Markdown → Notion blocks
    blocks = publisher._convert_to_blocks(original_markdown)
    print(f"Step 1 - Converted to {len(blocks)} blocks")

    # Step 2: Notion blocks → Markdown
    if blocks:
        restored_markdown = publisher._block_to_text(blocks[0])
        print(f"Step 2 - Restored markdown:\n{restored_markdown}")

        # Verify roundtrip preservation
        if restored_markdown.strip() == original_markdown.strip():
            print("✓ Roundtrip successful: Mermaid code preserved")
            return True
        else:
            print("⚠ Roundtrip warning: Content may differ slightly")
            print(f"Original: {original_markdown[:50]}...")
            print(f"Restored: {restored_markdown[:50]}...")
            # Check if key parts are preserved
            if "```mermaid" in restored_markdown and "graph LR" in restored_markdown:
                print("✓ At least Mermaid format and content preserved")
                return True
            else:
                print("✗ Roundtrip failed: Mermaid format lost")
                return False
    else:
        print("✗ No blocks generated")
        return False

if __name__ == "__main__":
    print("Testing Mermaid Diagram Conversion Fix\n")
    print("=" * 60)

    try:
        # Run all tests
        test_mermaid_to_notion_blocks()
        test_notion_blocks_to_markdown()
        test_regular_callout()
        test_roundtrip_conversion()

        print("\n" + "=" * 60)
        print("All tests completed!")

    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
