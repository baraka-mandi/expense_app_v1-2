"""
Personal Expense Management System - Streamlit Frontend
Provides the web interface for authentication, transaction management, and LLM chat.
"""

import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

API = "http://127.0.0.1:5000/api"
SESSION = requests.Session()

# ─── Page Config ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="ExpenseIQ",
    page_icon="💳",
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
        return "—"
    try:
        return datetime.fromisoformat(d.replace("Z","")).strftime("%b %d, %Y")
    except:
        return str(d)[:10]

# ─── Session State ────────────────────────────────────────────────────────────

if "logged_in"    not in st.session_state: st.session_state.logged_in    = False
if "token"        not in st.session_state: st.session_state.token        = ""
if "user_id"      not in st.session_state: st.session_state.user_id      = None
if "username"     not in st.session_state: st.session_state.username     = ""
if "balance"      not in st.session_state: st.session_state.balance      = 0.0
if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "active_tab"   not in st.session_state: st.session_state.active_tab   = "dashboard"

# ─── Auth Page ────────────────────────────────────────────────────────────────

def auth_page():
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("""
        <div style='text-align:center; padding: 2rem 0 1rem;'>
            <div class='logo'>💳 ExpenseIQ</div>
            <div class='logo-sub'>Personal Finance Intelligence</div>
        </div>
        """, unsafe_allow_html=True)

        tab_login, tab_register = st.tabs(["  Sign In  ", "  Create Account  "])

        with tab_login:
            st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
            username = st.text_input("Username", key="login_user", placeholder="Enter your username")
            password = st.text_input("Password", type="password", key="login_pass", placeholder="Enter your password")
            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
            if st.button("Sign In →", use_container_width=True, key="login_btn"):
                if username and password:
                    data, code = api("POST", "/login", json={"username": username, "password": password})
                    if code == 200:
                        st.session_state.logged_in = True
                        st.session_state.token     = data["token"]
                        st.session_state.user_id   = data["user_id"]
                        st.session_state.username  = data["username"]
                        st.session_state.balance   = data["balance"]
                        st.session_state.chat_history = []
                        st.success("Welcome back! 👋")
                        st.rerun()
                    else:
                        st.error(data.get("error", "Login failed"))
                else:
                    st.warning("Please enter your credentials.")

        with tab_register:
            st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
            new_user = st.text_input("Choose Username", key="reg_user", placeholder="e.g. john_doe")
            new_pass = st.text_input("Choose Password", type="password", key="reg_pass", placeholder="Minimum 6 characters")
            new_pass2 = st.text_input("Confirm Password", type="password", key="reg_pass2", placeholder="Repeat password")
            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
            if st.button("Create Account →", use_container_width=True, key="reg_btn"):
                if not new_user or not new_pass:
                    st.warning("All fields are required.")
                elif len(new_pass) < 6:
                    st.warning("Password must be at least 6 characters.")
                elif new_pass != new_pass2:
                    st.error("Passwords do not match.")
                else:
                    data, code = api("POST", "/register", json={"username": new_user, "password": new_pass})
                    if code == 201:
                        st.success("Account created! Sign in to continue.")
                    else:
                        st.error(data.get("error", "Registration failed"))

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
        net = summary_data.get("net_balance", 0)
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
            for tx in txns[:10]:
                badge_class = "credit" if tx["type"] == "CREDIT" else "debit"
                amount_str  = f'+${tx["amount"]:,.2f}' if tx["type"] == "CREDIT" else f'-${tx["amount"]:,.2f}'
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
            for cat, vals in sorted(cats.items(), key=lambda x: x[1].get("DEBIT",0)+x[1].get("CREDIT",0), reverse=True)[:8]:
                debit  = vals.get("DEBIT", 0)
                credit = vals.get("CREDIT", 0)
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

    col_form, col_list = st.columns([1, 1.8])

    with col_form:
        with st.expander("➕ Add New Transaction", expanded=True):
            tx_type  = st.selectbox("Type", ["DEBIT", "CREDIT"], format_func=lambda x: f"{'💸 DEBIT (Expense)' if x=='DEBIT' else '💰 CREDIT (Income)'}")
            amount   = st.number_input("Amount ($)", min_value=0.01, step=0.01, format="%.2f")
            category = st.selectbox("Category", [
                "General","Groceries","Salary","Housing","Transport","Food & Dining",
                "Entertainment","Shopping","Health","Education","Investment","Other"
            ])
            desc    = st.text_input("Description", placeholder="e.g. Weekly groceries")
            tx_date = st.date_input("Date", value=datetime.today())

            if st.button("Add Transaction", use_container_width=True):
                payload = {
                    "type": tx_type, "amount": amount, "category": category,
                    "description": desc, "transaction_date": tx_date.isoformat()
                }
                data, code = api("POST", "/transactions", json=payload)
                if code == 201:
                    st.success(f"Transaction added! New balance: ${data['balance']:,.2f}")
                    st.rerun()
                else:
                    st.error(data.get("error","Failed to add transaction"))

    with col_list:
        st.markdown("<div class='section-header'>All Transactions</div>", unsafe_allow_html=True)

        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            f_type = st.selectbox("Filter Type", ["All","DEBIT","CREDIT"], key="f_type")
        with fc2:
            f_start = st.date_input("From", value=datetime.today() - timedelta(days=30), key="f_start")
        with fc3:
            f_end = st.date_input("To", value=datetime.today(), key="f_end")

        params = f"?start_date={f_start}&end_date={f_end}"
        if f_type != "All":
            params += f"&type={f_type}"

        txns, code = api("GET", f"/transactions{params}")
        if code == 200 and txns:
            for tx in txns:
                badge_class  = "credit" if tx["type"] == "CREDIT" else "debit"
                amount_color = "#6ee7b7" if tx["type"] == "CREDIT" else "#f87171"
                amount_str   = f'+${tx["amount"]:,.2f}' if tx["type"] == "CREDIT" else f'-${tx["amount"]:,.2f}'

                c1, c2 = st.columns([5, 1])
                with c1:
                    st.markdown(f"""
                    <div class='tx-row'>
                        <span class='tx-badge {badge_class}'>{tx["type"]}</span>
                        <div style='flex:1'>
                            <div style='font-weight:500;font-size:0.9rem'>{tx.get("description") or "—"}</div>
                            <div style='font-size:0.75rem;color:var(--muted)'>{tx.get("category","—")} · {fmt_date(tx.get("transaction_date"))} · ID #{tx["transaction_id"]}</div>
                        </div>
                        <div style='font-family:"DM Mono",monospace;font-weight:600;color:{amount_color}'>{amount_str}</div>
                    </div>""", unsafe_allow_html=True)
                with c2:
                    if st.button("🗑", key=f"del_{tx['transaction_id']}", help="Delete"):
                        data, code2 = api("DELETE", f"/transactions/{tx['transaction_id']}")
                        if code2 == 200:
                            st.success("Deleted!")
                            st.rerun()
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
                st.error("Transaction not found")

        if "edit_tx" in st.session_state:
            tx = st.session_state["edit_tx"]
            e1, e2 = st.columns(2)
            with e1:
                new_type   = st.selectbox("Type", ["DEBIT","CREDIT"], index=0 if tx["type"]=="DEBIT" else 1, key="e_type")
                new_amount = st.number_input("Amount", value=float(tx["amount"]), step=0.01, key="e_amount")
            with e2:
                new_cat  = st.text_input("Category", value=tx.get("category",""), key="e_cat")
                new_desc = st.text_input("Description", value=tx.get("description",""), key="e_desc")
            if st.button("💾 Save Changes", key="save_edit"):
                payload = {"type": new_type, "amount": new_amount, "category": new_cat, "description": new_desc}
                data, code3 = api("PUT", f"/transactions/{tx['transaction_id']}", json=payload)
                if code3 == 200:
                    st.success(f"Updated! New balance: ${data['balance']:,.2f}")
                    del st.session_state["edit_tx"]
                    st.rerun()
                else:
                    st.error(data.get("error","Update failed"))

