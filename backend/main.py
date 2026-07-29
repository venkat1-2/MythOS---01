import os
import csv
import io
import re
import json
import math
import logging
from pathlib import Path
from datetime import date, timedelta
from dotenv import load_dotenv

# Load key.env from frontend/ (where the file lives)
_env_path = Path(__file__).resolve().parent.parent / "frontend" / "key.env"
load_dotenv(dotenv_path=_env_path)

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

logger = logging.getLogger("copilot")
logging.basicConfig(level=logging.INFO)


app = FastAPI(
    title="AI Financial Copilot for MSMEs API",
    description="Backend API supplying mock financial analysis and insights for MSME dashboard.",
    version="1.0.0"
)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))

class ChatMessageItem(BaseModel):
    role: str      # "user" or "assistant"
    content: str   # text message

class ChatRequest(BaseModel):
    message: str
    active_tab: Optional[str] = "cashflow"
    history: Optional[List[ChatMessageItem]] = []

@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "fastapi-backend"}

@app.get("/api/cash-flow")
def get_cash_flow_data():
    return {
        "summary": {
            "current_balance": 4850000,
            "monthly_inflow": 3200000,
            "monthly_outflow": 2650000,
            "net_cashflow": 550000,
            "runway_months": 5.4,
            "burn_rate": 2650000,
            "currency": "INR",
            "currency_symbol": "₹"
        },
        "forecast_chart": [
            {"month": "Mar 2026", "inflow": 2800000, "outflow": 2400000, "net": 400000, "projected": False},
            {"month": "Apr 2026", "inflow": 3100000, "outflow": 2500000, "net": 600000, "projected": False},
            {"month": "May 2026", "inflow": 2950000, "outflow": 2600000, "net": 350000, "projected": False},
            {"month": "Jun 2026", "inflow": 3400000, "outflow": 2700000, "net": 700000, "projected": False},
            {"month": "Jul 2026", "inflow": 3200000, "outflow": 2650000, "net": 550000, "projected": False},
            {"month": "Aug 2026", "inflow": 3600000, "outflow": 2800000, "net": 800000, "projected": True},
            {"month": "Sep 2026", "inflow": 3850000, "outflow": 2900000, "net": 950000, "projected": True},
            {"month": "Oct 2026", "inflow": 3500000, "outflow": 3100000, "net": 400000, "projected": True}
        ],
        "working_capital": {
            "accounts_receivable": 1850000,
            "accounts_payable": 920000,
            "inventory_value": 1400000,
            "cash_on_hand": 4850000,
            "dso_days": 42, # Days Sales Outstanding
            "dpo_days": 28  # Days Payable Outstanding
        },
        "alerts": [
            {
                "id": "alt-1",
                "severity": "high",
                "title": "GST Q2 Tax Liability Payment",
                "due_date": "2026-08-20",
                "amount": 420000,
                "description": "Estimated GST liability payment coming up. Recommend setting aside ₹420k from July receivables."
            },
            {
                "id": "alt-2",
                "severity": "medium",
                "title": "Vendor Delayed Receivables Risk",
                "due_date": "2026-07-30",
                "amount": 650000,
                "description": "Apex Auto Corp payment is 14 days overdue. Impact on August inventory purchase."
            }
        ]
    }

@app.get("/api/risk-radar")
def get_risk_radar_data():
    return {
        "overall_score": 28,  # 0 to 100, lower is better risk index
        "risk_level": "Low-Moderate Risk",
        "health_status": "Healthy with Monitor Points",
        "last_updated": "2026-07-22",
        "metrics": [
            {
                "name": "Customer Concentration",
                "score": 62,
                "status": "Warning",
                "details": "Top client Apex Auto accounts for 38% of monthly revenue. Diversification recommended.",
                "category": "Revenue Risk"
            },
            {
                "name": "Debt Service Coverage (DSCR)",
                "score": 22, # low risk
                "status": "Optimal",
                "details": "DSCR is 1.85x. Net operating income comfortably covers monthly debt obligations.",
                "category": "Solvency Risk"
            },
            {
                "name": "Inventory Aging (>60 Days)",
                "score": 45,
                "status": "Moderate",
                "details": "₹380,000 worth of raw material stock aging beyond 60 days in warehouse B.",
                "category": "Operational Risk"
            },
            {
                "name": "Supplier Single-Source Risk",
                "score": 75,
                "status": "High",
                "details": "80% of aluminum alloy sourced from single vendor Zenith Metals.",
                "category": "Supply Chain"
            }
        ],
        "radar_chart_data": [
            {"subject": "Liquidity", "score": 85, "benchmark": 70},
            {"subject": "Solvency", "score": 82, "benchmark": 75},
            {"subject": "Operational", "score": 60, "benchmark": 80},
            {"subject": "Market Risk", "score": 74, "benchmark": 70},
            {"subject": "Compliance", "score": 92, "benchmark": 85}
        ],
        "mitigation_suggestions": [
            "Incentivize Apex Auto Corp for early payment (1.5% 10-net-30 discount).",
            "Onboard secondary supplier for aluminum alloy to reduce Zenith Metals bottleneck.",
            "Run discount clearance on 60+ day old inventory raw material."
        ]
    }

class LoanScoreInputs(BaseModel):
    gst_filing_score: float = 90.0         # 0 - 100
    overdue_invoice_ratio: float = 14.0   # % of receivables overdue >30d
    bank_stability_score: float = 78.0    # 0 - 100 stability index
    debt_ratio_score: float = 65.0        # 0 - 100 debt load health

def _compute_loan_score(inputs: LoanScoreInputs) -> Dict[str, Any]:
    # 1. GST Filing Consistency: 0-100 scale, weight = 30%
    s_gst = min(100.0, max(0.0, inputs.gst_filing_score))

    # 2. Overdue Invoice Ratio: % overdue receivables. 0% -> 100 score, 40%+ -> 0 score. Weight = 25%
    s_overdue = min(100.0, max(0.0, 100.0 - (inputs.overdue_invoice_ratio * 2.5)))

    # 3. Bank Balance Stability (90 days): 0-100 scale, weight = 25%
    s_stability = min(100.0, max(0.0, inputs.bank_stability_score))

    # 4. Existing Debt Ratio Score: 0-100 scale, weight = 20%
    s_debt = min(100.0, max(0.0, inputs.debt_ratio_score))

    weights = {
        "gst": 0.30,
        "overdue": 0.25,
        "stability": 0.25,
        "debt": 0.20
    }

    overall_score = round(
        s_gst * weights["gst"] +
        s_overdue * weights["overdue"] +
        s_stability * weights["stability"] +
        s_debt * weights["debt"],
        1
    )

    if overall_score >= 85:
        tier = "Prime MSME"
    elif overall_score >= 70:
        tier = "Standard Eligible"
    elif overall_score >= 50:
        tier = "Moderate Risk"
    else:
        tier = "High Risk / Review Required"

    cibil_equiv = int(300 + (overall_score / 100.0) * 600)

    factors = [
        {
            "id": "gst",
            "name": "GST Filing Consistency",
            "raw_input": f"{inputs.gst_filing_score:.0f}%",
            "score": round(s_gst, 1),
            "weight_pct": 30,
            "weighted_contrib": round(s_gst * weights["gst"], 1),
            "max_contrib": 30.0,
            "drag_penalty": round((100.0 - s_gst) * weights["gst"], 1),
            "status": "Excellent" if s_gst >= 85 else "Good" if s_gst >= 70 else "Warning" if s_gst >= 50 else "Critical",
            "detail": f"{inputs.gst_filing_score:.0f}% timely GSTR-3B & GSTR-1 filings over last 12 months"
        },
        {
            "id": "overdue",
            "name": "Overdue Invoice Ratio",
            "raw_input": f"{inputs.overdue_invoice_ratio:.1f}%",
            "score": round(s_overdue, 1),
            "weight_pct": 25,
            "weighted_contrib": round(s_overdue * weights["overdue"], 1),
            "max_contrib": 25.0,
            "drag_penalty": round((100.0 - s_overdue) * weights["overdue"], 1),
            "status": "Excellent" if s_overdue >= 85 else "Good" if s_overdue >= 70 else "Warning" if s_overdue >= 50 else "Critical",
            "detail": f"{inputs.overdue_invoice_ratio:.1f}% of receivables overdue > 30 days"
        },
        {
            "id": "stability",
            "name": "Bank Balance Stability (90-Day)",
            "raw_input": f"{inputs.bank_stability_score:.0f}/100",
            "score": round(s_stability, 1),
            "weight_pct": 25,
            "weighted_contrib": round(s_stability * weights["stability"], 1),
            "max_contrib": 25.0,
            "drag_penalty": round((100.0 - s_stability) * weights["stability"], 1),
            "status": "Excellent" if s_stability >= 85 else "Good" if s_stability >= 70 else "Warning" if s_stability >= 50 else "Critical",
            "detail": f"90-day cash flow variance score: {inputs.bank_stability_score:.0f}/100"
        },
        {
            "id": "debt",
            "name": "Existing Debt Ratio (Solvency)",
            "raw_input": f"{inputs.debt_ratio_score:.0f}/100",
            "score": round(s_debt, 1),
            "weight_pct": 20,
            "weighted_contrib": round(s_debt * weights["debt"], 1),
            "max_contrib": 20.0,
            "drag_penalty": round((100.0 - s_debt) * weights["debt"], 1),
            "status": "Excellent" if s_debt >= 85 else "Good" if s_debt >= 70 else "Warning" if s_debt >= 50 else "Critical",
            "detail": f"Debt service capacity score: {inputs.debt_ratio_score:.0f}/100"
        }
    ]

    sorted_drag = sorted(factors, key=lambda x: x["drag_penalty"], reverse=True)
    top_drag = sorted_drag[0] if sorted_drag and sorted_drag[0]["drag_penalty"] > 0 else None

    suggested_actions = []
    for f in sorted_drag:
        if len(suggested_actions) >= 3:
            break
        if f["id"] == "overdue" and f["score"] < 80:
            suggested_actions.append(f"Incentivize early payments (1.5% 10-net-30 discount) to reduce overdue invoices from {inputs.overdue_invoice_ratio:.1f}% to under 5%.")
        elif f["id"] == "gst" and f["score"] < 85:
            suggested_actions.append("File GSTR-1 and GSTR-3B at least 3 days prior to the 20th deadline to improve tax compliance rating.")
        elif f["id"] == "stability" and f["score"] < 80:
            suggested_actions.append("Maintain a minimum float of ₹5,00,000 to smooth out 90-day bank balance variance.")
        elif f["id"] == "debt" and f["score"] < 75:
            suggested_actions.append("Refinance high-interest short-term credit lines into CGTMSE collateral-free term loans.")

    if len(suggested_actions) < 2:
        suggested_actions.append("Upload audited FY 2024-25 balance sheet to unlock maximum pre-approved bank credit caps.")
    if len(suggested_actions) < 3:
        suggested_actions.append("Maintain clean 12-month bank repayment records to qualify for 0.50% interest rate concessions.")

    return {
        "overall_score": overall_score,
        "cibil_equivalent": cibil_equiv,
        "score_tier": tier,
        "inputs": inputs.dict(),
        "factors": factors,
        "top_drag_factor": top_drag,
        "suggested_actions": suggested_actions
    }


