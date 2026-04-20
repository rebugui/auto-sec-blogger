#!/usr/bin/env python3
"""
Simple test script to debug the auto-sec-blogger issue
"""

import sys
import os
sys.path.insert(0, '.')

print("=== Simple Intelligence Pipeline Test ===")

try:
    # Test 1: Config loading
    print("\n1. Testing config loading...")
    from config import DB_PATH, GLM_API_KEY, NOTION_API_KEY
    print(f"✅ Config loaded: DB_PATH={DB_PATH}")
    print(f"✅ GLM_API_KEY set: {bool(GLM_API_KEY)}")
    print(f"✅ NOTION_API_KEY set: {bool(NOTION_API_KEY)}")
    
    # Test 2: Database initialization
    print("\n2. Testing database initialization...")
    import sqlite3
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT 1")
    result = cursor.fetchone()
    print(f"✅ Database accessible: {result}")
    conn.close()
    
    # Test 3: Simple HTTP request
    print("\n3. Testing HTTP request...")
    import requests
    response = requests.get('https://httpbin.org/get', timeout=10)
    print(f"✅ HTTP request successful: {response.status_code}")
    
    # Test 4: News collector (limited)
    print("\n4. Testing news collector (very limited)...")
    from collector import NewsCollector
    collector = NewsCollector()
    print(f"✅ Collector initialized with {len(collector.keywords)} keywords")
    
    # Test 5: Just arXiv with minimal results
    print("\n5. Testing arXiv fetch (minimal)...")
    try:
        articles = collector.fetch_arxiv(max_results=1)
        print(f"✅ arXiv fetch successful: {len(articles)} articles")
        if articles:
            print(f"   Sample title: {articles[0].get('title', 'No title')[:50]}...")
    except Exception as e:
        print(f"⚠️ arXiv fetch failed: {e}")
    
    print("\n=== All tests completed successfully! ===")
    
except Exception as e:
    print(f"❌ Test failed: {e}")
    import traceback
    traceback.print_exc()