import requests
import json

# Get a token
reg = requests.post('http://localhost:8001/register', json={'username': 'test_' + str(int(__import__('time').time())), 'password': 'test123'})
token = reg.json()['token']

# Get a product
response = requests.post(
    'http://localhost:8001/buy',
    headers={'Authorization': f'Bearer {token}'},
    json={'query': 'laptop', 'budget': 700, 'search_online': True}
)

product = response.json()['product']

# Create a test message with OLD format (Python default - WITH spaces)
payment_payload = {
    'currency': product.get('currency', 'USDC'),
    'price': product['price'],
    'product_name': product['name'],
}

old_json = json.dumps(payment_payload, sort_keys=True)
old_message = f"Autobuy payment confirmation {old_json}"

# Create a test message with NEW format (JavaScript - NO spaces)
new_json = json.dumps(payment_payload, sort_keys=True, separators=(',', ':'))
new_message = f"Autobuy payment confirmation {new_json}"

print('PYTHON DEFAULT FORMAT (WITH spaces):')
print(repr(old_message))
print(f'Length: {len(old_message)}')
print()

print('JAVASCRIPT FORMAT (NO spaces):')
print(repr(new_message))
print(f'Length: {len(new_message)}')
print()

print('Frontend format (from user logs):')
frontend_format = 'Autobuy payment confirmation {"currency":"USD","price":599.99,"product_name":"Test"}'
print(repr(frontend_format))
print()

expected = '{"currency":"USD","price":650,"product_name":"Laptop C"}'
print(f'Does NEW backend format match JavaScript style? {new_json == expected}')
