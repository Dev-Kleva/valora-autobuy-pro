#!/usr/bin/env python3
"""
Test script for Kite Agent Passport integration
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from backend.kite_passport import get_passport
import json

def test_passport_integration():
    """Test basic Passport functionality"""
    print("🧪 Testing Kite Agent Passport Integration")
    print("=" * 50)

    try:
        # Initialize Passport
        passport = get_passport()
        print("✅ Passport initialized successfully")

        # Test service discovery
        print("\n🔍 Testing service discovery...")
        services = passport.discover_services(query="payment", limit=5)
        print(f"✅ Found {len(services.get('services', []))} services")

        # Test wallet balance (may fail if not logged in)
        print("\n💰 Testing wallet balance...")
        try:
            balance = passport.get_wallet_balance()
            print(f"✅ Wallet balance: {balance}")
        except Exception as e:
            print(f"⚠️ Wallet check failed (expected if not logged in): {e}")

        # Test agent registration (may fail if not logged in)
        print("\n🤖 Testing agent registration...")
        try:
            agent = passport.register_agent("Test AutoBuy Agent", "Test agent for integration")
            print(f"✅ Agent registered: {agent}")
        except Exception as e:
            print(f"⚠️ Agent registration failed (expected if not logged in): {e}")

        print("\n🎉 Passport integration test completed!")
        print("Note: Full functionality requires Passport CLI login and wallet setup")

    except Exception as e:
        print(f"❌ Passport integration test failed: {e}")
        return False

    return True

if __name__ == "__main__":
    success = test_passport_integration()
    sys.exit(0 if success else 1)