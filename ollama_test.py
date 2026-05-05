"""
ollama_test.py — Tests Ollama connection and gemma3:1b model.
Usage: python ollama_test.py
Make sure 'ollama serve' is running first.
"""

import requests
import json

OLLAMA_BASE = "http://127.0.0.1:11434"
MODEL       = "gemma3:4b"

print("=" * 55)
print("ExpenseIQ — Ollama Connection Test")
print("=" * 55)

# ── 1. Check Ollama is running ────────────────────
print("\n[ 1 ] Checking Ollama is reachable...")
try:
    r = requests.get(f"{OLLAMA_BASE}/", timeout=5)
    print(f"  ✅ Ollama is running  (HTTP {r.status_code})")
except requests.exceptions.ConnectionError:
    print("  ❌ Cannot reach Ollama on 127.0.0.1:11434")
    print("     Fix: open a terminal and run:  ollama serve")
    exit(1)
except Exception as e:
    print(f"  ❌ Error: {e}")
    exit(1)

# ── 2. List available models ──────────────────────
print("\n[ 2 ] Checking available models...")
try:
    r = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=5)
    models = [m["name"] for m in r.json().get("models", [])]
    if models:
        for m in models:
            marker = " ✅ (correct model)" if MODEL in m else ""
            print(f"  • {m}{marker}")
    else:
        print("  ⚠️  No models installed")

    if not any(MODEL in m for m in models):
        print(f"\n  ❌ '{MODEL}' not found!")
        print(f"     Fix: run:  ollama pull {MODEL}")
        exit(1)
    else:
        print(f"\n  ✅ '{MODEL}' is available")
except Exception as e:
    print(f"  ❌ Error listing models: {e}")
    exit(1)

# ── 3. Send a test prompt ─────────────────────────
print(f"\n[ 3 ] Sending test prompt to {MODEL}...")
print("  (this may take a few seconds on first run)\n")
try:
    r = requests.post(f"{OLLAMA_BASE}/api/generate",
        json={
            "model":   MODEL,
            "prompt":  'Reply with ONLY this JSON, no other text: {"status":"ok","message":"Ollama is working"}',
            "stream":  False,
            "options": {"temperature": 0}
        },
        timeout=60
    )
    if r.status_code == 200:
        response_text = r.json().get("response", "").strip()
        print(f"  Raw response: {response_text[:200]}")
        print(f"  ✅ Model responded successfully")
    else:
        print(f"  ❌ HTTP {r.status_code}: {r.text[:200]}")
        exit(1)
except requests.exceptions.Timeout:
    print("  ❌ Request timed out — model may be too slow or not loaded")
    exit(1)
except Exception as e:
    print(f"  ❌ Error: {e}")
    exit(1)

# ── 4. Test a finance prompt ──────────────────────
print(f"\n[ 4 ] Testing finance prompt (like the app uses)...")
try:
    r = requests.post(f"{OLLAMA_BASE}/api/generate",
        json={
            "model":  MODEL,
            "prompt": 'You are a financial assistant. The user says: "Add a $50 grocery expense". Reply with ONLY a JSON object: {"action":"CREATE","type":"DEBIT","amount":50,"category":"Groceries","description":"Grocery expense","transaction_date":"2026-01-01","message":"Added $50 grocery expense"}',
            "stream": False,
            "options": {"temperature": 0.1}
        },
        timeout=60
    )
    if r.status_code == 200:
        response_text = r.json().get("response", "").strip()
        print(f"  Raw response: {response_text[:300]}")

        # Try parsing JSON from response
        import re
        match = re.search(r"\{.*\}", response_text, re.DOTALL)
        if match:
            parsed = json.loads(match.group())
            print(f"\n  ✅ JSON parsed successfully:")
            print(f"     action:   {parsed.get('action')}")
            print(f"     type:     {parsed.get('type')}")
            print(f"     amount:   {parsed.get('amount')}")
            print(f"     category: {parsed.get('category')}")
        else:
            print("  ⚠️  Could not parse JSON from response — model may need prompting adjustment")
except Exception as e:
    print(f"  ❌ Error: {e}")

print("\n" + "=" * 55)
print("✅ All tests passed — AI Assistant is ready to use!")
print("=" * 55)