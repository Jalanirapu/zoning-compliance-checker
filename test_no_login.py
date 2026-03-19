import requests

# Test all pages work without login
pages = ['/', '/analysis', '/about', '/support', '/documentation']
for page in pages:
    r = requests.get(f'http://localhost:5000{page}')
    print(f'{page}: {r.status_code}')

# Test login page is removed
login_resp = requests.get('http://localhost:5000/login')
print(f'/login: {login_resp.status_code} (should be 404)')

# Test analyze endpoint WITHOUT authentication
print('\n--- Testing Compliance Analysis ---')
geo_data = {'address': '1600 Pennsylvania Avenue, Washington, DC'}
geo_response = requests.post('http://localhost:5000/api/geocode', json=geo_data)
print(f'Geocoding: {geo_response.status_code}')

if geo_response.status_code == 200:
    coords = geo_response.json().get('coordinates', {})
    analysis_data = {
        'zone_type': 'R-1',
        'coordinates': coords,
        'building_height_ft': 35.0,
        'lot_coverage_percent': 40.0
    }
    analysis_response = requests.post('http://localhost:5000/api/compliance/analyze', json=analysis_data)
    print(f'Analysis: {analysis_response.status_code}')
    if analysis_response.status_code == 200:
        result = analysis_response.json()
        if result.get('success'):
            print(f"Score: {result['report']['compliance_score']}%")
            print('All functionality works WITHOUT login!')
