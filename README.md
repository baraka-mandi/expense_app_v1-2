# 💳 Expense Tracker — Personal Expense Management System

A full-stack personal finance app with AI-powered natural language transaction management,
built with Python Flask, Streamlit, SQLite3, and Ollama (gemma3:1b).

---

## 📁 Project Structure

```
expense_app/
├── app.py            # Flask backend — REST API & database logic
├── frontend.py       # Streamlit frontend — UI & user interaction
├── run.py            # Single-terminal launcher
├── requirements.txt  # Python dependencies
├── expenses.db       # SQLite3 database (auto-created on first run)
└── README.md         # This file
```

---

## ⚙️ Prerequisites

- Python 3.9+
- Ollama installed on your Mac (for AI Chat feature)

---

## 🚀 Setup & Run

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Set up Ollama (for AI Chat)

In a **separate terminal**:

```bash
ollama serve
ollama pull gemma3:1b   # one-time only
```

### 3. Start the application

```bash
python run.py
```

Open your browser at **http://localhost:8501**

Press `Ctrl+C` to stop all services.

---

## 🖥️ Features

- **Authentication** — Register & login with username/password
- **Dashboard** — Balance, monthly metrics, recent transactions, category breakdown
- **Transactions** — Full CRUD: add, view (with filters), edit, delete
- **Analytics** — Monthly summaries, category breakdown, bar charts
- **AI Assistant** — Natural language interface via Ollama (gemma3:1b)

### AI examples:
- `"Add a $50 grocery expense"`
- `"Record salary income of $2000"`
- `"Show all transactions this month"`
- `"What is my current balance?"`
- `"Show this month's summary"`

---

## 🗄️ Database Schema

### Users
| Column | Type |
|--------|------|
| user_id | INTEGER PK |
| username | VARCHAR(50) UNIQUE |
| password | VARCHAR(255) — SHA-256 hash |
| balance | DECIMAL(12,2) — auto-updated |
| last_login | DATETIME |

### Transactions
| Column | Type |
|--------|------|
| transaction_id | INTEGER PK |
| user_id | INTEGER FK |
| type | DEBIT or CREDIT |
| category | VARCHAR(50) |
| amount | DECIMAL(12,2) |
| description | TEXT |
| transaction_date | DATETIME |
| last_update | DATETIME |

---

## 🔌 API Endpoints

| Method | Endpoint | Auth |
|--------|----------|------|
| POST | `/api/register` | No |
| POST | `/api/login` | No |
| POST | `/api/logout` | Session |
| GET  | `/api/balance` | Session |
| GET  | `/api/transactions` | Session |
| POST | `/api/transactions` | Session |
| PUT  | `/api/transactions/<id>` | Session |
| DELETE | `/api/transactions/<id>` | Session |
| GET  | `/api/summary` | Session |
| POST | `/api/llm` | Session |

---

## 🛠️ Troubleshooting

| Issue | Fix |
|-------|-----|
| Port 5000 in use | `lsof -ti:5000 \| xargs kill` |
| Port 8501 in use | `lsof -ti:8501 \| xargs kill` |
| "Ollama unavailable" | Run `ollama serve` in a separate terminal |
| Model not found | Run `ollama pull gemma3:1b` |
