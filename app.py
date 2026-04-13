"""
Personal Expense Management System - Flask Backend
Token-based auth (stored in DB) — avoids Flask session/cookie issues on Mac.
"""

from flask import Flask, request, jsonify
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

# ─── Database ─────────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db()
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
    c.execute("""
        CREATE TABLE IF NOT EXISTS Tokens (
            token    TEXT PRIMARY KEY,
            user_id  INTEGER NOT NULL,
            username TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

# ─── Auth helpers ─────────────────────────────────────────────────────────────

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_token(user_id, username):
    token = secrets.token_hex(32)
    conn  = get_db()
    conn.execute("INSERT INTO Tokens (token, user_id, username) VALUES (?,?,?)",
                 (token, user_id, username))
    conn.commit()
    conn.close()
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
        conn.close()
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

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO Users (username, password) VALUES (?, ?)",
            (username, hash_password(password))
        )
        conn.commit()
        return jsonify({"message": "User registered successfully"}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Username already exists"}), 409
    finally:
        conn.close()

@app.route("/api/login", methods=["POST"])
def login():
    data     = request.get_json(force=True, silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    conn = get_db()
    user = conn.execute(
        "SELECT * FROM Users WHERE username = ? AND password = ?",
        (username, hash_password(password))
    ).fetchone()

    if not user:
        conn.close()
        return jsonify({"error": "Invalid credentials"}), 401

    conn.execute("UPDATE Users SET last_login = ? WHERE user_id = ?",
                 (datetime.now().isoformat(), user["user_id"]))
    conn.commit()
    conn.close()

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
        conn.close()
    return jsonify({"message": "Logged out"})

@app.route("/api/me", methods=["GET"])
@login_required
def me():
    conn = get_db()
    user = conn.execute("SELECT * FROM Users WHERE user_id = ?",
                        (request.user_id,)).fetchone()
    conn.close()
    return jsonify({
        "user_id":    user["user_id"],
        "username":   user["username"],
        "balance":    float(user["balance"]),
        "last_login": user["last_login"]
    })

# ─── Transaction CRUD ─────────────────────────────────────────────────────────

@app.route("/api/transactions", methods=["GET"])
@login_required
def get_transactions():
    uid        = request.user_id
    start_date = request.args.get("start_date")
    end_date   = request.args.get("end_date")
    category   = request.args.get("category")
    tx_type    = request.args.get("type")

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

    query += " ORDER BY transaction_date DESC"

    conn = get_db()
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/transactions", methods=["POST"])
@login_required
def create_transaction():
    uid  = request.user_id
    data = request.get_json(force=True, silent=True) or {}

    tx_type  = (data.get("type") or "").upper()
    category = data.get("category", "General")
    amount   = data.get("amount")
    desc     = data.get("description", "")
    tx_date  = data.get("transaction_date", datetime.now().isoformat())

    if tx_type not in ("DEBIT", "CREDIT"):
        return jsonify({"error": "Type must be DEBIT or CREDIT"}), 400
    if not amount or float(amount) <= 0:
        return jsonify({"error": "Amount must be positive"}), 400

    conn   = get_db()
    now    = datetime.now().isoformat()
    cursor = conn.execute(
        """INSERT INTO Transactions
           (user_id, type, category, amount, description, transaction_date, last_update)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (uid, tx_type, category, float(amount), desc, tx_date, now)
    )
    new_id  = cursor.lastrowid
    balance = recalculate_balance(conn, uid)
    conn.commit()
    tx = dict(conn.execute("SELECT * FROM Transactions WHERE transaction_id = ?",
                           (new_id,)).fetchone())
    conn.close()
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
        conn.close()
        return jsonify({"error": "Transaction not found"}), 404

    tx_type  = (data.get("type") or tx["type"]).upper()
    category = data.get("category", tx["category"])
    amount   = float(data.get("amount", tx["amount"]))
    desc     = data.get("description", tx["description"])
    tx_date  = data.get("transaction_date", tx["transaction_date"])

    conn.execute(
        """UPDATE Transactions SET type=?, category=?, amount=?, description=?,
           transaction_date=?, last_update=? WHERE transaction_id=?""",
        (tx_type, category, amount, desc, tx_date, datetime.now().isoformat(), tid)
    )
    balance = recalculate_balance(conn, uid)
    conn.commit()
    updated = dict(conn.execute("SELECT * FROM Transactions WHERE transaction_id = ?",
                                (tid,)).fetchone())
    conn.close()
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
        conn.close()
        return jsonify({"error": "Transaction not found"}), 404

    conn.execute("DELETE FROM Transactions WHERE transaction_id = ?", (tid,))
    balance = recalculate_balance(conn, uid)
    conn.commit()
    conn.close()
    return jsonify({"message": "Transaction deleted", "balance": balance})

