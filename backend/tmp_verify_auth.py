import requests
import uuid

base = 'http://127.0.0.1:8001'
username = f'testuser_{uuid.uuid4().hex[:6]}'
password = 'Password123!'
print('registering', username)
r = requests.post(f'{base}/register', json={'username': username, 'password': password})
print('register', r.status_code, r.text)
r2 = requests.post(f'{base}/login', json={'username': username, 'password': password})
print('login', r2.status_code, r2.text)
if r2.status_code == 200:
    token = r2.json().get('token')
    print('token', token)
    headers = {'Authorization': f'Bearer {token}'}
r3 = requests.get(f'{base}/passport/health', headers=headers if r2.status_code == 200 else {})
print('passport health', r3.status_code, r3.text)