@app.get("/api/loan-score")
def get_loan_score_data():
    calc = _compute_loan_score(LoanScoreInputs())
    return {
        "credit_score": calc["cibil_equivalent"],
        "overall_score": calc["overall_score"],
        "score_tier": calc["score_tier"],
        "max_score": 900,
        "pre_approved_limit": 5000000,
        "recommended_term_months": 36,
        "est_interest_rate_range": "9.2% - 11.5% p.a.",
        "calculation": calc,
        "document_readiness": [
            {"doc": "Last 12 Months Bank Statement (API Synced)", "status": "Verified", "ready": True},
            {"doc": "GST Returns (GSTR-3B & GSTR-1)", "status": "Verified", "ready": True},
            {"doc": "Audited Balance Sheet (FY 2024-25)", "status": "Verified", "ready": True},
            {"doc": "Udyam MSME Registration Certificate", "status": "Verified", "ready": True},
            {"doc": "Provisional P&L (Q1 2026)", "status": "Pending Upload", "ready": False}
        ],
        "matched_lenders": [
            {
                "name": "State Bank of India (MSME Express)",
                "max_amount": 7500000,
                "interest_rate": "9.2% p.a.",
                "collateral_required": "CGTMSE Covered (Collateral Free)",
                "approval_probability": 94
            },
            {
                "name": "HDFC Bank Working Capital Line",
                "max_amount": 5000000,
                "interest_rate": "10.1% p.a.",
                "collateral_required": "Hypothecation of Stock & Receivables",
                "approval_probability": 89
            },
            {
                "name": "SIDBI Make in India Soft Loan",
                "max_amount": 10000000,
                "interest_rate": "8.5% p.a.",
                "collateral_required": "Machinery Charge",
                "approval_probability": 82
            }
        ]
    }


@app.post("/api/loan-score/calculate")
def calculate_loan_score_api(payload: LoanScoreInputs):
    calc = _compute_loan_score(payload)
    return {
        "credit_score": calc["cibil_equivalent"],
        "overall_score": calc["overall_score"],
        "score_tier": calc["score_tier"],
        "calculation": calc
    }

@app.get("/api/scheme-finder")
def get_scheme_finder_data():
    return {
        "schemes": [
            {
                "id": "sch-1",
                "title": "CGTMSE Collateral Free Credit Guarantee",
                "ministry": "Ministry of MSME, Govt of India",
                "match_percentage": 98,
                "max_benefit": "Up to ₹5 Crore collateral-free loan coverage",
                "category": "Credit Support",
                "target_sector": "Manufacturing & Services",
                "subsidy_nature": "85% Guarantee coverage on default to banks",
                "key_eligibility": "Udyam registered MSME with valid bank credit score > 700",
                "status": "Highly Recommended"
            },
            {
                "id": "sch-2",
                "title": "PMEGP (Prime Minister's Employment Generation Programme)",
                "ministry": "KVIC / Ministry of MSME",
                "match_percentage": 88,
                "max_benefit": "15% to 35% Capital Margin Subsidy",
                "category": "Subsidies & Grants",
                "target_sector": "New Manufacturing & Service units",
                "subsidy_nature": "Capital grant up to ₹50 Lakhs for Manufacturing",
                "key_eligibility": "Individuals above 18, SHGs, Firms under expansion",
                "status": "Eligible"
            },
            {
                "id": "sch-3",
                "title": "MSME ZED Certification Scheme (Zero Defect Zero Effect)",
                "ministry": "Ministry of MSME",
                "match_percentage": 92,
                "max_benefit": "80% Subsidy on Certification & Financial Support for Tech Upgrade",
                "category": "Quality & Tech Upgradation",
                "target_sector": "Manufacturing MSMEs",
                "subsidy_nature": "Up to ₹5 Lakhs for handholding and ₹50,000 subsidy on certification",
                "key_eligibility": "Udyam registered MSMEs with manufacturing premises",
                "status": "Highly Recommended"
            },
            {
                "id": "sch-4",
                "title": "PLI Scheme for Auto Components & Micro Tech",
                "ministry": "Ministry of Heavy Industries",
                "match_percentage": 76,
                "max_benefit": "8% to 13% Incentive on Incremental Sales",
                "category": "Production Linked Incentive",
                "target_sector": "Auto Components & Electronics",
                "subsidy_nature": "Quarterly cash payout based on audited turnover growth",
                "key_eligibility": "Minimum revenue threshold ₹10 Crore, investment > ₹1 Crore",
                "status": "Requires Scaling"
            }
        ]
    }


# ─────────────────────────────────────────────────────────────────────────────
# GLOBAL RISK INTELLIGENCE
# ─────────────────────────────────────────────────────────────────────────────

# Business exposure profile for Rajesh Engineering & Textile MSME
_BUSINESS_EXPOSURE = {
    "name": "Rajesh Textiles & Manufacturing",
    "sector": "Textile & Technical Fabrics (Manufacturing)",
    "materials": ["polyester", "cotton", "dyes", "yarn", "synthetic fabric"],
    "supplier_countries": ["china", "vietnam", "usa", "germany"],
    "export_markets": ["usa", "eu", "middle east"],
    "energy_dependent": True,
    "logistics_modes": ["sea freight", "road"],
    "currency_exposure": ["usd", "inr", "eur"],
}

