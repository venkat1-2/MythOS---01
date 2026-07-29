# Working Notes — AI Financial Copilot for MSMEs

## Project Structure

```
MythOS/
├── backend/
│   ├── main.py           ← FastAPI server (all API endpoints)
│   └── requirements.txt  ← Python dependencies
└── frontend/
    └── index.html        ← Full React app (CDN-based, no build step)
```

## How to Run

```powershell
# From the backend/ directory:
python -m uvicorn main:app --port 8000
```

Then open **http://localhost:8000/** in the browser.

> The frontend is served as a static file by FastAPI — no separate dev server needed.

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET  | `/api/health`                     | Health check |
| GET  | `/api/cash-flow`                  | Mock monthly inflow/outflow + working capital |
| GET  | `/api/risk-radar`                 | MSME risk scores & mitigation suggestions |
| GET  | `/api/loan-score`                 | Credit score, gauge chart data, lender matches |
| POST | `/api/loan-score/calculate`       | Recalculate rule-based score with custom inputs |
| GET  | `/api/scheme-finder`             | Govt MSME subsidy & scheme matches |
| POST | `/api/chat`                       | AI Copilot chat (contextual MSME advice) |
| POST | `/api/cash-flow/analyze-csv`      | Upload CSV → WMA projection + breach alerts |
| GET  | `/api/cash-flow/sample-csv`       | Download 90-day sample bank statement CSV |

### CSV Analyze Endpoint (POST `/api/cash-flow/analyze-csv`)

**Form fields:**
- `csv_text` (string) — raw CSV content, OR
- `file` (file upload) — multipart file
- `threshold` (float, default `500000`) — safety balance threshold in ₹

**Returns:**
```json
{
  "summary": {
    "total_transactions": 123,
    "date_range_start": "2026-04-26",
    "date_range_end": "2026-07-25",
    "current_balance": 12968842.06,
    "rolling_avg_daily_inflow": 138591.2,
    "rolling_avg_daily_outflow": 91234.5,
    "projected_daily_net": 123259.63
  },
  "historical_chart": [{ "date": "...", "balance": 0.0 }],
  "forecast_chart":   [{ "date": "...", "balance": 0.0 }],
  "alerts": [],
  "first_breach": null
}
```

---

## CSV Format (for Upload)

```csv
date,description,amount
2026-04-26,Opening Balance Transfer,4200000.00
2026-04-27,Client Payment - Apex Auto Corp,342150.50
2026-04-27,Salary Disbursement,-95000.00
```

- `amount` positive = inflow, negative = outflow
- Dates must be YYYY-MM-DD

---

## Forecasting Algorithm

1. **Aggregate** all transactions by date → daily net flow
2. **Cumulative balance** series built from start
3. **30-day rolling average** inflow & outflow computed from last 30 trading days
4. **WMA (Weighted Moving Average)** over last 30 daily nets:
   - Weights: `[1, 2, 3, …, 30]` — most recent day weighted highest
   - `daily_wma_net = Σ(net_i × weight_i) / Σ(weights)`
5. **Project** next 30 days: `balance[t+1] = balance[t] + daily_wma_net`
6. **Breach detection**: flag any projected day where `balance < threshold`

---

## Loan Score Weighted Rule-Based Scorer

The **Loan Score** tab evaluates creditworthiness using a weighted multi-factor rule-based algorithm:

### Factors & Weights

| Factor | Weight | Scoring Rule |
|--------|--------|--------------|
| **GST Filing Consistency** | **30%** | Direct 0–100 compliance rating (GSTR-3B & GSTR-1 timeliness) |
| **Overdue Invoice Ratio** | **25%** | `max(0, 100 - (Overdue_% × 2.5))` (% receivables overdue > 30d) |
| **Bank Balance Stability** | **25%** | Direct 0–100 stability index (inverse 90-day cashflow variance) |
| **Existing Debt Ratio** | **20%** | Direct 0–100 solvency & DSCR capacity rating |

### Scoring Output & Features
- **Overall Score**: Weighted sum `(0 – 100)`
- **CIBIL Rating Equivalent**: Mapped `(300 – 900)`
- **Credit Tier**: Prime MSME (≥85), Standard Eligible (≥70), Moderate Risk (≥50), High Risk (<50)
- **Top Score Drag Callout**: Automatically identifies which factor incurs the largest point penalty (`(100 - score) × weight`)
- **Actionable Advice**: Generates 2–3 targeted recommendations based on lowest-scoring factors
- **Interactive UI**: SVG semi-circle Gauge Chart with real-time parameter sliders

---

## Natural Language AI Copilot Chat Interface (Claude API Integration)

The **Chat** tab connects to `/api/chat`, serializing the company's real-time financial telemetry directly into the system prompt context:

