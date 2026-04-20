#!/usr/bin/env python3
"""
Test arxiv library specifically
"""

import sys
import os
sys.path.insert(0, '.')

print("=== ArXiv Library Test ===")

try:
    print("\n1. Testing basic arxiv import...")
    import arxiv
    print("✅ arxiv imported successfully")
    
    print("\n2. Testing arxiv search with minimal parameters...")
    try:
        search = arxiv.Search(
            query="cat:cs.CR",
            max_results=1,
            sort_by=arxiv.SortCriterion.SubmittedDate
        )
        print("✅ Search object created successfully")
        
        print("\n3. Testing results iteration...")
        count = 0
        for result in search.results():
            count += 1
            print(f"✅ Got result {count}: {result.title[:50]}...")
            if count >= 1:  # Only process first result
                break
        
        print(f"✅ Results iteration successful: {count} results")
        
    except Exception as e:
        print(f"❌ ArXiv search failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n=== ArXiv test completed ===")
    
except Exception as e:
    print(f"❌ Test failed: {e}")
    import traceback
    traceback.print_exc()