# 6 structured global macro events
_GLOBAL_EVENTS = [
    {
        "id": "evt-001",
        "event_name": "China Anti-Dumping Duties on Polyester Staple Fiber Exports",
        "category": "tariff",
        "date": "2026-06-15",
        "region": "china / asia",
        "affected_materials": ["polyester", "synthetic fabric", "yarn"],
        "affected_countries": ["china"],
        "affected_currencies": [],
        "severity": "high",
        "description": "China has implemented new export tariff adjustments and anti-dumping regulations on polyester staple fiber and synthetic yarn exports to South Asia, causing immediate price shifts across Asian textile hubs.",
        "impact_templates": {
            "polyester": {
                "why_it_matters": "Polyester is your primary raw material input for synthetic weave production. Sourcing synthetic yarn from Chinese suppliers will see immediate tariff surcharges.",
                "estimated_impact": "Raw material cost increase: estimated 8-14% increase in polyester yarn procurement within 30-60 days.",
                "action": "Diversify polyester procurement to domestic Indian suppliers (e.g. Reliance/Grasim) or increase stock buffer before Q3 price locks."
            },
            "china": {
                "why_it_matters": "China is one of your key supplier countries for synthetic raw materials. Customs inspection delays and tariff filings will extend lead times.",
                "estimated_impact": "Procurement lead time delay: estimated 2-4 week delay on imported Chinese synthetic fiber shipments.",
                "action": "Initiate purchase orders 3 weeks earlier than normal and request preliminary customs clearance documentation."
            }
        }
    },
    {
        "id": "evt-002",
        "event_name": "US Farm Bill & Cotton Export Subsidy Reduction",
        "category": "commodity",
        "date": "2026-07-01",
        "region": "usa / global",
        "affected_materials": ["cotton", "yarn"],
        "affected_countries": ["usa"],
        "affected_currencies": [],
        "severity": "high",
        "description": "The US Department of Agriculture announced reduced export subsidies for long-staple cotton farmers, tightening global raw cotton export availability and driving up international ICE cotton futures by 14%.",
        "impact_templates": {
            "cotton": {
                "why_it_matters": "Cotton yarn constitutes 40% of your natural fabric blend. Higher global raw cotton prices directly inflate local mill yarn quotes in India.",
                "estimated_impact": "Input cost inflation: potential 6-12% increase in cotton yarn procurement over the next 90 days.",
                "action": "Pre-book 60-day cotton yarn supply with local spinning mills at current fixed rates using current cash buffer (₹48.5L)."
            },
            "usa": {
                "why_it_matters": "The USA is both a key supplier country for premium cotton fiber and your primary export market for finished garments.",
                "estimated_impact": "Margin pressure: estimated 4-7% profit margin squeeze unless output prices are adjusted.",
                "action": "Review contract pricing with US buyers to include raw material escalator clauses."
            }
        }
    },
    {
        "id": "evt-003",
        "event_name": "Red Sea Freight Container Rate Surge & Cape Rerouting",
        "category": "shipping",
        "date": "2026-07-10",
        "region": "middle east / europe",
        "affected_materials": [],
        "affected_countries": ["germany", "vietnam", "china"],
        "affected_currencies": [],
        "severity": "medium",
        "description": "Container shipping lines serving Asia-to-Europe and US East Coast lanes have reinstated peak season surcharges ($1,200/TEU) due to vessel rerouting around the Cape of Good Hope.",
        "impact_templates": {
            "germany": {
                "why_it_matters": "Specialty textile dyes and finishing chemicals imported from German chemical suppliers use Western maritime transit routes.",
                "estimated_impact": "Logistics cost increase: estimated 15-25% hike in import freight charges; 10-18 day transit delay.",
                "action": "Consolidate chemical import shipments into larger quarterly orders to minimize per-container surcharges."
            },
            "vietnam": {
                "why_it_matters": "Vietnam is a secondary sourcing hub for specialized textile trims and accessories.",
                "estimated_impact": "Shipping delay: estimated 1-3 week delay for feeder vessel transfers.",
                "action": "Maintain minimum 30-day stock reserve for essential garment trims and dyes."
            }
        }
    },
    {
        "id": "evt-004",
        "event_name": "USD/INR Exchange Rate Depreciation (6% Slide)",
        "category": "currency",
        "date": "2026-06-20",
        "region": "india / global",
        "affected_materials": [],
        "affected_countries": [],
        "affected_currencies": ["usd", "inr"],
        "severity": "medium",
        "description": "The Indian Rupee has weakened from ₹83.10 to ₹88.25 per USD over the last 90 days amidst rising crude oil prices and global dollar strength.",
        "impact_templates": {
            "usd": {
                "why_it_matters": "Your imported polyester and dyes are invoiced in USD, making raw material imports more expensive in INR terms.",
                "estimated_impact": "Landed cost increase: estimated 5-8% increase in INR outlay for USD-denominated raw material invoices.",
                "action": "Utilize USD export proceeds from US/EU clients to settle import payables directly via EEFC account, avoiding conversion fees."
            },
            "inr": {
                "why_it_matters": "Rupee depreciation enhances your competitiveness for garment exports to US and EU buyers.",
                "estimated_impact": "Export revenue gain: potential 4-6% boost in realized INR revenue from USD export billing.",
                "action": "Incentivize US buyers for early payment terms in USD to lock in favorable exchange conversion rates."
            }
        }
    },
    {
        "id": "evt-005",
        "event_name": "Global Lithium & Battery Cobalt Mining Sanctions in DRC",
        "category": "sanction",
        "date": "2026-07-05",
        "region": "africa",
        "affected_materials": ["lithium", "cobalt", "nickel"],
        "affected_countries": ["dr congo", "chile"],
        "affected_currencies": [],
        "severity": "high",
        "description": "International sanctions on Democratic Republic of Congo mining concessions have halted 25% of global cobalt supply, spiking battery EV prices.",
        "impact_templates": {}
    },
    {
        "id": "evt-006",
        "event_name": "Black Sea Grain Corridor Suspension & Wheat Export Ban",
        "category": "commodity",
        "date": "2026-07-18",
        "region": "eastern europe",
        "affected_materials": ["wheat", "grain", "fertilizer"],
        "affected_countries": ["russia", "ukraine"],
        "affected_currencies": [],
        "severity": "medium",
        "description": "Suspension of the Black Sea agricultural corridor has triggered a 22% spike in global wheat and fertilizer futures.",
        "impact_templates": {}
    },
    {
        "id": "evt-007",
        "event_name": "Strait of Malacca Port Congestion & Asian Feeder Container Bottlenecks",
        "category": "shipping",
        "date": "2026-07-22",
        "region": "southeast asia / east asia",
        "affected_materials": ["polyester", "synthetic_yarn", "dyes", "cotton"],
        "affected_countries": ["china", "vietnam", "singapore", "india"],
        "affected_currencies": ["usd"],
        "severity": "high",
        "description": "Severe port congestion at Malacca Strait feeder hubs has created a 14-day container backlog across South and East Asian maritime shipping lanes.",
        "impact_templates": {
            "polyester": {
                "why_it_matters": "Synthetic yarn shipments from Asian suppliers are delayed in regional port feeder queues.",
                "estimated_impact": "Transit delay: 10-16 days additional lead time; potential production line buffer erosion.",
                "action": "Re-allocate near-term raw material orders to domestic Indian yarn distributors or local buffer stock."
            },
            "china": {
                "why_it_matters": "China is a key sourcing market for your specialized yarn and textile chemical inputs.",
                "estimated_impact": "Supply delay: 2-3 week delay in receiving origin consignments.",
                "action": "Increase safety stock reserve for high-turnover synthetic yarn inputs to 45 days."
            }
        }
    },
    {
        "id": "evt-008",
        "event_name": "Middle East Maritime Corridor Flare & Energy Supply Risk Surge",
        "category": "commodity",
        "date": "2026-07-25",
        "region": "middle east",
        "affected_materials": ["dyes", "polyester", "crude_oil", "petrochemicals"],
        "affected_countries": ["saudi arabia", "uae", "iran", "germany"],
        "affected_currencies": ["usd", "inr"],
        "severity": "high",
        "description": "Geopolitical escalation near key Middle East maritime transit bottlenecks has driven up war risk marine insurance premiums and global crude oil futures.",
        "impact_templates": {
            "dyes": {
                "why_it_matters": "Petrochemical-derived raw materials for textile dyes face price pressure from rising global crude oil feedstock.",
                "estimated_impact": "Cost surge: 7-12% price increase in chemical dye procurement over the next quarter.",
                "action": "Pre-book quarterly dye supply contracts with domestic vendors at current fixed rates."
            },
            "usd": {
                "why_it_matters": "Energy market uncertainty increases global USD demand and import billing outlay.",
                "estimated_impact": "Currency margin pressure: higher INR outlay for USD-denominated raw material invoices.",
                "action": "Hedge pending USD import payables using forward contracts or EEFC balances."
            }
        }
    }
]


def _match_global_events(exposure: Dict[str, Any], events: List[Dict]) -> List[Dict]:
    """
    Pure rule-based matching: for each event, check material AND country overlap
    with the business exposure profile. Generate specific impact cards for each match.
    Returns only events with at least one match, with matched_impacts populated.
    """
    matched = []
    biz_materials  = {m.lower() for m in exposure.get("materials", [])}
    biz_countries  = {c.lower() for c in exposure.get("supplier_countries", [])}
    biz_currencies = {c.lower() for c in exposure.get("currency_exposure", [])}

    for event in events:
        evt_materials  = {m.lower() for m in event.get("affected_materials", [])}
        evt_countries  = {c.lower() for c in event.get("affected_countries", [])}
        evt_currencies = {c.lower() for c in event.get("affected_currencies", [])}

        # Find overlapping triggers
        mat_hits  = biz_materials  & evt_materials
        cty_hits  = biz_countries  & evt_countries
        cur_hits  = biz_currencies & evt_currencies

        if not (mat_hits or cty_hits or cur_hits):
            continue  # No match — skip this event

        # Build matched impact cards from templates
        impacts = []
        templates = event.get("impact_templates", {})
        for trigger in list(mat_hits) + list(cty_hits) + list(cur_hits):
            if trigger in templates:
                t = templates[trigger]
                impacts.append({
                    "trigger": trigger,
                    "why_it_matters": t["why_it_matters"],
                    "estimated_impact": t["estimated_impact"],
                    "action": t["action"]
                })

        if not impacts:
            # Event matched by tag but no template written — use generic
            all_triggers = list(mat_hits | cty_hits | cur_hits)
            impacts.append({
                "trigger": ", ".join(all_triggers),
                "why_it_matters": f"This event affects {', '.join(all_triggers)}, which are part of your supply chain or currency exposure.",
                "estimated_impact": "Monitor for upstream cost or lead time changes.",
                "action": "Review supplier contracts and hedge where possible."
            })

        # Build typed trigger list so frontend knows category for label phrasing
        typed_triggers = (
            [{"value": t, "type": "material"} for t in mat_hits] +
            [{"value": t, "type": "country"}  for t in cty_hits] +
            [{"value": t, "type": "currency"} for t in cur_hits]
        )

        matched.append({
            **{k: v for k, v in event.items() if k != "impact_templates"},
            "matched_triggers": typed_triggers,
            "matched_impacts": impacts,
        })

    # Sort: high severity first
    severity_order = {"high": 0, "medium": 1, "low": 2}
    matched.sort(key=lambda e: severity_order.get(e["severity"], 9))
    return matched


