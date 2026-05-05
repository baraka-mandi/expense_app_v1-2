# Expense Tracker — Personal Expense Management System

A full-stack personal finance application with AI-powered natural language transaction management, built with Python Flask, Streamlit, SQLite3, and Ollama (gemma3:4b).

---

## Project Structure

```
expense_app/
├── app.py            # Flask backend — REST API, database logic, validation
├── frontend.py       # Streamlit frontend — UI, pages, user interaction
├── run.py            # Single-terminal launcher (Flask + Streamlit)
├── db_test.py        # Database setup and connection verification script
├── diagnose.py       # Flask API network diagnostics script
├── requirements.txt  # Python dependencies
├── expenses.db       # SQLite3 database (auto-created on first run)
└── README.md         # This file
```

---

## Prerequisites

- Python 3.9+
- Ollama installed locally (for AI Chat feature only)

---

## Setup and Run

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Set up Ollama (for AI Chat)

In a **separate terminal**:

```bash
ollama serve
ollama pull gemma3:4b   # one-time download
```

### 3. Start the application

```bash
python run.py
```

Open your browser at **http://localhost:8501**

Press `Ctrl+C` to stop all services.

---

## Features

| Page | Description |
|------|-------------|
| Authentication | Register and login with username/password. Tokens stored in DB. |
| Dashboard | Live balance, monthly income/expense metrics, recent transactions, category breakdown |
| Transactions | Full CRUD — add, filter by date/type, edit, delete |
| Analytics | Monthly and all-time summaries; income vs. expense bar chart by category |
| Budgets | Set spending limits per category; live progress bar showing % of budget used |
| Categories | Create and manage custom income/expense categories per user |
| AI Assistant | Natural language chat interface backed by Ollama gemma3:4b; chat history persisted in DB |

### AI Assistant examples

```
"Add a $50 grocery expense"
"Record salary income of $2000"
"Show all transactions this month"
"What is my current balance?"
"Show this month's summary"
"Delete transaction #12"
```

---

## Database Schema

The database consists of six tables. Foreign key constraints are enforced via `PRAGMA foreign_keys = ON`.

---

### Users

Stores registered user accounts. Passwords are stored as SHA-256 hashes. Balance is automatically recalculated after every transaction change.

| Column | Type | Constraints |
|--------|------|-------------|
| user_id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| username | VARCHAR(50) | UNIQUE NOT NULL |
| password | VARCHAR(255) | NOT NULL (SHA-256 hash) |
| balance | DECIMAL(12,2) | DEFAULT 0.00 |
| last_login | DATETIME | |

---

### Category

Stores user-defined categories for classifying transactions. Each user has their own set of categories, seeded with defaults on registration. A category type controls whether it applies to income, expenses, or both.

| Column | Type | Constraints |
|--------|------|-------------|
| category_id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| user_id | INTEGER | NOT NULL, FK → Users(user_id) |
| name | VARCHAR(50) | NOT NULL |
| type | VARCHAR(10) | CHECK IN ('income', 'expense', 'both') |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP |

**Unique constraint:** (user_id, name) — a user cannot have two categories with the same name.

**Default categories seeded on registration:**

| Name | Type |
|------|------|
| Groceries | expense |
| Housing | expense |
| Transport | expense |
| Food & Dining | expense |
| Entertainment | expense |
| Shopping | expense |
| Health | expense |
| Education | expense |
| Utilities | expense |
| General | expense |
| Salary | income |
| Investment | income |
| Freelance | income |
| Other | both |

---

### Transactions

Records every financial transaction for a user. The `type` column distinguishes income (CREDIT) from expenses (DEBIT). The `balance` column in Users is recalculated after every insert, update, or delete on this table.

| Column | Type | Constraints |
|--------|------|-------------|
| transaction_id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| user_id | INTEGER | NOT NULL, FK → Users(user_id) |
| type | VARCHAR(10) | CHECK IN ('DEBIT', 'CREDIT') NOT NULL |
| category | VARCHAR(50) | |
| amount | DECIMAL(12,2) | NOT NULL |
| description | TEXT | |
| transaction_date | DATETIME | DEFAULT CURRENT_TIMESTAMP |
| last_update | DATETIME | DEFAULT CURRENT_TIMESTAMP |

---

### Budget

Allows users to set a spending limit for a category over a defined period. When budgets are retrieved, the API calculates how much has been spent in that category for the selected month and returns the remaining amount and percentage used.

| Column | Type | Constraints |
|--------|------|-------------|
| budget_id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| user_id | INTEGER | NOT NULL, FK → Users(user_id) |
| name | VARCHAR(100) | NOT NULL |
| category | VARCHAR(50) | NOT NULL |
| limit_amount | DECIMAL(12,2) | NOT NULL |
| period | VARCHAR(10) | CHECK IN ('monthly', 'weekly', 'yearly') DEFAULT 'monthly' |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP |

**Computed fields returned by GET /api/budgets (not stored):**

