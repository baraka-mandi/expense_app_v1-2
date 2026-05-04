"""
Personal Expense Management System - Flask Backend
Token-based auth (stored in DB) — avoids Flask session/cookie issues on Mac.
"""

from flask import Flask, request, jsonify, g
import sqlite3
import hashlib
import secrets
import os
import json
import re
import requests as http_requests
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)

@app.after_request
def add_cors(response):
    response.headers["Access-Control-Allow-Origin"]  = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Auth-Token"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    return response

@app.route("/api/<path:path>", methods=["OPTIONS"])
def options_handler(path):
    return jsonify({}), 200

DB_PATH      = os.path.join(os.path.dirname(os.path.abspath(__file__)), "expenses.db")
OLLAMA_URL   = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma3:4b"

DEFAULT_CATEGORIES = [
    ("Groceries",     "expense"),
    ("Housing",       "expense"),
    ("Transport",     "expense"),
    ("Food & Dining", "expense"),
    ("Entertainment", "expense"),
    ("Shopping",      "expense"),
    ("Health",        "expense"),
    ("Education",     "expense"),
    ("Utilities",     "expense"),
    ("General",       "expense"),
    ("Salary",        "income"),
    ("Investment",    "income"),
    ("Freelance",     "income"),
    ("Other",         "both"),
]

# ─── Database ─────────────────────────────────────────────────────────────────

def get_db():
    """Return the per-request DB connection stored in Flask g.
    Guaranteed to be closed by close_db() at request teardown."""
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

