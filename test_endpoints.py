import urllib.request
import json
import sys

base_url = "http://127.0.0.1:5000"

pages = [
    ('/', 'Dashboard'),
    ('/passengers', 'Passengers'),
    ('/baggage', 'Baggage'),
    ('/priority-queue', 'Priority Queue'),
    ('/assistance', 'Assistance Requests'),
    ('/notifications', 'Notifications'),
    ('/passenger-tracking', 'Passenger Tracking'),
    ('/passenger-tracking?query=PAX1002', 'Passenger Tracking (PAX1002)'),
    ('/passenger-tracking?query=BG1001', 'Passenger Tracking (BG1001)'),
    ('/reports', 'Reports'),
]

print("=== 1. TESTING MAJOR WEB PAGES ===")
all_success = True
for path, name in pages:
    url = base_url + path
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as res:
            content = res.read().decode('utf-8')
            print(f"[OK] {name:<35} -> HTTP {res.status} ({len(content)} chars)")
    except Exception as e:
        print(f"[FAIL] {name:<35} -> Error: {e}")
        all_success = False

print("\n=== 2. TESTING REST API ENDPOINTS ===")
apis = [
    ('/api/priority-queue', 'GET Priority Queue API'),
    ('/api/passengers', 'GET Passengers API'),
    ('/api/baggage', 'GET Baggage API'),
    ('/api/reports/data', 'GET Reports Data API'),
    ('/api/baggage/BG1001', 'GET Single Baggage API (BG1001)'),
    ('/api/track?query=BG1001', 'GET Track API (BG1001)'),
]

for path, name in apis:
    url = base_url + path
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as res:
            data = json.loads(res.read().decode('utf-8'))
            print(f"[OK] {name:<35} -> HTTP {res.status} (Valid JSON)")
    except Exception as e:
        print(f"[FAIL] {name:<35} -> Error: {e}")
        all_success = False

# Test POST /api/baggage/scan
try:
    url = base_url + '/api/baggage/scan'
    payload = json.dumps({'baggage_id': 'BG1002'}).encode('utf-8')
    req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=5) as res:
        data = json.loads(res.read().decode('utf-8'))
        print(f"[OK] {'POST /api/baggage/scan':<35} -> HTTP {res.status}")
        print(f"     Scanned Bag    : {data.get('baggage_id')}")
        print(f"     Passenger      : {data.get('passenger')}")
        print(f"     Priority Level : {data.get('priority_level')}")
        print(f"     Priority Score : {data.get('priority_score')}")
        print(f"     Reason         : {data.get('priority_reason')}")
except Exception as e:
    print(f"[FAIL] POST /api/baggage/scan -> Error: {e}")
    all_success = False

# Test POST /api/baggage/status
try:
    url = base_url + '/api/baggage/status'
    payload = json.dumps({'baggage_id': 'BG1002', 'status': 'Claim Ready'}).encode('utf-8')
    req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=5) as res:
        data = json.loads(res.read().decode('utf-8'))
        print(f"[OK] {'POST /api/baggage/status':<35} -> HTTP {res.status}")
        print(f"     Updated Status : {data.get('status')}")
        print(f"     New Wait Time  : {data.get('estimated_wait')} mins")
except Exception as e:
    print(f"[FAIL] POST /api/baggage/status -> Error: {e}")
    all_success = False

print("\n" + "=" * 55)
if all_success:
    print(">>> ALL 18 PAGES AND REST ENDPOINTS PASSED VERIFICATION! <<<")
else:
    print(">>> SOME CHECKS FAILED! <<<")
    sys.exit(1)
print("=" * 55)
