"""
db_test.py — Run this in the same folder as app.py to test the database.
Usage:  python db_test.py
"""

import sqlite3
import hashlib
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "expenses.db")

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

print("=" * 50)
print("ExpenseIQ — Database Test & Setup")
print("=" * 50)

# ── 1. Check DB file ──────────────────────────────
print(f"\n📁 DB path:   {DB_PATH}")
print(f"   Exists:    {os.path.exists(DB_PATH)}")
if os.path.exists(DB_PATH):
    print(f"   Size:      {os.path.getsize(DB_PATH)} bytes")
    print(f"   Writable:  {os.access(DB_PATH, os.W_OK)}")
else:
    print("   (Will be created)")

# ── 2. Connect ────────────────────────────────────
print("\n🔌 Connecting to SQLite...")
try:
    conn = get_db()
    print("   ✅ Connected")
except Exception as e:
    print(f"   ❌ Failed: {e}")
    exit(1)

# ── 3. Create tables ─────────────────────────────
print("\n🗄️  Creating tables...")
try:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS Users (
            user_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            username   VARCHAR(50) UNIQUE NOT NULL,
            password   VARCHAR(255) NOT NULL,
            balance    DECIMAL(12,2) DEFAULT 0.00,
            last_login DATETIME
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS Transactions (
            transaction_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id          INTEGER NOT NULL,
            type             VARCHAR(10) CHECK(type IN ('DEBIT','CREDIT')) NOT NULL,
            category         VARCHAR(50),
            amount           DECIMAL(12,2) NOT NULL,
            description      TEXT,
            transaction_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_update      DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES Users(user_id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS Tokens (
            token    TEXT PRIMARY KEY,
            user_id  INTEGER NOT NULL,
            username TEXT NOT NULL
        )
    """)
    conn.commit()
    print("   ✅ Tables ready")
except Exception as e:
    print(f"   ❌ Failed: {e}")
    exit(1)

# ── 4. List existing users ────────────────────────
print("\n👥 Existing users:")
users = conn.execute("SELECT user_id, username, balance FROM Users").fetchall()
if users:
    for u in users:
        print(f"   [{u['user_id']}] {u['username']}  balance=${u['balance']:.2f}")
else:
    print("   (none)")

# ── 5. Create test users ──────────────────────────
test_users = [
    ("alice", "password123"),
    ("bob",   "password123"),
]

print("\n➕ Creating test users...")
for username, password in test_users:
    try:
        conn.execute(
            "INSERT INTO Users (username, password) VALUES (?, ?)",
            (username, hash_password(password))
        )
        conn.commit()
        print(f"   ✅ Created:  {username}  /  {password}")
    except sqlite3.IntegrityError:
        print(f"   ⚠️  Already exists: {username}")

# ── 6. Verify login works ─────────────────────────
print("\n🔐 Testing login for 'alice'...")
user = conn.execute(
    "SELECT * FROM Users WHERE username=? AND password=?",
    ("alice", hash_password("password123"))
).fetchone()
if user:
    print(f"   ✅ Login OK — user_id={user['user_id']}, balance=${user['balance']:.2f}")
else:
    print("   ❌ Login failed — password hash mismatch")

# ── 7. Write permission test ──────────────────────
print("\n✏️  Write permission test...")
try:
    conn.execute("INSERT INTO Tokens (token, user_id, username) VALUES (?,?,?)",
                 ("test_token_abc123", 1, "alice"))
    conn.commit()
    conn.execute("DELETE FROM Tokens WHERE token=?", ("test_token_abc123",))
    conn.commit()
    print("   ✅ Read/write working")
except Exception as e:
    print(f"   ❌ Write failed: {e}")

# ── 8. Final summary ──────────────────────────────
print("\n📊 Final user list:")
users = conn.execute("SELECT user_id, username, balance FROM Users").fetchall()
for u in users:
    print(f"   [{u['user_id']}] {u['username']}  balance=${u['balance']:.2f}")

conn.close()
print("\n✅ Done. If all checks passed, the database is working correctly.")
print("   You can log in with:  alice / password123")
print("=" * 50)