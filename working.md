# Working Notes — AI Financial Copilot for MSMEs

## Project Structure

```
MythOS/
├── backend/
│   ├── main.py           ← FastAPI server (all API endpoints & telemetry calculation engine)
│   └── requirements.txt  ← Python dependencies (FastAPI, google-genai, etc.)
└── frontend/
    ├── index.html        ← Full React app (CDN-based, standalone UI)
    └── key.env           ← Environment variables (GEMINI_API_KEY)
```

## How to Run

1. Configure your Gemini API key in `frontend/key.env`:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

2. Run the FastAPI server from the `backend/` directory:
   ```powershell
   python -m uvicorn main:app --port 8000
   ```

3. Open **http://localhost:8000/** in your browser.

> The frontend is served directly as static content by FastAPI — no separate node/webpack build step is required.

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET  | `/api/health`                         | Health check |
| GET  | `/api/cash-flow`                      | Demo monthly inflow/outflow + working capital |
| POST | `/api/cash-flow/analyze-csv`          | Upload CSV → WMA 30-day projection + breach alerts |
| POST | `/api/cash-flow/analyze-csv-full`     | Upload CSV → Derives full business telemetry across all tabs |
| POST | `/api/cash-flow/analyze-ledger-photo` | Upload photo of handwritten paper ledger → Gemini Vision OCR extraction |
| GET  | `/api/cash-flow/sample-csv`           | Download 90-day sample bank statement CSV |
| GET  | `/api/risk-radar`                     | Demo MSME risk scores & mitigation suggestions |
| GET  | `/api/loan-score`                     | Demo credit score, gauge chart data, lender matches |
| POST | `/api/loan-score/calculate`           | Recalculate rule-based score with custom parameter inputs |
| GET  | `/api/scheme-finder`                 | Demo Govt MSME subsidy & scheme matches |
| GET  | `/api/global-risk`                    | Demo macro event impact matcher & exposure profile |
| POST | `/api/global-risk/match`              | Match global macro risk events against custom business exposure profile |
| POST | `/api/chat`                           | AI Copilot chat (live Gemini multi-turn advisor with topic-aware context) |

---

## Data Analysis & Endpoints Overview

### 1. CSV Telemetry Engine (`_derive_all_from_csv`)
- **100% Pure Python Arithmetic**: Derives full telemetry for Cash Flow, Loan Score, Risk Radar, and Scheme Finder dynamically from uploaded transaction CSVs without any LLM calls.
- **Customer Revenue Concentration**: Groups inflows by payer description (excluding opening balances) to determine top customer share.
- **Bank Balance Stability Index**: Calculates variance and coefficient of variation (CoV) of daily balances to derive a 30–98 stability score.
- **Dynamic Loan Score Re-calculation**: Feeds CSV-derived metrics (overdue ratio, bank stability CoV, debt capacity) into `_compute_loan_score()`.
- **Honest Working Capital Estimates**: Deliberately estimates Accounts Receivable (~45% of monthly inflow) and Accounts Payable (~35% of monthly outflow) as honest approximations, clearly labeled as estimates since transaction logs do not contain invoice due dates.
- **Scheme Finder Matching (`_match_schemes`)**: Matches annual turnover (`monthly_inflow × 12`) and creditworthiness against Udyam MSME categories (Micro, Small, Medium) and scheme criteria.

### 2. Ledger Photo OCR (`/api/cash-flow/analyze-ledger-photo`)
- **Gemini Vision Engine**: Uses `gemini-3.6-flash` via the `google.genai` SDK to extract structured transaction rows (`date`, `description`, `amount`, `confidence`) from photos of handwritten Indian paper ledgers (bahi-khata).
- **MSME Ledger Features**: Handles mixed English and regional scripts (Tamil, Hindi, Gujarati, Kannada, Telugu, Bengali), converts regional numerals (e.g., Tamil ௧ ௨ ௩ or Devanagari १ २ ३) to Arabic digits, interprets direction shorthand (Jama/Kharch, Cr/Dr, In/Out), filters out running balance columns, and respects struck-through corrections.
- **Low-Confidence Flagging**: Flags entries as `"confidence": "low"` when smudges or handwriting ambiguity exist so users can review before committing.
- **Requires**: `GEMINI_API_KEY` configured in `frontend/key.env`.

---

## CSV Format (for Upload)

```csv
date,description,amount
2026-04-26,Opening Balance Transfer,4200000.00
2026-04-27,Client Payment - Apex Auto Corp,342150.50
2026-04-27,Salary Disbursement,-95000.00
```

- `amount`: Positive = inflow, Negative = outflow
- `date`: YYYY-MM-DD format

---

## Forecasting Algorithm

1. **Daily Net Flow Aggregation**: Aggregates all transactions by date to build the daily net flow and cumulative balance series.
2. **30-Day Rolling Averages**: Computes daily rolling average inflow & outflow over the last 30 active trading days.
3. **30-Day WMA Projection**: Computes Weighted Moving Average over the last 30 daily nets (`weight = 1..30`):
   $$\text{daily\_wma\_net} = \frac{\sum_{i=1}^{30} (\text{net}_i \times i)}{\sum_{i=1}^{30} i}$$
   Projects future daily balances: $\text{balance}_{t+1} = \text{balance}_t + \text{daily\_wma\_net}$.
