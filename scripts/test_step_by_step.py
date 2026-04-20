#!/usr/bin/env python3
"""
Debug fetch_all by building it step by step
"""

import sys
import os
sys.path.insert(0, '.')

print("=== Step-by-Step Fetch All Debug ===")

try:
    from collector import NewsCollector
    print("✅ NewsCollector imported")
    
    collector = NewsCollector()
    print("✅ NewsCollector instantiated")
    
    print(f"\nAvailable keywords: {len(collector.keywords)}")
    print("First 5 keywords:", collector.keywords[:5])
    
    print("\n1. Testing just the first keyword Google News...")
    try:
        articles = []
        keyword = collector.keywords[0]
        articles.extend(collector.fetch_google_news(keyword, max_results=1))
        print(f"✅ First keyword: {len(articles)} articles")
    except Exception as e:
        print(f"❌ First keyword failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n2. Testing first 2 keywords...")
    try:
        articles = []
        for keyword in collector.keywords[:2]:
            articles.extend(collector.fetch_google_news(keyword, max_results=1))
            print(f"   Processed keyword: {keyword}")
        print(f"✅ First 2 keywords: {len(articles)} articles")
    except Exception as e:
        print(f"❌ First 2 keywords failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n3. Testing first 3 keywords (full fetch_all logic but no other sources)...")
    try:
        articles = []
        for keyword in collector.keywords[:3]:
            articles.extend(collector.fetch_google_news(keyword, max_results=1))
        print(f"✅ First 3 keywords: {len(articles)} articles")
    except Exception as e:
        print(f"❌ First 3 keywords failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n4. Testing full fetch_all but with arXiv only...")
    try:
        articles = []
        articles.extend(collector.fetch_arxiv(max_results=1))
        print(f"✅ ArXiv only: {len(articles)} articles")
    except Exception as e:
        print(f"❌ ArXiv only failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n5. Testing full fetch_all but step by step...")
    try:
        all_articles = []
        
        # Step 1: Google News
        print("   Step 1: Google News...")
        for keyword in collector.keywords[:3]:
            articles = collector.fetch_google_news(keyword, max_results=1)
            all_articles.extend(articles)
            print(f"      Keyword '{keyword}': {len(articles)} articles")
        
        print(f"   Total after Google News: {len(all_articles)}")
        
        # Step 2: arXiv
        print("   Step 2: arXiv...")
        articles = collector.fetch_arxiv(max_results=1)
        all_articles.extend(articles)
        print(f"   Total after arXiv: {len(all_articles)}")
        
        # Step 3: HackerNews
        print("   Step 3: HackerNews...")
        articles = collector.fetch_hackernews(max_results=1)
        all_articles.extend(articles)
        print(f"   Total after HackerNews: {len(all_articles)}")
        
        # Step 4: Hada.io
        print("   Step 4: Hada.io...")
        articles = collector.fetch_hadaio(max_results=1)
        all_articles.extend(articles)
        print(f"   Total after Hada.io: {len(all_articles)}")
        
        # Step 5: GeekNews
        print("   Step 5: GeekNews...")
        articles = collector.fetch_geeknews(max_results=1)
        all_articles.extend(articles)
        print(f"   Total after GeekNews: {len(all_articles)}")
        
        # Step 6: Sort
        print("   Step 6: Sorting...")
        all_articles.sort(key=lambda x: x["published"], reverse=True)
        print(f"   Final count: {len(all_articles)} articles")
        
        print("✅ Step-by-step fetch_all completed successfully!")
        
    except Exception as e:
        print(f"❌ Step-by-step fetch_all failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n=== Step-by-step debug completed ===")
    
except Exception as e:
    print(f"❌ Debug failed: {e}")
    import traceback
    traceback.print_exc()