| Field | Description |
|-------|-------------|
| spent | Total DEBIT transactions in this category for the selected month |
| remaining | limit_amount − spent |
| percentage | (spent / limit_amount) × 100 |
| status | 'ok' (< 80%), 'warning' (≥ 80%), or 'over' (> 100%) |

---

### ChatLog

Persists every message exchanged between the user and the AI assistant. This allows chat history to survive page reloads and be audited.

| Column | Type | Constraints |
|--------|------|-------------|
| log_id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| user_id | INTEGER | NOT NULL, FK → Users(user_id) |
| role | VARCHAR(10) | CHECK IN ('user', 'assistant') NOT NULL |
| message | TEXT | NOT NULL |
| action | VARCHAR(20) | LLM action type (CREATE, READ, UPDATE, etc.) |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP |

---

### Tokens

Stores active authentication tokens. A token is issued on login and deleted on logout. All authenticated API requests must include the token in the `X-Auth-Token` header.

| Column | Type | Constraints |
|--------|------|-------------|
| token | TEXT | PRIMARY KEY |
| user_id | INTEGER | NOT NULL |
| username | TEXT | NOT NULL |

---

## Entity-Relationship Overview

```
Users ──< Transactions
Users ──< Category
Users ──< Budget
Users ──< ChatLog
Users ──< Tokens
```

All five child tables reference `Users(user_id)` with a foreign key. There is no direct foreign key between `Transactions.category` and `Category.name` — the category field is stored as a string so that existing transaction records remain valid if a category is renamed or deleted.

---

## Validation Rules

| Field | Rule |
|-------|------|
| Amount | Must be a positive number; maximum $1,000,000 |
| Username | 3–50 characters; letters, numbers, and underscores only |
| Password | 6–255 characters |
| Category name | Required; maximum 50 characters; unique per user |
| Budget name | Required; maximum 100 characters |
| Description | Maximum 500 characters |
| Date | Must be after 2000-01-01; no more than 1 year in the future |
| Chat message | Maximum 2000 characters |

---

## API Endpoints

### Authentication

| Method | Endpoint | Auth Required | Description |
|--------|----------|:---:|-------------|
| POST | `/api/register` | No | Create a new user account |
| POST | `/api/login` | No | Log in; returns auth token |
| POST | `/api/logout` | Yes | Invalidate the current token |
| GET | `/api/me` | Yes | Get current user info |

### Transactions

| Method | Endpoint | Auth Required | Description |
|--------|----------|:---:|-------------|
| GET | `/api/transactions` | Yes | List transactions (filters: start_date, end_date, category, type) |
| POST | `/api/transactions` | Yes | Create a new transaction |
| PUT | `/api/transactions/<id>` | Yes | Update an existing transaction |
| DELETE | `/api/transactions/<id>` | Yes | Delete a transaction |

### Summary and Balance

| Method | Endpoint | Auth Required | Description |
|--------|----------|:---:|-------------|
| GET | `/api/balance` | Yes | Get current balance |
| GET | `/api/summary` | Yes | Aggregated totals (optional: ?month=YYYY-MM) |

### Categories

| Method | Endpoint | Auth Required | Description |
|--------|----------|:---:|-------------|
| GET | `/api/categories` | Yes | List all categories (optional: ?type=income\|expense) |
| POST | `/api/categories` | Yes | Create a new category |
| PUT | `/api/categories/<id>` | Yes | Update a category |
| DELETE | `/api/categories/<id>` | Yes | Delete a category |

### Budgets

| Method | Endpoint | Auth Required | Description |
|--------|----------|:---:|-------------|
| GET | `/api/budgets` | Yes | List all budgets with live spending data (optional: ?month=YYYY-MM) |
| POST | `/api/budgets` | Yes | Create a new budget |
| PUT | `/api/budgets/<id>` | Yes | Update a budget |
| DELETE | `/api/budgets/<id>` | Yes | Delete a budget |

### Chat Logs

| Method | Endpoint | Auth Required | Description |
|--------|----------|:---:|-------------|
| GET | `/api/chat/logs` | Yes | Retrieve chat history (optional: ?limit=N, max 200) |
| DELETE | `/api/chat/logs` | Yes | Clear all chat history for the current user |

### AI Assistant

| Method | Endpoint | Auth Required | Description |
|--------|----------|:---:|-------------|
| POST | `/api/llm` | Yes | Send a natural language message; AI parses and executes action |

---

## Authentication Flow

1. Client sends `POST /api/login` with `{"username": "...", "password": "..."}`.
2. Server verifies credentials, issues a random 64-character hex token, stores it in the `Tokens` table.
3. Client includes `X-Auth-Token: <token>` header on all subsequent requests.
4. Server looks up the token on every authenticated request via the `@login_required` decorator.
5. `POST /api/logout` deletes the token row, invalidating the session.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Port 5000 in use | `lsof -ti:5000 \| xargs kill` |
| Port 8501 in use | `lsof -ti:8501 \| xargs kill` |
| "Ollama unavailable" | Run `ollama serve` in a separate terminal |
| Model not found | Run `ollama pull gemma3:4b` |
| Empty category dropdown | Log out and log back in to trigger category seeding |
