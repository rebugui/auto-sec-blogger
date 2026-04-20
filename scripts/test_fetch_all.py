#!/usr/bin/env python3
"""
Test fetch_all method with very small limits
"""

import sys
import os
import signal
import threading
sys.path.insert(0, '.')

print("=== Fetch All Method Test ===")

class TimeoutException(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutException("fetch_all timed out")

try:
    from collector import NewsCollector
    print("✅ NewsCollector imported")
    
    collector = NewsCollector()
    print("✅ NewsCollector instantiated")
    
    print("\n1. Testing fetch_all with max_results_per_source=1...")
    try:
        articles = collector.fetch_all(max_results_per_source=1)
        print(f"✅ fetch_all successful: {len(articles)} articles")
        
        # Show first few articles
        for i, article in enumerate(articles[:3]):
            print(f"   {i+1}. {article.get('source', 'Unknown')}: {article.get('title', 'No title')[:50]}...")
            
    except Exception as e:
        print(f"❌ fetch_all failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n2. Testing fetch_all with max_results_per_source=0 (minimal)...")
    try:
        articles = collector.fetch_all(max_results_per_source=0)
        print(f"✅ fetch_all with 0 results: {len(articles)} articles")
    except Exception as e:
        print(f"❌ fetch_all with 0 failed: {e}")
    
    print("\n=== fetch_all test completed ===")
    
except Exception as e:
    print(f"❌ Test failed: {e}")
    import traceback
    traceback.print_exc()