# ─── Analytics Page ───────────────────────────────────────────────────────────

def analytics_page():
    st.markdown("### Financial Analytics")

    month_str = st.selectbox("Select Month", [
        datetime.now().strftime("%Y-%m"),
        (datetime.now() - timedelta(days=30)).strftime("%Y-%m"),
        (datetime.now() - timedelta(days=60)).strftime("%Y-%m"),
        "all"
    ], format_func=lambda x: "All Time" if x == "all" else datetime.strptime(x, "%Y-%m").strftime("%B %Y"))

    endpoint = "/summary" if month_str == "all" else f"/summary?month={month_str}"
    data, code = api("GET", endpoint)

    if code != 200:
        st.error("Could not load analytics")
        return

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""
        <div class='metric-card'><div class='metric-label'>Total Income</div>
        <div class='metric-value positive'>+${data.get('total_income',0):,.2f}</div></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class='metric-card danger'><div class='metric-label'>Total Expenses</div>
        <div class='metric-value negative'>-${data.get('total_expense',0):,.2f}</div></div>""", unsafe_allow_html=True)
    with c3:
        net = data.get('net_balance', 0)
        st.markdown(f"""
        <div class='metric-card blue'><div class='metric-label'>Net Balance</div>
        <div class='metric-value {"positive" if net>=0 else "negative"}'>{"+" if net>=0 else ""}${net:,.2f}</div></div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)

    cats = data.get("categories", {})
    if cats:
        st.markdown("<div class='section-header'>Spending by Category</div>", unsafe_allow_html=True)
        df_rows = []
        for cat, vals in cats.items():
            df_rows.append({
                "Category": cat,
                "Income (CREDIT)": vals.get("CREDIT", 0),
                "Expenses (DEBIT)": vals.get("DEBIT", 0),
                "Net": vals.get("CREDIT", 0) - vals.get("DEBIT", 0)
            })
        df = pd.DataFrame(df_rows).sort_values("Expenses (DEBIT)", ascending=False)
        st.dataframe(df.style.format({
            "Income (CREDIT)": "${:.2f}",
            "Expenses (DEBIT)": "${:.2f}",
            "Net": "${:.2f}"
        }), use_container_width=True, hide_index=True)

        if len(df) > 0:
            chart_df = df.set_index("Category")[["Income (CREDIT)", "Expenses (DEBIT)"]]
            st.bar_chart(chart_df, color=["#6ee7b7", "#f87171"])