@app.teardown_appcontext
def close_db(error):
    """Always called at end of every request — closes the connection."""
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    """Run at startup outside a request context — uses a direct connection."""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys = ON")

    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS Users (
            user_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            username   VARCHAR(50) UNIQUE NOT NULL,
            password   VARCHAR(255) NOT NULL,
            balance    DECIMAL(12,2) DEFAULT 0.00,
            last_login DATETIME
        )
    """)
    c.execute("""
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
    c.execute("""
        CREATE TABLE IF NOT EXISTS Budget (
            budget_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER NOT NULL,
            name         VARCHAR(100) NOT NULL,
            limit_amount DECIMAL(12,2) NOT NULL,
            period       VARCHAR(10) CHECK(period IN ('monthly','weekly','yearly')) NOT NULL DEFAULT 'monthly',
            created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES Users(user_id)
        )
    """)
    c.execute("""
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
    c.execute("""
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
    c.execute("""
        CREATE TABLE IF NOT EXISTS Tokens (
            token    TEXT PRIMARY KEY,
            user_id  INTEGER NOT NULL,
            username TEXT NOT NULL
        )
    """)
    conn.commit()

    # Migration: add budget_id to Transactions if it predates that column.
    tx_cols = {row[1] for row in conn.execute("PRAGMA table_info(Transactions)").fetchall()}
    if "budget_id" not in tx_cols:
        conn.execute(
            "ALTER TABLE Transactions ADD COLUMN budget_id INTEGER REFERENCES Budget(budget_id)"
        )
        conn.commit()

    # Migration: fix corrupted Transactions table that points to _Budget_old
    tx_schema = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='Transactions'").fetchone()
    if tx_schema and "_Budget_old" in tx_schema[0]:
        conn.execute("PRAGMA foreign_keys = OFF")
        try:
            conn.execute("PRAGMA legacy_alter_table = ON")
        except Exception:
            pass
        conn.execute("ALTER TABLE Transactions RENAME TO _Transactions_old")
        conn.execute("""
            CREATE TABLE Transactions (
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
        conn.execute("INSERT INTO Transactions SELECT * FROM _Transactions_old")
        conn.execute("DROP TABLE _Transactions_old")
        try:
            conn.execute("PRAGMA legacy_alter_table = OFF")
        except Exception:
            pass
        conn.commit()
        conn.execute("PRAGMA foreign_keys = ON")

    # Migration: recreate Budget without the legacy 'category' column.
    budget_cols = {row[1] for row in conn.execute("PRAGMA table_info(Budget)").fetchall()}
    if "category" in budget_cols:
        conn.execute("PRAGMA foreign_keys = OFF")
        try:
            conn.execute("PRAGMA legacy_alter_table = ON")
        except Exception:
            pass
        conn.execute("ALTER TABLE Budget RENAME TO _Budget_old")
        conn.execute("""
            CREATE TABLE Budget (
                budget_id    INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER NOT NULL,
                name         VARCHAR(100) NOT NULL,
                limit_amount DECIMAL(12,2) NOT NULL,
                period       VARCHAR(10) CHECK(period IN ('monthly','weekly','yearly')) NOT NULL DEFAULT 'monthly',
                created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES Users(user_id)
            )
        """)
        conn.execute("""
            INSERT INTO Budget (budget_id, user_id, name, limit_amount, period, created_at)
            SELECT budget_id, user_id, name, limit_amount, period, created_at FROM _Budget_old
        """)
        conn.execute("DROP TABLE _Budget_old")
        conn.commit()
        try:
            conn.execute("PRAGMA legacy_alter_table = OFF")
        except Exception:
            pass
        conn.execute("PRAGMA foreign_keys = ON")

    conn.close()


def seed_default_categories(conn, user_id):
    for name, cat_type in DEFAULT_CATEGORIES:
        conn.execute(
            "INSERT OR IGNORE INTO Category (user_id, name, type) VALUES (?,?,?)",
            (user_id, name, cat_type)
        )

# ─── Validation Helpers ───────────────────────────────────────────────────────

def validate_amount(amount):
    try:
        val = float(amount)
    except (TypeError, ValueError):
        return None, "Amount must be a valid number"
    if val <= 0:
        return None, "Amount must be greater than zero"
    if val > 1_000_000:
        return None, "Amount exceeds the maximum allowed value of $1,000,000"
    return round(val, 2), None

def validate_username(username):
    if not username:
        return "Username is required"
    if len(username) < 3:
        return "Username must be at least 3 characters"
    if len(username) > 50:
        return "Username must not exceed 50 characters"
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return "Username may only contain letters, numbers, and underscores"
    return None

def validate_password(password):
    if not password:
        return "Password is required"
    if len(password) < 6:
        return "Password must be at least 6 characters"
    if len(password) > 255:
        return "Password is too long"
    return None

def validate_date(date_str):
    if not date_str:
        return date_str, None
    try:
        dt = datetime.fromisoformat(str(date_str).replace("Z", ""))
        if dt.year < 2000:
            return None, "Date must be after year 2000"
        if dt > datetime.now() + timedelta(days=365):
            return None, "Date cannot be more than 1 year in the future"
        return date_str, None
    except ValueError:
        return None, f"Invalid date format: {date_str}"

# ─── Auth Helpers ─────────────────────────────────────────────────────────────

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_token(user_id, username):
    token = secrets.token_hex(32)
    conn  = get_db()
    conn.execute("INSERT INTO Tokens (token, user_id, username) VALUES (?,?,?)",
                 (token, user_id, username))
    conn.commit()
    return token

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("X-Auth-Token", "").strip()
        if not token:
            return jsonify({"error": "Authentication required"}), 401
        conn = get_db()
        row  = conn.execute(
            "SELECT user_id, username FROM Tokens WHERE token=?", (token,)
        ).fetchone()
        if not row:
            return jsonify({"error": "Invalid or expired token"}), 401
        request.user_id  = row["user_id"]
        request.username = row["username"]
        return f(*args, **kwargs)
    return decorated

def recalculate_balance(conn, user_id):
    c = conn.cursor()
    c.execute("""
        SELECT
            COALESCE(SUM(CASE WHEN type='CREDIT' THEN amount ELSE 0 END), 0) -
            COALESCE(SUM(CASE WHEN type='DEBIT'  THEN amount ELSE 0 END), 0)
        FROM Transactions WHERE user_id = ?
    """, (user_id,))
    balance = float(c.fetchone()[0])
    c.execute("UPDATE Users SET balance = ? WHERE user_id = ?", (balance, user_id))
    return balance

# ─── Auth Endpoints ───────────────────────────────────────────────────────────

@app.route("/api/register", methods=["POST"])
def register():
    data     = request.get_json(force=True, silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    err = validate_username(username)
    if err:
        return jsonify({"error": err}), 400
    err = validate_password(password)
    if err:
        return jsonify({"error": err}), 400

    conn = get_db()
    try:
        cursor = conn.execute(
            "INSERT INTO Users (username, password) VALUES (?, ?)",
            (username, hash_password(password))
        )
        seed_default_categories(conn, cursor.lastrowid)
        conn.commit()
        return jsonify({"message": "User registered successfully"}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Username already exists"}), 409

@app.route("/api/login", methods=["POST"])
def login():
    data     = request.get_json(force=True, silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    conn = get_db()
    user = conn.execute(
        "SELECT * FROM Users WHERE username = ? AND password = ?",
        (username, hash_password(password))
    ).fetchone()

    if not user:
        return jsonify({"error": "Invalid credentials"}), 401

    conn.execute("UPDATE Users SET last_login = ? WHERE user_id = ?",
                 (datetime.now().isoformat(), user["user_id"]))

    cat_count = conn.execute(
        "SELECT COUNT(*) FROM Category WHERE user_id=?", (user["user_id"],)
    ).fetchone()[0]
    if cat_count == 0:
        seed_default_categories(conn, user["user_id"])

    conn.commit()

    token = create_token(user["user_id"], user["username"])
    return jsonify({
        "message":  "Login successful",
        "token":    token,
        "user_id":  user["user_id"],
        "username": user["username"],
        "balance":  float(user["balance"])
    })

@app.route("/api/logout", methods=["POST"])
def logout():
    token = request.headers.get("X-Auth-Token", "").strip()
    if token:
        conn = get_db()
        conn.execute("DELETE FROM Tokens WHERE token=?", (token,))
        conn.commit()
    return jsonify({"message": "Logged out"})

@app.route("/api/me", methods=["GET"])
@login_required
def me():
    conn = get_db()
    user = conn.execute("SELECT * FROM Users WHERE user_id = ?",
                        (request.user_id,)).fetchone()
    return jsonify({
        "user_id":    user["user_id"],
        "username":   user["username"],
        "balance":    float(user["balance"]),
        "last_login": user["last_login"]
    })

# ─── Category Endpoints ───────────────────────────────────────────────────────

@app.route("/api/categories", methods=["GET"])
@login_required
def get_categories():
    cat_type = request.args.get("type")
    conn = get_db()
    if cat_type in ("income", "expense"):
        rows = conn.execute(
            "SELECT * FROM Category WHERE user_id=? AND type IN (?,?) ORDER BY name",
            (request.user_id, cat_type, "both")
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM Category WHERE user_id=? ORDER BY type, name",
            (request.user_id,)
        ).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/api/categories", methods=["POST"])
@login_required
def create_category():
    data     = request.get_json(force=True, silent=True) or {}
    name     = (data.get("name") or "").strip()
    cat_type = (data.get("type") or "expense").lower()

    if not name:
        return jsonify({"error": "Category name is required"}), 400
    if len(name) > 50:
        return jsonify({"error": "Category name must not exceed 50 characters"}), 400
    if cat_type not in ("income", "expense", "both"):
        return jsonify({"error": "Type must be 'income', 'expense', or 'both'"}), 400

    conn = get_db()
    try:
        cursor = conn.execute(
            "INSERT INTO Category (user_id, name, type) VALUES (?,?,?)",
            (request.user_id, name, cat_type)
        )
        conn.commit()
        row = dict(conn.execute("SELECT * FROM Category WHERE category_id=?",
                                (cursor.lastrowid,)).fetchone())
        return jsonify(row), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": f"Category '{name}' already exists"}), 409

@app.route("/api/categories/<int:cid>", methods=["PUT"])
@login_required
def update_category(cid):
    data = request.get_json(force=True, silent=True) or {}
    conn = get_db()
    row  = conn.execute(
        "SELECT * FROM Category WHERE category_id=? AND user_id=?",
        (cid, request.user_id)
    ).fetchone()
    if not row:
        return jsonify({"error": "Category not found"}), 404

    name     = (data.get("name") or row["name"]).strip()
    cat_type = (data.get("type") or row["type"]).lower()

    if not name:
        return jsonify({"error": "Category name is required"}), 400
    if len(name) > 50:
        return jsonify({"error": "Category name must not exceed 50 characters"}), 400
    if cat_type not in ("income", "expense", "both"):
        return jsonify({"error": "Type must be 'income', 'expense', or 'both'"}), 400

    try:
        conn.execute("UPDATE Category SET name=?, type=? WHERE category_id=?",
                     (name, cat_type, cid))
        conn.commit()
        updated = dict(conn.execute("SELECT * FROM Category WHERE category_id=?",
                                    (cid,)).fetchone())
        return jsonify(updated)
    except sqlite3.IntegrityError:
        return jsonify({"error": f"Category '{name}' already exists"}), 409

@app.route("/api/categories/<int:cid>", methods=["DELETE"])
@login_required
def delete_category(cid):
    conn = get_db()
    row  = conn.execute(
        "SELECT * FROM Category WHERE category_id=? AND user_id=?",
        (cid, request.user_id)
    ).fetchone()
    if not row:
        return jsonify({"error": "Category not found"}), 404
    conn.execute("DELETE FROM Category WHERE category_id=?", (cid,))
    conn.commit()
    return jsonify({"message": "Category deleted"})

# ─── Transaction CRUD ─────────────────────────────────────────────────────────

@app.route("/api/transactions", methods=["GET"])
@login_required
def get_transactions():
    uid        = request.user_id
    start_date = request.args.get("start_date")
    end_date   = request.args.get("end_date")
    category  = request.args.get("category")
    tx_type   = request.args.get("type")
    budget_id = request.args.get("budget_id")

    query  = "SELECT * FROM Transactions WHERE user_id = ?"
    params = [uid]

    if start_date:
        query += " AND transaction_date >= ?"; params.append(start_date)
    if end_date:
        query += " AND transaction_date <= ?"; params.append(end_date + " 23:59:59")
    if category:
        query += " AND LOWER(category) LIKE ?"; params.append(f"%{category.lower()}%")
    if tx_type:
        query += " AND type = ?"; params.append(tx_type.upper())
    if budget_id:
        query += " AND budget_id = ?"; params.append(int(budget_id))

    query += " ORDER BY transaction_date DESC"

    conn = get_db()
    rows = conn.execute(query, params).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/api/transactions", methods=["POST"])
@login_required
def create_transaction():
    uid  = request.user_id
    data = request.get_json(force=True, silent=True) or {}

    tx_type      = (data.get("type") or "").upper()
    category     = (data.get("category") or "General").strip()
    desc         = (data.get("description") or "").strip()
    tx_date      = data.get("transaction_date", datetime.now().isoformat())
    budget_id_in = data.get("budget_id")

    if tx_type not in ("DEBIT", "CREDIT"):
        return jsonify({"error": "Type must be DEBIT or CREDIT"}), 400

    amount, err = validate_amount(data.get("amount"))
    if err:
        return jsonify({"error": err}), 400

    if not category:
        return jsonify({"error": "Category is required"}), 400
    if len(category) > 50:
        return jsonify({"error": "Category name must not exceed 50 characters"}), 400
    if len(desc) > 500:
        return jsonify({"error": "Description must not exceed 500 characters"}), 400

    _, date_err = validate_date(tx_date)
    if date_err:
        return jsonify({"error": date_err}), 400

    conn      = get_db()
    budget_id = None
    if budget_id_in is not None:
        b = conn.execute(
            "SELECT budget_id FROM Budget WHERE budget_id=? AND user_id=?",
            (budget_id_in, uid)
        ).fetchone()
        if not b:
            return jsonify({"error": "Budget not found"}), 404
        budget_id = b["budget_id"]

    now    = datetime.now().isoformat()
    cursor = conn.execute(
        """INSERT INTO Transactions
           (user_id, type, category, amount, description, transaction_date, last_update, budget_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (uid, tx_type, category, amount, desc, tx_date, now, budget_id)
    )
    new_id  = cursor.lastrowid
    balance = recalculate_balance(conn, uid)
    conn.commit()
    tx = dict(conn.execute("SELECT * FROM Transactions WHERE transaction_id = ?",
                           (new_id,)).fetchone())
    return jsonify({"transaction": tx, "balance": balance}), 201

@app.route("/api/transactions/<int:tid>", methods=["PUT"])
@login_required
def update_transaction(tid):
    uid  = request.user_id
    data = request.get_json(force=True, silent=True) or {}
    conn = get_db()

    tx = conn.execute(
        "SELECT * FROM Transactions WHERE transaction_id = ? AND user_id = ?", (tid, uid)
    ).fetchone()
    if not tx:
        return jsonify({"error": "Transaction not found"}), 404

    tx_type      = (data.get("type") or tx["type"]).upper()
    category     = (data.get("category") or tx["category"] or "General").strip()
    desc         = (data.get("description") if "description" in data else (tx["description"] or ""))
    desc         = (desc or "").strip()
    tx_date      = data.get("transaction_date", tx["transaction_date"])
    budget_id_in = data.get("budget_id", tx["budget_id"])

    if tx_type not in ("DEBIT", "CREDIT"):
        return jsonify({"error": "Type must be DEBIT or CREDIT"}), 400

    if "amount" in data:
        amount, err = validate_amount(data["amount"])
        if err:
            return jsonify({"error": err}), 400
    else:
        amount = float(tx["amount"])

    if not category:
        return jsonify({"error": "Category is required"}), 400
    if len(category) > 50:
        return jsonify({"error": "Category name must not exceed 50 characters"}), 400
    if len(desc) > 500:
        return jsonify({"error": "Description must not exceed 500 characters"}), 400

    _, date_err = validate_date(tx_date)
    if date_err:
        return jsonify({"error": date_err}), 400

    budget_id = None
    if budget_id_in is not None:
        b = conn.execute(
            "SELECT budget_id FROM Budget WHERE budget_id=? AND user_id=?",
            (budget_id_in, uid)
        ).fetchone()
        if not b:
            return jsonify({"error": "Budget not found"}), 404
        budget_id = b["budget_id"]

    conn.execute(
        """UPDATE Transactions SET type=?, category=?, amount=?, description=?,
           transaction_date=?, last_update=?, budget_id=? WHERE transaction_id=?""",
        (tx_type, category, amount, desc, tx_date, datetime.now().isoformat(), budget_id, tid)
    )
    balance = recalculate_balance(conn, uid)
    conn.commit()
    updated = dict(conn.execute("SELECT * FROM Transactions WHERE transaction_id = ?",
                                (tid,)).fetchone())
    return jsonify({"transaction": updated, "balance": balance})

@app.route("/api/transactions/<int:tid>", methods=["DELETE"])
@login_required
def delete_transaction(tid):
    uid  = request.user_id
    conn = get_db()

    tx = conn.execute(
        "SELECT * FROM Transactions WHERE transaction_id = ? AND user_id = ?", (tid, uid)
    ).fetchone()
    if not tx:
        return jsonify({"error": "Transaction not found"}), 404

    conn.execute("DELETE FROM Transactions WHERE transaction_id = ?", (tid,))
    balance = recalculate_balance(conn, uid)
    conn.commit()
    return jsonify({"message": "Transaction deleted", "balance": balance})

# ─── Summary & Analytics ──────────────────────────────────────────────────────

@app.route("/api/summary", methods=["GET"])
@login_required
def summary():
    uid   = request.user_id
    month = request.args.get("month")
    conn  = get_db()

    if month:
        if not re.match(r'^\d{4}-\d{2}$', month):
            return jsonify({"error": "Month must be in YYYY-MM format"}), 400
        start = f"{month}-01"
        year, m = map(int, month.split("-"))
        end_dt  = datetime(year, m % 12 + 1, 1) if m < 12 else datetime(year + 1, 1, 1)
        end     = end_dt.strftime("%Y-%m-%d")
        rows = conn.execute(
            "SELECT * FROM Transactions WHERE user_id=? AND transaction_date>=? AND transaction_date<?",
            (uid, start, end)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM Transactions WHERE user_id=?", (uid,)).fetchall()

    total_income  = sum(r["amount"] for r in rows if r["type"] == "CREDIT")
    total_expense = sum(r["amount"] for r in rows if r["type"] == "DEBIT")
    user          = conn.execute("SELECT balance FROM Users WHERE user_id=?", (uid,)).fetchone()

    cat_totals = {}
    for r in rows:
        cat_totals.setdefault(r["category"], {"DEBIT": 0, "CREDIT": 0})
        cat_totals[r["category"]][r["type"]] += float(r["amount"])

    return jsonify({
        "total_income":      round(total_income, 2),
        "total_expense":     round(total_expense, 2),
        "net_balance":       round(total_income - total_expense, 2),
        "current_balance":   float(user["balance"]) if user else 0,
        "categories":        cat_totals,
        "transaction_count": len(rows)
    })

@app.route("/api/balance", methods=["GET"])
@login_required
def get_balance():
    conn = get_db()
    user = conn.execute("SELECT balance, username FROM Users WHERE user_id=?",
                        (request.user_id,)).fetchone()
    return jsonify({"balance": float(user["balance"]), "username": user["username"]})

# ─── Budget Endpoints ─────────────────────────────────────────────────────────

@app.route("/api/budgets", methods=["GET"])
@login_required
def get_budgets():
    uid   = request.user_id
    month = request.args.get("month", datetime.now().strftime("%Y-%m"))

    if not re.match(r'^\d{4}-\d{2}$', month):
        return jsonify({"error": "Month must be in YYYY-MM format"}), 400

    conn    = get_db()
    budgets = conn.execute(
        "SELECT * FROM Budget WHERE user_id=? ORDER BY name", (uid,)
    ).fetchall()

    year, m = map(int, month.split("-"))
    start   = f"{month}-01"
    end_dt  = datetime(year, m % 12 + 1, 1) if m < 12 else datetime(year + 1, 1, 1)
    end     = end_dt.strftime("%Y-%m-%d")

    result = []
    for b in budgets:
        spent_row = conn.execute(
            """SELECT COALESCE(SUM(amount), 0) as spent
               FROM Transactions
               WHERE user_id=? AND type='DEBIT'
               AND budget_id=?
               AND transaction_date>=? AND transaction_date<?""",
            (uid, b["budget_id"], start, end)
        ).fetchone()
        spent    = float(spent_row["spent"])
        limit    = float(b["limit_amount"])
        linked   = conn.execute(
            "SELECT COUNT(*) FROM Transactions WHERE budget_id=? AND user_id=?",
            (b["budget_id"], uid)
        ).fetchone()[0]
        row_dict = dict(b)
        row_dict["spent"]         = round(spent, 2)
        row_dict["remaining"]     = round(limit - spent, 2)
        row_dict["percentage"]    = round((spent / limit * 100) if limit > 0 else 0, 1)
        row_dict["status"]        = "over" if spent > limit else ("warning" if spent >= limit * 0.8 else "ok")
        row_dict["linked_count"]  = linked
        result.append(row_dict)

    return jsonify(result)

@app.route("/api/budgets", methods=["POST"])
@login_required
def create_budget():
    uid  = request.user_id
    data = request.get_json(force=True, silent=True) or {}

    name   = (data.get("name") or "").strip()
    period = (data.get("period") or "monthly").lower()

    if not name:
        return jsonify({"error": "Budget name is required"}), 400
    if len(name) > 100:
        return jsonify({"error": "Budget name must not exceed 100 characters"}), 400
    if period not in ("monthly", "weekly", "yearly"):
        return jsonify({"error": "Period must be 'monthly', 'weekly', or 'yearly'"}), 400

    limit_amount, err = validate_amount(data.get("limit_amount"))
    if err:
        return jsonify({"error": err}), 400

    conn   = get_db()
    cursor = conn.execute(
        "INSERT INTO Budget (user_id, name, limit_amount, period) VALUES (?,?,?,?)",
        (uid, name, limit_amount, period)
    )
    conn.commit()
    row = dict(conn.execute("SELECT * FROM Budget WHERE budget_id=?",
                            (cursor.lastrowid,)).fetchone())
    return jsonify(row), 201

@app.route("/api/budgets/<int:bid>", methods=["PUT"])
@login_required
def update_budget(bid):
    uid  = request.user_id
    data = request.get_json(force=True, silent=True) or {}
    conn = get_db()

    b = conn.execute(
        "SELECT * FROM Budget WHERE budget_id=? AND user_id=?", (bid, uid)
    ).fetchone()
    if not b:
        return jsonify({"error": "Budget not found"}), 404

    name   = (data.get("name") or b["name"]).strip()
    period = (data.get("period") or b["period"]).lower()

    if not name:
        return jsonify({"error": "Budget name is required"}), 400
    if len(name) > 100:
        return jsonify({"error": "Budget name must not exceed 100 characters"}), 400
    if period not in ("monthly", "weekly", "yearly"):
        return jsonify({"error": "Period must be 'monthly', 'weekly', or 'yearly'"}), 400

    if "limit_amount" in data:
        limit_amount, err = validate_amount(data["limit_amount"])
        if err:
            return jsonify({"error": err}), 400
    else:
        limit_amount = float(b["limit_amount"])

    conn.execute(
        "UPDATE Budget SET name=?, limit_amount=?, period=? WHERE budget_id=?",
        (name, limit_amount, period, bid)
    )
    conn.commit()
    updated = dict(conn.execute("SELECT * FROM Budget WHERE budget_id=?", (bid,)).fetchone())
    return jsonify(updated)

@app.route("/api/budgets/<int:bid>", methods=["DELETE"])
@login_required
def delete_budget(bid):
    uid  = request.user_id
    conn = get_db()
    b = conn.execute(
        "SELECT * FROM Budget WHERE budget_id=? AND user_id=?", (bid, uid)
    ).fetchone()
    if not b:
        return jsonify({"error": "Budget not found"}), 404
    conn.execute("DELETE FROM Budget WHERE budget_id=?", (bid,))
    conn.commit()
    return jsonify({"message": "Budget deleted"})

# ─── ChatLog Endpoints ────────────────────────────────────────────────────────

@app.route("/api/chat/logs", methods=["GET"])
@login_required
def get_chat_logs():
    uid = request.user_id
    try:
        limit = max(1, min(int(request.args.get("limit", 100)), 200))
    except (TypeError, ValueError):
        limit = 100

    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM ChatLog WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
        (uid, limit)
    ).fetchall()
    return jsonify(list(reversed([dict(r) for r in rows])))

@app.route("/api/chat/logs", methods=["DELETE"])
@login_required
def clear_chat_logs():
    uid  = request.user_id
    conn = get_db()
    conn.execute("DELETE FROM ChatLog WHERE user_id=?", (uid,))
    conn.commit()
    return jsonify({"message": "Chat history cleared"})

def _save_chat_log(conn, user_id, role, message, action=None):
    conn.execute(
        "INSERT INTO ChatLog (user_id, role, message, action) VALUES (?,?,?,?)",
        (user_id, role, message[:4000], action)
    )

# ─── LLM Integration ──────────────────────────────────────────────────────────

def call_ollama(prompt):
    try:
        resp = http_requests.post(OLLAMA_URL, json={
            "model":   OLLAMA_MODEL,
            "prompt":  prompt,
            "stream":  False,
            "options": {"temperature": 0.1}
        }, timeout=60)
        if resp.status_code == 200:
            return resp.json().get("response", "")
    except Exception as e:
        return f"__OLLAMA_ERROR__: {e}"
    return ""

def build_llm_prompt(user_message, context):
    today         = datetime.now().strftime("%Y-%m-%d")
    yesterday     = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    current_month = datetime.now().strftime("%Y-%m")

    return f"""You are a financial assistant that helps manage personal expenses.
Today is {today}. Yesterday was {yesterday}. Current month: {current_month}.

User's current balance: ${context.get('balance', 0):.2f}
Recent transactions (last 5):
{json.dumps(context.get('recent_transactions', []), indent=2)}

The user says: "{user_message}"

Respond with ONLY a valid JSON object (no markdown, no explanation):

1. CREATE: {{"action":"CREATE","type":"DEBIT or CREDIT","amount":number,"category":"string","description":"string","transaction_date":"YYYY-MM-DD","message":"confirmation"}}
2. READ:   {{"action":"READ","filters":{{"start_date":"YYYY-MM-DD or null","end_date":"YYYY-MM-DD or null","category":"string or null","type":"DEBIT or CREDIT or null"}},"message":"string"}}
3. UPDATE: {{"action":"UPDATE","transaction_id":number,"updates":{{"type":"optional","amount":"optional","category":"optional","description":"optional"}},"message":"string"}}
4. DELETE: {{"action":"DELETE","transaction_id":number,"message":"string"}}
5. SUMMARY:{{"action":"SUMMARY","month":"YYYY-MM or null","message":"string"}}
6. BALANCE:{{"action":"BALANCE","message":"string"}}
7. UNKNOWN:{{"action":"UNKNOWN","message":"helpful response"}}

Category rules: groceries/food->Groceries, salary/income->CREDIT+Salary, rent/utilities->Housing,
transport/uber/gas->Transport, restaurant/coffee->Food & Dining, movies/games->Entertainment,
shopping/clothes->Shopping, health/gym->Health. Default->General.

Return ONLY the JSON object, nothing else."""

@app.route("/api/llm", methods=["POST"])
@login_required
def llm_endpoint():
    uid          = request.user_id
    data         = request.get_json(force=True, silent=True) or {}
    user_message = (data.get("message") or "").strip()

    if not user_message:
        return jsonify({"error": "No message provided"}), 400
    if len(user_message) > 2000:
        return jsonify({"error": "Message must not exceed 2000 characters"}), 400

    conn   = get_db()
    user   = conn.execute("SELECT balance FROM Users WHERE user_id=?", (uid,)).fetchone()
    recent = conn.execute(
        "SELECT transaction_id, type, category, amount, description, transaction_date "
        "FROM Transactions WHERE user_id=? ORDER BY transaction_date DESC LIMIT 5",
        (uid,)
    ).fetchall()
    context = {
        "balance":             float(user["balance"]),
        "recent_transactions": [dict(r) for r in recent]
    }

    _save_chat_log(conn, uid, "user", user_message)
    conn.commit()
    # After commit, the connection holds no write lock — Ollama call won't block other writes.

    llm_resp = call_ollama(build_llm_prompt(user_message, context))

    if "__OLLAMA_ERROR__" in llm_resp:
        return jsonify({"error": f"LLM unavailable: {llm_resp}"}), 503

    try:
        clean  = re.sub(r"```json|```", "", llm_resp).strip()
        match  = re.search(r"\{.*\}", clean, re.DOTALL)
        if not match:
            raise ValueError("No JSON found")
        parsed = json.loads(match.group())
    except Exception:
        _save_chat_log(conn, uid, "assistant",
                       "I couldn't understand that. Try: 'Add $50 grocery expense'.", "UNKNOWN")
        conn.commit()
        return jsonify({
            "action":  "UNKNOWN",
            "message": "I couldn't understand that. Try: 'Add $50 grocery expense'.",
        })

    action = parsed.get("action", "UNKNOWN")
    result = {"action": action, "message": parsed.get("message", "")}

    if action == "CREATE":
        amount_val, amount_err = validate_amount(parsed.get("amount"))
        if amount_err:
            result["action"]  = "UNKNOWN"
            result["message"] = f"Invalid amount in your request: {amount_err}"
        else:
            now     = datetime.now().isoformat()
            tx_date = parsed.get("transaction_date", datetime.now().strftime("%Y-%m-%d"))
            cursor  = conn.execute(
                "INSERT INTO Transactions (user_id,type,category,amount,description,transaction_date,last_update) VALUES (?,?,?,?,?,?,?)",
                (uid, parsed["type"], parsed.get("category", "General"),
                 amount_val, parsed.get("description", ""), tx_date, now)
            )
            balance = recalculate_balance(conn, uid)
            conn.commit()
            tx = dict(conn.execute("SELECT * FROM Transactions WHERE transaction_id=?",
                                   (cursor.lastrowid,)).fetchone())
            result["transaction"] = tx
            result["balance"]     = balance

    elif action == "READ":
        filters       = parsed.get("filters", {})
        query, params = "SELECT * FROM Transactions WHERE user_id=?", [uid]
        if filters.get("start_date"):
            query += " AND transaction_date >= ?"; params.append(filters["start_date"])
        if filters.get("end_date"):
            query += " AND transaction_date <= ?"; params.append(filters["end_date"] + " 23:59:59")
        if filters.get("category"):
            query += " AND LOWER(category) LIKE ?"; params.append(f"%{filters['category'].lower()}%")
        if filters.get("type"):
            query += " AND type = ?"; params.append(filters["type"])
        query += " ORDER BY transaction_date DESC"
        rows = conn.execute(query, params).fetchall()
        result["transactions"] = [dict(r) for r in rows]
        result["count"]        = len(rows)

    elif action == "UPDATE":
        tid, updates = parsed.get("transaction_id"), parsed.get("updates", {})
        tx = conn.execute("SELECT * FROM Transactions WHERE transaction_id=? AND user_id=?",
                          (tid, uid)).fetchone()
        if tx:
            nt = updates.get("type", tx["type"]).upper()
            if "amount" in updates:
                na, aerr = validate_amount(updates["amount"])
                if aerr:
                    result["message"] = f"Invalid amount: {aerr}"
                    na = float(tx["amount"])
            else:
                na = float(tx["amount"])
            nc = updates.get("category", tx["category"])
            nd = updates.get("description", tx["description"])
            conn.execute(
                "UPDATE Transactions SET type=?,amount=?,category=?,description=?,last_update=? WHERE transaction_id=?",
                (nt, na, nc, nd, datetime.now().isoformat(), tid)
            )
            balance = recalculate_balance(conn, uid)
            conn.commit()
            result["balance"]     = balance
            result["transaction"] = dict(conn.execute(
                "SELECT * FROM Transactions WHERE transaction_id=?", (tid,)).fetchone())
        else:
            result["message"] = f"Transaction #{tid} not found."

    elif action == "DELETE":
        tid = parsed.get("transaction_id")
        tx  = conn.execute("SELECT * FROM Transactions WHERE transaction_id=? AND user_id=?",
                           (tid, uid)).fetchone()
        if tx:
            conn.execute("DELETE FROM Transactions WHERE transaction_id=?", (tid,))
            balance = recalculate_balance(conn, uid)
            conn.commit()
            result["balance"] = balance
        else:
            result["message"] = f"Transaction #{tid} not found."

    elif action == "SUMMARY":
        month    = parsed.get("month")
        user_row = conn.execute("SELECT balance FROM Users WHERE user_id=?", (uid,)).fetchone()
        if month:
            year, m = map(int, month.split("-"))
            start   = f"{month}-01"
            end_dt  = datetime(year, m % 12 + 1, 1) if m < 12 else datetime(year + 1, 1, 1)
            rows = conn.execute(
                "SELECT * FROM Transactions WHERE user_id=? AND transaction_date>=? AND transaction_date<?",
                (uid, start, end_dt.strftime("%Y-%m-%d"))
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM Transactions WHERE user_id=?", (uid,)).fetchall()
        ti = sum(r["amount"] for r in rows if r["type"] == "CREDIT")
        te = sum(r["amount"] for r in rows if r["type"] == "DEBIT")
        result["summary"] = {
            "total_income":      round(ti, 2),
            "total_expense":     round(te, 2),
            "net_balance":       round(ti - te, 2),
            "current_balance":   float(user_row["balance"]),
            "transaction_count": len(rows)
        }

    elif action == "BALANCE":
        user_row      = conn.execute("SELECT balance FROM Users WHERE user_id=?", (uid,)).fetchone()
        result["balance"] = float(user_row["balance"])

    ai_reply = result.get("message", "")
    _save_chat_log(conn, uid, "assistant", ai_reply or "Done.", action)
    conn.commit()
    return jsonify(result)

# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    print("Database initialized")
    print("Flask API running on http://localhost:5000")
    app.run(debug=False, port=5000, use_reloader=False)