@app.get("/api/global-risk")
def get_global_risk_data():
    """
    Returns the business exposure profile, all global events (for transparency),
    and only the events that are relevant to this business with pre-written impact cards.
    """
    matched = _match_global_events(_BUSINESS_EXPOSURE, _GLOBAL_EVENTS)
    filtered_out = [
        {"id": e["id"], "event_name": e["event_name"], "category": e["category"]}
        for e in _GLOBAL_EVENTS
        if e["id"] not in {m["id"] for m in matched}
    ]
    return {
        "business_exposure": _BUSINESS_EXPOSURE,
        "total_events_scanned": len(_GLOBAL_EVENTS),
        "matched_events": len(matched),
        "filtered_out_count": len(filtered_out),
        "filtered_out_events": filtered_out,
        "events": matched,
        "last_updated": "2026-07-28",
        "data_sources": ["LME Commodities", "WTO Tariff Portal", "Freightos Baltic Index", "RBI Exchange Rates", "Ministry of Commerce India"]
    }


@app.post("/api/global-risk/match")
def match_global_risk_for_uploaded_profile(exposure: Dict[str, Any]):
    """
    Accepts a custom business exposure profile (from uploaded CSV profile) and
    returns matched global risk events for that specific profile.
    The exposure body should include: name, materials[], supplier_countries[], currency_exposure[].
    All other fields (export_markets, energy_dependent, logistics_modes) are optional.
    """
    # Merge with defaults so partial payloads work safely
    safe_exposure = {
        "name": exposure.get("name", "My Business"),
        "sector": exposure.get("sector", "Business"),
        "materials": [m.lower() for m in exposure.get("materials", [])],
        "supplier_countries": [c.lower() for c in exposure.get("supplier_countries", [])],
        "export_markets": exposure.get("export_markets", []),
        "currency_exposure": [c.lower() for c in exposure.get("currency_exposure", ["inr"])],
        "energy_dependent": exposure.get("energy_dependent", False),
        "logistics_modes": exposure.get("logistics_modes", ["road"]),
    }

    matched = _match_global_events(safe_exposure, _GLOBAL_EVENTS)
    filtered_out = [
        {"id": e["id"], "event_name": e["event_name"], "category": e["category"]}
        for e in _GLOBAL_EVENTS
        if e["id"] not in {m["id"] for m in matched}
    ]

    logger.info(
        f"[/api/global-risk/match] Custom profile '{safe_exposure['name']}' — "
        f"materials: {safe_exposure['materials']}, countries: {safe_exposure['supplier_countries']} "
        f"→ {len(matched)} matched events"
    )

    return {
        "business_exposure": safe_exposure,
        "total_events_scanned": len(_GLOBAL_EVENTS),
        "matched_events": len(matched),
        "filtered_out_count": len(filtered_out),
        "filtered_out_events": filtered_out,
        "events": matched,
        "last_updated": "2026-07-28",
        "data_sources": ["LME Commodities", "WTO Tariff Portal", "Freightos Baltic Index", "RBI Exchange Rates", "Ministry of Commerce India"]
    }


def _get_serialized_business_context() -> Dict[str, Any]:
    """Build a rich, fully numeric JSON payload of all business data for LLM consumption."""
    cash_flow     = get_cash_flow_data()
    risk_radar    = get_risk_radar_data()
    loan_score    = get_loan_score_data()
    scheme_finder = get_scheme_finder_data()

    cf_sum = cash_flow["summary"]
    cf_wc  = cash_flow["working_capital"]
    calc   = loan_score["calculation"]

    return {
        "company_profile": {
            "name": "Rajesh Engineering Works",
            "sector": "Manufacturing (Engineering Components)",
            "udyam_status": "Active MSME (Udyam Registered)",
            "overall_health_index": 84,
            "overall_health_label": "Strong"
        },
        "cash_flow": {
            "current_bank_balance_inr": cf_sum["current_balance"],
            "monthly_inflow_inr": cf_sum["monthly_inflow"],
            "monthly_outflow_inr": cf_sum["monthly_outflow"],
            "net_monthly_cashflow_inr": cf_sum["net_cashflow"],
            "cash_runway_months": cf_sum["runway_months"],
            "monthly_burn_rate_inr": cf_sum["burn_rate"],
            "accounts_receivable_inr": cf_wc["accounts_receivable"],
            "accounts_payable_inr": cf_wc["accounts_payable"],
            "inventory_value_inr": cf_wc["inventory_value"],
            "cash_on_hand_inr": cf_wc["cash_on_hand"],
            "dso_days": cf_wc["dso_days"],
            "dpo_days": cf_wc["dpo_days"],
            "monthly_forecast": cash_flow["forecast_chart"],
            "upcoming_liabilities": [
                {
                    "title": a["title"],
                    "amount_inr": a["amount"],
                    "due_date": a["due_date"],
                    "severity": a["severity"],
                    "description": a["description"]
                }
                for a in cash_flow.get("alerts", [])
            ]
        },
        "loan_score": {
            "overall_score_out_of_100": calc["overall_score"],
            "cibil_equivalent_out_of_900": calc["cibil_equivalent"],
            "score_tier": calc["score_tier"],
            "pre_approved_limit_inr": loan_score["pre_approved_limit"],
            "recommended_term_months": loan_score["recommended_term_months"],
            "interest_rate_range": loan_score["est_interest_rate_range"],
            "top_drag_factor": calc["top_drag_factor"],
            "factor_breakdown": calc.get("factors", []),
            "matched_lenders": loan_score.get("matched_lenders", []),
            "document_readiness": loan_score.get("document_readiness", [])
        },
        "risk": {
            "overall_risk_index_out_of_100": risk_radar["overall_score"],
            "risk_level_label": risk_radar["risk_level"],
            "health_status": risk_radar["health_status"],
            "risk_metrics": risk_radar["metrics"],
            "radar_chart_scores": risk_radar["radar_chart_data"],
            "mitigation_suggestions": risk_radar["mitigation_suggestions"],
            "key_flags": {
                "customer_concentration": "38% of revenue from single client (Apex Auto Corp) — overdue receivable: 650000 INR",
                "supplier_single_source": "80% aluminum alloy from Zenith Metals only",
                "dscr": 1.85,
                "inventory_aging_60d_inr": 380000
            }
        },
        "government_schemes": [
            {
                "title": s["title"],
                "match_pct": s["match_percentage"],
                "category": s["category"],
                "max_benefit": s["max_benefit"],
                "subsidy_nature": s["subsidy_nature"],
                "eligibility": s["key_eligibility"],
                "status": s["status"]
            }
            for s in scheme_finder.get("schemes", [])
        ]
    }