# ─── LLM Chat Page ────────────────────────────────────────────────────────────

def llm_page():
    st.markdown("### AI Financial Assistant")
    st.markdown("""
    <div style='background:var(--bg3);border:1px solid var(--border);border-radius:12px;padding:1rem 1.25rem;margin-bottom:1.5rem'>
        <div style='font-size:0.8rem;color:var(--muted);margin-bottom:0.5rem'>💡 POWERED BY GEMMA3:1B VIA OLLAMA</div>
        <div style='font-size:0.9rem;color:var(--text)'>Ask me anything about your finances. I can add, view, update, or delete transactions using natural language.</div>
    </div>
    """, unsafe_allow_html=True)

    suggestions = [
        "Add a $50 grocery expense",
        "Record salary income of $2000",
        "Show all transactions this month",
        "What is my current balance?",
        "Show this month's summary",
        "Add $15 coffee expense today"
    ]
    st.markdown("**Quick Actions:**")
    cols = st.columns(3)
    for i, s in enumerate(suggestions):
        with cols[i % 3]:
            if st.button(s, key=f"sug_{i}", use_container_width=True):
                st.session_state["llm_send"] = s

    st.markdown("---")

    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                st.markdown(f"<div class='chat-msg chat-user'>👤 {msg['content']}</div>", unsafe_allow_html=True)
            else:
                content_html = msg['content'].replace("\n", "<br>")
                st.markdown(f"""
                <div class='chat-msg chat-ai'>
                    <div class='chat-ai-header'>✦ ExpenseIQ AI</div>
                    {content_html}
                </div>""", unsafe_allow_html=True)

    user_input = st.text_input(
        "Message",
        value="",
        placeholder="Type your request... e.g. 'Add a $30 transport expense'",
        label_visibility="collapsed",
        key="chat_input"
    )

    col_send, col_clear = st.columns([5, 1])
    with col_send:
        send = st.button("Send Message →", use_container_width=True, key="send_btn")
    with col_clear:
        if st.button("Clear", use_container_width=True, key="clear_btn"):
            st.session_state.chat_history = []
            st.rerun()

    # Determine what message to send — typed input takes priority, else quick action
    message_to_send = ""
    if send and user_input.strip():
        message_to_send = user_input.strip()
    elif "llm_send" in st.session_state:
        message_to_send = st.session_state.pop("llm_send")

    if message_to_send:
        st.session_state.chat_history.append({"role": "user", "content": message_to_send})

        with st.spinner("🤔 Thinking..."):
            data, code = api("POST", "/llm", json={"message": message_to_send})

        if code == 503:
            reply = "⚠️ **Ollama is not running.** Please start Ollama with `ollama serve` and ensure the `gemma3:1b` model is available."
        elif code != 200 and "error" in data:
            reply = f"⚠️ Error: {data['error']}"
        else:
            action = data.get("action", "UNKNOWN")
            msg    = data.get("message", "")
            reply  = msg

            if action == "CREATE" and "transaction" in data:
                tx = data["transaction"]
                sign = "+" if tx["type"] == "CREDIT" else "-"
                reply += f"\n\n✅ **Transaction Added**\n- Type: {tx['type']}\n- Amount: {sign}${float(tx['amount']):,.2f}\n- Category: {tx.get('category','—')}\n- Description: {tx.get('description','—')}\n- 💰 New Balance: **${float(data.get('balance',0)):,.2f}**"
                st.session_state.balance = float(data.get("balance", 0))

            elif action == "READ" and "transactions" in data:
                txns = data["transactions"]
                count = data.get("count", len(txns))
                reply += f"\n\n📋 **Found {count} transaction(s):**"
                for tx in txns[:10]:
                    sign = "+" if tx["type"] == "CREDIT" else "-"
                    reply += f"\n- #{tx['transaction_id']} [{tx['type']}] {tx.get('description') or tx.get('category','—')} — {sign}${float(tx['amount']):,.2f} ({fmt_date(tx.get('transaction_date'))})"
                if count > 10:
                    reply += f"\n_...and {count - 10} more._"

            elif action == "DELETE" and "balance" in data:
                reply += f"\n\n🗑️ Transaction deleted. New Balance: **${float(data['balance']):,.2f}**"
                st.session_state.balance = float(data["balance"])

            elif action == "UPDATE" and "transaction" in data:
                tx = data["transaction"]
                reply += f"\n\n✏️ Transaction #{tx['transaction_id']} updated. New Balance: **${float(data.get('balance',0)):,.2f}**"
                st.session_state.balance = float(data.get("balance", 0))

            elif action == "SUMMARY" and "summary" in data:
                s = data["summary"]
                reply += f"\n\n📊 **Financial Summary**\n- 💰 Income: +${s['total_income']:,.2f}\n- 💸 Expenses: -${s['total_expense']:,.2f}\n- 📈 Net: {'+'if s['net_balance']>=0 else ''}${s['net_balance']:,.2f}\n- 🏦 Current Balance: **${s['current_balance']:,.2f}**\n- 📝 Transactions: {s['transaction_count']}"
                st.session_state.balance = float(s["current_balance"])

            elif action == "BALANCE" and "balance" in data:
                reply = f"💰 Your current balance is **${float(data['balance']):,.2f}**"
                st.session_state.balance = float(data["balance"])

        st.session_state.chat_history.append({"role": "assistant", "content": reply})
        st.rerun()

