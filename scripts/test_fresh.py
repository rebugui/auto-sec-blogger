#!/usr/bin/env python3
"""
Test creating fresh collector instances for each operation
"""

import sys
import os
sys.path.insert(0, '.')

print("=== Fresh Collector Instance Test ===")

try:
    from collector import NewsCollector
    
    print("\n1. Testing with completely fresh instances...")
    
    # Test 1: Fresh collector, just Google News
    print("\n1a. Fresh collector + Google News...")
    collector1 = NewsCollector()
    articles1 = collector1.fetch_google_news("security", max_results=1)
    print(f"✅ Fresh Google News: {len(articles1)} articles")
    
    # Test 2: Fresh collector, just arXiv
    print("\n1b. Fresh collector + arXiv...")
    collector2 = NewsCollector()
    articles2 = collector2.fetch_arxiv(max_results=1)
    print(f"✅ Fresh arXiv: {len(articles2)} articles")
    
    # Test 3: Fresh collector, just HackerNews
    print("\n1c. Fresh collector + HackerNews...")
    collector3 = NewsCollector()
    articles3 = collector3.fetch_hackernews(max_results=1)
    print(f"✅ Fresh HackerNews: {len(articles3)} articles")
    
    # Test 4: Fresh collector, fetch_all minimal
    print("\n1d. Fresh collector + fetch_all minimal...")
    collector4 = NewsCollector()
    articles4 = collector4.fetch_all(max_results_per_source=0)
    print(f"✅ Fresh fetch_all (0): {len(articles4)} articles")
    
    print("\n2. Now testing the same collector sequentially...")
    
    # Test 5: Same collector, sequential operations
    print("\n2a. Same collector + sequential operations...")
    collector5 = NewsCollector()
    
    articles5a = collector5.fetch_google_news("security", max_results=1)
    print(f"   Google News: {len(articles5a)} articles")
    
    articles5b = collector5.fetch_arxiv(max_results=1)
    print(f"   arXiv: {len(articles5b)} articles")
    
    articles5c = collector5.fetch_hackernews(max_results=1)
    print(f"   HackerNews: {len(articles5c)} articles")
    
    print(f"   Total: {len(articles5a) + len(articles5b) + len(articles5c)} articles")
    
    print("\n3. Testing the same collector with limited fetch_all...")
    
    # Test 6: Same collector, limited fetch_all
    print("\n2b. Same collector + fetch_all minimal...")
    collector6 = NewsCollector()
    articles6 = collector6.fetch_all(max_results_per_source=0)
    print(f"✅ Same collector fetch_all (0): {len(articles6)} articles")
    
    print("\n=== Fresh instance test completed ===")
    
except Exception as e:
    print(f"❌ Test failed: {e}")
    import traceback
    traceback.print_exc()