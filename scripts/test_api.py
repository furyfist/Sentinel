"""Smoke test: hits all 8 API routes and checks for valid JSON with no 500s."""
import sys
import requests

BASE = "http://127.0.0.1:8000/api"

ROUTES = [
    ("GET", "/health",           None),
    ("GET", "/incidents",        None),
    ("GET", "/incidents/1",      None),
    ("GET", "/risk/history",     None),
    ("GET", "/risk/current/3",   None),
    ("GET", "/digest/latest",    None),
    ("GET", "/digest/history",   None),
    ("GET", "/settings",         None),
    ("PUT", "/settings",         {
        "cost_spike_multiplier": 2.5,
        "pr_risk_threshold": 70,
        "agent_loop_generation_threshold": 10,
        "error_cascade_threshold": 10.0,
    }),
]

passed = 0
failed = 0

for method, path, body in ROUTES:
    url = BASE + path
    try:
        if method == "PUT":
            resp = requests.put(url, json=body, timeout=15)
        else:
            resp = requests.get(url, timeout=15)

        if resp.status_code >= 500:
            print(f" FAIL {method} {path} -> {resp.status_code}: {resp.text[:80]}")
            failed += 1
            continue

        data = resp.json()
        print(f"  OK  {method} {path} -> {resp.status_code}")
        passed += 1

    except Exception as e:
        print(f" FAIL {method} {path} -> {e}")
        failed += 1

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