4. **6-Month Overview Consistency**: Aggregates actual historical months from the CSV, then projects 3 future months using the exact same rolling averages ($\text{rolling\_avg\_inflow} \times 30$, $\text{rolling\_avg\_outflow} \times 30$, $\text{daily\_wma\_net} \times 30$). Both 30-day and 6-month views derive from one unified calculation engine.
5. **Breach Detection**: Identifies any projected day where $\text{balance} < \text{threshold}$.

---

## Cash Strain Alerts Engine (`_detect_cash_strain_alerts`)

Scans raw transaction rows for recurring outflow obligations across 6 specific categories:
1. **Salary**: Keywords (`salary`, `staff`, `wages`, `payroll`)
2. **EMI**: Keywords (`emi`, `loan`, `mortgage`, `nbfc`, `equated`)
3. **Rent**: Keywords (`rent`, `lease`, `premises`, `factory`, `unit`)
4. **Tax**: Keywords (`gst`, `tax`, `tds`, `advance tax`, `challan`)
5. **Utility**: Keywords (`electricity`, `power`, `utility`, `water`, `msedcl`)
6. **Vendor**: Keywords (`vendor`, `material`, `logistics`, `freight`, `supplier`, `purchase`)

- **Projections**: Estimates next due date (~30 days from last detected transaction) and average obligation amount.
- **Severity Rating**: Marked `high` if average obligation exceeds 25% of threshold or current balance is less than 1.5x obligation amount; otherwise `medium`.
- **Fallback**: If no keyword pattern matches, extracts the top 3 largest negative transactions as fallback strain alerts.

---

## Loan Score Weighted Rule-Based Scorer

Evaluates creditworthiness using a weighted multi-factor rule-based algorithm (`_compute_loan_score`):

| Factor | Weight | Scoring Rule |
|--------|--------|--------------|
| **GST Filing Consistency** | **30%** | Direct 0–100 compliance rating (GSTR-3B & GSTR-1 timeliness) |
| **Overdue Invoice Ratio** | **25%** | $\max(0, 100 - (\text{Overdue\_Ratio} \times 2.5))$ |
| **Bank Balance Stability** | **25%** | Direct 0–100 stability index (inverse 90-day cashflow CoV) |
| **Existing Debt Ratio** | **20%** | Direct 0–100 solvency & DSCR capacity rating |

- **Overall Score**: Weighted sum $(0 - 100)$
- **CIBIL Equivalent**: Mapped scale $(300 - 900)$
- **Credit Tier**: Prime MSME ($\ge 85$), Standard Eligible ($\ge 70$), Moderate Risk ($\ge 50$), High Risk ($< 50$)
- **Top Score Drag Callout**: Automatically identifies factor incurring largest point penalty
- **Actionable Suggestions**: Generates targeted recommendations for lowest scoring factors

---

## Natural Language AI Copilot Chat Interface (Gemini API Integration)

The `/api/chat` endpoint provides a fully live, multi-turn AI advisor powered by **Gemini 3.6 Flash** via the `google.genai` SDK:

### Architecture & Features:
- **Live Gemini Integration**: Uses `client.models.generate_content(model="gemini-3.6-flash", ...)` with `GEMINI_API_KEY` from `frontend/key.env`.
- **Topic-Aware Context Injection (`_build_context_for_question`)**: Analyzes user question keywords and appends only relevant telemetry sections (Cash Flow, Loan Score, Risk Radar, Scheme Finder, Monthly Forecast) to the system prompt rather than dumping unnecessary data.
- **Multi-Turn Continuity**: Sends full message history (`payload.history`) to Gemini so follow-up queries (e.g., *"What if we hire 5 employees instead?"*) seamlessly reference previous calculations.
- **Zero Fallback/Hardcoding**: Every chat response is generated live by Gemini — no hardcoded templates or offline fallback modes exist.

---

## Global Risk Intelligence Engine (`_match_global_events`)

Translates global macro events (tariffs, sanctions, commodity price shifts, shipping bottlenecks, currency moves) into business impact assessments.

### Architecture & Features:
- **Exposure Matching**: Rule-based matching engine comparing event tags against business raw materials, supplier countries, export markets, and currency exposures.
- **Typed Trigger Labels**: Returns typed trigger objects (`material`, `country`, `currency`) so the frontend renders appropriate phrasing (`Affects Your: [Material]`, `Related Country: [Country]`, `Currency Impact: [Code]`) and correct acronym casing (e.g. `USA`, `USD`, `INR`).
- **Uploaded Profile Match Endpoint (`POST /api/global-risk/match`)**: Accepts custom business exposure profiles generated from CSV uploads to compute profile-specific global risk impact cards on the fly.

