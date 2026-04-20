#!/usr/bin/env python3
"""
Test individual fetch methods with timeout and debugging
"""

import sys
import os
import signal
import threading
sys.path.insert(0, '.')

print("=== Individual Fetch Method Test with Timeout ===")

class TimeoutException(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutException("Method timed out")

try:
    from collector import NewsCollector
    print("✅ NewsCollector imported")
    
    collector = NewsCollector()
    print("✅ NewsCollector instantiated")
    
    # Set up timeout for each test
    signal.signal(signal.SIGALRM, timeout_handler)
    
    # Test 1: fetch_google_news
    print("\n1. Testing fetch_google_news...")
    signal.alarm(15)  # 15 second timeout
    try:
        articles = collector.fetch_google_news("security", max_results=1)
        print(f"✅ Google News: {len(articles)} articles")
        signal.alarm(0)  # Cancel timeout
    except TimeoutException:
        print("❌ Google News: TIMEOUT (15s exceeded)")
        signal.alarm(0)
    except Exception as e:
        print(f"❌ Google News failed: {e}")
        signal.alarm(0)
    
    # Test 2: fetch_hackernews  
    print("\n2. Testing fetch_hackernews...")
    signal.alarm(15)
    try:
        articles = collector.fetch_hackernews(max_results=1)
        print(f"✅ HackerNews: {len(articles)} articles")
        signal.alarm(0)
    except TimeoutException:
        print("❌ HackerNews: TIMEOUT (15s exceeded)")
        signal.alarm(0)
    except Exception as e:
        print(f"❌ HackerNews failed: {e}")
        signal.alarm(0)
    
    # Test 3: fetch_hadaio
    print("\n3. Testing fetch_hadaio...")
    signal.alarm(15)
    try:
        articles = collector.fetch_hadaio(max_results=1)
        print(f"✅ Hada.io: {len(articles)} articles")
        signal.alarm(0)
    except TimeoutException:
        print("❌ Hada.io: TIMEOUT (15s exceeded)")
        signal.alarm(0)
    except Exception as e:
        print(f"❌ Hada.io failed: {e}")
        signal.alarm(0)
    
    # Test 4: fetch_geeknews
    print("\n4. Testing fetch_geeknews...")
    signal.alarm(15)
    try:
        articles = collector.fetch_geeknews(max_results=1)
        print(f"✅ GeekNews: {len(articles)} articles")
        signal.alarm(0)
    except TimeoutException:
        print("❌ GeekNews: TIMEOUT (15s exceeded)")
        signal.alarm(0)
    except Exception as e:
        print(f"❌ GeekNews failed: {e}")
        signal.alarm(0)
    
    print("\n=== Individual fetch test completed ===")
    
except Exception as e:
    print(f"❌ Test failed: {e}")
    import traceback
    traceback.print_exc()