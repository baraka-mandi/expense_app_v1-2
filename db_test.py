"""
db_test.py — Run this in the same folder as app.py to verify and set up the database.
Usage:  python db_test.py
"""

import sqlite3
import hashlib
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "expenses.db")

PASS_MARK = "  PASS"
FAIL_MARK = "  FAIL"

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def section(title):
    print(f"\n{'─' * 55}")
    print(f"  {title}")
    print(f"{'─' * 55}")

def check(label, condition, detail=""):
    mark = PASS_MARK if condition else FAIL_MARK
    print(f"{mark}  {label}")
    if detail:
        print(f"         {detail}")
    return condition

print("=" * 55)
print("  Expense Tracker — Database Test")
print("=" * 55)

# ── 1. File check ──────────────────────────────────────
section("1. Database File")
print(f"   Path:     {DB_PATH}")
exists   = os.path.exists(DB_PATH)
writable = os.access(DB_PATH, os.W_OK) if exists else os.access(os.path.dirname(DB_PATH), os.W_OK)
check("DB file accessible", True)
if exists:
    print(f"   Size:     {os.path.getsize(DB_PATH):,} bytes")
check("DB path is writable", writable)

# ── 2. Connection ──────────────────────────────────────
section("2. Connection")
try:
    conn = get_db()
    check("SQLite connection opened", True)
except Exception as e:
    check("SQLite connection opened", False, str(e))
    print("\nCannot continue without a database connection.")
    exit(1)

# ── 3. Create / verify all tables ─────────────────────
section("3. Schema — Create Tables")

conn.execute("""
    CREATE TABLE IF NOT EXISTS Users (
        user_id    INTEGER PRIMARY KEY AUTOINCREMENT,
        username   VARCHAR(50) UNIQUE NOT NULL,
        email      VARCHAR(100),
        password   VARCHAR(255) NOT NULL,
        balance    DECIMAL(12,2) DEFAULT 0.00,
        last_login DATETIME
    )
""")

conn.execute("""
    CREATE TABLE IF NOT EXISTS Category (
        category_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     INTEGER NOT NULL,
        name        VARCHAR(50) NOT NULL,
        type        VARCHAR(10) CHECK(type IN ('income','expense','both')) NOT NULL DEFAULT 'expense',
        created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, name),
        FOREIGN KEY (user_id) REFERENCES Users(user_id)
    )
""")

conn.execute("""
    CREATE TABLE IF NOT EXISTS Budget (
        budget_id    INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id      INTEGER NOT NULL,
        name         VARCHAR(100) NOT NULL,
        category     VARCHAR(50) NOT NULL,
        limit_amount DECIMAL(12,2) NOT NULL,
        period       VARCHAR(10) CHECK(period IN ('monthly','weekly','yearly')) NOT NULL DEFAULT 'monthly',
        created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES Users(user_id)
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
        budget_id        INTEGER REFERENCES Budget(budget_id),
        FOREIGN KEY (user_id) REFERENCES Users(user_id)
    )
""")

