#!/usr/bin/env python3
"""
Direct test of Amazon search functionality
"""

from backend.agent import search_amazon_products

def test_amazon_direct():
    print("🔍 Testing Amazon Search Function Directly")
    print("=" * 50)

    # Test 1: Simple laptop search
    print("\n1. Searching for 'laptop'...")
    results = search_amazon_products("laptop", min_price=0, max_price=1000, limit=3)
    print(f"   Found {len(results)} products:")
    for i, product in enumerate(results, 1):
        print(f"   {i}. {product['name'][:60]}... - ${product['price']}")

    # Test 2: Wireless headphones
    print("\n2. Searching for 'wireless headphones'...")
    results = search_amazon_products("wireless headphones", min_price=0, max_price=200, limit=3)
    print(f"   Found {len(results)} products:")
    for i, product in enumerate(results, 1):
        print(f"   {i}. {product['name'][:60]}... - ${product['price']}")

    # Test 3: Specific price range
    print("\n3. Searching for laptops $500-$600...")
    results = search_amazon_products("laptop", min_price=500, max_price=600, limit=3)
    print(f"   Found {len(results)} products in price range:")
    for i, product in enumerate(results, 1):
        print(f"   {i}. {product['name'][:60]}... - ${product['price']}")

if __name__ == "__main__":
    test_amazon_direct()
