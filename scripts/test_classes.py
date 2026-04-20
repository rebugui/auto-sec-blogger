#!/usr/bin/env python3
"""
Test instantiation of main classes
"""

import sys
import os
sys.path.insert(0, '.')

print("=== Class Instantiation Test ===")

try:
    print("\n1. Testing NewsCollector instantiation...")
    from collector import NewsCollector
    collector = NewsCollector()
    print("✅ NewsCollector instantiated successfully")
    print(f"   Keywords count: {len(collector.keywords)}")
    
    print("\n2. Testing NotionPublisher instantiation...")
    from notion_publisher import NotionPublisher
    notion_pub = NotionPublisher()
    print("✅ NotionPublisher instantiated successfully")
    
    print("\n3. Testing ArticleSelector instantiation...")
    from selector import ArticleSelector
    selector = ArticleSelector()
    print("✅ ArticleSelector instantiated successfully")
    
    print("\n4. Testing BlogWriter instantiation...")
    from writer import BlogWriter
    writer = BlogWriter()
    print("✅ BlogWriter instantiated successfully")
    
    print("\n=== All classes instantiated successfully! ===")
    
except Exception as e:
    print(f"❌ Class instantiation failed: {e}")
    import traceback
    traceback.print_exc()