def _build_context_for_question(q: str, biz: Dict[str, Any]) -> str:
    """
    Build a condensed context string for the system prompt.
    Core 6-line summary is always included.
    Additional detail sections are appended only when the question is
    about that topic — keeping the prompt tight and relevant.
    """
    cf  = biz["cash_flow"]
    ls  = biz["loan_score"]
    rsk = biz["risk"]

    balance  = cf["current_bank_balance_inr"]
    net_cf   = cf["net_monthly_cashflow_inr"]
    inflow   = cf["monthly_inflow_inr"]
    outflow  = cf["monthly_outflow_inr"]
    runway   = cf["cash_runway_months"]
    dso      = cf["dso_days"]
    gst_liab = next((l["amount_inr"] for l in cf["upcoming_liabilities"]
                     if "gst" in l["title"].lower()), 0)
    gst_date = next((l["due_date"] for l in cf["upcoming_liabilities"]
                     if "gst" in l["title"].lower()), "N/A")

    # ── Core summary (always sent) ──────────────────────────────────────────
    ctx = (
        f"COMPANY: Rajesh Engineering Works (Manufacturing MSME, Health 84/100)\n"
        f"CASH: Balance INR {balance:,} | Monthly inflow INR {inflow:,} | "
        f"outflow INR {outflow:,} | net +INR {net_cf:,}/mo | runway {runway} months\n"
        f"WORKING CAPITAL: AR INR {cf['accounts_receivable_inr']:,} (DSO {dso}d) | "
        f"AP INR {cf['accounts_payable_inr']:,} (DPO {cf['dpo_days']}d) | "
        f"inventory INR {cf['inventory_value_inr']:,}\n"
        f"LIABILITIES: GST INR {gst_liab:,} due {gst_date} | "
        f"Overdue receivable INR 650,000 from Apex Auto (14d late)\n"
        f"LOAN SCORE: {ls['overall_score_out_of_100']}/100 ({ls['score_tier']}) | "
        f"CIBIL {ls['cibil_equivalent_out_of_900']}/900 | "
        f"Pre-approved INR {ls['pre_approved_limit_inr']:,} @ {ls['interest_rate_range']}\n"
        f"TOP RISK FLAG: Customer concentration — Apex Auto = 38% revenue | "
        f"Supplier — 80% aluminum from Zenith Metals | DSCR {rsk['key_flags']['dscr']}x\n"
    )

    # ── Topic-specific expansions (appended only when relevant) ─────────────
    q_lower = q.lower()

    # Loan / credit / score details
    if any(w in q_lower for w in ["loan", "credit", "borrow", "score", "sbi", "hdfc", "lender", "interest", "cibil", "eligible", "apply"]):
        drag = ls["top_drag_factor"]
        ctx += "\nLOAN DETAIL:\n"
        for f in ls["factor_breakdown"]:
            ctx += f"  - {f['name']}: {f['score']}/100 (weight {f['weight_pct']}%, drag {f['drag_penalty']}pt) — {f['detail']}\n"
        ctx += "LENDERS:\n"
        for l in ls["matched_lenders"]:
            ctx += (f"  - {l['name']}: INR {l['max_amount']:,} @ {l['interest_rate']} "
                    f"({l['approval_probability']}% match, {l['collateral_required']})\n")

    # Risk / supplier / customer details
    if any(w in q_lower for w in ["risk", "supplier", "zenith", "apex", "concentration", "dscr", "inventory", "aging", "warehouse"]):
        ctx += "\nRISK DETAIL:\n"
        for m in rsk["risk_metrics"]:
            ctx += f"  - {m['name']} ({m['category']}): score {m['score']}/100 — {m['details']}\n"
        ctx += "MITIGATION SUGGESTIONS:\n"
        for s in rsk["mitigation_suggestions"]:
            ctx += f"  - {s}\n"

    # Government schemes
    if any(w in q_lower for w in ["scheme", "subsidy", "grant", "government", "cgtmse", "zed", "pli", "pmegp", "programme"]):
        ctx += "\nGOVERNMENT SCHEMES:\n"
        for s in biz["government_schemes"]:
            ctx += (f"  - {s['title']} ({s['match_pct']}% match, {s['status']}): "
                    f"{s['max_benefit']} | {s['subsidy_nature']} | "
                    f"Eligibility: {s['eligibility']}\n")

    # Monthly forecast / supply purchase / affordability questions
    if any(w in q_lower for w in [
        "forecast", "projection", "next month", "august", "september", "trend",
        "buy", "afford", "supplies", "supply", "purchase", "vendor", "lakh", "material"
    ]):
        ctx += "\nMONTHLY FORECAST:\n"
        for m in cf.get("monthly_forecast", []):
            tag = " (projected)" if m.get("projected") else ""
            ctx += f"  - {m['month']}: inflow INR {m['inflow']:,} | outflow INR {m['outflow']:,} | net INR {m['net']:,}{tag}\n"

    return ctx


@app.post("/api/chat")
def copilot_chat(payload: ChatRequest):
    """
    Multi-turn financial copilot.

    Every request:
      1. Builds a condensed, topic-aware context string (not the full JSON blob).
      2. Sends full conversation history to Claude.
      3. Returns Claude's real response — no hardcoded templates, no fallback branches.
    """
    active_tab  = payload.active_tab or "cashflow"
    biz_context = _get_serialized_business_context()

    # Build condensed, topic-aware context (only sends relevant sections)
    condensed_ctx = _build_context_for_question(payload.message, biz_context)

    # Build multi-turn messages array
    messages_payload: List[Dict[str, str]] = []
    for item in (payload.history or []):
        role = "assistant" if item.role in ("assistant", "bot", "copilot") else "user"
        messages_payload.append({"role": role, "content": item.content})
    messages_payload.append({"role": "user", "content": payload.message})

    # System prompt: condensed, topic-relevant context (not the full JSON blob)
    system_prompt = (
        "You are an expert AI Financial Copilot advising 'Rajesh Engineering Works', "
        "an Indian manufacturing MSME. Use ONLY the financial data below to answer — "
        "do not invent numbers or give generic advice.\n\n"
        "BUSINESS DATA:\n"
        f"{condensed_ctx}\n"
        "INSTRUCTIONS:\n"
        "1. Answer ANY financial question — cashflow, purchasing, loans, risk, suppliers, "
        "government schemes, working capital, receivables, payables, inventory, or anything "
        "derivable from the data above.\n"
        "2. Be concise, professional, and data-driven. Always cite specific rupee figures, "
        "percentages, and dates from the data.\n"
        "3. Maintain full conversation continuity — when the user references an earlier answer "
        "('instead of 3, what about 5?'), refer back to the prior calculation explicitly.\n"
        "4. Format responses with **bold** for key numbers and bullet points.\n"
        "5. If a question cannot be answered from the available data, say so clearly."
    )

    logger.info(
        "[/api/chat] Q=%r | history_turns=%d | context_chars=%d",
        payload.message, len(payload.history or []), len(condensed_ctx)
    )

    # ── Claude API call (the one and only path to a response) ───────────────
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        response_text = (
            "⚠️ **No API key configured.**\n\n"
            "Set the `ANTHROPIC_API_KEY` environment variable and restart the server "
            "to enable AI responses."
        )
    else:
        try:
            import anthropic
            client   = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=900,
                system=system_prompt,
                messages=messages_payload
            )
            response_text = response.content[0].text
            logger.info("[/api/chat] Claude responded (%d chars)", len(response_text))
        except Exception as exc:
            logger.error("[/api/chat] Claude API error: %s", exc)
            response_text = (
                f"⚠️ **Claude API error:** {exc}\n\n"
                "Please verify your `ANTHROPIC_API_KEY` is valid and has sufficient credits."
            )

    # Insight chips (always from live data)
    cf = biz_context["cash_flow"]
    ls = biz_context["loan_score"]
    insights = [
        f"Balance: INR {cf['current_bank_balance_inr']/100000:.1f}L",
        f"Net CF: +INR {cf['net_monthly_cashflow_inr']/100000:.2f}L/mo",
        f"Loan Score: {ls['overall_score_out_of_100']}/100",
        f"Pre-Approved: INR {ls['pre_approved_limit_inr']/100000:.0f}L"
    ]

    suggestions = [
        "What is my biggest expense category?",
        "Am I ready for a loan from SBI?",
        "What's my riskiest supplier dependency?"
    ]

    return {
        "user_query": payload.message,
        "response": response_text,
        "insights": insights,
        "suggested_actions": suggestions,
        "context_tab": active_tab,
        "debug": {
            "api_key_present": bool(api_key),
            "history_turns": len(payload.history or []),
            "context_chars": len(condensed_ctx),
            "context_preview": condensed_ctx
        }
    }

# ─────────────────────────────────────────────────────────────────────────────
# CSV FORECASTING ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def _wma(values: List[float]) -> float:
    """Weighted Moving Average — linearly weighted so recent days count more."""
    n = len(values)
    if n == 0:
        return 0.0
    weights = list(range(1, n + 1))          # 1, 2, 3, …, n
    total_w = sum(weights)
    return sum(v * w for v, w in zip(values, weights)) / total_w

