#!/usr/bin/env python3
"""
Test individual fetch methods to isolate the issue
"""

import sys
import os
sys.path.insert(0, '.')

print("=== Individual Fetch Method Test ===")

try:
    from collector import NewsCollector
    print("✅ NewsCollector imported")
    
    collector = NewsCollector()
    print("✅ NewsCollector instantiated")
    
    # Test each fetch method individually with very small limits
    print("\n1. Testing fetch_google_news...")
    try:
        articles = collector.fetch_google_news("security", max_results=1)
        print(f"✅ Google News: {len(articles)} articles")
    except Exception as e:
        print(f"❌ Google News failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n2. Testing fetch_arxiv...")
    try:
        articles = collector.fetch_arxiv(max_results=1)
        print(f"✅ arXiv: {len(articles)} articles")
    except Exception as e:
        print(f"❌ arXiv failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n3. Testing fetch_hackernews...")
    try:
        articles = collector.fetch_hackernews(max_results=1)
        print(f"✅ HackerNews: {len(articles)} articles")
    except Exception as e:
        print(f"❌ HackerNews failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n4. Testing fetch_hadaio...")
    try:
        articles = collector.fetch_hadaio(max_results=1)
        print(f"✅ Hada.io: {len(articles)} articles")
    except Exception as e:
        print(f"❌ Hada.io failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n5. Testing fetch_geeknews...")
    try:
        articles = collector.fetch_geeknews(max_results=1)
        print(f"✅ GeekNews: {len(articles)} articles")
    except Exception as e:
        print(f"❌ GeekNews failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n=== Individual fetch test completed ===")
    
except Exception as e:
    print(f"❌ Test failed: {e}")
    import traceback
    traceback.print_exc()