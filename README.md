POLARIS — AI-Powered MSME Business Intelligence Platform

An AI financial copilot for Indian MSMEs (Micro, Small & Medium Enterprises) that turns scattered financial signals — bank balances, GST filings, receivables, supplier exposure, global macro events — into a single dashboard with actionable, data-grounded advice.

Built by **Team MythOS**.

---

## What it does

MythOS gives an MSME owner one place to see and act on their financial position:

| Module | What it shows |
|---|---|
| **Cash Flow** | Monthly inflow/outflow, working capital, and a CSV-upload forecasting engine (30-day weighted moving average projection with breach-threshold alerts) |
| **Risk Radar** | Customer concentration, supplier dependency, and other business risk scores |
| **Loan Score** | A weighted, rule-based creditworthiness score (GST filing consistency, overdue invoices, bank stability, debt ratio) mapped to a CIBIL-equivalent rating, credit tier, and targeted improvement actions |
| **Scheme Finder** | Matches the business against government MSME subsidy and scheme eligibility |
| **Global Risk Intelligence** | Translates global macro events (tariffs, sanctions, commodity spikes, shipping disruptions, currency moves) into specific impact estimates based on the business's material, supplier-country, and currency exposure |
| **AI Copilot Chat** | A Claude-powered assistant that answers financial questions using the business's real, live telemetry — with full multi-turn conversation memory |

## How it's built

```
MythOS/
├── backend/
│   ├── main.py              ← FastAPI server (all API endpoints & business logic)
│   └── requirements.txt     ← Python dependencies
├── frontend/
│   └── index.html           ← Full React app (CDN-based, no build step)
├── requirements.txt         ← Root-level dependency list (used for local dev)
└── working.md               ← Detailed engineering notes, algorithms, and changelog
```

- **Backend:** FastAPI, serving both the REST API and the static frontend.
- **Frontend:** A single-file React app loaded via CDN — no bundler required to run it.
- **AI Copilot:** Uses the Anthropic Claude API, with a condensed, topic-aware business context injected into the system prompt (not a raw data dump) so responses stay grounded in real numbers.
- **Forecasting & scoring:** Cash-flow projection and the loan scorer are rule-based and deterministic — no LLM dependency, so they're fast, explainable, and don't require an API key to work.

## Getting started

### 1. Install dependencies

```bash
pip install -r backend/requirements.txt
```

### 2. Configure your Claude API key (optional — enables the AI Copilot chat)

Create a `key.env` file inside `frontend/`:

```
ANTHROPIC_API_KEY=your-api-key-here
```

Without this, every other module still works — only the Copilot chat tab will show a "no API key configured" message instead of live AI responses.

### 3. Run the server

```bash
cd backend
python -m uvicorn main:app --port 8000
```

### 4. Open the app

Visit **http://localhost:8000/** — the frontend is served directly by FastAPI, so there's no separate dev server to start.

## API reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/cash-flow` | Monthly inflow/outflow + working capital |
| `GET` | `/api/risk-radar` | MSME risk scores & mitigation suggestions |
| `GET` | `/api/loan-score` | Credit score, gauge chart data, lender matches |
| `POST` | `/api/loan-score/calculate` | Recalculate the rule-based score with custom inputs |
| `GET` | `/api/scheme-finder` | Government MSME subsidy & scheme matches |
| `GET` | `/api/global-risk` | Macro event impact matching against business exposure |
| `POST` | `/api/global-risk/match` | Match macro events against a custom exposure profile |
| `POST` | `/api/chat` | AI Copilot chat (contextual MSME advice, multi-turn) |
| `POST` | `/api/cash-flow/analyze-csv` | Upload a bank statement CSV → WMA projection + breach alerts |
| `GET` | `/api/cash-flow/sample-csv` | Download a sample 90-day bank statement CSV |

### CSV upload format

```csv
date,description,amount
2026-04-26,Opening Balance Transfer,4200000.00
2026-04-27,Client Payment - Apex Auto Corp,342150.50
2026-04-27,Salary Disbursement,-95000.00
```

- `amount`: positive = inflow, negative = outflow
- Dates are parsed flexibly (`YYYY-MM-DD`, `DD-MM-YYYY`, `MM-DD-YYYY`), but `YYYY-MM-DD` is preferred

For full algorithm details (the weighted moving average forecast, the loan-score weighting formula, and how business context gets serialized into the Claude prompt), see [`working.md`](./working.md).

## Tech stack

- **Backend:** FastAPI, Pydantic, Uvicorn
- **AI:** Anthropic Claude API (`claude-3-5-sonnet-20241022`)
- **Frontend:** React (CDN), Recharts, Lucide icons
- **Data:** Rule-based scoring engines + CSV parsing (no ML model dependency for core financial logic)

## Status

| Tab | Status |
|---|---|
| Cash Flow | ✅ Built + CSV forecasting engine |
| Risk Radar | ✅ Built (mock telemetry) |
| Loan Score | ✅ Built — interactive weighted scorer with live sliders |
| Scheme Finder | ✅ Built (mock data) |
| Global Risk Intel | ✅ Built — rule-based macro event matcher |
| AI Copilot Chat | ✅ Built — multi-turn, Claude-integrated |

---

*Built for the MSME IDEA Hackathon 6.0.*