def _parse_csv_text(text: str) -> List[Dict]:
    """Parse CSV text → list of {date, description, amount} rows."""
    rows = []
    reader = csv.DictReader(io.StringIO(text.strip()))
    for i, raw_row in enumerate(reader):
        if not raw_row:
            continue
        # Normalize header keys to lowercase stripped strings
        row = {str(k).strip().lower(): str(v).strip() for k, v in raw_row.items() if k}

        raw_amt  = row.get("amount") or row.get("amt") or "0"
        raw_date = row.get("date") or row.get("txn_date") or row.get("transaction_date") or ""
        raw_desc = row.get("description") or row.get("desc") or row.get("particulars") or ""

        try:
            # Clean amount string: strip currency symbols, commas, spaces
            amt_clean = re.sub(r'[^\d\.\-\+]', '', raw_amt)
            amount = float(amt_clean) if amt_clean else 0.0

            # Parse date flexibly: strip time if present, normalize delimiters to '-'
            d_clean = raw_date.split(" ")[0].split("T")[0].replace("/", "-").strip()
            parts = d_clean.split("-")
            if len(parts) == 3:
                if len(parts[0]) == 4:     # YYYY-MM-DD
                    norm_date = f"{int(parts[0]):04d}-{int(parts[1]):02d}-{int(parts[2]):02d}"
                elif len(parts[2]) == 4:   # DD-MM-YYYY or MM-DD-YYYY -> convert to YYYY-MM-DD
                    norm_date = f"{int(parts[2]):04d}-{int(parts[1]):02d}-{int(parts[0]):02d}"
                else:
                    norm_date = d_clean
            else:
                norm_date = d_clean

            # Validate date format
            date.fromisoformat(norm_date)
            rows.append({"date": norm_date, "description": raw_desc, "amount": amount})
        except Exception as exc:
            logger.warning("[CSV PARSE SKIP] Row %d failed parsing (raw: %s): %s", i+1, raw_row, exc)
            continue

    sorted_rows = sorted(rows, key=lambda r: r["date"])
    
    # Requirement 2: Log first 3 parsed rows right after parsing
    logger.info("[CSV PARSED] Total parsed rows: %d. First 3 rows: %s", len(sorted_rows), sorted_rows[:3])
    print(f"[CSV PARSED] Total rows: {len(sorted_rows)}. First 3 parsed rows: {json.dumps(sorted_rows[:3])}")
    
    return sorted_rows

def _detect_cash_strain_alerts(rows: List[Dict], threshold: float, current_balance: float) -> List[Dict[str, Any]]:
    """
    Scans raw transaction rows for recurring outflow patterns (salary, EMI, rent, GST, utilities, vendors).
    Generates structured Cash Strain Alerts with due dates, amounts, and severity.
    """
    if not rows:
        return []

    # Category patterns with keywords
    patterns = [
        ("salary", ["salary", "staff", "wages", "payroll"], "Staff Salary Outflow", "Monthly payroll disbursement"),
        ("emi", ["emi", "loan", "mortgage", "nbfc", "equated"], "Loan EMI Obligation", "Term loan & credit facility repayment"),
        ("rent", ["rent", "lease", "premises", "factory", "unit"], "Factory & Office Rent", "Commercial lease commitment"),
        ("tax", ["gst", "tax", "tds", "advance tax", "challan"], "Statutory Tax Payable", "GST / TDS compliance payout"),
        ("utility", ["electricity", "power", "utility", "water", "msedcl"], "Utility Power Bill", "Recurring operational utility charge"),
        ("vendor", ["vendor", "material", "logistics", "freight", "supplier", "purchase"], "Key Vendor Payable", "Raw material & logistics payment"),
    ]

    detected = {}
    for r in sorted(rows, key=lambda x: x["date"]):
        amt = r["amount"]
        if amt >= 0:
            continue
        desc = r["description"].lower()
        amt_abs = abs(amt)
        dt_str = r["date"]

        for cat_key, keywords, title, base_desc in patterns:
            if any(k in desc for k in keywords):
                if cat_key not in detected:
                    detected[cat_key] = {
                        "title": title,
                        "base_desc": base_desc,
                        "amounts": [],
                        "last_date": dt_str,
                        "last_desc": r["description"]
                    }
                detected[cat_key]["amounts"].append(amt_abs)
                detected[cat_key]["last_date"] = dt_str

    # Build upcoming strain alerts based on recurring patterns
    alerts = []
    alert_idx = 1
    for cat_key, info in detected.items():
        avg_amt = sum(info["amounts"]) / len(info["amounts"])
        last_dt = date.fromisoformat(info["last_date"])
        # Project next due date (~30 days from last transaction)
        next_due = last_dt + timedelta(days=30)
        
        # Severity calculation
        severity = "high" if (avg_amt > threshold * 0.25 or current_balance < avg_amt * 1.5) else "medium"

        alerts.append({
            "id": f"alt-csv-{alert_idx}",
            "title": info["title"],
            "amount": round(avg_amt, 2),
            "due_date": str(next_due),
            "severity": severity,
            "description": f"{info['base_desc']} estimated at ₹{avg_amt:,.0f} based on historical transactions ({info['last_desc']})."
        })
        alert_idx += 1

    # Fallback: if no keyword matches found, extract top 3 largest negative transactions
    if not alerts:
        outflows = [r for r in rows if r["amount"] < 0]
        outflows_sorted = sorted(outflows, key=lambda x: abs(x["amount"]), reverse=True)[:3]
        for r in outflows_sorted:
            last_dt = date.fromisoformat(r["date"])
            next_due = last_dt + timedelta(days=30)
            amt_abs = abs(r["amount"])
            alerts.append({
                "id": f"alt-csv-{alert_idx}",
                "title": f"Recurring Outflow: {r['description'][:30]}",
                "amount": round(amt_abs, 2),
                "due_date": str(next_due),
                "severity": "high" if amt_abs > threshold * 0.3 else "medium",
                "description": f"Outflow obligation of ₹{amt_abs:,.0f} recurring monthly."
            })
            alert_idx += 1

    # Sort alerts by severity (high first) then due_date
    alerts.sort(key=lambda a: (0 if a["severity"] == "high" else 1, a["due_date"]))
    return alerts


def _compute_forecast(rows: List[Dict], threshold: float):
    """
    Given sorted transaction rows:
      1. Aggregate daily net flow
      2. Build cumulative balance series
      3. Compute 30-day rolling avg inflow & outflow
      4. Project next 30 days using WMA
      5. Detect breach days
    """
    # Requirement 3: Log row count right before forecast calculation runs
    logger.info("[FORECAST CALCULATION] Received %d rows for forecast calculation", len(rows))
    print(f"[FORECAST CALCULATION] Received {len(rows)} rows for forecast calculation")

    if not rows:
        return None

    try:
        # --- 1. Aggregate daily net by date ---
        daily: Dict[str, float] = {}
        daily_inflow: Dict[str, float] = {}
        daily_outflow: Dict[str, float] = {}
        for row in rows:
            d = row["date"]
            amt = row["amount"]
            daily[d] = daily.get(d, 0.0) + amt
            if amt >= 0:
                daily_inflow[d] = daily_inflow.get(d, 0.0) + amt
            else:
                daily_outflow[d] = daily_outflow.get(d, 0.0) + abs(amt)

        all_dates = sorted(daily.keys())
        if not all_dates:
            return None

        # --- 2. Build cumulative balance ---
        cumulative = 0.0
        balance_series = []
        inflow_series = []
        outflow_series = []
        for d in all_dates:
            cumulative += daily[d]
            balance_series.append(cumulative)
            inflow_series.append(daily_inflow.get(d, 0.0))
            outflow_series.append(daily_outflow.get(d, 0.0))

        # --- 3. 30-day rolling averages (use up to last 30 days) ---
        window = min(30, len(balance_series))
        recent_inflows = inflow_series[-window:]
        recent_outflows = outflow_series[-window:]
        rolling_avg_inflow = sum(recent_inflows) / window
        rolling_avg_outflow = sum(recent_outflows) / window

        # --- 4. Project next 30 days using WMA on recent net daily flows ---
        recent_nets = [daily[d] for d in all_dates[-window:]]
        daily_wma_net = _wma(recent_nets)          # projected daily net change

        last_balance = balance_series[-1]
        last_date = date.fromisoformat(all_dates[-1])

        projected_dates = []
        projected_balances = []
        current_bal = last_balance
        for i in range(1, 31):
            proj_date = last_date + timedelta(days=i)
            current_bal += daily_wma_net
            projected_dates.append(str(proj_date))
            projected_balances.append(round(current_bal, 2))

        # --- 5. Breach & Strain Alert Detection ---
        breach_alerts = []
        for i, (pd, pb) in enumerate(zip(projected_dates, projected_balances)):
            if pb < threshold:
                breach_alerts.append({
                    "day": i + 1,
                    "date": pd,
                    "projected_balance": round(pb, 2),
                    "message": f"In {i + 1} day{'s' if i > 0 else ''} your balance may fall below ₹{threshold:,.0f} (projected ₹{pb:,.0f})"
                })

        # Pattern analyzer for Cash Strain Alerts
        strain_alerts = _detect_cash_strain_alerts(rows, threshold, balance_series[-1])

        # Build historical series for chart (last 30 days of actuals)
        hist_dates = all_dates[-30:] if len(all_dates) >= 30 else all_dates
        hist_balances = balance_series[-len(hist_dates):]

        # --- 6. Unified 6-Month Monthly Forecast (Stage 2) ---
        # Reuses exact same daily WMA & 30-day rolling averages for 6-month consistency
        monthly_groups: Dict[str, Dict[str, float]] = {}
        for d in all_dates:
            dt = date.fromisoformat(d)
            m_key = dt.strftime("%b %Y")
            if m_key not in monthly_groups:
                monthly_groups[m_key] = {"inflow": 0.0, "outflow": 0.0, "net": 0.0}
            in_amt = daily_inflow.get(d, 0.0)
            out_amt = daily_outflow.get(d, 0.0)
            monthly_groups[m_key]["inflow"] += in_amt
            monthly_groups[m_key]["outflow"] += out_amt
            monthly_groups[m_key]["net"] += (in_amt - out_amt)

        forecast_6m_chart = [
            {
                "month": m,
                "inflow": round(vals["inflow"], 2),
                "outflow": round(vals["outflow"], 2),
                "net": round(vals["net"], 2),
                "projected": False
            }
            for m, vals in monthly_groups.items()
        ]

        # Project 3 future months using same WMA net & rolling inflow/outflow
        last_dt = date.fromisoformat(all_dates[-1])
        for step in range(1, 4):
            fut_dt = last_dt + timedelta(days=30 * step)
            fut_m_key = fut_dt.strftime("%b %Y")
            proj_inflow = round(rolling_avg_inflow * 30, 2)
            proj_outflow = round(rolling_avg_outflow * 30, 2)
            proj_net = round(daily_wma_net * 30, 2)
            forecast_6m_chart.append({
                "month": fut_m_key,
                "inflow": proj_inflow,
                "outflow": proj_outflow,
                "net": proj_net,
                "projected": True
            })

        return {
            "summary": {
                "total_transactions": len(rows),
                "date_range_start": all_dates[0],
                "date_range_end": all_dates[-1],
                "starting_balance": round(balance_series[0], 2),
                "current_balance": round(balance_series[-1], 2),
                "rolling_avg_daily_inflow": round(rolling_avg_inflow, 2),
                "rolling_avg_daily_outflow": round(rolling_avg_outflow, 2),
                "projected_daily_net": round(daily_wma_net, 2),
                "runway_months": round(balance_series[-1] / (rolling_avg_outflow * 30 or 1.0), 1),
                "monthly_inflow": round(rolling_avg_inflow * 30, 2),
                "monthly_outflow": round(rolling_avg_outflow * 30, 2),
                "net_cashflow": round(daily_wma_net * 30, 2),
                "burn_rate": round(rolling_avg_outflow * 30, 2),
            },
            "historical_chart": [
                {"date": d, "balance": round(b, 2)}
                for d, b in zip(hist_dates, hist_balances)
            ],
            "forecast_chart": [
                {"date": d, "balance": b}
                for d, b in zip(projected_dates, projected_balances)
            ],
            "forecast_6m_chart": forecast_6m_chart,
            "threshold": threshold,
            "alerts": strain_alerts,
            "breach_alerts": breach_alerts,
            "first_breach": breach_alerts[0] if breach_alerts else None,
        }
    except Exception as exc:
        logger.error("[FORECAST ERROR] Failed computing forecast: %s", exc)
        return {"error": f"Forecast computation error: {str(exc)}"}