# ─── Main App ─────────────────────────────────────────────────────────────────

def main():
    if not st.session_state.logged_in:
        auth_page()
        return

    with st.sidebar:
        st.markdown("""
        <div style='padding-bottom:1rem;border-bottom:1px solid var(--border);margin-bottom:1.5rem'>
            <div class='logo'>💳 Expense Tracker</div>
            <div class='logo-sub'>Personal Finance Intelligence</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"<div style='font-size:0.85rem;color:var(--muted)'>Signed in as</div><div style='font-weight:600;margin-bottom:0.5rem'>{st.session_state.username}</div>", unsafe_allow_html=True)

        bal = st.session_state.balance
        bal_color = "#6ee7b7" if bal >= 0 else "#f87171"
        st.markdown(f"""
        <div style='background:var(--bg3);border:1px solid var(--border);border-radius:10px;padding:0.75rem 1rem;margin-bottom:1.5rem'>
            <div style='font-size:0.7rem;text-transform:uppercase;letter-spacing:0.1em;color:var(--muted)'>Balance</div>
            <div style='font-size:1.4rem;font-weight:700;color:{bal_color};font-family:"DM Mono",monospace'>{"+" if bal >= 0 else ""}${abs(bal):,.2f}</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("**Navigation**")
        nav_items = {
            "dashboard":    "🏠  Dashboard",
            "transactions": "📝  Transactions",
            "analytics":    "📊  Analytics",
            "ai_chat":      "🤖  AI Assistant",
        }
        for key, label in nav_items.items():
            if st.button(label, key=f"nav_{key}", use_container_width=True):
                st.session_state.active_tab = key
                st.rerun()

        st.markdown("---")
        if st.button("Sign Out", use_container_width=True, key="logout_btn"):
            api("POST", "/logout")
            for k in ["logged_in","token","user_id","username","balance","chat_history","active_tab"]:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()

    tab = st.session_state.get("active_tab", "dashboard")
    if tab == "dashboard":
        dashboard_page()
    elif tab == "transactions":
        transactions_page()
    elif tab == "analytics":
        analytics_page()
    elif tab == "ai_chat":
        llm_page()

if __name__ == "__main__":
    main()