### Live Market Indicators Component (`LiveMarketIndicators`)
- **4 Live Market Cards**: Rendered at the top of the Global Risk Intelligence tab (`frontend/index.html`):
  1. **USD/INR Exchange Rate**: Fetched live from Frankfurter API (`https://api.frankfurter.dev/v1/latest?from=USD&to=INR`).
  2. **Crude Oil Price**: Fetched live from World Bank API (`indicator/EP.PMP.SGAS.CD`).
  3. **Cotton Price**: Fetched live from World Bank API (`indicator/PCOTTIND.USD`).
  4. **India Inflation (CPI)**: Fetched live from World Bank API (`indicator/FP.CPI.TOTL.ZG`, country `IN`).
- **Client-Side Caching**: Implements `sessionStorage` caching (`live_market_indicators_cache_v2`) so indicators persist across tab navigation without redundant network requests.
- **Profile Independence**: Explicitly independent of business profile state — renders identically in both Demo Data and My Business profile modes and does not rely on any profile-specific data.

### Language Selection Feature (English / Tamil)
- **App-Level State**: Single `lang` state (`'en'` / `'ta'`) stored at root `App()` component, with header dropdown selector (`🌐 English / தமிழ்`).
- **Single Shared Source of Truth**: Centralized `LABELS` dictionary mapping UI keys for both English and Tamil, consumed across all 6 views and modals.
- **AI Copilot Multilingual Reasoning**: `ChatRequest` endpoint (`POST /api/chat`) accepts `language` param (`'en'` / `'ta'`) and injects system instructions directing Gemini 3.6 Flash to output responses in Tamil when `'ta'` is active.

---

## Dashboard Tabs Status

| Tab | Demo Data Profile Mode | My Business Profile Mode (CSV / Ledger Upload) |
|-----|------------------------|------------------------------------------------|
| **Cash Flow** | ✅ Live (Hardcoded sample data & alerts) | ✅ Live (Pure Python 30-day WMA + 6-month forecast + strain alerts) |
| **Risk Radar** | ✅ Live (Hardcoded MSME metrics) | ✅ Live (Derived dynamically from CSV concentration & outflow CoV) |
| **Loan Score** | ✅ Live (Interactive sliders & gauge chart) | ✅ Live (Re-calculated from CSV overdue ratio & stability CoV) |
| **Scheme Finder** | ✅ Live (Catalog of MSME schemes) | ✅ Live (Filtered by CSV-derived annual turnover & Udyam tier) |
| **Global Risk Intel** | ✅ Live (Standard Textile profile matcher + Live Market Indicators) | ✅ Live (Custom matched against uploaded exposure profile + Live Market Indicators) |
| **AI Copilot Chat** | ✅ Live (Gemini 3.6 Flash + Topic-aware context) | ✅ Live (Gemini 3.6 Flash + CSV Telemetry context) |

---

## Python Dependencies

```
fastapi
uvicorn
pydantic
python-multipart
google-genai
python-dotenv
```

Install command:
```powershell
pip install fastapi uvicorn pydantic python-multipart google-genai python-dotenv
```

---

## Change Log

| Date | Change |
|------|--------|
| 2026-07-22 | Initial full-stack shell — 5 tabs, all mock data APIs |
| 2026-07-25 | Added CSV Forecasting Module (WMA engine, threshold alerts, red zone chart) |
| 2026-07-25 | Built rule-based Loan Scorer (SVG Gauge Chart, 4 weighted factors, top drag callout, live sliders) |
| 2026-07-28 | Built **Global Risk Intelligence** tab — rule-based macro event matcher, textile exposure profile, range impact cards |
| 2026-07-29 | Migrated LLM integration from Claude (Anthropic) to **Gemini 3.6 Flash** (`google.genai` SDK, `GEMINI_API_KEY` in `frontend/key.env`) |
| 2026-07-29 | Integrated topic-aware dynamic context builder (`_build_context_for_question`) for AI Copilot chat |
| 2026-07-29 | Implemented full CSV-derived telemetry engine (`_derive_all_from_csv`) for dynamic Risk Radar, Loan Score, and Scheme Finder |
| 2026-07-29 | Added Cash Strain Alerts pattern detection engine (`_detect_cash_strain_alerts`) for recurring outflows |
| 2026-07-29 | Added Ledger Photo OCR feature (`/api/cash-flow/analyze-ledger-photo`) with Gemini Vision for handwritten ledgers |
| 2026-07-29 | Added typed trigger labels (`material`/`country`/`currency`) and `/api/global-risk/match` endpoint for uploaded business profiles |
| 2026-07-29 | Integrated `LiveMarketIndicators` component (USD/INR via Frankfurter API, Crude/Cotton/CPI via World Bank API with `sessionStorage` caching) |
| 2026-08-14 | Added **Language Selection feature** (English / Tamil) — header selector, single shared `LABELS` lookup object, and Gemini system prompt language steering |
| 2026-08-14 | Fixed AI Copilot profile context resolution bug — updated `ChatRequest`, `_get_serialized_business_context`, and `copilot_chat` system prompt to dynamically inject active profile telemetry ("My Business" vs "Demo Data") |
| 2026-08-14 | Replaced hardcoded "Apex Auto" and "Zenith Metals" strings in `_build_context_for_question` with dynamic profile receivables and risk flags; added explicit Gemini API call logging |