def _derive_all_from_csv(rows: List[Dict], threshold: float = 500000.0) -> Dict[str, Any]:
    """
    Stage 3: Derive entire dynamic business profile telemetry from uploaded CSV.
    Calculates Cash Flow, Loan Score, Risk Radar, and Scheme Finder.
    100% pure Python arithmetic — zero LLM calls.
    """
    fc = _compute_forecast(rows, threshold)
    if not fc or "error" in fc:
        return {"error": fc.get("error") if fc else "Failed parsing CSV transactions."}

    s = fc["summary"]
    cur_bal = s["current_balance"]
    m_inflow = s["monthly_inflow"]
    m_outflow = s["monthly_outflow"]
    net_cf = s["net_cashflow"]
    runway = s["runway_months"]

    # 1. Customer Concentration derived from CSV counterparty inflows (excluding opening balance)
    inflows_by_payer = {}
    total_inflow_sum = 0.0
    for r in rows:
        if r["amount"] > 0 and "Opening Balance" not in r["description"]:
            desc = r["description"].replace("Client Payment - ", "").replace("Payment received - ", "").replace("Invoice Settlement - ", "").strip()
            inflows_by_payer[desc] = inflows_by_payer.get(desc, 0.0) + r["amount"]
            total_inflow_sum += r["amount"]

    if inflows_by_payer and total_inflow_sum > 0:
        top_payer, top_payer_amount = max(inflows_by_payer.items(), key=lambda x: x[1])
        top_payer_share = round((top_payer_amount / total_inflow_sum) * 100.0, 1)
    else:
        top_payer = "Apex Auto Corp"
        top_payer_share = 24.5

    # 2. Outflow-to-Inflow ratio & Volatility
    outflow_ratio = round((m_outflow / (m_inflow or 1.0)) * 100.0, 1)

    daily_balances = [h["balance"] for h in fc["historical_chart"]]
    if len(daily_balances) > 1:
        mean_bal = sum(daily_balances) / len(daily_balances)
        variance = sum((b - mean_bal) ** 2 for b in daily_balances) / len(daily_balances)
        std_dev  = math.sqrt(variance)
        cov = std_dev / (mean_bal or 1.0)
        bank_stability_score = round(max(30.0, min(98.0, 100.0 - (cov * 120.0))), 1)
    else:
        bank_stability_score = 75.0

    negative_days = sum(1 for h in fc["historical_chart"] if h["balance"] < threshold)
    overdue_ratio = round(min(40.0, (negative_days / max(1, len(daily_balances))) * 100.0 + 8.0), 1)

    # 3. Recompute Loan Readiness Score dynamically from CSV metrics
    loan_inputs = LoanScoreInputs(
        gst_filing_score=92.0,
        overdue_invoice_ratio=overdue_ratio,
        bank_stability_score=bank_stability_score,
        debt_ratio_score=round(max(40.0, min(95.0, 70.0 + (net_cf / 50000.0))), 1)
    )
    loan_calc = _compute_loan_score(loan_inputs)
    loan_score_data = {
        "credit_score": loan_calc["cibil_equivalent"],
        "overall_score": loan_calc["overall_score"],
        "score_tier": loan_calc["score_tier"],
        "max_score": 900,
        "pre_approved_limit": int(max(1000000, min(10000000, cur_bal * 0.8 + net_cf * 6))),
        "recommended_term_months": 36,
        "est_interest_rate_range": "9.5% - 11.8% p.a." if loan_calc["overall_score"] >= 70 else "12.0% - 14.5% p.a.",
        "calculation": loan_calc,
        "document_readiness": [
            {"doc": "Uploaded CSV Bank Statement (Processed)", "status": "Verified", "ready": True},
            {"doc": "GST Returns (GSTR-3B & GSTR-1)", "status": "Verified", "ready": True},
            {"doc": "Audited Balance Sheet", "status": "Verified", "ready": True},
            {"doc": "Udyam MSME Certificate", "status": "Verified", "ready": True},
            {"doc": "Provisional P&L", "status": "Pending Upload", "ready": False}
        ],
        "matched_lenders": [
            {
                "name": "State Bank of India (MSME Express)",
                "max_amount": int(cur_bal * 1.2),
                "interest_rate": "9.5% p.a.",
                "collateral_required": "CGTMSE Covered (Collateral Free)",
                "approval_probability": int(min(96, loan_calc["overall_score"] + 15))
            },
            {
                "name": "HDFC Bank Working Capital Line",
                "max_amount": int(cur_bal * 0.9),
                "interest_rate": "10.5% p.a.",
                "collateral_required": "Hypothecation of Stock",
                "approval_probability": int(min(92, loan_calc["overall_score"] + 10))
            }
        ]
    }

    # 4. Derive Risk Radar Telemetry from CSV
    overall_risk_score = round(max(15.0, min(85.0, 100.0 - loan_calc["overall_score"] + (10.0 if net_cf < 0 else 0.0))), 1)
    risk_level = "Low Risk" if overall_risk_score < 35 else "Moderate Risk" if overall_risk_score < 60 else "High Risk"
    
    risk_radar_data = {
        "overall_score": overall_risk_score,
        "risk_level": risk_level,
        "health_status": f"CSV Derived Telemetry — {len(rows)} Records Processed",
        "last_updated": fc["summary"]["date_range_end"],
        "metrics": [
            {
                "name": "Customer Revenue Concentration",
                "score": int(min(95, max(15, top_payer_share))),
                "status": "High" if top_payer_share > 40 else "Warning" if top_payer_share > 25 else "Good",
                "details": f"Top client '{top_payer}' accounts for {top_payer_share}% of total CSV inflows.",
                "category": "Revenue Risk"
            },
            {
                "name": "Outflow-to-Inflow Pressure",
                "score": int(min(95, max(10, outflow_ratio))),
                "status": "High" if outflow_ratio > 90 else "Warning" if outflow_ratio > 75 else "Optimal",
                "details": f"Monthly cash outflow represents {outflow_ratio}% of total monthly inflows.",
                "category": "Solvency Risk"
            },
            {
                "name": "Cash Runway Vulnerability",
                "score": int(max(10, min(90, 100 - runway * 15))),
                "status": "Optimal" if runway >= 4 else "Moderate" if runway >= 2 else "High",
                "details": f"Estimated cash runway is {runway} months based on current monthly outflow.",
                "category": "Operational Risk"
            }
        ],
        "radar_chart_data": [
            {"subject": "Liquidity", "score": int(min(95, max(30, runway * 16))), "benchmark": 70},
            {"subject": "Solvency", "score": int(min(95, max(30, 100 - outflow_ratio * 0.5))), "benchmark": 75},
            {"subject": "Operational", "score": int(min(95, max(30, bank_stability_score))), "benchmark": 80},
            {"subject": "Revenue Concentration", "score": int(min(95, max(20, 100 - top_payer_share))), "benchmark": 70},
            {"subject": "Compliance", "score": int(min(95, max(50, 90 - negative_days * 5))), "benchmark": 85}
        ],
        "mitigation_suggestions": [
            f"Diversify revenue away from top payer ('{top_payer}') to lower concentration risk.",
            "Maintain minimum balance float to improve bank stability score.",
            "Utilize pre-approved credit lines to cover projected low-balance days."
        ]
    }

    # 4. Derive Scheme Finder Eligibility from CSV
    annual_turnover = m_inflow * 12
    schemes = [
        {
            "id": "sch-1",
            "title": "CGTMSE Collateral Free Credit Guarantee",
            "ministry": "Ministry of MSME, Govt of India",
            "match_percentage": int(min(99, max(60, loan_calc["overall_score"] + 12))),
            "max_benefit": f"Up to ₹5 Crore collateral-free loan (Pre-approved ₹{loan_score_data['pre_approved_limit']:,})",
            "category": "Credit Support",
            "target_sector": "Manufacturing & Services",
            "subsidy_nature": "85% Guarantee coverage on default to banks",
            "key_eligibility": f"Udyam registered MSME with credit score > 700 (Current CSV score: {loan_calc['cibil_equivalent']})",
            "status": "Highly Recommended" if loan_calc["overall_score"] >= 70 else "Eligible"
        },
        {
            "id": "sch-2",
            "title": "PMEGP (Prime Minister's Employment Generation Programme)",
            "ministry": "KVIC / Ministry of MSME",
            "match_percentage": int(min(95, max(50, 75 + (m_inflow / 100000.0)))),
            "max_benefit": "15% to 35% Capital Margin Subsidy",
            "category": "Subsidies & Grants",
            "target_sector": "Manufacturing & Services",
            "subsidy_nature": "Capital grant up to ₹50 Lakhs for Manufacturing",
            "key_eligibility": "Firms under expansion / new manufacturing units",
            "status": "Eligible"
        },
        {
            "id": "sch-3",
            "title": "MSME ZED Certification Scheme",
            "ministry": "Ministry of MSME",
            "match_percentage": 94,
            "max_benefit": "80% Subsidy on Certification & Financial Support for Tech Upgrade",
            "category": "Quality & Tech Upgradation",
            "target_sector": "Manufacturing MSMEs",
            "subsidy_nature": "Up to ₹5 Lakhs for handholding and ₹50,000 subsidy on certification",
            "key_eligibility": "Udyam registered MSMEs with manufacturing premises",
            "status": "Highly Recommended"
        }
    ]

    return {
        "company_profile": {
            "name": "Uploaded Business Profile",
            "sector": "Custom MSME (CSV Synced)",
            "udyam_status": "Uploaded Transaction Data",
            "overall_health_index": int(loan_calc["overall_score"]),
            "overall_health_label": "Healthy" if loan_calc["overall_score"] >= 70 else "Monitor"
        },
        "cash_flow": {
            "summary": {
                "current_balance": cur_bal,
                "starting_balance": s["starting_balance"],
                "monthly_inflow": m_inflow,
                "monthly_outflow": m_outflow,
                "net_cashflow": net_cf,
                "runway_months": runway,
                "burn_rate": m_outflow,
                "currency": "INR",
                "currency_symbol": "₹"
            },
            "forecast_chart": fc["forecast_6m_chart"], # 6-month overview
            "forecast_30d": fc["forecast_chart"],       # 30-day detailed
            "working_capital": {
                "accounts_receivable": int(m_inflow * 0.45),   # ~45% of monthly inflow outstanding
                "accounts_payable": int(m_outflow * 0.35),     # ~35% of monthly outflow outstanding
                "cash_on_hand": int(cur_bal),
                "dso_days": min(60, max(15, round((m_inflow * 0.45 / (m_inflow / 30 or 1)))), ),
                "dpo_days": min(45, max(10, round((m_outflow * 0.35 / (m_outflow / 30 or 1)))))
            },
            "alerts": fc["alerts"]
        },
        "loan_score": loan_score_data,
        "risk_radar": risk_radar_data,
        "scheme_finder": {"schemes": schemes},
        "fc_raw": fc
    }


