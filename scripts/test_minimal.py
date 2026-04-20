#!/usr/bin/env python3
"""
Minimal test to identify the exact issue
"""

import sys
import os
sys.path.insert(0, '.')

print("=== Minimal Debug Test ===")

try:
    print("\n1. Testing basic Python...")
    print("Python works")
    
    print("\n2. Testing os.path...")
    print(f"Current dir: {os.getcwd()}")
    
    print("\n3. Testing import of individual modules...")
    
    print("\n3a. Testing config...")
    try:
        import config
        print("✅ config imported")
    except Exception as e:
        print(f"❌ config failed: {e}")
    
    print("\n3b. Testing utils...")
    try:
        import utils
        print("✅ utils imported")
    except Exception as e:
        print(f"❌ utils failed: {e}")
    
    print("\n3c. Testing collector...")
    try:
        import collector
        print("✅ collector imported")
    except Exception as e:
        print(f"❌ collector failed: {e}")
    
    print("\n3d. Testing notion_publisher...")
    try:
        import notion_publisher
        print("✅ notion_publisher imported")
    except Exception as e:
        print(f"❌ notion_publisher failed: {e}")
    
    print("\n3e. Testing selector...")
    try:
        import selector
        print("✅ selector imported")
    except Exception as e:
        print(f"❌ selector failed: {e}")
    
    print("\n3f. Testing writer...")
    try:
        import writer
        print("✅ writer imported")
    except Exception as e:
        print(f"❌ writer failed: {e}")
    
    print("\n=== Test completed ===")
    
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc()