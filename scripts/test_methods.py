#!/usr/bin/env python3
"""
Test pipeline methods step by step
"""

import sys
import os
sys.path.insert(0, '.')
import asyncio

print("=== Pipeline Method Test ===")

try:
    from collector import NewsCollector
    from notion_publisher import NotionPublisher
    from selector import ArticleSelector
    from writer import BlogWriter
    print("✅ All imports successful")
    
    print("\n1. Creating instances...")
    collector = NewsCollector()
    notion_pub = NotionPublisher()
    selector = ArticleSelector()
    writer = BlogWriter()
    print("✅ All instances created")
    
    print("\n2. Testing news collection (very limited)...")
    try:
        articles = collector.fetch_all(max_results_per_source=1)
        print(f"✅ News collection successful: {len(articles)} articles")
    except Exception as e:
        print(f"❌ News collection failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n3. Testing article selection (if we have articles)...")
    try:
        # This will only run if we successfully got articles
        if 'articles' in locals() and articles:
            selected = asyncio.run(selector.evaluate_and_select(articles, max_articles=1))
            print(f"✅ Article selection successful: {len(selected)} articles")
        else:
            print("⚠️ Skipping article selection (no articles collected)")
    except Exception as e:
        print(f"❌ Article selection failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n=== Method testing completed ===")
    
except Exception as e:
    print(f"❌ Test failed: {e}")
    import traceback
    traceback.print_exc()