# ─── Summary & Analytics ──────────────────────────────────────────────────────

@app.route("/api/summary", methods=["GET"])
@login_required
def summary():
    uid   = request.user_id
    month = request.args.get("month")
    conn  = get_db()

    if month:
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

    conn.close()
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
    conn.close()
    return jsonify({"balance": float(user["balance"]), "username": user["username"]})

@app.route("/api/categories", methods=["GET"])
@login_required
def get_categories():
    conn = get_db()
    rows = conn.execute(
        "SELECT DISTINCT category FROM Transactions WHERE user_id=? ORDER BY category",
        (request.user_id,)
    ).fetchall()
    conn.close()
    return jsonify([r["category"] for r in rows])

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

Category rules: groceries/food→Groceries, salary/income→CREDIT+Salary, rent/utilities→Housing,
transport/uber/gas→Transport, restaurant/coffee→Food & Dining, movies/games→Entertainment,
shopping/clothes→Shopping, health/gym→Health. Default→General.

Return ONLY the JSON object, nothing else."""

@app.route("/api/llm", methods=["POST"])
@login_required
def llm_endpoint():
    uid          = request.user_id
    data         = request.get_json(force=True, silent=True) or {}
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({"error": "No message provided"}), 400

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

    llm_resp = call_ollama(build_llm_prompt(user_message, context))

    if "__OLLAMA_ERROR__" in llm_resp:
        conn.close()
        return jsonify({"error": f"LLM unavailable: {llm_resp}"}), 503

    try:
        clean  = re.sub(r"```json|```", "", llm_resp).strip()
        match  = re.search(r"\{.*\}", clean, re.DOTALL)
        if not match:
            raise ValueError("No JSON found")
        parsed = json.loads(match.group())
    except Exception as e:
        conn.close()
        return jsonify({
            "action":  "UNKNOWN",
            "message": "I couldn't understand that. Try: 'Add $50 grocery expense'.",
        })

    action = parsed.get("action", "UNKNOWN")
    result = {"action": action, "message": parsed.get("message", "")}

    if action == "CREATE":
        now     = datetime.now().isoformat()
        tx_date = parsed.get("transaction_date", datetime.now().strftime("%Y-%m-%d"))
        cursor  = conn.execute(
            "INSERT INTO Transactions (user_id,type,category,amount,description,transaction_date,last_update) VALUES (?,?,?,?,?,?,?)",
            (uid, parsed["type"], parsed.get("category","General"),
             float(parsed["amount"]), parsed.get("description",""), tx_date, now)
        )
        balance = recalculate_balance(conn, uid)
        conn.commit()
        tx = dict(conn.execute("SELECT * FROM Transactions WHERE transaction_id=?",
                               (cursor.lastrowid,)).fetchone())
        result["transaction"] = tx
        result["balance"]     = balance

    elif action == "READ":
        filters = parsed.get("filters", {})
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
            na = float(updates.get("amount", tx["amount"]))
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

    conn.close()
    return jsonify(result)

# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    print("✅ Database initialized")
    print("🚀 Flask API running on http://localhost:5000")
    app.run(debug=False, port=5000, use_reloader=False)
