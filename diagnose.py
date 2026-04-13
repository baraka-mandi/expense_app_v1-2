"""
diagnose.py — Run this while Flask is running (python run.py in another terminal)
Usage: python diagnose.py
"""

import requests
import json

BASE = "http://127.0.0.1:5000/api"   # use 127.0.0.1 instead of localhost

print("=" * 55)
print("ExpenseIQ — Flask Network Diagnostics")
print("=" * 55)

def test(label, method, path, **kwargs):
    url = f"{BASE}{path}"
    try:
        r = requests.request(method, url, timeout=5, **kwargs)
        status = r.status_code
        body   = r.text[:120].strip()
        print(f"  {'✅' if status < 400 else '❌'} {label}")
        print(f"     {method} {url}")
        print(f"     Status: {status}")
        print(f"     Body:   {body}")
        print()
        return r
    except Exception as e:
        print(f"  ❌ {label}")
        print(f"     ERROR: {e}")
        print()
        return None

# ── 1. Plain GET (no auth) ────────────────────────
print("\n[ 1 ] Basic connectivity")
test("GET /api/register (should 405, not 403)", "GET", "/register")

# ── 2. POST with no headers ───────────────────────
print("[ 2 ] POST with no Content-Type")
test("POST /register no headers",
     "POST", "/register",
     data='{"username":"diag1","password":"pass1234"}')

# ── 3. POST with Content-Type ─────────────────────
print("[ 3 ] POST with Content-Type: application/json")
test("POST /register with content-type",
     "POST", "/register",
     headers={"Content-Type": "application/json"},
     data='{"username":"diag2","password":"pass1234"}')

# ── 4. POST with json= kwarg (sets Content-Type automatically) ───
print("[ 4 ] POST with requests json= (auto content-type)")
test("POST /register json kwarg",
     "POST", "/register",
     json={"username": "diag3", "password": "pass1234"})

# ── 5. Try localhost vs 127.0.0.1 ────────────────
print("[ 5 ] Try localhost instead of 127.0.0.1")
try:
    r = requests.post("http://localhost:5000/api/register",
                      json={"username": "diag4", "password": "pass1234"},
                      timeout=5)
    print(f"  {'✅' if r.status_code < 400 else '❌'} localhost POST")
    print(f"     Status: {r.status_code}  Body: {r.text[:120]}")
except Exception as e:
    print(f"  ❌ localhost POST failed: {e}")
print()

# ── 6. OPTIONS preflight ──────────────────────────
print("[ 6 ] OPTIONS preflight (CORS check)")
test("OPTIONS /register",
     "OPTIONS", "/register",
     headers={
         "Origin": "http://localhost:8501",
         "Access-Control-Request-Method": "POST",
         "Access-Control-Request-Headers": "Content-Type,X-Auth-Token"
     })

# ── 7. Login test ─────────────────────────────────
print("[ 7 ] Login with known user (alice/password123)")
r = test("POST /login",
         "POST", "/login",
         json={"username": "alice", "password": "password123"})
if r and r.status_code == 200:
    token = r.json().get("token", "")
    print(f"  🔑 Token received: {token[:20]}...")

    # ── 8. Authenticated request ──────────────────
    print("[ 8 ] Authenticated request with token")
    test("GET /balance with token",
         "GET", "/balance",
         headers={"X-Auth-Token": token})

print("=" * 55)
print("Paste the full output above if you need further help.")
print("=" * 55)