### Serialized Context Injected into Claude Prompt:
- **Cash Flow Telemetry**: Bank balance (₹48.5L), net monthly cashflow (+₹5.5L/mo), runway (5.4 months), DSO (42 days), upcoming GST tax liability (₹420,000 due Aug 20).
- **Loan & Credit Telemetry**: Overall Loan Score (75.8/100), CIBIL equivalent (754/900), pre-approved limit (₹50 Lakhs), primary score drag (Overdue invoice ratio), matched bank offers.
- **Risk Telemetry**: Overall Risk (28/100), customer concentration risk (Apex Auto 38%), single-supplier risk (Zenith Metals 80%), DSCR (1.85x).
- **Government Schemes**: CGTMSE (98% match), ZED Certification (92% match).

### Scenario & Query Capabilities:
- **Hiring Decisions**: e.g., *"Can I hire 3 more employees?"* → Calculates payroll cost addition (~₹1.05L/mo), computes post-hiring surplus (+₹4.45L/mo), verifies GST tax reserve (₹4.2L), and returns a concrete recommendation referencing actual numbers.
- **Loan & Credit Line Queries**: Recommends SBI MSME Express @ 9.2% interest backed by CGTMSE.
- **Risk & Concentration Queries**: Suggests early payment discount strategies to reduce receivables risk.

### Multi-Turn Conversation Thread & History Carry-Over:
- **State Persistence**: React state maintains the complete `messages` array (`[{sender, text, insights, suggested}]`).
- **Request Payload**: Sends `history: [{role: 'user'|'assistant', content: string}]` along with the current question to `POST /api/chat`.
- **Claude Multi-Turn Context**: Injects `history` array into the messages pipeline so follow-up queries seamlessly reference earlier calculations.
- **Tested 3-Turn Flow Verification**:
  1. *Q1: "Can I hire 3 more employees?"* → Calculates +₹1.05L/mo salary addition, adjusted surplus +₹4.45L/mo.
  2. *Q2: "What about 5 employees instead?"* → Updates payroll addition to +₹1.75L/mo, adjusted surplus +₹3.75L/mo, explicitly contrasting with Turn 1.
  3. *Q3: "Will that impact our GST tax payment next month?"* → Validates that ₹4.20L GST due Aug 20 is 11.5x covered by the ₹48.5L cash balance and positive net surplus (+₹3.75L/mo).

---

## Global Risk Intelligence Module (New Tab)

The **Global Risk Intelligence** tab (`/api/global-risk`) translates macro global events (tariffs, sanctions, commodity spikes, shipping disruptions, currency moves) into specific impact estimates for the active business profile.

### Key Architecture & Logic:
- **Business Exposure Profile**: Configured for Textile & Technical Fabrics (materials: *polyester, cotton, dyes, yarn*; supplier countries: *China, Vietnam, USA, Germany*; currencies: *USD, INR, EUR*).
- **Macro Events Engine**: Scans 6 structured global macro events tagged by materials, countries, and currencies.
- **Rule-Based Matching (No LLM dependency)**: Overlaps event tags with the business exposure profile. Filters out irrelevant events (e.g. Cobalt/Lithium sanctions, Wheat export bans).
- **Estimated Impact Cards**: Generates severity-coded cards (High / Medium / Low Opportunity) with:
  1. *Why This Affects You* — contextual explanation of supply chain vulnerability.
  2. *Estimated Impact Range* — range-based estimates (e.g., `8–14% cost increase`, `2–4 week delay`).
  3. *Recommended Action* — concrete risk mitigation steps (price locks, currency hedging, supplier diversification).

---

## Dashboard Tabs

| Tab | Status | Notes |
|-----|--------|-------|
| Cash Flow | ✅ Built + CSV Forecasting Module | Mock data + CSV upload/WMA engine live |
| Risk Radar | ✅ Built | Mock local financial telemetry |
| Loan Score | ✅ Built + Interactive Rule-Based Scorer | SVG Gauge chart, weighted factor breakdown, drag alert, live sliders |
| Scheme Finder | ✅ Built | Mock data |
| Global Risk Intel | ✅ Built + Macro Event Matcher | Rule-based matching engine, exposure profile, severity impact cards |
| AI Copilot Chat | ✅ Built + Multi-Turn Thread & Context Serializer | Full scrolling chat thread with conversation history & Claude API integration |

---

## Python Dependencies

```
fastapi
uvicorn
pydantic
python-multipart
anthropic
```

Install: `pip install fastapi uvicorn pydantic python-multipart anthropic`

---

## Change Log

| Date | Change |
|------|--------|
| 2026-07-22 | Initial full-stack shell — 5 tabs, all mock data APIs |
| 2026-07-22 | Fixed JSX comment syntax causing blank screen |
| 2026-07-25 | Added CSV Forecasting Module (WMA engine, threshold alerts, red zone chart) |
| 2026-07-25 | Installed `python-multipart` for form/file upload support |
| 2026-07-25 | Built rule-based Loan Scorer (SVG Gauge Chart, 4 weighted factors, top drag callout, live sliders) |
| 2026-07-25 | Built Natural Language Chat Copilot with serialized business telemetry & Claude API integration |
| 2026-07-25 | Multi-turn chat thread upgrade: full state history persistence & multi-turn context carry-over verified |
| 2026-07-28 | Built **Global Risk Intelligence** tab — rule-based macro event matcher, textile exposure profile, range impact cards |




