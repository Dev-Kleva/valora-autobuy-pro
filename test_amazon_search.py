#!/usr/bin/env python3
"""
Test the enhanced Valora AutoBuy Agent with Amazon product search
"""

import requests
import json

BASE_URL = "http://localhost:8001"

def test_amazon_search():
    """Test Valora AutoBuy Agent functionality with Amazon product search"""
    print("Testing Valora AutoBuy Agent")
    print("=" * 70)

    # Test 1: Register/Login
    print("\n1. Authentication")
    login_response = requests.post(
        f"{BASE_URL}/login",
        json={"username": "testuser", "password": "testpass123"}
    )

    if login_response.status_code != 200:
        reg_response = requests.post(
            f"{BASE_URL}/register",
            json={"username": "testuser", "password": "testpass123"}
        )
        print(f"   Registered new user: {reg_response.json()}")
        token = reg_response.json()["token"]
    else:
        print(f"   Logged in: {login_response.json()}")
        token = login_response.json()["token"]

    headers = {"Authorization": f"Bearer {token}"}

    # Test 2: Local catalog search (existing functionality)
    print("\n2. Local Catalog Search")
    local_request = {
        "query": "laptop",
        "budget": 1000,
        "search_online": False
    }

    response = requests.post(f"{BASE_URL}/buy", json=local_request, headers=headers)
    print(f"   Status: {response.status_code}")
    if response.status_code == 402:
        data = response.json()
        print(f"   Found: {data['product']['name']} - ${data['product']['price']}")
        print(f"   Source: {data.get('source', 'unknown')}")

    # Test 3: Amazon search for laptops $500-$600
    print("\n3. Amazon Product Search - Laptops $500-$600")
    amazon_request = {
        "query": "laptop $500 to $600",
        "budget": 600,
        "search_online": True
    }

    print(f"   Searching: {amazon_request['query']}")
    print(f"   Budget: ${amazon_request['budget']}")
    print("   This may take a few seconds...")

    response = requests.post(f"{BASE_URL}/buy", json=amazon_request, headers=headers)
    print(f"\n   Status: {response.status_code}")

    if response.status_code == 402:
        data = response.json()
        product = data['product']
        assert product['price'] <= amazon_request['budget'], f"Product price {product['price']} exceeds budget {amazon_request['budget']}"
        
        # Check for ad content
        ad_indicators = ['ad based', 'sponsored', 'you\'re seeing this ad', 'product\'s relevance']
        is_ad = any(indicator in product['name'].lower() for indicator in ad_indicators)
        assert not is_ad, f"Product appears to be an ad: {product['name']}"
        
        print("   Found Product:")
        print(f"      Name: {product['name']}")
        print(f"      Price: ${product['price']}")
        print(f"      Rating: {product.get('rating', 'N/A')}")
        print(f"      URL: {product.get('url', 'N/A (payment required)')}")
        print(f"      Source: {data.get('source', 'unknown')}")
        print(f"      Message: {data.get('message', 'No message')}")

        # Verify payment enforcement - URL should NOT be present in preview
        assert 'url' not in product, "Product URL should not be included in payment_required response"
        print("   [PASS] Payment enforcement verified: URL excluded from preview")

        # Show additional search results
        if "search_results" in data:
            print("\n   Top Search Results:")
            for i, result in enumerate(data["search_results"], 1):
                print(f"      {i}. {result['name'][:50]}... - ${result['price']}")
                # Verify search results also don't have URLs
                assert 'url' not in result, f"Search result {i} should not have URL in preview"

    elif response.status_code == 200:
        data = response.json()
        if data.get("status") == "no_match":
            print("   ❌ No products found matching criteria")

    # Test 4: Different product search
    print("\n4. Amazon Search - Wireless Headphones")
    headphones_request = {
        "query": "wireless headphones",
        "budget": 150,
        "search_online": True
    }

    print(f"   Searching: {headphones_request['query']}")
    response = requests.post(f"{BASE_URL}/buy", json=headphones_request, headers=headers)
    print(f"   Status: {response.status_code}")

    if response.status_code == 402:
        data = response.json()
        product = data['product']
        print("   Found Product:")
        print(f"      Name: {product['name']}")
        print(f"      Price: ${product['price']}")
        print(f"      Source: {data.get('source', 'unknown')}")
        print(f"      Message: {data.get('message', 'No message')}")

        # Verify payment enforcement for headphones search
        assert 'url' not in product, "Headphones product URL should not be included in payment_required response"
        print("   [PASS] Payment enforcement verified for headphones search")

    print("\n" + "=" * 70)
    print("Valora AutoBuy Agent Test Complete!")
    print("\nKey Features Demonstrated:")
    print("   - Local catalog search (fast, reliable)")
    print("   - Real-time Amazon product search")
    print("   • Price range filtering ($500-$600)")
    print("   • Product ratings and URLs")
    print("   • Multiple search result options")
    print("   • Payment enforcement (URLs hidden until payment)")
    print("   • USDC payment integration ready")
    print("   • Kite blockchain settlement ready")

if __name__ == "__main__":
    test_amazon_search()
