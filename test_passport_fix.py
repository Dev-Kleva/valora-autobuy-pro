#!/usr/bin/env python3
"""Test the fixed Passport execution."""

import os
import sys
from dotenv import load_dotenv

# Load environment variables from root .env for direct tests
root_env = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(root_env):
    load_dotenv(root_env)

os.environ['KITE_PASSPORT_BASE_URL'] = os.getenv('KITE_PASSPORT_BASE_URL', 'https://passport.dev.gokite.ai')

from backend.kite_passport import get_passport

try:
    passport = get_passport()
    print('✅ Passport initialized')
    
    # Test execute_agent_request with a dummy recipient
    result = passport.execute_agent_request(
        service_query='Test payment execution',
        payment_amount=0.01,
        payment_asset='USDC',
        recipient_address='0xBB9EeF933426C07348d79A46b61FE94C99f6aeb7'
    )
    print('✅ Payment execution result:')
    print(f'  TX Hash: {result.get("tx_hash")}')
    print(f'  Status: {result.get("status")}')
    print(f'  Message: {result.get("message")}')
except Exception as e:
    print(f'❌ Error: {e}')
    sys.exit(1)