@app.post("/api/cash-flow/analyze-csv-full")
async def analyze_csv_full(
    file: UploadFile = File(None),
    threshold: float = Form(500000.0),
    csv_text: str = Form(None),
):
    """Accept multipart CSV upload OR raw csv_text string, return full dynamic dashboard telemetry."""
    try:
        if file and file.filename:
            raw = await file.read()
            text = raw.decode("utf-8", errors="replace")
        elif csv_text:
            text = csv_text
        else:
            return {"error": "No CSV data provided. Please select or paste a CSV file."}

        rows = _parse_csv_text(text)
        if not rows:
            return {"error": "Could not parse any valid rows from CSV. Please check column headers (date, description, amount)."}

        result = _derive_all_from_csv(rows, threshold)
        return result
    except Exception as exc:
        logger.error("[ANALYZE CSV FULL ERROR] %s", exc)
        return {"error": f"Server error analyzing CSV: {str(exc)}"}


@app.post("/api/cash-flow/analyze-csv")
async def analyze_csv(
    file: UploadFile = File(None),
    threshold: float = Form(500000.0),
    csv_text: str = Form(None),
):
    """Accept multipart CSV upload OR raw csv_text string, return forecast."""
    try:
        if file and file.filename:
            raw = await file.read()
            text = raw.decode("utf-8", errors="replace")
        elif csv_text:
            text = csv_text
        else:
            return {"error": "No CSV data provided. Please select or paste a CSV file."}

        rows = _parse_csv_text(text)
        if not rows:
            return {"error": "Could not parse any valid rows from CSV. Please check column headers (date, description, amount) and date format (YYYY-MM-DD)."}

        result = _compute_forecast(rows, threshold)
        if isinstance(result, dict) and "error" in result:
            return result
        if result is None:
            return {"error": "Insufficient data to compute forecast."}
        return result
    except Exception as exc:
        logger.error("[ANALYZE CSV ERROR] %s", exc)
        return {"error": f"Server error parsing CSV: {str(exc)}"}


@app.get("/api/cash-flow/sample-csv")
def get_sample_csv():
    """Generate a realistic 90-day MSME bank statement CSV."""
    import random, math as _math
    random.seed(42)

    today = date.today()
    start = today - timedelta(days=90)

    lines = ["date,description,amount"]
    # Opening credit
    lines.append(f"{start},Opening Balance Transfer,4200000.00")

    descriptions_in = [
        "Client Payment - Apex Auto Corp",
        "Client Payment - National Engineering",
        "Client Payment - Bharat Forge Ltd",
        "Invoice Settlement - MRF Tyres",
        "Advance Receipt - New Project",
        "GST Refund Credit",
        "Export Incentive DGFT",
    ]
    descriptions_out = [
        "Salary Disbursement - Staff",
        "Raw Material Purchase - Zenith Metals",
        "Rent Payment - Factory Unit B",
        "Electricity Bill - MSEDCL",
        "Loan EMI - SBI MSME Term",
        "GST Payment - Q1",
        "Vendor Payment - Allied Components",
        "Transport & Logistics",
        "Office Supplies",
        "Insurance Premium",
    ]

    for day_offset in range(1, 91):
        d = start + timedelta(days=day_offset)
        dow = d.weekday()
        if dow >= 6:  # skip Sundays
            continue

        # 2-3 inflows per week (Mon/Wed/Fri)
        if dow in (0, 2, 4):
            amt = round(random.uniform(150000, 650000) * (1 + 0.1 * _math.sin(day_offset / 10)), 2)
            desc = random.choice(descriptions_in)
            lines.append(f"{d},{desc},{amt}")

        # Daily outflows (smaller on weekends/month-end large)
        base_out = 80000 if d.day not in (1, 2, 15, 25) else 320000
        amt_out = round(random.uniform(base_out * 0.8, base_out * 1.3), 2)
        desc_out = random.choice(descriptions_out)
        lines.append(f"{d},{desc_out},-{amt_out}")

        # Extra salary day hit
        if d.day == 28:
            lines.append(f"{d},Salary Disbursement - Full Month,-420000.00")

        # Occasional large inflow
        if day_offset in (15, 35, 55, 75):
            lines.append(f"{d},Bulk Order Payment - Priority Client,850000.00")

    csv_content = "\n".join(lines)
    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=sample_transactions_90d.csv"}
    )


# Mount static frontend at root URL '/'
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
