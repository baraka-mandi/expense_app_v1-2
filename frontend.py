"""
Personal Expense Management System - Streamlit Frontend
"""

import streamlit as st
import requests
import pandas as pd
import re
from datetime import datetime, timedelta

API     = "http://127.0.0.1:5000/api"
SESSION = requests.Session()

# ─── Page Config ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="ExpenseIQ",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── Custom CSS ───────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');

:root {
    --bg:       #0a0e1a;
    --bg2:      #111827;
    --bg3:      #1a2236;
    --accent:   #6ee7b7;
    --accent2:  #3b82f6;
    --danger:   #f87171;
    --warning:  #fbbf24;
    --text:     #e2e8f0;
    --muted:    #64748b;
    --border:   #1e293b;
    --card-bg:  #111827;
}

html, body, [class*="css"] {
    font-family: 'Space Grotesk', sans-serif;
    background: var(--bg);
    color: var(--text);
}

.stApp { background: var(--bg); }

.block-container { padding-top: 1.5rem; max-width: 1400px; }

/* ── Hide Streamlit default UI elements ── */
#MainMenu                          { visibility: hidden; }
footer                             { visibility: hidden; }
header                             { visibility: hidden; }
[data-testid="stToolbar"]          { display: none !important; }
[data-testid="stDecoration"]       { display: none !important; }
[data-testid="stStatusWidget"]     { display: none !important; }
[data-testid="stDeployButton"]     { display: none !important; }
.stDeployButton                    { display: none !important; }

.metric-card {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 1.25rem 1.5rem;
    position: relative;
    overflow: hidden;
}
.metric-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 4px; height: 100%;
    background: var(--accent);
    border-radius: 4px 0 0 4px;
}
.metric-card.danger::before { background: var(--danger); }
.metric-card.blue::before   { background: var(--accent2); }
.metric-label { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.1em; color: var(--muted); margin-bottom: 0.4rem; }
.metric-value { font-size: 2rem; font-weight: 700; color: var(--text); font-family: 'DM Mono', monospace; }
.metric-value.positive { color: var(--accent); }
.metric-value.negative { color: var(--danger); }

.tx-row {
    background: var(--bg3);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1rem 1.25rem;
    margin-bottom: 0.5rem;
    display: flex;
    align-items: center;
    gap: 1rem;
    transition: border-color 0.2s;
}
.tx-row:hover { border-color: var(--accent); }
.tx-badge {
    padding: 0.25rem 0.75rem;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.05em;
}
.tx-badge.credit { background: rgba(110,231,183,0.15); color: var(--accent); }
.tx-badge.debit  { background: rgba(248,113,113,0.15); color: var(--danger); }

.chat-msg {
    padding: 0.9rem 1.2rem;
    border-radius: 14px;
    margin-bottom: 0.75rem;
    line-height: 1.6;
    font-size: 0.95rem;
}
.chat-user {
    background: linear-gradient(135deg, #1e3a5f, #1a3354);
    border: 1px solid rgba(59,130,246,0.3);
    border-radius: 14px 14px 4px 14px;
    margin-left: 3rem;
}
.chat-ai {
    background: var(--bg3);
    border: 1px solid var(--border);
    border-radius: 14px 14px 14px 4px;
    margin-right: 3rem;
}
.chat-ai-header {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: var(--accent);
    font-weight: 600;
    margin-bottom: 0.4rem;
}

section[data-testid="stSidebar"] {
    background: var(--bg2) !important;
    border-right: 1px solid var(--border);
}
section[data-testid="stSidebar"] .block-container { padding: 1.5rem 1rem; }

h1, h2, h3 { font-family: 'Space Grotesk', sans-serif !important; color: var(--text) !important; }

.stButton > button {
    background: var(--accent) !important;
    color: #0a0e1a !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-family: 'Space Grotesk', sans-serif !important;
    transition: all 0.2s !important;
}
.stButton > button:hover { opacity: 0.85 !important; transform: translateY(-1px) !important; }

.stTextInput input, .stSelectbox select, .stNumberInput input, .stDateInput input {
    background: var(--bg3) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    color: var(--text) !important;
    font-family: 'Space Grotesk', sans-serif !important;
}

.stTabs [data-baseweb="tab-list"] { background: var(--bg2); border-radius: 12px; padding: 4px; gap: 4px; }
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: var(--muted) !important;
    border-radius: 8px !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 500 !important;
}
.stTabs [aria-selected="true"] {
    background: var(--bg3) !important;
    color: var(--text) !important;
}

hr { border-color: var(--border) !important; }

.logo {
    font-size: 1.6rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.25rem;
}
.logo-sub { font-size: 0.75rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.15em; }

.section-header {
    font-size: 1.1rem;
    font-weight: 600;
    color: var(--text);
    border-bottom: 1px solid var(--border);
    padding-bottom: 0.75rem;
    margin-bottom: 1rem;
}

