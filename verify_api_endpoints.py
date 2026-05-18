#!/usr/bin/env python3
"""Verify API endpoint compatibility between frontend and backend"""

import re

# Check frontend API calls
with open('frontend/src/App.jsx', 'r', encoding='utf-8') as f:
    frontend_content = f.read()
    api_calls = re.findall(r"\`\$\{API_BASE\}([^`\s]+)", frontend_content)
    print("=" * 60)
    print("FRONTEND API CALLS")
    print("=" * 60)
    for call in sorted(set(api_calls)):
        print(f"  {call}")

# Check backend endpoints
with open('backend/main.py', 'r', encoding='utf-8') as f:
    backend_content = f.read()
    endpoints = re.findall(r'@app\.(get|post|put|delete)\("([^"]+)"', backend_content)
    print("\n" + "=" * 60)
    print("BACKEND ENDPOINTS")
    print("=" * 60)
    for method, path in sorted(set(endpoints)):
        print(f"  [{method.upper():6}] {path}")

# Verify critical endpoints
critical_endpoints = [
    ('post', '/register'),
    ('post', '/login'),
    ('post', '/buy'),
    ('post', '/confirm-payment'),
    ('get', '/kite/health'),
    ('post', '/wallet/check-requirements'),
    ('get', '/wallet/balances'),
    ('get', '/wallet/network-config'),
    ('get', '/wallet/faucets'),
    ('post', '/payment/prepare'),
]

print("\n" + "=" * 60)
print("CRITICAL ENDPOINT VERIFICATION")
print("=" * 60)

backend_endpoints_set = set((method.lower(), path) for method, path in endpoints)

for method, path in critical_endpoints:
    exists = (method, path) in backend_endpoints_set
    status = "✅" if exists else "❌"
    print(f"  {status} [{method.upper():6}] {path}")

print("\n✅ API endpoint verification complete!")
