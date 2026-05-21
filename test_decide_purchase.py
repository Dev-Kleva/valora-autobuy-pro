#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.agent import decide_purchase

def test_decide_purchase():
    """Test the decide_purchase function with multi-platform search"""
    print("🧪 Testing decide_purchase function")
    print("=" * 50)

    # Test 1: Local catalog match
    print("\nTest 1: Local catalog match")
    request1 = {
        "budget": 1000,
        "query": "gaming laptop",
        "search_online": False
    }

    result1 = decide_purchase(request1)
    print(f"Result: {result1}")

    # Test 2: Online search (will try multi-platform)
    print("\nTest 2: Multi-platform search")
    request2 = {
        "budget": 600,
        "query": "laptop $500 to $600",
        "search_online": True
    }

    result2 = decide_purchase(request2)
    print(f"Result: {result2}")

    print("\n✅ Tests completed successfully!")

if __name__ == "__main__":
    test_decide_purchase()