conn.execute("""
    CREATE TABLE IF NOT EXISTS ChatLog (
        log_id     INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    INTEGER NOT NULL,
        role       VARCHAR(10) CHECK(role IN ('user','assistant')) NOT NULL,
        message    TEXT NOT NULL,
        action     VARCHAR(20),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
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

conn.execute("""
    CREATE TABLE IF NOT EXISTS ResetTokens (
        token      TEXT PRIMARY KEY,
        user_id    INTEGER NOT NULL,
        expires_at DATETIME NOT NULL,
        FOREIGN KEY (user_id) REFERENCES Users(user_id)
    )
""")

conn.commit()

tables = {r[0] for r in conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table'"
).fetchall()}

for tbl in ("Users", "Category", "Transactions", "Budget", "ChatLog", "Tokens", "ResetTokens"):
    check(f"Table '{tbl}' exists", tbl in tables)

# ── 4. Foreign key enforcement ─────────────────────────
section("4. Constraints — Foreign Keys")
fk_status = conn.execute("PRAGMA foreign_keys").fetchone()[0]
check("PRAGMA foreign_keys = ON", fk_status == 1, f"value={fk_status}")

try:
    conn.execute("INSERT INTO Transactions (user_id,type,amount) VALUES (999999,'DEBIT',1.00)")
    conn.commit()
    check("FK violation rejected (user_id=999999)", False, "Expected IntegrityError but got none")
    conn.execute("DELETE FROM Transactions WHERE user_id=999999")
    conn.commit()
except sqlite3.IntegrityError:
    check("FK violation rejected (user_id=999999)", True)

# ── 5. Category type CHECK constraint ─────────────────
section("5. Constraints — CHECK on Category.type")
try:
    conn.execute("INSERT INTO Category (user_id, name, type) VALUES (1,'BadType','invalid')")
    conn.commit()
    check("CHECK rejects invalid Category.type", False)
    conn.execute("DELETE FROM Category WHERE name='BadType'")
    conn.commit()
except sqlite3.IntegrityError:
    check("CHECK rejects invalid Category.type", True)

# ── 6. Seed test users ─────────────────────────────────
section("6. Users — Create Test Accounts")

DEFAULT_CATEGORIES = [
    ("Groceries","expense"), ("Housing","expense"), ("Transport","expense"),
    ("Food & Dining","expense"), ("Entertainment","expense"), ("Shopping","expense"),
    ("Health","expense"), ("Education","expense"), ("Utilities","expense"),
    ("General","expense"), ("Salary","income"), ("Investment","income"),
    ("Freelance","income"), ("Other","both"),
]

test_users = [("alice", "password123"), ("bob", "password123")]
created_ids = {}

for username, password in test_users:
    try:
        cur = conn.execute(
            "INSERT INTO Users (username, password) VALUES (?, ?)",
            (username, hash_password(password))
        )
        uid = cur.lastrowid
        for name, ctype in DEFAULT_CATEGORIES:
            conn.execute(
                "INSERT OR IGNORE INTO Category (user_id, name, type) VALUES (?,?,?)",
                (uid, name, ctype)
            )
        conn.commit()
        created_ids[username] = uid
        check(f"Created user '{username}' (id={uid}) with default categories", True)
    except sqlite3.IntegrityError:
        row = conn.execute("SELECT user_id FROM Users WHERE username=?", (username,)).fetchone()
        created_ids[username] = row["user_id"]
        check(f"User '{username}' already exists (id={row['user_id']})", True)

# ── 7. Login verification ──────────────────────────────
section("7. Authentication — Password Hash")

user = conn.execute(
    "SELECT * FROM Users WHERE username=? AND password=?",
    ("alice", hash_password("password123"))
).fetchone()
check("alice login with correct password", user is not None,
      f"user_id={user['user_id']}" if user else "")

bad = conn.execute(
    "SELECT * FROM Users WHERE username=? AND password=?",
    ("alice", hash_password("wrongpassword"))
).fetchone()
check("alice login with wrong password rejected", bad is None)

# ── 8. Transactions CRUD ───────────────────────────────
section("8. Transactions — CRUD")

uid = created_ids.get("alice", 1)
now = datetime.now().isoformat()

cur = conn.execute(
    "INSERT INTO Transactions (user_id,type,category,amount,description,transaction_date,last_update) "
    "VALUES (?,?,?,?,?,?,?)",
    (uid, "CREDIT", "Salary", 3000.00, "Monthly salary", now, now)
)
salary_id = cur.lastrowid
conn.commit()
check("Insert CREDIT transaction", salary_id is not None, f"id={salary_id}")

cur = conn.execute(
    "INSERT INTO Transactions (user_id,type,category,amount,description,transaction_date,last_update) "
    "VALUES (?,?,?,?,?,?,?)",
    (uid, "DEBIT", "Groceries", 85.50, "Weekly groceries", now, now)
)
grocery_id = cur.lastrowid
conn.commit()
check("Insert DEBIT transaction", grocery_id is not None, f"id={grocery_id}")

conn.execute("UPDATE Transactions SET amount=90.00 WHERE transaction_id=?", (grocery_id,))
conn.commit()
updated = conn.execute("SELECT amount FROM Transactions WHERE transaction_id=?",
                       (grocery_id,)).fetchone()
check("Update transaction amount", float(updated["amount"]) == 90.00,
      f"amount={updated['amount']}")

rows = conn.execute("SELECT * FROM Transactions WHERE user_id=? ORDER BY transaction_date DESC",
                    (uid,)).fetchall()
check("Read transactions for alice", len(rows) >= 2, f"count={len(rows)}")

conn.execute("DELETE FROM Transactions WHERE transaction_id=?", (grocery_id,))
conn.commit()
gone = conn.execute("SELECT * FROM Transactions WHERE transaction_id=?",
                    (grocery_id,)).fetchone()
check("Delete transaction", gone is None)

# ── 9. Category CRUD ───────────────────────────────────
section("9. Category — CRUD")

uid = created_ids.get("alice", 1)

cur = conn.execute(
    "INSERT OR IGNORE INTO Category (user_id, name, type) VALUES (?,?,?)",
    (uid, "Subscriptions", "expense")
)
conn.commit()
cat = conn.execute(
    "SELECT * FROM Category WHERE user_id=? AND name='Subscriptions'", (uid,)
).fetchone()
check("Insert custom category 'Subscriptions'", cat is not None,
      f"id={cat['category_id']}" if cat else "")

conn.execute("UPDATE Category SET name='Streaming' WHERE category_id=?",
             (cat["category_id"],))
conn.commit()
updated_cat = conn.execute("SELECT name FROM Category WHERE category_id=?",
                           (cat["category_id"],)).fetchone()
check("Update category name to 'Streaming'", updated_cat["name"] == "Streaming")

all_cats = conn.execute("SELECT * FROM Category WHERE user_id=?", (uid,)).fetchall()
check("Read all categories for alice", len(all_cats) >= 1, f"count={len(all_cats)}")

expense_cats = conn.execute(
    "SELECT * FROM Category WHERE user_id=? AND type IN ('expense','both')", (uid,)
).fetchall()
check("Filter categories by type=expense", len(expense_cats) >= 1,
      f"count={len(expense_cats)}")

conn.execute("DELETE FROM Category WHERE category_id=?", (cat["category_id"],))
conn.commit()
gone_cat = conn.execute("SELECT * FROM Category WHERE category_id=?",
                        (cat["category_id"],)).fetchone()
check("Delete category 'Streaming'", gone_cat is None)

conn.execute(
    "INSERT OR IGNORE INTO Category (user_id, name, type) VALUES (?,?,?)",
    (uid, "UniqueTest", "expense")
)
conn.commit()
try:
    conn.execute(
        "INSERT INTO Category (user_id, name, type) VALUES (?,?,?)",
        (uid, "UniqueTest", "expense")
    )
    conn.commit()
    check("UNIQUE constraint on (user_id, name) enforced", False)
except sqlite3.IntegrityError:
    check("UNIQUE constraint on (user_id, name) enforced", True)
finally:
    conn.execute("DELETE FROM Category WHERE user_id=? AND name='UniqueTest'", (uid,))
    conn.commit()

# ── 10. Budget CRUD ────────────────────────────────────
section("10. Budget — CRUD")

uid = created_ids.get("alice", 1)

cur = conn.execute(
    "INSERT INTO Budget (user_id, name, category, limit_amount, period) VALUES (?,?,?,?,?)",
    (uid, "Monthly Groceries", "Groceries", 300.00, "monthly")
)
budget_id = cur.lastrowid
conn.commit()
check("Insert budget", budget_id is not None, f"id={budget_id}")

b = conn.execute("SELECT * FROM Budget WHERE budget_id=?", (budget_id,)).fetchone()
check("Read budget", b is not None and float(b["limit_amount"]) == 300.00,
      f"limit={b['limit_amount']}" if b else "")

conn.execute("UPDATE Budget SET limit_amount=350.00 WHERE budget_id=?", (budget_id,))
conn.commit()
updated_b = conn.execute("SELECT limit_amount FROM Budget WHERE budget_id=?",
                         (budget_id,)).fetchone()
check("Update budget limit to $350", float(updated_b["limit_amount"]) == 350.00)

try:
    conn.execute(
        "INSERT INTO Budget (user_id, name, category, limit_amount, period) VALUES (?,?,?,?,?)",
        (uid, "Bad Budget", "Groceries", 100.00, "invalid_period")
    )
    conn.commit()
    check("CHECK rejects invalid Budget.period", False)
    conn.execute("DELETE FROM Budget WHERE name='Bad Budget'")
    conn.commit()
except sqlite3.IntegrityError:
    check("CHECK rejects invalid Budget.period", True)

conn.execute("DELETE FROM Budget WHERE budget_id=?", (budget_id,))
conn.commit()
gone_b = conn.execute("SELECT * FROM Budget WHERE budget_id=?", (budget_id,)).fetchone()
check("Delete budget", gone_b is None)

# ── 11. ChatLog CRUD ───────────────────────────────────
section("11. ChatLog — CRUD")

uid = created_ids.get("alice", 1)

conn.execute(
    "INSERT INTO ChatLog (user_id, role, message, action) VALUES (?,?,?,?)",
    (uid, "user", "Add a $50 grocery expense", None)
)
conn.execute(
    "INSERT INTO ChatLog (user_id, role, message, action) VALUES (?,?,?,?)",
    (uid, "assistant", "Added $50.00 expense in Groceries. New balance: $2910.00", "CREATE")
)
conn.commit()
logs = conn.execute(
    "SELECT * FROM ChatLog WHERE user_id=? ORDER BY created_at", (uid,)
).fetchall()
check("Insert and read chat log entries", len(logs) >= 2, f"count={len(logs)}")
check("User message recorded", any(r["role"] == "user" for r in logs))
check("Assistant message recorded", any(r["role"] == "assistant" for r in logs))

try:
    conn.execute(
        "INSERT INTO ChatLog (user_id, role, message) VALUES (?,?,?)",
        (uid, "system", "This role is not allowed")
    )
    conn.commit()
    check("CHECK rejects invalid ChatLog.role", False)
    conn.execute("DELETE FROM ChatLog WHERE role='system'")
    conn.commit()
except sqlite3.IntegrityError:
    check("CHECK rejects invalid ChatLog.role", True)

conn.execute("DELETE FROM ChatLog WHERE user_id=?", (uid,))
conn.commit()
cleared = conn.execute("SELECT COUNT(*) FROM ChatLog WHERE user_id=?", (uid,)).fetchone()[0]
check("Clear all chat logs for user", cleared == 0)

# ── 12. Token write/delete ─────────────────────────────
section("12. Tokens — Read/Write")

try:
    conn.execute("INSERT INTO Tokens (token, user_id, username) VALUES (?,?,?)",
                 ("test_token_abc123", 1, "alice"))
    conn.commit()
    conn.execute("DELETE FROM Tokens WHERE token=?", ("test_token_abc123",))
    conn.commit()
    check("Token insert and delete", True)
except Exception as e:
    check("Token insert and delete", False, str(e))

# ── 13. Summary query ──────────────────────────────────
section("13. Analytics — Balance Recalculation Query")

uid = created_ids.get("alice", 1)
row = conn.execute("""
    SELECT
        COALESCE(SUM(CASE WHEN type='CREDIT' THEN amount ELSE 0 END), 0) AS total_income,
        COALESCE(SUM(CASE WHEN type='DEBIT'  THEN amount ELSE 0 END), 0) AS total_expense,
        COALESCE(SUM(CASE WHEN type='CREDIT' THEN amount ELSE 0 END), 0) -
        COALESCE(SUM(CASE WHEN type='DEBIT'  THEN amount ELSE 0 END), 0) AS net
    FROM Transactions WHERE user_id=?
""", (uid,)).fetchone()
check("Balance aggregation query executes",
      row is not None,
      f"income=${row['total_income']:.2f}, expenses=${row['total_expense']:.2f}, net=${row['net']:.2f}")

# ── 14. Final table summary ────────────────────────────
section("14. Final State")
for tbl in ("Users", "Category", "Transactions", "Budget", "ChatLog", "Tokens", "ResetTokens"):
    count = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
    print(f"   {tbl:<16} {count:>4} row(s)")

conn.close()

print()
print("=" * 55)
print("  Done. Log in with:  alice / password123")
print("=" * 55)
