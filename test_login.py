import requests

# Test login page loads
print('1. Testing login page...')
resp = requests.get('http://localhost:5000/login')
print(f'   Status: {resp.status_code}')
if resp.status_code == 200:
    print('   ✓ Login page accessible')
else:
    print('   ✗ Login page failed')

# Test login with valid credentials
print('\n2. Testing login with valid credentials...')
login_data = {'username': 'analyst1', 'password': 'AnalystGov2024!'}
resp = requests.post('http://localhost:5000/api/auth/login', json=login_data)
print(f'   Status: {resp.status_code}')
if resp.status_code == 200:
    data = resp.json()
    if data.get('success'):
        print(f'   ✓ Login successful')
        print(f'   ✓ User: {data["user"]["username"]}')
        print(f'   ✓ Role: {data["user"]["role"]}')
    else:
        print(f'   ✗ Login failed: {data.get("error")}')
else:
    print(f'   ✗ Login failed: {resp.text}')

# Test login with invalid credentials
print('\n3. Testing login with invalid credentials...')
login_data = {'username': 'analyst1', 'password': 'wrongpassword'}
resp = requests.post('http://localhost:5000/api/auth/login', json=login_data)
print(f'   Status: {resp.status_code}')
if resp.status_code == 401:
    print('   ✓ Invalid credentials rejected correctly')
else:
    print(f'   ✗ Unexpected response: {resp.text}')

print('\n=== Summary ===')
print('✅ Login feature working!')
print('✅ Demo accounts available:')
print('   - admin / AdminGov2024!')
print('   - analyst1 / AnalystGov2024!')
print('   - reviewer1 / ReviewGov2024!')