.budget-bar-bg {
    background: var(--bg2);
    border-radius: 4px;
    height: 8px;
    overflow: hidden;
    margin-top: 0.4rem;
}
</style>
""", unsafe_allow_html=True)

# ─── API Helpers ──────────────────────────────────────────────────────────────

def api(method: str, path: str, **kwargs):
    headers = kwargs.pop("headers", {})
    headers["Content-Type"] = "application/json"
    if st.session_state.get("token"):
        headers["X-Auth-Token"] = st.session_state.token
    try:
        r = SESSION.request(method, f"{API}{path}", headers=headers, timeout=90, **kwargs)
        if not r.content or not r.content.strip():
            return {"error": f"Empty response from Flask (HTTP {r.status_code})"}, r.status_code
        try:
            return r.json(), r.status_code
        except ValueError:
            return {"error": f"Flask returned non-JSON (HTTP {r.status_code}): {r.text[:300]}"}, r.status_code
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to Flask on port 5000. Is it running?"}, 503
    except Exception as e:
        return {"error": str(e)}, 500

def fmt_date(d):
    if not d:
        return "-"
    try:
        return datetime.fromisoformat(d.replace("Z", "")).strftime("%b %d, %Y")
    except Exception:
        return str(d)[:10]

def get_user_categories(cat_type=None):
    path = "/categories"
    if cat_type:
        path += f"?type={cat_type}"
    data, code = api("GET", path)
    if code == 200 and isinstance(data, list):
        return [c["name"] for c in data]
    return ["General", "Groceries", "Housing", "Transport", "Food & Dining",
            "Entertainment", "Shopping", "Health", "Education", "Utilities",
            "Salary", "Investment", "Other"]

def validate_username_input(username):
    if not username:
        return "Username is required"
    if len(username) < 3:
        return "Username must be at least 3 characters"
    if len(username) > 50:
        return "Username must not exceed 50 characters"
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return "Username may only contain letters, numbers, and underscores"
    return None

# ─── Session State ────────────────────────────────────────────────────────────

for _k, _v in [
    ("logged_in",    False),
    ("token",        ""),
    ("user_id",      None),
    ("username",     ""),
    ("balance",      0.0),
    ("chat_history", []),
    ("chat_loaded",  False),
    ("active_tab",   "dashboard"),
]:
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ─── Auth Page ────────────────────────────────────────────────────────────────

def auth_page():
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("""
        <div style='text-align:center; padding: 2rem 0 1rem;'>
            <div class='logo'>Expense Tracker</div>
            <div class='logo-sub'>Personal Finance Intelligence</div>
        </div>
        """, unsafe_allow_html=True)

        tab_login, tab_register, tab_forgot = st.tabs(["  Sign In  ", "  Create Account  ", "  Forgot Password  "])

        with tab_login:
            st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
            username = st.text_input("Username", key="login_user", placeholder="Enter your username")
            password = st.text_input("Password", type="password", key="login_pass", placeholder="Enter your password")
            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
            if st.button("Sign In", use_container_width=True, key="login_btn"):
                if not username or not password:
                    st.warning("Please enter your username and password.")
                else:
                    data, code = api("POST", "/login", json={"username": username, "password": password})
                    if code == 200:
                        st.session_state.logged_in    = True
                        st.session_state.token        = data["token"]
                        st.session_state.user_id      = data["user_id"]
                        st.session_state.username     = data["username"]
                        st.session_state.balance      = data["balance"]
                        st.session_state.chat_history = []
                        st.session_state.chat_loaded  = False
                        st.success("Welcome back!")
                        st.rerun()
                    else:
                        st.error(data.get("error", "Login failed"))

        with tab_register:
            st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
            new_user  = st.text_input("Choose Username", key="reg_user",
                                      placeholder="Letters, numbers, underscores (3-50 chars)")
            new_email = st.text_input("Email (optional, for password reset)", key="reg_email", placeholder="Enter your email")
            new_pass  = st.text_input("Choose Password", type="password", key="reg_pass",
                                      placeholder="Minimum 6 characters")
            new_pass2 = st.text_input("Confirm Password", type="password", key="reg_pass2",
                                      placeholder="Repeat password")
            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
            if st.button("Create Account", use_container_width=True, key="reg_btn"):
                err = validate_username_input(new_user)
                if err:
                    st.warning(err)
                elif not new_pass:
                    st.warning("Password is required.")
                elif len(new_pass) < 6:
                    st.warning("Password must be at least 6 characters.")
                elif new_pass != new_pass2:
                    st.error("Passwords do not match.")
                else:
                    data, code = api("POST", "/register",
                                     json={"username": new_user, "email": new_email, "password": new_pass})
                    if code == 201:
                        st.success("Account created! Sign in to continue.")
                    else:
                        st.error(data.get("error", "Registration failed"))

        with tab_forgot:
            st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
            forgot_email = st.text_input("Enter your registered email", key="forgot_email")
            if st.button("Send Reset Link", use_container_width=True, key="forgot_btn"):
                if not forgot_email:
                    st.warning("Please enter your email.")
                else:
                    data, code = api("POST", "/forgot-password", json={"email": forgot_email})
                    if code == 200:
                        st.success("If that email exists, a reset link has been sent to it (check emails.txt in the app directory).")
                    else:
                        st.error(data.get("error", "Failed to send reset link."))
            
            st.markdown("---")
            st.markdown("##### Reset Password")
            reset_token = st.text_input("Reset Token", key="reset_token", placeholder="Enter token from email")
            reset_pass = st.text_input("New Password", type="password", key="reset_pass", placeholder="Minimum 6 characters")
            reset_pass2 = st.text_input("Confirm New Password", type="password", key="reset_pass2")
            if st.button("Reset Password", use_container_width=True, key="reset_btn"):
                if not reset_token:
                    st.warning("Please enter the reset token.")
                elif not reset_pass:
                    st.warning("Please enter a new password.")
                elif len(reset_pass) < 6:
                    st.warning("Password must be at least 6 characters.")
                elif reset_pass != reset_pass2:
                    st.error("Passwords do not match.")
                else:
                    data, code = api("POST", "/reset-password", json={"token": reset_token, "new_password": reset_pass})
                    if code == 200:
                        st.success("Password reset successfully! You can now sign in.")
                    else:
                        st.error(data.get("error", "Failed to reset password."))

# ─── Dashboard ────────────────────────────────────────────────────────────────

def dashboard_page():
    summary_data, _ = api("GET", f"/summary?month={datetime.now().strftime('%Y-%m')}")
    balance_data, _ = api("GET", "/balance")
    balance = float(balance_data.get("balance", 0)) if "balance" in balance_data else 0.0
    st.session_state.balance = balance

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        sign_class = "positive" if balance >= 0 else "negative"
        st.markdown(f"""
        <div class='metric-card {"danger" if balance < 0 else ""}'>
            <div class='metric-label'>Current Balance</div>
            <div class='metric-value {sign_class}'>{"+" if balance >= 0 else ""}${abs(balance):,.2f}</div>
        </div>""", unsafe_allow_html=True)
    with col2:
        inc = summary_data.get("total_income", 0)
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>This Month Income</div>
            <div class='metric-value positive'>+${inc:,.2f}</div>
        </div>""", unsafe_allow_html=True)
    with col3:
        exp = summary_data.get("total_expense", 0)
        st.markdown(f"""
        <div class='metric-card danger'>
            <div class='metric-label'>This Month Expenses</div>
            <div class='metric-value negative'>-${exp:,.2f}</div>
        </div>""", unsafe_allow_html=True)
    with col4:
        net       = summary_data.get("net_balance", 0)
        net_class = "positive" if net >= 0 else "negative"
        st.markdown(f"""
        <div class='metric-card blue'>
            <div class='metric-label'>Net This Month</div>
            <div class='metric-value {net_class}'>{"+" if net >= 0 else ""}${abs(net):,.2f}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)

    col_left, col_right = st.columns([1.6, 1])

    with col_left:
        st.markdown("<div class='section-header'>Recent Transactions</div>", unsafe_allow_html=True)
        txns, code = api("GET", "/transactions")
        if code == 200 and txns:
            # Order transactions by the exact time they were done/recorded (most recent first)
            txns = sorted(txns, key=lambda x: x.get("last_update", x.get("transaction_date", "")), reverse=True)
            for tx in txns[:10]:
                badge_class  = "credit" if tx["type"] == "CREDIT" else "debit"
                amount_str   = f'+${tx["amount"]:,.2f}' if tx["type"] == "CREDIT" else f'-${tx["amount"]:,.2f}'
                amount_color = "#6ee7b7" if tx["type"] == "CREDIT" else "#f87171"
                st.markdown(f"""
                <div class='tx-row'>
                    <span class='tx-badge {badge_class}'>{tx["type"]}</span>
                    <div style='flex:1'>
                        <div style='font-weight:500;font-size:0.9rem'>{tx.get("description") or tx.get("category","—")}</div>
                        <div style='font-size:0.75rem;color:var(--muted)'>{tx.get("category","—")} · {fmt_date(tx.get("transaction_date"))}</div>
                    </div>
                    <div style='font-family:"DM Mono",monospace;font-weight:600;color:{amount_color}'>{amount_str}</div>
                    <div style='font-size:0.75rem;color:var(--muted)'>#{tx["transaction_id"]}</div>
                </div>""", unsafe_allow_html=True)
        else:
            st.markdown("<div style='color:var(--muted);text-align:center;padding:2rem'>No transactions yet. Use the AI Assistant to add your first transaction!</div>", unsafe_allow_html=True)

    with col_right:
        st.markdown("<div class='section-header'>Category Breakdown</div>", unsafe_allow_html=True)
        cats = summary_data.get("categories", {})
        if cats:
            for cat, vals in sorted(cats.items(),
                                    key=lambda x: x[1].get("DEBIT", 0) + x[1].get("CREDIT", 0),
                                    reverse=True)[:8]:
                debit, credit = vals.get("DEBIT", 0), vals.get("CREDIT", 0)
                parts = []
                if credit:
                    parts.append(f"<span style='color:#6ee7b7'>+${credit:,.0f}</span>")
                if debit:
                    parts.append(f"<span style='color:#f87171'>-${debit:,.0f}</span>")
                st.markdown(f"""
                <div style='background:var(--bg3);border:1px solid var(--border);border-radius:10px;
                            padding:0.75rem 1rem;margin-bottom:0.5rem;display:flex;
                            justify-content:space-between;align-items:center'>
                    <span style='font-size:0.85rem;font-weight:500'>{cat}</span>
                    <span style='font-size:0.8rem;font-family:"DM Mono",monospace'>{" / ".join(parts)}</span>
                </div>""", unsafe_allow_html=True)
        else:
            st.markdown("<div style='color:var(--muted);text-align:center;padding:1rem'>No data yet</div>", unsafe_allow_html=True)

# ─── Transactions Page ────────────────────────────────────────────────────────

def transactions_page():
    st.markdown("### Manage Transactions")

    # Load budgets once for the dropdown and badge lookup
    budgets_resp, _ = api("GET", "/budgets")
    budget_list     = budgets_resp if isinstance(budgets_resp, list) else []
    # id → name map used when rendering the transaction list
    budget_id_to_name = {b["budget_id"]: b["name"] for b in budget_list}
    # label → id map used in the selectboxes ("No Budget" maps to None)
    budget_select_map = {"No Budget": None}
    budget_select_map.update({b["name"]: b["budget_id"] for b in budget_list})
    budget_labels = list(budget_select_map.keys())

    col_form, col_list = st.columns([1, 1.8])

    with col_form:
        with st.expander("Add New Transaction", expanded=True):
            tx_type  = st.selectbox("Type", ["DEBIT", "CREDIT"],
                                    format_func=lambda x: "DEBIT (Expense)" if x == "DEBIT" else "CREDIT (Income)")
            amount   = st.number_input("Amount ($)", min_value=0.01, max_value=1_000_000.0,
                                       step=0.01, format="%.2f")
            cat_type_filter = "expense" if tx_type == "DEBIT" else "income"
            categories      = get_user_categories(cat_type_filter)
            category = st.selectbox("Category", categories)
            desc     = st.text_input("Description", placeholder="e.g. Weekly groceries",
                                     max_chars=500)
            tx_date  = st.date_input("Date", value=datetime.today())
            budget_sel = st.selectbox("Link to Budget (optional)", budget_labels, key="add_tx_budget",
                                      help="Optionally associate this transaction with a budget.")
            budget_id  = budget_select_map[budget_sel]

            if st.button("Add Transaction", use_container_width=True):
                if amount <= 0:
                    st.error("Amount must be greater than zero.")
                elif not category:
                    st.error("Please select a category.")
                else:
                    payload = {
                        "type":             tx_type,
                        "amount":           amount,
                        "category":         category,
                        "description":      desc,
                        "transaction_date": tx_date.isoformat(),
                        "budget_id":        budget_id,
                    }
                    data, code = api("POST", "/transactions", json=payload)
                    if code == 201:
                        st.success(f"Transaction added. New balance: ${data['balance']:,.2f}")
                        st.rerun()
                    else:
                        st.error(data.get("error", "Failed to add transaction"))

    with col_list:
        st.markdown("<div class='section-header'>All Transactions</div>", unsafe_allow_html=True)

        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            f_type  = st.selectbox("Filter Type", ["All", "DEBIT", "CREDIT"], key="f_type")
        with fc2:
            f_start = st.date_input("From", value=datetime.today() - timedelta(days=30), key="f_start")
        with fc3:
            f_end   = st.date_input("To", value=datetime.today(), key="f_end")

        if f_start > f_end:
            st.warning("'From' date must be on or before 'To' date.")
        else:
            params = f"?start_date={f_start}&end_date={f_end}"
            if f_type != "All":
                params += f"&type={f_type}"

            txns, code = api("GET", f"/transactions{params}")
            if code == 200 and txns:
                for tx in txns:
                    badge_class  = "credit" if tx["type"] == "CREDIT" else "debit"
                    amount_color = "#6ee7b7" if tx["type"] == "CREDIT" else "#f87171"
                    amount_str   = f'+${tx["amount"]:,.2f}' if tx["type"] == "CREDIT" else f'-${tx["amount"]:,.2f}'

                    # Budget badge — shown only when this transaction is linked to a budget
                    tx_budget_id   = tx.get("budget_id")
                    budget_badge   = ""
                    if tx_budget_id and tx_budget_id in budget_id_to_name:
                        b_name       = budget_id_to_name[tx_budget_id]
                        budget_badge = (
                            f"<span style='font-size:0.7rem;background:rgba(59,130,246,0.18);"
                            f"color:#93c5fd;padding:0.15rem 0.55rem;border-radius:10px;"
                            f"margin-left:0.4rem;white-space:nowrap'>Budget: {b_name}</span>"
                        )

                    c1, c2 = st.columns([5, 1])
                    with c1:
                        st.markdown(f"""
                        <div class='tx-row'>
                            <span class='tx-badge {badge_class}'>{tx["type"]}</span>
                            <div style='flex:1'>
                                <div style='font-weight:500;font-size:0.9rem'>
                                    {tx.get("description") or "—"}{budget_badge}
                                </div>
                                <div style='font-size:0.75rem;color:var(--muted)'>{tx.get("category","—")} · {fmt_date(tx.get("transaction_date"))} · ID #{tx["transaction_id"]}</div>
                            </div>
                            <div style='font-family:"DM Mono",monospace;font-weight:600;color:{amount_color}'>{amount_str}</div>
                        </div>""", unsafe_allow_html=True)
                    with c2:
                        if st.button("Delete", key=f"del_{tx['transaction_id']}"):
                            data, code2 = api("DELETE", f"/transactions/{tx['transaction_id']}")
                            if code2 == 200:
                                st.success("Deleted.")
                                st.rerun()
                            else:
                                st.error(data.get("error", "Delete failed"))
            elif code == 200:
                st.markdown("<div style='color:var(--muted);text-align:center;padding:2rem'>No transactions in this period.</div>", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("**Edit Transaction**")
        edit_id = st.number_input("Transaction ID to Edit", min_value=1, step=1, key="edit_id")
        if st.button("Load Transaction", key="load_tx"):
            all_txns, _ = api("GET", "/transactions")
            match = next((t for t in (all_txns or []) if t["transaction_id"] == int(edit_id)), None)
            if match:
                st.session_state["edit_tx"] = match
            else:
                st.error("Transaction not found.")

        if "edit_tx" in st.session_state:
            tx = st.session_state["edit_tx"]
            e1, e2 = st.columns(2)
            with e1:
                new_type   = st.selectbox("Type", ["DEBIT", "CREDIT"],
                                          index=0 if tx["type"] == "DEBIT" else 1, key="e_type")
                new_amount = st.number_input("Amount ($)", value=float(tx["amount"]),
                                             min_value=0.01, max_value=1_000_000.0,
                                             step=0.01, key="e_amount")
            with e2:
                new_cat  = st.text_input("Category", value=tx.get("category", ""),
                                         max_chars=50, key="e_cat")
                new_desc = st.text_input("Description", value=tx.get("description", ""),
                                         max_chars=500, key="e_desc")

            # Pre-select the budget this transaction is currently linked to (if any)
            cur_budget_id = tx.get("budget_id")
            cur_label     = next(
                (lbl for lbl, bid in budget_select_map.items() if bid == cur_budget_id),
                "No Budget"
            )
            edit_budget_sel = st.selectbox(
                "Link to Budget (optional)", budget_labels,
                index=budget_labels.index(cur_label),
                key="edit_tx_budget",
                help="Change or remove the budget linked to this transaction."
            )
            new_budget_id = budget_select_map[edit_budget_sel]

            if st.button("Save Changes", key="save_edit"):
                if new_amount <= 0:
                    st.error("Amount must be greater than zero.")
                elif not new_cat.strip():
                    st.error("Category is required.")
                else:
                    payload  = {
                        "type":        new_type,
                        "amount":      new_amount,
                        "category":    new_cat,
                        "description": new_desc,
                        "budget_id":   new_budget_id,
                    }
                    data, code3 = api("PUT", f"/transactions/{tx['transaction_id']}", json=payload)
                    if code3 == 200:
                        st.success(f"Updated. New balance: ${data['balance']:,.2f}")
                        del st.session_state["edit_tx"]
                        st.rerun()
                    else:
                        st.error(data.get("error", "Update failed"))

# ─── Analytics Page ───────────────────────────────────────────────────────────

def analytics_page():
    st.markdown("### Financial Analytics")

    month_str = st.selectbox("Select Month", [
        datetime.now().strftime("%Y-%m"),
        (datetime.now() - timedelta(days=30)).strftime("%Y-%m"),
        (datetime.now() - timedelta(days=60)).strftime("%Y-%m"),
        "all"
    ], format_func=lambda x: "All Time" if x == "all" else datetime.strptime(x, "%Y-%m").strftime("%B %Y"))

    endpoint     = "/summary" if month_str == "all" else f"/summary?month={month_str}"
    data, code   = api("GET", endpoint)

    if code != 200:
        st.error("Could not load analytics.")
        return

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""
        <div class='metric-card'><div class='metric-label'>Total Income</div>
        <div class='metric-value positive'>+${data.get('total_income',0):,.2f}</div></div>""",
        unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class='metric-card danger'><div class='metric-label'>Total Expenses</div>
        <div class='metric-value negative'>-${data.get('total_expense',0):,.2f}</div></div>""",
        unsafe_allow_html=True)
    with c3:
        net = data.get("net_balance", 0)
        st.markdown(f"""
        <div class='metric-card blue'><div class='metric-label'>Net Balance</div>
        <div class='metric-value {"positive" if net >= 0 else "negative"}'>{"+" if net >= 0 else ""}${net:,.2f}</div></div>""",
        unsafe_allow_html=True)

    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)

    cats = data.get("categories", {})
    if cats:
        st.markdown("<div class='section-header'>Spending by Category</div>", unsafe_allow_html=True)
        df_rows = [
            {
                "Category":          cat,
                "Income (CREDIT)":   vals.get("CREDIT", 0),
                "Expenses (DEBIT)":  vals.get("DEBIT", 0),
                "Net":               vals.get("CREDIT", 0) - vals.get("DEBIT", 0),
            }
            for cat, vals in cats.items()
        ]
        df = pd.DataFrame(df_rows).sort_values("Expenses (DEBIT)", ascending=False)
        st.dataframe(
            df.style.format({
                "Income (CREDIT)":  "${:.2f}",
                "Expenses (DEBIT)": "${:.2f}",
                "Net":              "${:.2f}",
            }),
            use_container_width=True,
            hide_index=True,
        )
        if len(df) > 0:
            st.bar_chart(df.set_index("Category")[["Income (CREDIT)", "Expenses (DEBIT)"]],
                         color=["#6ee7b7", "#f87171"])

# ─── Budgets Page ─────────────────────────────────────────────────────────────

def budgets_page():
    st.markdown("### Budgets")

    col_form, col_list = st.columns([1, 1.6])

    with col_form:
        with st.expander("Add Budget", expanded=True):
            b_name   = st.text_input("Budget Name", placeholder="e.g. Monthly Food & Transport",
                                     max_chars=100, key="b_name")
            b_limit  = st.number_input("Spending Limit ($)", min_value=0.01,
                                       max_value=1_000_000.0, step=1.0,
                                       format="%.2f", key="b_limit")
            b_period = st.selectbox("Period", ["monthly", "weekly", "yearly"], key="b_period")

            if st.button("Create Budget", use_container_width=True, key="create_budget"):
                if not b_name.strip():
                    st.error("Budget name is required.")
                elif b_limit <= 0:
                    st.error("Spending limit must be greater than zero.")
                else:
                    payload   = {"name": b_name, "limit_amount": b_limit, "period": b_period}
                    data, code = api("POST", "/budgets", json=payload)
                    if code == 201:
                        st.success(f"Budget '{b_name}' created.")
                        st.rerun()
                    else:
                        st.error(data.get("error", "Failed to create budget"))

    with col_list:
        month_str = datetime.now().strftime("%Y-%m")
        month_sel = st.selectbox("View spending for", [
            month_str,
            (datetime.now() - timedelta(days=30)).strftime("%Y-%m"),
            (datetime.now() - timedelta(days=60)).strftime("%Y-%m"),
        ], format_func=lambda x: datetime.strptime(x, "%Y-%m").strftime("%B %Y"),
           key="budget_month")

        budgets, code = api("GET", f"/budgets?month={month_sel}")
        if code != 200:
            st.error("Could not load budgets.")
            return

        if not budgets:
            st.markdown("<div style='color:var(--muted);text-align:center;padding:2rem'>No budgets set. Add one to start tracking spending limits.</div>", unsafe_allow_html=True)
            return

        st.markdown("<div class='section-header'>Budget Status</div>", unsafe_allow_html=True)

        for b in budgets:
            pct    = min(b["percentage"], 100)
            status = b["status"]
            bar_color = {"ok": "#6ee7b7", "warning": "#fbbf24", "over": "#f87171"}.get(status, "#6ee7b7")
            status_label = {"ok": "On Track", "warning": "Near Limit", "over": "Over Budget"}.get(status, "")
            status_color = {"ok": "#6ee7b7", "warning": "#fbbf24", "over": "#f87171"}.get(status, "#6ee7b7")

            c1, c2 = st.columns([5, 1])
            with c1:
                st.markdown(f"""
                <div style='background:var(--bg3);border:1px solid var(--border);border-radius:12px;
                            padding:1rem 1.25rem;margin-bottom:0.5rem'>
                    <div style='display:flex;justify-content:space-between;align-items:center'>
                        <div>
                            <div style='font-weight:600;font-size:0.95rem'>{b["name"]}</div>
                            <div style='font-size:0.75rem;color:var(--muted)'>{b["period"].capitalize()}</div>
                        </div>
                        <div style='text-align:right'>
                            <div style='font-family:"DM Mono",monospace;font-weight:600'>
                                ${b["spent"]:,.2f} / ${b["limit_amount"]:,.2f}
                            </div>
                            <div style='font-size:0.75rem;color:{status_color};font-weight:600'>{status_label}</div>
                        </div>
                    </div>
                    <div class='budget-bar-bg'>
                        <div style='background:{bar_color};height:100%;width:{pct}%;border-radius:4px;transition:width 0.3s'></div>
                    </div>
                    <div style='font-size:0.7rem;color:var(--muted);margin-top:0.3rem'>
                        {b["percentage"]:.1f}% used &nbsp;·&nbsp; ${b["remaining"]:,.2f} remaining
                        &nbsp;·&nbsp; {b.get("linked_count", 0)} transaction(s) linked
                    </div>
                </div>""", unsafe_allow_html=True)
            with c2:
                if st.button("Delete", key=f"del_budget_{b['budget_id']}"):
                    data, code2 = api("DELETE", f"/budgets/{b['budget_id']}")
                    if code2 == 200:
                        st.success("Budget deleted.")
                        st.rerun()
                    else:
                        st.error(data.get("error", "Delete failed"))

# ─── Categories Page ─────────────────────────────────────────────────────────

def categories_page():
    st.markdown("### Categories")

    col_form, col_list = st.columns([1, 1.6])

    with col_form:
        with st.expander("Add Category", expanded=True):
            c_name = st.text_input("Category Name", placeholder="e.g. Subscriptions",
                                   max_chars=50, key="c_name")
            c_type = st.selectbox("Type", ["expense", "income", "both"],
                                  format_func=lambda x: x.capitalize(), key="c_type")

            if st.button("Add Category", use_container_width=True, key="add_cat"):
                if not c_name.strip():
                    st.error("Category name is required.")
                elif len(c_name.strip()) > 50:
                    st.error("Category name must not exceed 50 characters.")
                else:
                    data, code = api("POST", "/categories",
                                     json={"name": c_name.strip(), "type": c_type})
                    if code == 201:
                        st.success(f"Category '{c_name}' added.")
                        st.rerun()
                    else:
                        st.error(data.get("error", "Failed to add category"))

    with col_list:
        st.markdown("<div class='section-header'>Your Categories</div>", unsafe_allow_html=True)

        cats, code = api("GET", "/categories")
        if code != 200:
            st.error("Could not load categories.")
            return

        if not cats:
            st.markdown("<div style='color:var(--muted);text-align:center;padding:2rem'>No categories yet.</div>", unsafe_allow_html=True)
            return

        type_colors = {"income": "#6ee7b7", "expense": "#f87171", "both": "#3b82f6"}

        for cat in cats:
            tc = type_colors.get(cat["type"], "#64748b")
            c1, c2 = st.columns([5, 1])
            with c1:
                st.markdown(f"""
                <div style='background:var(--bg3);border:1px solid var(--border);border-radius:10px;
                            padding:0.75rem 1rem;margin-bottom:0.4rem;display:flex;
                            justify-content:space-between;align-items:center'>
                    <span style='font-weight:500'>{cat["name"]}</span>
                    <span style='font-size:0.75rem;font-weight:600;color:{tc};
                                 background:rgba(255,255,255,0.06);padding:0.2rem 0.6rem;
                                 border-radius:12px'>{cat["type"].upper()}</span>
                </div>""", unsafe_allow_html=True)
            with c2:
                if st.button("Edit", key=f"edit_cat_{cat['category_id']}"):
                    st.session_state["edit_cat"] = cat
                    st.rerun()

        if "edit_cat" in st.session_state:
            st.markdown("---")
            st.markdown("**Edit Category**")
            cat_to_edit = st.session_state["edit_cat"]
            
            e1, e2 = st.columns(2)
            with e1:
                e_name = st.text_input("Name", value=cat_to_edit["name"], key="e_c_name", max_chars=50)
            with e2:
                types = ["expense", "income", "both"]
                idx = types.index(cat_to_edit["type"]) if cat_to_edit["type"] in types else 0
                e_type = st.selectbox("Type", types, index=idx, format_func=lambda x: x.capitalize(), key="e_c_type")
                
            b1, b2 = st.columns(2)
            with b1:
                if st.button("Save Changes", use_container_width=True, key="save_c_btn"):
                    if not e_name.strip():
                        st.error("Category name is required.")
                    else:
                        payload = {"name": e_name.strip(), "type": e_type}
                        data, code = api("PUT", f"/categories/{cat_to_edit['category_id']}", json=payload)
                        if code == 200:
                            st.success("Category updated.")
                            del st.session_state["edit_cat"]
                            st.rerun()
                        else:
                            st.error(data.get("error", "Update failed"))
            with b2:
                if st.button("Cancel", use_container_width=True, key="cancel_c_btn"):
                    del st.session_state["edit_cat"]
                    st.rerun()

# ─── AI Assistant Page ────────────────────────────────────────────────────────

def llm_page():
    st.markdown("### AI Financial Assistant")

    if not st.session_state.chat_loaded:
        logs, code = api("GET", "/chat/logs?limit=100")
        if code == 200 and isinstance(logs, list):
            st.session_state.chat_history = [
                {"role": r["role"], "content": r["message"], "is_old": True} for r in logs
            ]
        st.session_state.chat_loaded = True

    col_chat, col_right = st.columns([2.5, 1], gap="large")

    with col_right:
        st.markdown("<div class='section-header'>Quick Actions</div>", unsafe_allow_html=True)
        suggestions = [
            "Add a $50 grocery expense",
            "Record salary income of $2000",
            "Show all transactions this month",
            "What is my current balance?",
            "Show this month's summary",
            "Add $15 coffee expense today",
        ]
        for i, s in enumerate(suggestions):
            if st.button(s, key=f"sug_{i}", use_container_width=True):
                st.session_state["llm_send"] = s

        st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)
        st.markdown("<div class='section-header'>Settings & History</div>", unsafe_allow_html=True)

        show_history = st.toggle("Show Previous History", value=False)
        if st.button("Clear", use_container_width=True, key="clear_btn"):
            api("DELETE", "/chat/logs")
            st.session_state.chat_history = []
            st.session_state.chat_loaded  = True
            st.rerun()

        if show_history:
            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
            st.markdown("**Previous Conversations**")
            old_msgs = [m for m in st.session_state.chat_history if m.get("is_old", False)]
            if not old_msgs:
                st.info("No previous history found.")
            else:
                with st.container(height=400):
                    for msg in old_msgs:
                        role_icon = "👤 User" if msg["role"] == "user" else "🤖 AI"
                        st.markdown(f"**{role_icon}**<br><span style='font-size:0.85em;color:var(--muted)'>{msg['content'].replace(chr(10), '<br>')}</span>", unsafe_allow_html=True)
                        st.markdown("<hr style='margin: 0.5rem 0'>", unsafe_allow_html=True)

    with col_chat:
        st.markdown("""
        <div style='background:var(--bg3);border:1px solid var(--border);border-radius:12px;padding:1rem 1.25rem;margin-bottom:1rem'>
            <div style='font-size:0.8rem;color:var(--muted);margin-bottom:0.3rem'>POWERED BY GEMMA3 VIA OLLAMA</div>
            <div style='font-size:0.9rem;color:var(--text)'>Ask me anything about your finances. I can add, view, update, or delete transactions using natural language.</div>
        </div>
        """, unsafe_allow_html=True)

        chat_container = st.container(height=500)
        with chat_container:
            display_msgs = st.session_state.chat_history
            if show_history:
                display_msgs = [m for m in st.session_state.chat_history if not m.get("is_old", False)]

            if not display_msgs:
                st.markdown("<div style='color:var(--muted);text-align:center;padding:2rem'>Start a conversation!</div>", unsafe_allow_html=True)

            for msg in display_msgs:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

        message_to_send = st.chat_input("Type your request... e.g. 'Add a $30 transport expense'")

    if "llm_send" in st.session_state:
        message_to_send = st.session_state.pop("llm_send")

    if message_to_send:
        st.session_state.chat_history.append({"role": "user", "content": message_to_send, "is_old": False})

        with col_chat:
            with chat_container:
                with st.chat_message("user"):
                    st.markdown(message_to_send)
                with st.chat_message("assistant"):
                    response_placeholder = st.empty()
                    response_placeholder.markdown("Thinking...")

        data, code = api("POST", "/llm", json={"message": message_to_send})

        if code == 503:
            reply = "Ollama is not running. Please start Ollama with 'ollama serve' and ensure the 'gemma3:4b' model is available."
        elif code != 200 and "error" in data:
            reply = f"Error: {data['error']}"
        else:
            action = data.get("action", "UNKNOWN")
            msg    = data.get("message", "")
            reply  = msg

            if action == "CREATE" and "transaction" in data:
                tx   = data["transaction"]
                sign = "+" if tx["type"] == "CREDIT" else "-"
                reply += (f"\n\n**Transaction Added**"
                          f"\n- **Type:** {tx['type']}"
                          f"\n- **Amount:** {sign}${float(tx['amount']):,.2f}"
                          f"\n- **Category:** {tx.get('category','—')}"
                          f"\n- **Description:** {tx.get('description','—')}"
                          f"\n- **New Balance:** ${float(data.get('balance',0)):,.2f}")
                st.session_state.balance = float(data.get("balance", 0))

            elif action == "READ" and "transactions" in data:
                txns  = data["transactions"]
                count = data.get("count", len(txns))
                reply += f"\n\nFound {count} transaction(s):"
                for tx in txns[:10]:
                    sign = "+" if tx["type"] == "CREDIT" else "-"
                    reply += f"\n- #{tx['transaction_id']} [{tx['type']}] {tx.get('description') or tx.get('category','—')} — {sign}${float(tx['amount']):,.2f} ({fmt_date(tx.get('transaction_date'))})"
                if count > 10:
                    reply += f"\n...and {count - 10} more."

            elif action == "DELETE" and "balance" in data:
                reply += f"\n\nTransaction deleted. **New Balance:** ${float(data['balance']):,.2f}"
                st.session_state.balance = float(data["balance"])

            elif action == "UPDATE" and "transaction" in data:
                tx = data["transaction"]
                reply += f"\n\nTransaction #{tx['transaction_id']} updated. **New Balance:** ${float(data.get('balance',0)):,.2f}"
                st.session_state.balance = float(data.get("balance", 0))

            elif action == "SUMMARY" and "summary" in data:
                s = data["summary"]
                reply += (f"\n\n**Financial Summary**"
                          f"\n- **Income:** +${s['total_income']:,.2f}"
                          f"\n- **Expenses:** -${s['total_expense']:,.2f}"
                          f"\n- **Net:** {'+'if s['net_balance']>=0 else ''}${s['net_balance']:,.2f}"
                          f"\n- **Current Balance:** ${s['current_balance']:,.2f}"
                          f"\n- **Transactions:** {s['transaction_count']}")
                st.session_state.balance = float(s["current_balance"])

            elif action == "BALANCE" and "balance" in data:
                reply = f"Your current balance is **${float(data['balance']):,.2f}**"
                st.session_state.balance = float(data["balance"])

        st.session_state.chat_history.append({"role": "assistant", "content": reply, "is_old": False})
        st.rerun()

# ─── Main App ─────────────────────────────────────────────────────────────────

def main():
    if not st.session_state.logged_in:
        auth_page()
        return

    with st.sidebar:
        st.markdown("""
        <div style='padding-bottom:1rem;border-bottom:1px solid var(--border);margin-bottom:1.5rem'>
            <div class='logo'>Expense Tracker</div>
            <div class='logo-sub'>Personal Finance Intelligence</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"<div style='font-size:0.85rem;color:var(--muted)'>Signed in as</div>"
                    f"<div style='font-weight:600;margin-bottom:0.5rem'>{st.session_state.username}</div>",
                    unsafe_allow_html=True)

        bal       = st.session_state.balance
        bal_color = "#6ee7b7" if bal >= 0 else "#f87171"
        st.markdown(f"""
        <div style='background:var(--bg3);border:1px solid var(--border);border-radius:10px;padding:0.75rem 1rem;margin-bottom:1.5rem'>
            <div style='font-size:0.7rem;text-transform:uppercase;letter-spacing:0.1em;color:var(--muted)'>Balance</div>
            <div style='font-size:1.4rem;font-weight:700;color:{bal_color};font-family:"DM Mono",monospace'>{"+" if bal >= 0 else ""}${abs(bal):,.2f}</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("**Navigation**")
        nav_items = {
            "dashboard":    "Dashboard",
            "transactions": "Transactions",
            "analytics":    "Analytics",
            "budgets":      "Budgets",
            "categories":   "Categories",
            "ai_chat":      "AI Assistant",
        }
        for key, label in nav_items.items():
            if st.button(label, key=f"nav_{key}", use_container_width=True):
                st.session_state.active_tab = key
                st.rerun()

        st.markdown("---")
        if st.button("Sign Out", use_container_width=True, key="logout_btn"):
            api("POST", "/logout")
            for k in ["logged_in", "token", "user_id", "username", "balance",
                       "chat_history", "chat_loaded", "active_tab"]:
                st.session_state.pop(k, None)
            st.rerun()

    tab = st.session_state.get("active_tab", "dashboard")
    if tab == "dashboard":
        dashboard_page()
    elif tab == "transactions":
        transactions_page()
    elif tab == "analytics":
        analytics_page()
    elif tab == "budgets":
        budgets_page()
    elif tab == "categories":
        categories_page()
    elif tab == "ai_chat":
        llm_page()

if __name__ == "__main__":
    main()
