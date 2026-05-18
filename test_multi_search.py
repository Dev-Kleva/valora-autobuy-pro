#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from agent import search_all_platforms

def test_multi_platform_search():
    """Test the multi-platform search functionality"""
    print("🧪 Testing Multi-Platform Product Search")
    print("=" * 50)

    # Test search for laptops in budget range
    query = "laptop"
    min_price = 500
    max_price = 800

    print(f"Searching for: '{query}' (${min_price}-${max_price})")
    print("Platforms: Google Shopping, Amazon, Walmart, Best Buy")
    print("-" * 50)

    try:
        results = search_all_platforms(query, min_price, max_price, limit_per_platform=3)

        print(f"\n✅ Found {len(results)} products total")
        print("\nTop results:")

        for i, product in enumerate(results[:5], 1):
            name = product.get('name', 'Unknown')[:60]
            price = product.get('price', 0)
            store = product.get('store', 'Unknown')
            source = product.get('source', 'unknown')
            rating = product.get('rating', 0)

            print(f"{i}. {name}")
            print(f"   💰 ${price} at {store} ({source})")
            if rating > 0:
                print(f"   ⭐ {rating}/5")
            print()

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    test_multi_platform_search()