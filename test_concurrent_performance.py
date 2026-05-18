#!/usr/bin/env python3
"""
Performance comparison: Sequential vs Concurrent platform searches
"""

import time
import requests
from backend.agent import search_all_platforms, search_all_platforms_concurrent

def test_search_performance():
    """Compare sequential vs concurrent search performance"""

    query = "wireless headphones"
    min_price = 50
    max_price = 150

    print("🚀 Valora Search Performance Test")
    print("=" * 60)
    print(f"Query: '{query}' (${min_price}-${max_price})")
    print()

    # Test Sequential Search
    print("🐌 SEQUENTIAL SEARCH (old method):")
    start_time = time.time()
    sequential_results = search_all_platforms(query, min_price, max_price, limit_per_platform=3)
    sequential_time = time.time() - start_time

    print(".2f")
    print(f"   Results: {len(sequential_results)} products")
    print()

    # Test Concurrent Search
    print("⚡ CONCURRENT SEARCH (new method):")
    start_time = time.time()
    concurrent_results = search_all_platforms_concurrent(query, min_price, max_price, limit_per_platform=3)
    concurrent_time = time.time() - start_time

    print(".2f")
    print(f"   Results: {len(concurrent_results)} products")
    print()

    # Performance Comparison
    print("📊 PERFORMANCE COMPARISON:")
    print("-" * 40)
    print(".2f")
    print(".2f")

    if concurrent_time > 0:
        speedup = sequential_time / concurrent_time
        print(".1f")
        print(".0f")

    # Show sample results
    if concurrent_results:
        print("\n🎯 SAMPLE RESULTS (Concurrent):")
        for i, product in enumerate(concurrent_results[:3], 1):
            print(f"   {i}. {product['name'][:50]}... - ${product['price']:.2f} ({product.get('store', 'Unknown')})")

if __name__ == "__main__":
    test_search_performance()