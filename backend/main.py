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
    allow_credentials=False,
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
    language: Optional[str] = "en"

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

def _compute_loan_score(inputs: LoanScoreInputs, lang: str = "en") -> Dict[str, Any]:
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

    # ── Language-aware detail strings ──────────────────────────────────────
    _ta = (lang == "ta")

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
            "detail": (
                f"கடந்த 12 மாதங்களில் {inputs.gst_filing_score:.0f}% GSTR-3B & GSTR-1 தாக்கல் சரியான நேரத்தில் செய்யப்பட்டது"
                if _ta else
                f"{inputs.gst_filing_score:.0f}% timely GSTR-3B & GSTR-1 filings over last 12 months"
            )
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
            "detail": (
                f"{inputs.overdue_invoice_ratio:.1f}% பெறத்தக்க கணக்குகள் 30 நாட்களுக்கு மேல் நிலுவையில் உள்ளன"
                if _ta else
                f"{inputs.overdue_invoice_ratio:.1f}% of receivables overdue > 30 days"
            )
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
            "detail": (
                f"90 நாள் பணப்பாய்வு மாறுபாடு மதிப்பெண்: {inputs.bank_stability_score:.0f}/100"
                if _ta else
                f"90-day cash flow variance score: {inputs.bank_stability_score:.0f}/100"
            )
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
            "detail": (
                f"கடன் சேவை திறன் மதிப்பெண்: {inputs.debt_ratio_score:.0f}/100"
                if _ta else
                f"Debt service capacity score: {inputs.debt_ratio_score:.0f}/100"
            )
        }
    ]

    sorted_drag = sorted(factors, key=lambda x: x["drag_penalty"], reverse=True)
    top_drag = sorted_drag[0] if sorted_drag and sorted_drag[0]["drag_penalty"] > 0 else None

    suggested_actions = []
    for f in sorted_drag:
        if len(suggested_actions) >= 3:
            break
        if f["id"] == "overdue" and f["score"] < 80:
            suggested_actions.append(
                f"முன்கூட்டி பணம் செலுத்துவதற்கு ஊக்கமளிக்கவும் (1.5% 10-நிகர-30 தள்ளுபடி) — நிலுவை விகிதத்தை {inputs.overdue_invoice_ratio:.1f}% இலிருந்து 5%க்கும் குறைவாக குறைக்கவும்."
                if _ta else
                f"Incentivize early payments (1.5% 10-net-30 discount) to reduce overdue invoices from {inputs.overdue_invoice_ratio:.1f}% to under 5%."
            )
        elif f["id"] == "gst" and f["score"] < 85:
            suggested_actions.append(
                "வரி இணக்கத்தன்மை மதிப்பீட்டை மேம்படுத்த, 20ம் தேதி காலக்கெடுவுக்கு குறைந்தது 3 நாட்கள் முன்னதாக GSTR-1 மற்றும் GSTR-3B தாக்கல் செய்யுங்கள்."
                if _ta else
                "File GSTR-1 and GSTR-3B at least 3 days prior to the 20th deadline to improve tax compliance rating."
            )
        elif f["id"] == "stability" and f["score"] < 80:
            suggested_actions.append(
                "90 நாள் வங்கி இருப்பு மாறுபாட்டை சமன்படுத்த குறைந்தது ₹5,00,000 இருப்பு வைத்திருக்கவும்."
                if _ta else
                "Maintain a minimum float of ₹5,00,000 to smooth out 90-day bank balance variance."
            )
        elif f["id"] == "debt" and f["score"] < 75:
            suggested_actions.append(
                "அதிக வட்டி கொண்ட குறுகிய கால கடன் வரிசைகளை CGTMSE பிணை இல்லா கால கடன்களாக மறுநிதியளித்துக்கவும்."
                if _ta else
                "Refinance high-interest short-term credit lines into CGTMSE collateral-free term loans."
            )

    if len(suggested_actions) < 2:
        suggested_actions.append(
            "அதிகபட்ச முன் அங்கீகரிக்கப்பட்ட வங்கி கடன் வரம்பை திறக்க FY 2024-25 தணிக்கை செய்யப்பட்ட இருப்புநிலை பதிவேற்றவும்."
            if _ta else
            "Upload audited FY 2024-25 balance sheet to unlock maximum pre-approved bank credit caps."
        )
    if len(suggested_actions) < 3:
        suggested_actions.append(
            "0.50% வட்டி விகித சலுகைகளுக்கு தகுதி பெற சுத்தமான 12 மாத வங்கி திருப்பிச் செலுத்தல் பதிவுகளை பராமரிக்கவும்."
            if _ta else
            "Maintain clean 12-month bank repayment records to qualify for 0.50% interest rate concessions."
        )

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
def get_loan_score_data(lang: str = "en"):
    calc = _compute_loan_score(LoanScoreInputs(), lang=lang)
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
def calculate_loan_score_api(payload: LoanScoreInputs, lang: str = "en"):
    calc = _compute_loan_score(payload, lang=lang)
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
# SCHEME FINDER CATALOG & ENGINE
# ─────────────────────────────────────────────────────────────────────────────

# Each scheme has an `eligibility` dict. Empty list = no restriction on that field.
# All monetary bounds are annual INR. null = no bound.
_SCHEME_CATALOG: List[Dict[str, Any]] = [
    {
        "id": "sch-cgtmse",
        "title": "CGTMSE – Credit Guarantee Fund Trust for MSEs",
        "ministry": "Ministry of MSME / SIDBI",
        "category": "Credit Support",
        "max_benefit": "Collateral-free loans up to ₹5 Crore",
        "subsidy_nature": "85% guarantee coverage on loan default to member lending institutions",
        "description": "Enables MSMEs to obtain collateral-free term and working capital loans from scheduled commercial banks.",
        "eligibility": {
            "business_types": ["manufacturing", "service"],
            "sectors": [],
            "min_turnover": None,
            "max_turnover": 2500000000,  # ₹250 Cr (medium cap)
            "udyam_categories": ["micro", "small", "medium"],
            "states": [],
            "special_tags": []
        }
    },
    {
        "id": "sch-pmegp",
        "title": "PMEGP – PM's Employment Generation Programme",
        "ministry": "KVIC / Ministry of MSME",
        "category": "Subsidies & Grants",
        "max_benefit": "15% – 35% Capital Margin Subsidy",
        "subsidy_nature": "Capital grant up to ₹50 Lakhs for manufacturing; ₹20 Lakhs for services",
        "description": "Provides capital subsidy to set up new micro-enterprises and generate rural & urban employment.",
        "eligibility": {
            "business_types": ["manufacturing", "service"],
            "sectors": [],
            "min_turnover": None,
            "max_turnover": 500000000,  # ₹50 Cr (new/micro-small)
            "udyam_categories": ["micro", "small"],
            "states": [],
            "special_tags": ["new_business"]
        }
    },
    {
        "id": "sch-mudra-tarun",
        "title": "PM Mudra Yojana (Tarun) – Working Capital & Term Loan",
        "ministry": "Ministry of Finance / MUDRA Ltd",
        "category": "Credit Support",
        "max_benefit": "Loans from ₹10 Lakhs up to ₹20 Lakhs (Tarun category)",
        "subsidy_nature": "Subsidised interest; no collateral for micro category",
        "description": "Provides finance to non-corporate, non-farm micro-enterprises across all sectors.",
        "eligibility": {
            "business_types": ["manufacturing", "service", "trading"],
            "sectors": [],
            "min_turnover": None,
            "max_turnover": 50000000,  # ₹5 Cr (true micro)
            "udyam_categories": ["micro"],
            "states": [],
            "special_tags": []
        }
    },
    {
        "id": "sch-standup-india",
        "title": "Stand-Up India – SC/ST & Women Entrepreneurs",
        "ministry": "Department of Financial Services / SIDBI",
        "category": "Credit Support",
        "max_benefit": "Composite loan ₹10 Lakhs – ₹1 Crore (greenfield projects)",
        "subsidy_nature": "Bank loans with CGFMU guarantee; at least one SC/ST or women beneficiary per bank branch",
        "description": "Facilitates bank loans for SC/ST and women borrowers to set up greenfield enterprises.",
        "eligibility": {
            "business_types": ["manufacturing", "service", "trading"],
            "sectors": [],
            "min_turnover": None,
            "max_turnover": None,
            "udyam_categories": ["micro", "small", "medium"],
            "states": [],
            "special_tags": ["sc_st_owned", "women_owned"]
        }
    },
    {
        "id": "sch-clcss",
        "title": "CLCSS – Credit Linked Capital Subsidy Scheme",
        "ministry": "Ministry of MSME / SIDBI",
        "category": "Technology Upgradation",
        "max_benefit": "15% capital subsidy on institutional credit up to ₹1 Crore for technology upgradation",
        "subsidy_nature": "Direct upfront subsidy on term loan for approved technology",
        "description": "Incentivises MSMEs to upgrade technology by providing capital subsidy on institutional credit for well-established and improved technologies.",
        "eligibility": {
            "business_types": ["manufacturing"],
            "sectors": [],
            "min_turnover": None,
            "max_turnover": 500000000,  # ₹50 Cr
            "udyam_categories": ["micro", "small"],
            "states": [],
            "special_tags": []
        }
    },
    {
        "id": "sch-zed",
        "title": "MSME ZED Certification (Zero Defect Zero Effect)",
        "ministry": "Ministry of MSME",
        "category": "Quality & Tech Upgradation",
        "max_benefit": "80% subsidy on certification fee; up to ₹5 Lakhs handholding support",
        "subsidy_nature": "₹50,000 certification subsidy + financial assistance for quality systems & tech upgrade",
        "description": "Motivates MSMEs to adopt quality standards and environmentally sustainable processes through ZED ratings.",
        "eligibility": {
            "business_types": ["manufacturing"],
            "sectors": [],
            "min_turnover": None,
            "max_turnover": None,
            "udyam_categories": ["micro", "small", "medium"],
            "states": [],
            "special_tags": []
        }
    },
    {
        "id": "sch-ies",
        "title": "Interest Equalisation Scheme for Exporters",
        "ministry": "Ministry of Commerce / RBI",
        "category": "Export Support",
        "max_benefit": "3% – 5% interest rate subvention on pre- and post-shipment credit",
        "subsidy_nature": "Interest rate reduction on export credit; directly credited to borrower's account",
        "description": "Provides interest rate relief to exporting MSMEs to make their products more competitive in global markets.",
        "eligibility": {
            "business_types": ["manufacturing", "service"],
            "sectors": [],
            "min_turnover": None,
            "max_turnover": None,
            "udyam_categories": ["micro", "small", "medium"],
            "states": [],
            "special_tags": ["export_oriented"]
        }
    },
    {
        "id": "sch-mda",
        "title": "Market Development Assistance (MDA) for Exporters",
        "ministry": "Ministry of Commerce & Industry",
        "category": "Export Support",
        "max_benefit": "Reimbursement of 75% – 90% of international marketing expenses",
        "subsidy_nature": "Grant reimbursement for participation in international trade fairs, buyer-seller meets, and export promotion trips",
        "description": "Assists export-oriented MSMEs in exploring and expanding overseas markets through financial support for marketing activities.",
        "eligibility": {
            "business_types": ["manufacturing", "service", "trading"],
            "sectors": [],
            "min_turnover": None,
            "max_turnover": None,
            "udyam_categories": ["micro", "small", "medium"],
            "states": [],
            "special_tags": ["export_oriented"]
        }
    },
    {
        "id": "sch-national-sc-st-hub",
        "title": "National SC/ST Hub Scheme",
        "ministry": "Ministry of MSME",
        "category": "Inclusive Entrepreneurship",
        "max_benefit": "Business development support, mentoring, and market linkages; financial support for GeM onboarding",
        "subsidy_nature": "Non-monetary: handholding, market access to central PSUs, technology transfer, skill upgradation",
        "description": "Provides support to SC/ST entrepreneurs to achieve sub-contracting targets in Government/PSU procurement.",
        "eligibility": {
            "business_types": ["manufacturing", "service", "trading"],
            "sectors": [],
            "min_turnover": None,
            "max_turnover": None,
            "udyam_categories": ["micro", "small", "medium"],
            "states": [],
            "special_tags": ["sc_st_owned"]
        }
    },
    {
        "id": "sch-vishwakarma",
        "title": "PM Vishwakarma Yojana",
        "ministry": "Ministry of MSME / Ministry of Skill Development",
        "category": "Artisan & Craft Support",
        "max_benefit": "Collateral-free credit up to ₹3 Lakhs (Phase 1) and ₹3–15 Lakhs (Phase 2) at 5% concessional rate",
        "subsidy_nature": "Skill training stipend ₹500/day + basic toolkit grant ₹15,000 + collateral-free credit",
        "description": "Comprehensive support programme for artisans and craftsmen in 18 traditional trades including weaving, blacksmithing, pottery, and tailoring.",
        "eligibility": {
            "business_types": ["manufacturing", "service"],
            "sectors": ["textile", "handicraft", "artisan", "craft", "weaving", "pottery", "wood", "leather", "metal"],
            "min_turnover": None,
            "max_turnover": 50000000,  # ₹5 Cr
            "udyam_categories": ["micro"],
            "states": [],
            "special_tags": []
        }
    },
    {
        "id": "sch-treds",
        "title": "TReDS – Trade Receivables Discounting System",
        "ministry": "Ministry of Finance / RBI",
        "category": "Working Capital & Receivables",
        "max_benefit": "Immediate liquidity on trade receivables at competitive discount rates",
        "subsidy_nature": "Electronic discounting of invoices raised by MSMEs on corporate buyers; faster payment realisation",
        "description": "Digital platform for MSMEs to discount their trade receivables from corporates and government buyers to improve working capital.",
        "eligibility": {
            "business_types": ["manufacturing", "service"],
            "sectors": [],
            "min_turnover": 10000000,  # ₹1 Cr minimum scale
            "max_turnover": None,
            "udyam_categories": ["micro", "small", "medium"],
            "states": [],
            "special_tags": []
        }
    },
    {
        "id": "sch-ramp",
        "title": "RAMP – Raising & Accelerating MSME Performance",
        "ministry": "Ministry of MSME (World Bank supported)",
        "category": "Capacity Building",
        "max_benefit": "State-channelled grants, technology access, and institutional capacity support",
        "subsidy_nature": "Performance-linked financial assistance to states; indirect benefit to MSMEs through improved ecosystem",
        "description": "World Bank-assisted programme to strengthen the MSME ecosystem through state-level interventions, technology, market access, and finance linkages.",
        "eligibility": {
            "business_types": ["manufacturing", "service", "trading"],
            "sectors": [],
            "min_turnover": None,
            "max_turnover": None,
            "udyam_categories": ["micro", "small", "medium"],
            "states": [],
            "special_tags": []
        }
    },
    {
        "id": "sch-sfurti",
        "title": "SFURTI – Scheme of Fund for Regeneration of Traditional Industries",
        "ministry": "Ministry of MSME",
        "category": "Cluster Development",
        "max_benefit": "Up to ₹5 Crore for regular clusters; ₹15 Crore for heritage/major clusters",
        "subsidy_nature": "Common facility centre, raw material bank, skill upgradation, and market development for artisan clusters",
        "description": "Establishes traditional industry clusters as competitive, profitable and sustainable units by providing better infrastructure and common service facilities.",
        "eligibility": {
            "business_types": ["manufacturing"],
            "sectors": ["textile", "handicraft", "artisan", "khadi", "coir", "pottery", "leather", "bamboo", "wood"],
            "min_turnover": None,
            "max_turnover": None,
            "udyam_categories": ["micro", "small"],
            "states": [],
            "special_tags": []
        }
    },
    {
        "id": "sch-pli-textiles",
        "title": "PLI Scheme – Textiles (MMF Apparel & Technical Textiles)",
        "ministry": "Ministry of Textiles",
        "category": "Production Linked Incentive",
        "max_benefit": "15% production linked incentive on incremental sales for 5 years",
        "subsidy_nature": "Cash payout per year based on audited incremental turnover over base year",
        "description": "Incentivises scale-up of manufacturing in man-made fibre (MMF) apparel, MMF fabrics, and technical textiles segments.",
        "eligibility": {
            "business_types": ["manufacturing"],
            "sectors": ["textile", "apparel", "fabric", "technical textile", "mmf", "yarn"],
            "min_turnover": 100000000,  # ₹10 Cr minimum scale
            "max_turnover": None,
            "udyam_categories": ["small", "medium"],
            "states": [],
            "special_tags": []
        }
    },
]


class BusinessProfile(BaseModel):
    """Optional business profile for scheme matching. Defaults to broadest matching if not supplied."""
    sector: Optional[str] = ""           # e.g. "textile", "food processing", "engineering"
    business_type: Optional[str] = "manufacturing"  # "manufacturing" | "service" | "trading"
    state: Optional[str] = ""            # e.g. "Tamil Nadu", "Maharashtra"
    women_owned: Optional[bool] = False
    export_oriented: Optional[bool] = False
    sc_st_owned: Optional[bool] = False


def _classify_udyam_category(annual_turnover: float) -> str:
    """Classify MSME tier from annual turnover (INR)."""
    if annual_turnover <= 50000000:      # ≤ ₹5 Crore
        return "micro"
    elif annual_turnover <= 500000000:   # ≤ ₹50 Crore
        return "small"
    elif annual_turnover <= 2500000000:  # ≤ ₹250 Crore
        return "medium"
    else:
        return "large"


def _match_schemes(
    profile: Dict[str, Any],
    annual_turnover: float,
    loan_calc: Dict[str, Any],
    schemes: List[Dict]
) -> List[Dict]:
    """
    Pure rule-based scheme eligibility engine — same pattern as _match_global_events.

    Hard-filters schemes where the profile fails a restriction the scheme enforces,
    then scores passing schemes on sector match, special tags, credit score, and
    turnover fit. Returns top 8, sorted by match_percentage descending.
    """
    biz_type    = (profile.get("business_type") or "manufacturing").lower().strip()
    biz_sector  = (profile.get("sector") or "").lower().strip()
    biz_state   = (profile.get("state") or "").lower().strip()
    women_owned = bool(profile.get("women_owned", False))
    export_ori  = bool(profile.get("export_oriented", False))
    sc_st_owned = bool(profile.get("sc_st_owned", False))

    udyam_cat   = _classify_udyam_category(annual_turnover)
    credit_score = loan_calc.get("overall_score", 70.0)

    # Build the caller's active special tags set
    caller_tags: set = set()
    if women_owned:   caller_tags.add("women_owned")
    if export_ori:    caller_tags.add("export_oriented")
    if sc_st_owned:   caller_tags.add("sc_st_owned")

    # Confidence note when profile is sparse
    low_confidence = not biz_sector and not biz_state

    matched_output = []

    for sch in schemes:
        elig = sch.get("eligibility", {})

        # ── HARD FILTERS (fail = skip entirely) ──────────────────────────────

        # Business type filter (only enforce when scheme restricts)
        allowed_types = elig.get("business_types", [])
        if allowed_types and biz_type not in [t.lower() for t in allowed_types]:
            continue

        # Udyam category filter
        allowed_udyam = elig.get("udyam_categories", [])
        if allowed_udyam and udyam_cat not in allowed_udyam and udyam_cat != "large":
            if udyam_cat == "large":
                continue  # large businesses are out of MSME scope entirely
            if udyam_cat not in allowed_udyam:
                continue

        # Turnover bounds filter
        min_t = elig.get("min_turnover")
        max_t = elig.get("max_turnover")
        if min_t is not None and annual_turnover < min_t:
            continue
        if max_t is not None and annual_turnover > max_t:
            continue

        # State filter (only enforce when scheme restricts to specific states)
        allowed_states = [s.lower() for s in elig.get("states", [])]
        if allowed_states and biz_state and biz_state not in allowed_states:
            continue

        # Special tag HARD requirement: scheme requires at least one tag the business MUST have
        # (Stand-Up India, National SC/ST Hub, IES, MDA — these require specific eligibility)
        required_tags = set(t.lower() for t in elig.get("special_tags", []))
        # For tag-gated schemes: if all required tags are identity tags (women/sc_st/export),
        # the business must match at least one to hard-qualify.
        identity_gates = {"women_owned", "sc_st_owned", "export_oriented", "new_business"}
        hard_required = required_tags & identity_gates
        if hard_required and not (hard_required & caller_tags):
            # Identity-gated scheme — business doesn't qualify
            continue

        # ── SCORING (50–99) ──────────────────────────────────────────────────
        score = 50  # base

        # Sector keyword match bonus (up to +15)
        sch_sectors = [s.lower() for s in elig.get("sectors", [])]
        sector_hits = [s for s in sch_sectors if s in biz_sector] if biz_sector else []
        if sch_sectors:  # scheme has sector restriction
            if sector_hits:
                score += 15  # strong sector match
            else:
                score += 2   # scheme sector-restricted but no overlap (still passed — sector filter is soft here)
        else:
            # Pan-sector scheme
            score += 8  # mild bonus — broad eligibility

        # Special tag bonus (up to +10 per matched tag)
        matched_tags = caller_tags & required_tags
        score += min(20, len(matched_tags) * 10)

        # Credit score adjustment for credit-type schemes
        if sch.get("category") in ("Credit Support", "Export Support"):
            score += int((credit_score - 50) * 0.3)  # +0 at 50, +15 at 100

        # Turnover fit bonus (closer to scheme sweet spot = higher score)
        if max_t and annual_turnover <= max_t:
            fit_ratio = annual_turnover / max_t
            if fit_ratio <= 0.5:
                score += 5   # well within range
            elif fit_ratio <= 0.8:
                score += 3
            else:
                score += 1   # near the ceiling
        elif not max_t:
            score += 5   # no upper cap = good fit for any size

        # Low confidence penalty when no sector/state provided
        if low_confidence:
            score -= 5

        # Clamp to 50–99
        score = max(50, min(99, score))

        # ── GENERATE DYNAMIC KEY_ELIGIBILITY & EXPLANATION ───────────────────
        udyam_label = udyam_cat.capitalize()
        turnover_cr = round(annual_turnover / 10000000, 2)  # convert to Crore
        sector_label = biz_sector.title() if biz_sector else "Your sector"
        state_label  = biz_state.title() if biz_state else "Pan-India"

        key_elig_parts = [
            f"Udyam: {udyam_label} (annual turnover ₹{turnover_cr:.2f} Cr)",
            f"Loan score: {credit_score}/100 ({loan_calc.get('score_tier', 'N/A')})",
            f"Sector: {sector_label} | State: {state_label}",
        ]
        if matched_tags:
            key_elig_parts.append(f"Eligibility tags matched: {', '.join(sorted(matched_tags))}")

        # One-line explanation referencing actual business numbers
        tag_note = ""
        if matched_tags:
            tag_note = f"; matches on {', '.join(sorted(matched_tags))} eligibility"

        sector_note = f" for {sector_label} sector" if biz_sector else ""
        confidence_note = " (lower confidence — provide sector & state for sharper matching)" if low_confidence else ""

        explanation = (
            f"{sch['title']} is {_scheme_status(score)} for your {udyam_label} "
            f"{biz_type} business with ₹{turnover_cr:.2f} Cr annual turnover"
            f"{sector_note}{tag_note}.\n"
            f"Credit score {credit_score:.1f}/100 qualifies for "
            f"{sch['category']} schemes at {state_label} level{confidence_note}."
        )

        # Status badge
        status = _scheme_status(score)

        matched_output.append({
            "id": sch["id"],
            "title": sch["title"],
            "ministry": sch["ministry"],
            "match_percentage": score,
            "max_benefit": sch["max_benefit"],
            "category": sch["category"],
            "target_sector": sector_label if sch_sectors else "All Sectors",
            "subsidy_nature": sch["subsidy_nature"],
            "key_eligibility": " | ".join(key_elig_parts),
            "explanation": explanation,
            "matched_tags": sorted(matched_tags),
            "status": status,
        })

    # Sort by match_percentage descending, return top 8
    matched_output.sort(key=lambda x: x["match_percentage"], reverse=True)
    return matched_output[:8]


def _scheme_status(score: int) -> str:
    if score >= 85:
        return "Highly Recommended"
    elif score >= 70:
        return "Eligible"
    elif score >= 60:
        return "Review Eligibility"
    else:
        return "Conditionally Eligible"


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
        "event_name_ta": "சீனா போலியெஸ்டர் உளை ஏற்றுமதியில் கும்பலிடு உளக்கத் தீர்வு வரிகள்",
        "category": "tariff",
        "date": "2026-06-15",
        "region": "china / asia",
        "affected_materials": ["polyester", "synthetic fabric", "yarn"],
        "affected_countries": ["china"],
        "affected_currencies": [],
        "severity": "high",
        "description": "China has implemented new export tariff adjustments and anti-dumping regulations on polyester staple fiber and synthetic yarn exports to South Asia, causing immediate price shifts across Asian textile hubs.",
        "description_ta": "சீனா தெற்கு ஆசியாவிற்கு போலியெஸ்டர் உளை ஏற்றுமதியில் புதிய ஏற்றுமதி வரி திருத்தங்கள் மற்றும் கும்பலிடு உளக்கத் ஒழுங்குமுறைகளை செயல்படுத்தியுள்ளது, ஆசிய திரையல் மூலங்களில் உடனடி விலை மாற்றங்களை ஏற்படுத்தியுள்ளது.",
        "impact_templates": {
            "polyester": {
                "why_it_matters": "Polyester is your primary raw material input for synthetic weave production. Sourcing synthetic yarn from Chinese suppliers will see immediate tariff surcharges.",
                "why_it_matters_ta": "போலியெஸ்டர் உங்கள் சிந்தெடிக் நூல் உற்பத்திக்கான முக்கிய மூலப்பொருள். சீன சப்ளையரர்களிடமிருந்து சிந்தெடிக் நூல் வாங்குவதில் உடனடி வரி கூடுதல் காணப்படும்.",
                "estimated_impact": "Raw material cost increase: estimated 8-14% increase in polyester yarn procurement within 30-60 days.",
                "estimated_impact_ta": "மூலப்பொருள் விலை உயர்வு: 30-60 நாட்களில் போலியெஸ்டர் நூல் கொள்மதலில் 8-14% அதிகரிப்பு நிகழலாம்.",
                "action": "Diversify polyester procurement to domestic Indian suppliers (e.g. Reliance/Grasim) or increase stock buffer before Q3 price locks.",
                "action_ta": "போலியெஸ்டர் கொள்மதியை உள்நாட்டு இந்திய சப்ளையரர்களிடம் (Reliance/Grasim) பரவலாக்குங்கள், அல்லது Q3 விலை பூட்டுக்கு முந்தி ஞிகழ்நிலையை அதிகரிக்கவும்."
            },
            "china": {
                "why_it_matters": "China is one of your key supplier countries for synthetic raw materials. Customs inspection delays and tariff filings will extend lead times.",
                "why_it_matters_ta": "சீனா உங்கள் சிந்தெடிக் மூலப்பொரள்களுக்கான முக்கிய சப்ளை நாடுகளில் ஒன்றாகும். குடியிவற்று தளி தாமதங்கள் மற்றும் வரி தாக்கல் முன்னளி நேரத்தை நீடிக்கும்.",
                "estimated_impact": "Procurement lead time delay: estimated 2-4 week delay on imported Chinese synthetic fiber shipments.",
                "estimated_impact_ta": "கொள்மதி முன்னளி நேர தாமதம்: இறக்குமதி சீன சிந்தெடிக் ஏர் ஏற்றுமதியில் 2-4 வார தாமதம் நிகழலாம்.",
                "action": "Initiate purchase orders 3 weeks earlier than normal and request preliminary customs clearance documentation.",
                "action_ta": "இயல்பு நிலையை விட 3 வாரம் முன்னதாக கொள்மதி உத்தரவுகளை தொடங்கி ஆரம்பிக்கவும் மற்றும் முன்னேர் குடியிவற்றல் பதிவுகளை கோரிக்கவும்."
            }
        }
    },
    {
        "id": "evt-002",
        "event_name": "US Farm Bill & Cotton Export Subsidy Reduction",
        "event_name_ta": "மெரிக்க வேளாண்மை சட்டம் & பருத்தி ஏற்றுமதி மானிய குறைப்பு",
        "category": "commodity",
        "date": "2026-07-01",
        "region": "usa / global",
        "affected_materials": ["cotton", "yarn"],
        "affected_countries": ["usa"],
        "affected_currencies": [],
        "severity": "high",
        "description": "The US Department of Agriculture announced reduced export subsidies for long-staple cotton farmers, tightening global raw cotton export availability and driving up international ICE cotton futures by 14%.",
        "description_ta": "மெரிக்க வேளாண்மை செயலகம் நீண்ட டெயில் பருத்தி விவசாயிகளுக்கான ஏற்றுமதி மானியங்களை குறைத்ததாக அறிவித்தது, உலக்களாவிய பருத்தி ஏற்றுமதி கிடைப்பை இறுக்கி ICE பருத்தி எதிர்கால முதலீடுகளை 14% உயர்த்தியது.",
        "impact_templates": {
            "cotton": {
                "why_it_matters": "Cotton yarn constitutes 40% of your natural fabric blend. Higher global raw cotton prices directly inflate local mill yarn quotes in India.",
                "why_it_matters_ta": "பருத்தி நூல் உங்கள் இயற்கை துணி கலவையில் 40% ஆகும். உலக்களாவிய பருத்தி விலை உயர்வு இந்தியாவில் தள்ளுபடி நூல் ஒப்பந்த விலைகளை நேரடியாக உயர்த்துகிறது.",
                "estimated_impact": "Input cost inflation: potential 6-12% increase in cotton yarn procurement over the next 90 days.",
                "estimated_impact_ta": "உள்ளீடு விலை உயர்வு: முந்தைய 90 நாட்களில் பருத்தி நூல் கொள்மதியில் 6-12% அதிகரிப்பு சாத்தியம்.",
                "action": "Pre-book 60-day cotton yarn supply with local spinning mills at current fixed rates using current cash buffer (₹48.5L).",
                "action_ta": "தற்போதைய பண இருப்பை (₹48.5L) பயன்படுத்தி உள்ளூர் நூல் தள்ளுமேடுகளிடம் 60 நாள் பருத்தி நூல் விநியோகத்தை முன் பதிவு செய்யுங்கள்."
            },
            "usa": {
                "why_it_matters": "The USA is both a key supplier country for premium cotton fiber and your primary export market for finished garments.",
                "why_it_matters_ta": "மெரிக்கா மேல்தரமான பருத்தி ஏருக்கான ஒரு முக்கிய சப்ளை நாடும் உலர்ந்த ஆடை முடிவுகளுக்கான உங்கள் முக்கிய ஏற்றுமதி சந்தையும் ஆகும்.",
                "estimated_impact": "Margin pressure: estimated 4-7% profit margin squeeze unless output prices are adjusted.",
                "estimated_impact_ta": "லாப மார்ஜின் அழுத்தம்: வெளியீட்டு விலைகள் திருத்தப்படாவிட்டால் 4-7% லாப மார்ஜின் குறைய்வு.",
                "action": "Review contract pricing with US buyers to include raw material escalator clauses.",
                "action_ta": "மூலப்பொருள் உயர்வு உட்பிரிவு ழெய்ல் சேர்க்க மெரிக்க வாங்குபவர்களுடன் ஒப்பந்த விலையிட்டலை மதிப்பாய்வு செய்யுங்கள்."
            }
        }
    },
    {
        "id": "evt-003",
        "event_name": "Red Sea Freight Container Rate Surge & Cape Rerouting",
        "event_name_ta": "செம்மறிக்கடல் சரக்கு கப்பல் கட்டணம் உயர்வு & கேப் வழிப்புத்திப்பண்",
        "category": "shipping",
        "date": "2026-07-10",
        "region": "middle east / europe",
        "affected_materials": [],
        "affected_countries": ["germany", "vietnam", "china"],
        "affected_currencies": [],
        "severity": "medium",
        "description": "Container shipping lines serving Asia-to-Europe and US East Coast lanes have reinstated peak season surcharges ($1,200/TEU) due to vessel rerouting around the Cape of Good Hope.",
        "description_ta": "ஆசியா-ஐரோப்பா மற்றும் மெரிக்க கிழக்கு கரைப்புக்கு சேவை செய்யும் சரக்கு கப்பல் கம்பெனிகள் ெளியும் குட்டை நூற்களுக்கு உயர்திய முடிவு மாத கூடுதல் கட்டணங்களை ($1,200/TEU) மீண்டும் அமல்படுத்தியுள்ளனர்.",
        "impact_templates": {
            "germany": {
                "why_it_matters": "Specialty textile dyes and finishing chemicals imported from German chemical suppliers use Western maritime transit routes.",
                "why_it_matters_ta": "ஜர்மனிய ராசாயன சப்ளையரர்களிடமிருந்து இறக்குமதி சிறப்பு திரையல் சாயங்கள் மற்றும் முடிப்பு ராசாயனங்கள் மேற்கத்திய கடல் கடப்பு மார்க்கர்களை பயன்படுத்துகின்றன.",
                "estimated_impact": "Logistics cost increase: estimated 15-25% hike in import freight charges; 10-18 day transit delay.",
                "estimated_impact_ta": "லாஜிஸ்டிக்ஸ் விலை உயர்வு: இறக்குமதி சரக்குக் கட்டணங்களில் 15-25% உயர்வு; 10-18 நாள் கடப்பு தாமதம்.",
                "action": "Consolidate chemical import shipments into larger quarterly orders to minimize per-container surcharges.",
                "action_ta": "கப்பல் ஒன்றுக்கு கூடுதல் கட்டணத்தை குறைக்க இறக்குமதி ராசாயன ஏற்றுமதி சரக்குகளை பெரிய திரைமாத உத்தரவுகளாக ௎க்கிப்படுத்தவும்."
            },
            "vietnam": {
                "why_it_matters": "Vietnam is a secondary sourcing hub for specialized textile trims and accessories.",
                "why_it_matters_ta": "வியட்நாம் சிறப்பு திரையல் ட்ரிம்ஸ் மற்றும் அககரம்களுக்கான இரண்டாம் நிலை சப்ளை முட்டமாகும்.",
                "estimated_impact": "Shipping delay: estimated 1-3 week delay for feeder vessel transfers.",
                "estimated_impact_ta": "கப்பல் தாமதம்: எம்முடியு கப்பல் மாற்றத்திற்கு 1-3 வார தாமதம்.",
                "action": "Maintain minimum 30-day stock reserve for essential garment trims and dyes.",
                "action_ta": "முக்கிய ஆடை ட்ரிம்ஸ் மற்றும் ராசாயன சாயங்களுக்கு குறைந்தது 30 நாள் ஞிகழ்நிலையை பராமரிக்கவும்."
            }
        }
    },
    {
        "id": "evt-004",
        "event_name": "USD/INR Exchange Rate Depreciation (6% Slide)",
        "event_name_ta": "USD/INR மாற்று விகித தெளிவு (6% குறைவு)",
        "category": "currency",
        "date": "2026-06-20",
        "region": "india / global",
        "affected_materials": [],
        "affected_countries": [],
        "affected_currencies": ["usd", "inr"],
        "severity": "medium",
        "description": "The Indian Rupee has weakened from ₹83.10 to ₹88.25 per USD over the last 90 days amidst rising crude oil prices and global dollar strength.",
        "description_ta": "கடந்த 90 நாட்களில் எண்ணெய் விலை உயர்வு மற்றும் உலகளாவிய டாலர் வலிமையால் இந்திய ரூபாய் ஒரு USD-க்கு ₹83.10 இருந்து ₹88.25 ஆக மதிப்பிழந்துள்ளது.",
        "impact_templates": {
            "usd": {
                "why_it_matters": "Your imported polyester and dyes are invoiced in USD, making raw material imports more expensive in INR terms.",
                "why_it_matters_ta": "உங்கள் இறக்குமதி போலியெஸ்டர் மற்றும் ராசாயன சாயங்கள் USD இல் கணக்கிடப்படுகின்றன, INR மதிப்பில் மூலப்பொருள் இறக்குமதி மிகவும் இலக்கு ஆகிறது.",
                "estimated_impact": "Landed cost increase: estimated 5-8% increase in INR outlay for USD-denominated raw material invoices.",
                "estimated_impact_ta": "இறக்குமதி விலை உயர்வு: USD மூலப்பொருள் விலைப்பட்டியல்கடுக்கான INR செலவில் 5-8% அதிகரிப்பு.",
                "action": "Utilize USD export proceeds from US/EU clients to settle import payables directly via EEFC account, avoiding conversion fees.",
                "action_ta": "மாற்று கட்டணங்களை தவிர்த்து, இறக்குமதி செலுத்தல்களை நேரடியாக தீர்க்க US/EU வாடகர்களிடமிருந்து USD ஏற்றுமதி வருமானத்தை EEFC கணக்கு மூலம் பயன்படுத்துங்கள்."
            },
            "inr": {
                "why_it_matters": "Rupee depreciation enhances your competitiveness for garment exports to US and EU buyers.",
                "why_it_matters_ta": "ரூபாய் மதிப்பிழந்தல் US மற்றும் EU வாங்குபவர்களிடம் ஆடை ஏற்றுமதிக்கான உங்கள் போட்டித்தன்மையை மேம்படுத்துகிறது.",
                "estimated_impact": "Export revenue gain: potential 4-6% boost in realized INR revenue from USD export billing.",
                "estimated_impact_ta": "ஏற்றுமதி வருமான உயர்வு: USD ஏற்றுமதி கணக்கிடலிலிருந்து INR வருமானத்தில் 4-6% உயர்வு சாத்தியம்.",
                "action": "Incentivize US buyers for early payment terms in USD to lock in favorable exchange conversion rates.",
                "action_ta": "சாதகமான மாற்று விகிதங்களை பூட்ட மெரிக்க வாங்குபவர்களை USD இல் முன்கூட்டிய கட்டண விதிமுறைகளுக்கு ஊக்கமளிக்கவும்."
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
        "event_name_ta": "மலாக்கா ஜலசந்தி துறைமுக நெரிசல் & ஆசிய கொள்கலன் தாமதங்கள்",
        "category": "shipping",
        "date": "2026-07-22",
        "region": "southeast asia / east asia",
        "affected_materials": ["polyester", "synthetic_yarn", "dyes", "cotton"],
        "affected_countries": ["china", "vietnam", "singapore", "india"],
        "affected_currencies": ["usd"],
        "severity": "high",
        "description": "Severe port congestion at Malacca Strait feeder hubs has created a 14-day container backlog across South and East Asian maritime shipping lanes.",
        "description_ta": "மலாக்கா ஜலசந்தி துறைமுகங்களில் கடுமையான நெரிசல் காரணமாக தெற்கு மற்றும் கிழக்கு ஆசிய கப்பல் பாதைகளில் 14 நாட்கள் கொள்கலன் தாமதம் ஏற்பட்டுள்ளது.",
        "impact_templates": {
            "polyester": {
                "why_it_matters": "Synthetic yarn shipments from Asian suppliers are delayed in regional port feeder queues.",
                "why_it_matters_ta": "ஆசிய சப்ளையர்களிடமிருந்து செயற்கை நூல் சரக்குகள் பிராந்திய துறைமுக வரிசைகளில் தாமதமாகின்றன.",
                "estimated_impact": "Transit delay: 10-16 days additional lead time; potential production line buffer erosion.",
                "estimated_impact_ta": "போக்குவரத்து தாமதம்: 10-16 நாட்கள் கூடுதல் கால அவகாசம்; தயாரிப்பு வரிசை பாதிக்கப்படலாம்.",
                "action": "Re-allocate near-term raw material orders to domestic Indian yarn distributors or local buffer stock.",
                "action_ta": "அண்மைக்கால மூலப்பொருள் ஆர்டர்களை இந்திய உள்நாட்டு நூல் விநியோகஸ்தர்களுக்கு மாற்றவும்."
            },
            "china": {
                "why_it_matters": "China is a key sourcing market for your specialized yarn and textile chemical inputs.",
                "why_it_matters_ta": "சீனா உங்களின் சிறப்பு நூல் மற்றும் ஜவுளி இரசாயன உள்ளீடுகளுக்கான முக்கிய கொள்முதல் சந்தையாகும்.",
                "estimated_impact": "Supply delay: 2-3 week delay in receiving origin consignments.",
                "estimated_impact_ta": "விநியோக தாமதம்: மூலப் பொருட்களைப் பெறுவதில் 2-3 வாரங்கள் தாமதம்.",
                "action": "Increase safety stock reserve for high-turnover synthetic yarn inputs to 45 days.",
                "action_ta": "செயற்கை நூல் உள்ளீடுகளுக்கான பாதுகாப்பு பங்கு இருப்பை 45 நாட்களாக உயர்த்தவும்."
            }
        }
    },
    {
        "id": "evt-008",
        "event_name": "Middle East Maritime Corridor Flare & Energy Supply Risk Surge",
        "event_name_ta": "மத்திய கிழக்கு கடல் வழித்தட பதற்றம் & எரிசக்தி விநியோக ஆபத்து",
        "category": "commodity",
        "date": "2026-07-25",
        "region": "middle east",
        "affected_materials": ["dyes", "polyester", "crude_oil", "petrochemicals"],
        "affected_countries": ["saudi arabia", "uae", "iran", "germany"],
        "affected_currencies": ["usd", "inr"],
        "severity": "high",
        "description": "Geopolitical escalation near key Middle East maritime transit bottlenecks has driven up war risk marine insurance premiums and global crude oil futures.",
        "description_ta": "மத்திய கிழக்கு கடல் போக்குவரத்து பகுதிகளில் நிலவும் பதற்றம் காரணமாக காப்பீட்டு பிரீமியங்கள் மற்றும் கச்சா எண்ணெய் விலை உயர்ந்துள்ளது.",
        "impact_templates": {
            "dyes": {
                "why_it_matters": "Petrochemical-derived raw materials for textile dyes face price pressure from rising global crude oil feedstock.",
                "why_it_matters_ta": "ஜவுளி சாயங்களுக்கான பெட்ரோ கெமிக்கல் மூலப்பொருட்கள் கச்சா எண்ணெய் விலை உயர்வால் விலை அழுத்தத்தை எதிர்கொள்கின்றன.",
                "estimated_impact": "Cost surge: 7-12% price increase in chemical dye procurement over the next quarter.",
                "estimated_impact_ta": "செலவு உயர்வு: அடுத்த காலாண்டில் இரசாயன சாயம் கொள்முதலில் 7-12% விலை உயர்வு.",
                "action": "Pre-book quarterly dye supply contracts with domestic vendors at current fixed rates.",
                "action_ta": "தற்போதைய நிலையான கட்டணத்தில் உள்நாட்டு விற்பனையாளர்களுடன் காலாண்டு சாயம் விநியோக ஒப்பந்தங்களை முன்பதிவு செய்யவும்."
            },
            "usd": {
                "why_it_matters": "Energy market uncertainty increases global USD demand and import billing outlay.",
                "why_it_matters_ta": "எரிசக்தி சந்தை நிச்சயமற்ற தன்மை உலகளாவிய டாலர் தேவையை உயர்த்துகிறது.",
                "estimated_impact": "Currency margin pressure: higher INR outlay for USD-denominated raw material invoices.",
                "estimated_impact_ta": "நாணய லாப வரம்பு அழுத்தம்: டாலர் இன்வாய்ஸ்களுக்கு அதிக ரூபாய் செலவு.",
                "action": "Hedge pending USD import payables using forward contracts or EEFC balances.",
                "action_ta": "முன்னோக்கி ஒப்பந்தங்கள் அல்லது EEFC இருப்புகளைப் பயன்படுத்தி நிலுவையிலுள்ள டாலர் இறக்குமதி தொகைகளைப் பாதுகாக்கவும்."
            }
        }
    }
]


def _match_global_events(exposure: Dict[str, Any], events: List[Dict], lang: str = "en") -> List[Dict]:
    """
    Pure rule-based matching: for each event, check material AND country overlap
    with the business exposure profile. Generate specific impact cards for each match.
    Returns only events with at least one match, with matched_impacts populated.
    When lang='ta', uses Tamil translations embedded in each impact_template.
    """
    _ta = (lang == "ta")
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

        # Build matched impact cards from templates, picking Tamil fields when lang=ta
        impacts = []
        templates = event.get("impact_templates", {})
        for trigger in list(mat_hits) + list(cty_hits) + list(cur_hits):
            if trigger in templates:
                t = templates[trigger]
                impacts.append({
                    "trigger": trigger,
                    "why_it_matters": t.get("why_it_matters_ta", t["why_it_matters"]) if _ta else t["why_it_matters"],
                    "estimated_impact": t.get("estimated_impact_ta", t["estimated_impact"]) if _ta else t["estimated_impact"],
                    "action": t.get("action_ta", t["action"]) if _ta else t["action"]
                })

        if not impacts:
            # Event matched by tag but no template written — use generic
            all_triggers = list(mat_hits | cty_hits | cur_hits)
            impacts.append({
                "trigger": ", ".join(all_triggers),
                "why_it_matters": (
                    f"இந்த நிகழ்வு {', '.join(all_triggers)}-ஐ பாதிக்கிறது, இவை உங்கள் சப்ளை சங்கிலி அல்லது நாணய வெளிப்பாட்டின் ஒரு பகுதியாகும்."
                    if _ta else
                    f"This event affects {', '.join(all_triggers)}, which are part of your supply chain or currency exposure."
                ),
                "estimated_impact": (
                    "மேல்நிலை செலவு அல்லது முன்னணி நேர மாற்றங்களை கண்காணிக்கவும்."
                    if _ta else
                    "Monitor for upstream cost or lead time changes."
                ),
                "action": (
                    "சப்ளையர் ஒப்பந்தங்களை மதிப்பாய்வு செய்து, சாத்தியமான இடங்களில் ஹெட்ஜிங் செய்யுங்கள்."
                    if _ta else
                    "Review supplier contracts and hedge where possible."
                )
            })

        # Build typed trigger list so frontend knows category for label phrasing
        typed_triggers = (
            [{"value": t, "type": "material"} for t in mat_hits] +
            [{"value": t, "type": "country"}  for t in cty_hits] +
            [{"value": t, "type": "currency"} for t in cur_hits]
        )

        # Use Tamil event name/description if available and requested
        event_out = {k: v for k, v in event.items() if k != "impact_templates"}
        if _ta:
            if "event_name_ta" in event:
                event_out["event_name"] = event["event_name_ta"]
            if "description_ta" in event:
                event_out["description"] = event["description_ta"]

        matched.append({
            **event_out,
            "matched_triggers": typed_triggers,
            "matched_impacts": impacts,
        })

    # Sort: high severity first
    severity_order = {"high": 0, "medium": 1, "low": 2}
    matched.sort(key=lambda e: severity_order.get(e["severity"], 9))
    return matched


@app.get("/api/global-risk")
def get_global_risk_data(lang: str = "en"):
    """
    Returns the business exposure profile, all global events (for transparency),
    and only the events that are relevant to this business with pre-written impact cards.
    Accepts ?lang=ta to return Tamil translations of all impact text.
    """
    matched = _match_global_events(_BUSINESS_EXPOSURE, _GLOBAL_EVENTS, lang=lang)
    filtered_out = [
        {"id": e["id"], "event_name": e.get("event_name_ta", e["event_name"]) if lang == "ta" else e["event_name"], "category": e["category"]}
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
def match_global_risk_for_uploaded_profile(exposure: Dict[str, Any], lang: str = "en"):
    """
    Accepts a custom business exposure profile (from uploaded CSV profile) and
    returns matched global risk events for that specific profile.
    The exposure body should include: name, materials[], supplier_countries[], currency_exposure[].
    All other fields (export_markets, energy_dependent, logistics_modes) are optional.
    Accepts ?lang=ta query param to return Tamil translations of all impact text.
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

    matched = _match_global_events(safe_exposure, _GLOBAL_EVENTS, lang=lang)
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

class ChatRequest(BaseModel):
    message: str
    active_tab: Optional[str] = "cashflow"
    history: Optional[List[ChatMessageItem]] = []
    language: Optional[str] = "en"
    profile_data: Optional[Dict[str, Any]] = None

@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "fastapi-backend"}

@app.get("/api/cash-flow")
def get_cash_flow_data(lang: str = "en"):
    return {
        "summary": {
            "current_balance": 4850000,
            "starting_balance": 4300000,
            "monthly_inflow": 2850000,
            "monthly_outflow": 2300000,
            "net_cashflow": 550000,
            "runway_months": 5.4,
            "burn_rate": 2300000,
            "currency": "INR",
            "currency_symbol": "₹"
        },
        "forecast_chart": [
            {"month": "Mar 2026", "inflow": 2600000, "outflow": 2100000, "net": 500000, "projected": False},
            {"month": "Apr 2026", "inflow": 2750000, "outflow": 2200000, "net": 550000, "projected": False},
            {"month": "May 2026", "inflow": 2800000, "outflow": 2250000, "net": 550000, "projected": False},
            {"month": "Jun 2026", "inflow": 2850000, "outflow": 2300000, "net": 550000, "projected": False},
            {"month": "Jul 2026", "inflow": 2900000, "outflow": 2350000, "net": 550000, "projected": True},
            {"month": "Aug 2026", "inflow": 3000000, "outflow": 2400000, "net": 600000, "projected": True}
        ],
        "working_capital": {
            "accounts_receivable": 3950000,
            "accounts_payable": 1820000,
            "inventory_value": 2450000,
            "cash_on_hand": 4850000,
            "dso_days": 42,
            "dpo_days": 28
        },
        "alerts": [
            {
                "id": "alt-1",
                "severity": "high",
                "title": "GST கட்டணம் நிலுவை — ₹3.4L" if lang == "ta" else "GST Payment Due — ₹3.4L",
                "due_date": "ஆக 20, 2026" if lang == "ta" else "Aug 20, 2026",
                "amount": 340000,
                "description": "ஜூலை 2026 GST கடமை. போதுமான இருப்பு உள்ளது (₹48.5L)." if lang == "ta" else "GST liability for July 2026. Sufficient balance available (₹48.5L)."
            },
            {
                "id": "alt-2",
                "severity": "medium",
                "title": "நிலுவை விலைப்பட்டியல் — Apex Auto Corp" if lang == "ta" else "Overdue Invoice — Apex Auto Corp",
                "due_date": "14 நாட்கள் நிலுவை" if lang == "ta" else "Overdue by 14 days",
                "amount": 650000,
                "description": "விலைப்பட்டியல் #INV-2026-089 (₹6.5L) 30 நாள் கட்டண காலக்கெடு தாண்டியது." if lang == "ta" else "Invoice #INV-2026-089 (₹6.5L) past 30-day payment term."
            }
        ]
    }

@app.get("/api/risk-radar")
def get_risk_radar_data(lang: str = "en"):
    _ta = (lang == "ta")
    return {
        "overall_score": 28,
        "risk_level": "குறைந்த ஆபத்து" if _ta else "Low Risk",
        "health_status": (
            "நிலையான தரவு — அனைத்து முக்கிய அளவீடுகளும் சிறந்த நிலையில் உள்ளன"
            if _ta else "Stable Telemetry — All Key Metrics Optimal"
        ),
        "last_updated": "2026-07-28",
        "metrics": [
            {
                "name": "Customer Revenue Concentration",
                "score": 38,
                "status": "Warning",
                "details": (
                    "Apex Auto Corp மொத்த மாதாந்திர வருவாயில் 38% பங்கு வகிக்கிறது."
                    if _ta else
                    "Apex Auto Corp accounts for 38% of total monthly revenue."
                ),
                "category": "Revenue Risk"
            },
            {
                "name": "Debt Service Coverage Ratio (DSCR)",
                "score": 18,
                "status": "Optimal",
                "details": (
                    "DSCR 1.85x — கடன்தாரர் வரம்பான 1.25x-ஐ விட மிகவும் அதிகம்."
                    if _ta else
                    "DSCR is 1.85x — well above lender threshold of 1.25x."
                ),
                "category": "Solvency Risk"
            },
            {
                "name": "Inventory Aging (>60 Days)",
                "score": 22,
                "status": "Optimal",
                "details": (
                    "மொத்த சரக்கில் 15.5% மட்டுமே 60 நாட்களுக்கு மேல் பழையதாக உள்ளது."
                    if _ta else
                    "Only 15.5% of total stock aged beyond 60 days."
                ),
                "category": "Operational Risk"
            },
            {
                "name": "Supplier Single-Source Bottleneck",
                "score": 32,
                "status": "Warning",
                "details": (
                    "மூல அலுமினியம் உலோகக் கலவையில் 80% ஒரே சப்ளையர் (Zenith Metals) மூலம் பெறப்படுகிறது."
                    if _ta else
                    "80% of raw aluminum alloy sourced from single vendor (Zenith Metals)."
                ),
                "category": "Supply Chain Risk"
            }
        ],
        "radar_chart_data": [
            {"subject": "Liquidity", "score": 85, "benchmark": 70},
            {"subject": "Solvency", "score": 78, "benchmark": 75},
            {"subject": "Operational", "score": 72, "benchmark": 80},
            {"subject": "Revenue Concentration", "score": 62, "benchmark": 70},
            {"subject": "Compliance", "score": 90, "benchmark": 85}
        ],
        "mitigation_suggestions": [
            (
                "Apex Auto Corp-க்கு விலைப்பட்டியல் வயதை குறைக்க 1.5% முன்கூட்டிய கட்டண தள்ளுபடி வழங்குங்கள்."
                if _ta else
                "Offer 1.5% early payment discount to Apex Auto Corp to reduce invoice aging."
            ),
            (
                "ஒரே மூலத்தின் ஆபத்தை குறைக்க இரண்டாம் நிலை அலுமினியம் உலோக சப்ளையரை சேர்க்கவும்."
                if _ta else
                "Onboard secondary aluminum alloy supplier to mitigate single-source risk."
            ),
            (
                "5.4 மாத ரன்வேயை உறுதி செய்ய தற்போதைய ₹48.5L பண இருப்பை பராமரிக்கவும்."
                if _ta else
                "Maintain current cash balance of ₹48.5L to ensure 5.4 months runway."
            )
        ],
        "key_flags": {
            "customer_concentration": "38% of revenue from single client (Apex Auto Corp) — overdue receivable: 650000 INR",
            "supplier_single_source": "80% aluminum alloy from Zenith Metals only",
            "dscr": 1.85,
            "inventory_aging_60d_inr": 380000
        }
    }

def _get_serialized_business_context(profile_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Build a rich, fully numeric JSON payload of all business data for LLM consumption."""
    if profile_data:
        cash_flow     = profile_data.get("cash_flow") or get_cash_flow_data()
        risk_radar    = profile_data.get("risk_radar") or get_risk_radar_data()
        loan_score    = profile_data.get("loan_score") or get_loan_score_data()
        scheme_finder = profile_data.get("scheme_finder") or get_scheme_finder_data()
        company_prof  = profile_data.get("company_profile") or {
            "name": "My Business",
            "sector": "Custom MSME (Uploaded Data)",
            "overall_health_index": int(loan_score.get("calculation", {}).get("overall_score", 75)),
            "overall_health_label": "Healthy"
        }
    else:
        cash_flow     = get_cash_flow_data()
        risk_radar    = get_risk_radar_data()
        loan_score    = get_loan_score_data()
        scheme_finder = get_scheme_finder_data()
        company_prof  = {
            "name": "Rajesh Engineering Works",
            "sector": "Manufacturing (Engineering Components)",
            "udyam_status": "Active MSME (Udyam Registered)",
            "overall_health_index": 84,
            "overall_health_label": "Strong"
        }

    cf_sum = cash_flow.get("summary", {})
    cf_wc  = cash_flow.get("working_capital", {})
    calc   = loan_score.get("calculation", {})

    metrics_list = risk_radar.get("metrics") or []
    first_metric_details = metrics_list[0].get("details") if metrics_list else "Derived from uploaded transactions"

    key_flags = risk_radar.get("key_flags") or {
        "customer_concentration": first_metric_details,
        "supplier_single_source": "Derived supplier metrics",
        "dscr": round(max(1.1, min(2.5, cf_sum.get("net_cashflow", 0) / 100000.0 + 1.2)), 2),
        "inventory_aging_60d_inr": cf_wc.get("inventory_value", 0)
    }

    return {
        "company_profile": company_prof,
        "cash_flow": {
            "current_bank_balance_inr": cf_sum.get("current_balance", 0),
            "monthly_inflow_inr": cf_sum.get("monthly_inflow", 0),
            "monthly_outflow_inr": cf_sum.get("monthly_outflow", 0),
            "net_monthly_cashflow_inr": cf_sum.get("net_cashflow", 0),
            "cash_runway_months": cf_sum.get("runway_months", 0),
            "monthly_burn_rate_inr": cf_sum.get("burn_rate", 0),
            "accounts_receivable_inr": cf_wc.get("accounts_receivable", 0),
            "accounts_payable_inr": cf_wc.get("accounts_payable", 0),
            "inventory_value_inr": cf_wc.get("inventory_value", 0),
            "cash_on_hand_inr": cf_wc.get("cash_on_hand", 0),
            "dso_days": cf_wc.get("dso_days", 0),
            "dpo_days": cf_wc.get("dpo_days", 0),
            "monthly_forecast": cash_flow.get("forecast_chart", []),
            "upcoming_liabilities": [
                {
                    "title": a.get("title", ""),
                    "amount_inr": a.get("amount", 0),
                    "due_date": a.get("due_date", "N/A"),
                    "severity": a.get("severity", "medium"),
                    "description": a.get("description", "")
                }
                for a in cash_flow.get("alerts", [])
            ]
        },
        "loan_score": {
            "overall_score_out_of_100": calc.get("overall_score", 0),
            "cibil_equivalent_out_of_900": calc.get("cibil_equivalent", 0),
            "score_tier": calc.get("score_tier", "N/A"),
            "pre_approved_limit_inr": loan_score.get("pre_approved_limit", 0),
            "recommended_term_months": loan_score.get("recommended_term_months", 36),
            "interest_rate_range": loan_score.get("est_interest_rate_range") or loan_score.get("interest_rate_range", "9.5% p.a."),
            "top_drag_factor": calc.get("top_drag_factor"),
            "factor_breakdown": calc.get("factors", []),
            "matched_lenders": loan_score.get("matched_lenders", []),
            "document_readiness": loan_score.get("document_readiness", [])
        },
        "risk": {
            "overall_risk_index_out_of_100": risk_radar.get("overall_score", 0),
            "risk_level_label": risk_radar.get("risk_level", "N/A"),
            "health_status": risk_radar.get("health_status", ""),
            "risk_metrics": risk_radar.get("metrics", []),
            "radar_chart_scores": risk_radar.get("radar_chart_data", []),
            "mitigation_suggestions": risk_radar.get("mitigation_suggestions", []),
            "key_flags": key_flags
        },
        "government_schemes": [
            {
                "title": s.get("title", ""),
                "match_pct": s.get("match_percentage") or s.get("match_pct", 0),
                "category": s.get("category", ""),
                "max_benefit": s.get("max_benefit", ""),
                "subsidy_nature": s.get("subsidy_nature", ""),
                "eligibility": s.get("key_eligibility") or s.get("eligibility", ""),
                "status": s.get("status", "Eligible")
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

    company_name = biz.get("company_profile", {}).get("name", "Rajesh Engineering Works")
    sector_info  = biz.get("company_profile", {}).get("sector", "Manufacturing MSME")
    health_idx   = biz.get("company_profile", {}).get("overall_health_index", 84)

    # ── Liabilities & Overdue Line (Dynamic) ────────────────────────────────
    liabilities_str = f"LIABILITIES: GST INR {gst_liab:,} due {gst_date}"
    key_flags = rsk.get("key_flags", {})
    overdue_info = key_flags.get("overdue_receivable")
    if overdue_info:
        liabilities_str += f" | Overdue receivable {overdue_info}"
    elif company_name == "Rajesh Engineering Works":
        liabilities_str += " | Overdue receivable INR 650,000 from Apex Auto (14d late)"

    # ── Top Risk Flag Line (Dynamic) ────────────────────────────────────────
    cust_conc = key_flags.get("customer_concentration")
    supp_source = key_flags.get("supplier_single_source")
    dscr_val = key_flags.get("dscr", 1.85)

    risk_flags_parts = []
    if cust_conc:
        risk_flags_parts.append(f"Customer concentration — {cust_conc}")
    if supp_source and supp_source != "Derived supplier metrics":
        risk_flags_parts.append(f"Supplier — {supp_source}")

    if not risk_flags_parts:
        metrics = rsk.get("risk_metrics", [])
        if metrics:
            top_m = metrics[0]
            risk_flags_parts.append(f"{top_m.get('name')}: {top_m.get('details')}")

    risk_flag_str = " | ".join(risk_flags_parts) if risk_flags_parts else "No major risk flags"

    # ── Core summary (always sent) ──────────────────────────────────────────
    ctx = (
        f"COMPANY: {company_name} ({sector_info}, Health {health_idx}/100)\n"
        f"CASH: Balance INR {balance:,} | Monthly inflow INR {inflow:,} | "
        f"outflow INR {outflow:,} | net +INR {net_cf:,}/mo | runway {runway} months\n"
        f"WORKING CAPITAL: AR INR {cf['accounts_receivable_inr']:,} (DSO {dso}d) | "
        f"AP INR {cf['accounts_payable_inr']:,} (DPO {cf['dpo_days']}d) | "
        f"inventory INR {cf['inventory_value_inr']:,}\n"
        f"{liabilities_str}\n"
        f"LOAN SCORE: {ls['overall_score_out_of_100']}/100 ({ls['score_tier']}) | "
        f"CIBIL {ls['cibil_equivalent_out_of_900']}/900 | "
        f"Pre-approved INR {ls['pre_approved_limit_inr']:,} @ {ls['interest_rate_range']}\n"
        f"TOP RISK FLAG: {risk_flag_str} | DSCR {dscr_val}x\n"
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
      2. Sends full conversation history to Gemini.
      3. Returns Gemini's real response — no hardcoded templates, no fallback branches.
    """
    active_tab   = payload.active_tab or "cashflow"
    biz_context  = _get_serialized_business_context(payload.profile_data)
    company_name = biz_context.get("company_profile", {}).get("name", "Rajesh Engineering Works")

    # Build condensed, topic-aware context (only sends relevant sections)
    condensed_ctx = _build_context_for_question(payload.message, biz_context)

    # Build multi-turn messages array
    messages_payload: List[Dict[str, str]] = []
    for item in (payload.history or []):
        role = "assistant" if item.role in ("assistant", "bot", "copilot") else "user"
        messages_payload.append({"role": role, "content": item.content})
    messages_payload.append({"role": "user", "content": payload.message})

    lang_instruction = (
        "\n6. IMPORTANT: You MUST respond entirely in Tamil (தமிழ்). "
        "All explanations, numbers commentary, and advice must be in Tamil."
        if payload.language == "ta"
        else ""
    )

    # System prompt: condensed, topic-relevant context (not the full JSON blob)
    system_prompt = (
        f"You are an expert AI Financial Copilot advising '{company_name}', "
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
        f"{lang_instruction}"
    )

    logger.info(
        "[/api/chat] Q=%r | history_turns=%d | context_chars=%d | company=%r",
        payload.message, len(payload.history or []), len(condensed_ctx), company_name
    )

    # ── Gemini API call (the one and only path to a response) ───────────────
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        logger.warning("[/api/chat] FAIL: GEMINI_API_KEY is missing or empty!")
        return {
            "user_query": payload.message,
            "error": "No API key configured. Set GEMINI_API_KEY in frontend/key.env and restart the server.",
            "response": None,
            "insights": [],
            "suggested_actions": [],
            "context_tab": active_tab,
        }

    try:
        from google import genai
        from google.genai import types

        logger.info("[/api/chat] Connecting to Gemini API (api_key starts with %r)...", api_key[:6] + "...")
        client = genai.Client(api_key=api_key)

        gemini_contents = []
        for item in (payload.history or []):
            role = "model" if item.role in ("assistant", "bot", "copilot", "model") else "user"
            gemini_contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=item.content)]
                )
            )
        gemini_contents.append(
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=payload.message)]
            )
        )

        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=900
        )

        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=gemini_contents,
            config=config
        )
        response_text = response.text or ""
        logger.info("[/api/chat] SUCCESS: Gemini API call succeeded (%d chars response)", len(response_text))
    except Exception as exc:
        logger.error("[/api/chat] FAIL: Gemini API call error: %s", exc)
        return {
            "user_query": payload.message,
            "error": f"Gemini API error: {str(exc)}",
            "response": None,
            "insights": [],
            "suggested_actions": [],
            "context_tab": active_tab,
        }
    except Exception as exc:
        logger.error("[/api/chat] Gemini API error: %s", exc)
        return {
            "user_query": payload.message,
            "error": f"Gemini API error: {exc}",
            "response": None,
            "insights": [],
            "suggested_actions": [],
            "context_tab": active_tab,
        }

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

def _detect_cash_strain_alerts(rows: List[Dict], threshold: float, current_balance: float, lang: str = "en") -> List[Dict[str, Any]]:
    """
    Scans raw transaction rows for recurring outflow patterns (salary, EMI, rent, GST, utilities, vendors).
    Generates structured Cash Strain Alerts with due dates, amounts, and severity.
    """
    if not rows:
        return []

    _ta = (lang == "ta")

    # Category patterns with keywords — (key, keywords, title_en, base_desc_en, title_ta, base_desc_ta)
    patterns = [
        ("salary",  ["salary", "staff", "wages", "payroll"],
         "Staff Salary Outflow",   "Monthly payroll disbursement",
         "ஊழியர் சம்பள செலவு",     "மாதாந்திர ஊதிய விநியோகம்"),
        ("emi",     ["emi", "loan", "mortgage", "nbfc", "equated"],
         "Loan EMI Obligation",    "Term loan & credit facility repayment",
         "கடன் EMI கடமை",          "கால கடன் & கடன் வசதி திருப்பிச் செலுத்தல்"),
        ("rent",    ["rent", "lease", "premises", "factory", "unit"],
         "Factory & Office Rent",  "Commercial lease commitment",
         "தொழிற்சாலை & அலுவலக வாடகை", "வணிக குத்தகை கடமை"),
        ("tax",     ["gst", "tax", "tds", "advance tax", "challan"],
         "Statutory Tax Payable",  "GST / TDS compliance payout",
         "சட்டப்பூர்வ வரி செலுத்தல்", "GST / TDS இணக்கத்தன்மை செலுத்தல்"),
        ("utility", ["electricity", "power", "utility", "water", "msedcl"],
         "Utility Power Bill",     "Recurring operational utility charge",
         "மின்சார பயன்பாட்டு கட்டணம்", "தொடர்ச்சியான செயல்பாட்டு மின்சார கட்டணம்"),
        ("vendor",  ["vendor", "material", "logistics", "freight", "supplier", "purchase"],
         "Key Vendor Payable",     "Raw material & logistics payment",
         "முக்கிய சப்ளையர் செலுத்தல்", "மூலப்பொருள் & லாஜிஸ்டிக்ஸ் கட்டணம்"),
    ]

    detected = {}
    for r in sorted(rows, key=lambda x: x["date"]):
        amt = r["amount"]
        if amt >= 0:
            continue
        desc = r["description"].lower()
        amt_abs = abs(amt)
        dt_str = r["date"]

        for cat_key, keywords, title, base_desc, title_ta, base_desc_ta in patterns:
            if any(k in desc for k in keywords):
                if cat_key not in detected:
                    detected[cat_key] = {
                        "title": title_ta if _ta else title,
                        "base_desc": base_desc_ta if _ta else base_desc,
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


def _derive_all_from_csv(rows: List[Dict], threshold: float = 500000.0, profile: Dict[str, Any] = None) -> Dict[str, Any]:
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

    # 5. Derive Scheme Finder Eligibility from CSV + business profile (rule-based engine)
    annual_turnover = m_inflow * 12
    _profile = profile or {}
    schemes = _match_schemes(_profile, annual_turnover, loan_calc, _SCHEME_CATALOG)
    logger.info(
        "[SCHEME FINDER] profile=%r | udyam=%s | turnover=₹%.2f Cr | matched=%d schemes",
        _profile,
        _classify_udyam_category(annual_turnover),
        annual_turnover / 10000000,
        len(schemes),
    )

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
    sector: str = Form(""),
    business_type: str = Form("manufacturing"),
    state: str = Form(""),
    women_owned: bool = Form(False),
    export_oriented: bool = Form(False),
    sc_st_owned: bool = Form(False),
):
    """
    Accept multipart CSV upload OR raw csv_text string, return full dynamic dashboard telemetry.
    Optional profile fields (sector, business_type, state, women_owned, export_oriented,
    sc_st_owned) are forwarded to the rule-based scheme eligibility engine.
    """
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

        profile = {
            "sector": sector.strip(),
            "business_type": business_type.strip() or "manufacturing",
            "state": state.strip(),
            "women_owned": women_owned,
            "export_oriented": export_oriented,
            "sc_st_owned": sc_st_owned,
        }
        logger.info("[ANALYZE CSV FULL] Profile: %r", profile)

        result = _derive_all_from_csv(rows, threshold, profile=profile)
        return result
    except Exception as exc:
        logger.error("[ANALYZE CSV FULL ERROR] %s", exc)
        return {"error": f"Server error analyzing CSV: {str(exc)}"}


@app.post("/api/cash-flow/analyze-ledger-photo")
async def analyze_ledger_photo(
    file: UploadFile = File(...),
):
    """
    Accept an uploaded photo (PNG/JPG) of a handwritten paper ledger.
    Uses Gemini Vision (gemini-3.6-flash) to extract structured transaction rows
    [{date, description, amount, confidence}].
    Returns extracted rows WITHOUT auto-committing for user review.
    """
    try:
        if not file or not file.filename:
            return {"error": "No image file provided."}

        filename = file.filename
        ext = os.path.splitext(filename)[1].lower()
        if ext not in (".png", ".jpg", ".jpeg", ".webp"):
            return {"error": f"Invalid image format '{ext}'. Please upload a PNG, JPG, or JPEG photo of your ledger."}

        image_bytes = await file.read()
        if not image_bytes:
            return {"error": "Uploaded image file is empty."}

        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not api_key:
            return {"error": "Gemini API key is not configured (`GEMINI_API_KEY`). Please set your key in frontend/key.env."}

        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)

        mime_type = file.content_type or ("image/jpeg" if ext in (".jpg", ".jpeg") else "image/png")
        image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)

        current_year = date.today().year
        prompt_text = f"""
You are an expert financial OCR assistant specialized in reading handwritten Indian MSME paper ledgers, bahi-khata notebooks, and daily transaction logs.

Examine the provided image of a ledger page carefully and extract every visible financial transaction.

### INPUT CHARACTERISTICS & MSME SHORTHAND TO HANDLE:
1. Handwriting & Scripts: Indian MSME ledgers frequently contain mixed English and regional scripts (Tamil, Hindi/Devanagari, Gujarati, Kannada, Telugu, Bengali) and regional numerals (e.g. Tamil ௧ ௨ ௩ or Devanagari १ २ ३). Convert all numerals to standard Arabic digits (0-9). Translate or transcribe regional words into clean English descriptions (e.g., "சம்பளம்" or "वेतन" → "Salary Payment").
2. Direction of Funds (Inflow vs Outflow):
   - INFLOWS (Positive amount +X): Marked as "In", " जमा" (Jama), "Credit" / "Cr", "Recd" / "Received", "Inflow", "+", or written in a "Received/Jama" column.
   - OUTFLOWS (Negative amount -X): Marked as "Out", "खर्च" / "नामे" (Kharch/Name), "Debit" / "Dr", "Paid" / "Given", "Gave", "Outflow", "-", or written in a "Paid/Kharch" column.
3. Cr vs Dr Rules: "Cr" or "Dr" written directly next to an amount indicates direction (Credit/Debit), NOT a Crore magnitude. Only treat "Crore" or "Cr." as a magnitude multiplier when spelled out in full as a distinct word (e.g. "₹1.2 Crore"), never from a bare "Cr" suffix on a transaction line.
4. Amounts: Parse currency notations (₹, Rs, INR, K, L, Lakhs, Cr, C). Convert all amounts into plain numeric float values in INR. (e.g. "₹25K" or "25,000" → 25000; "₹1.5L" → 150000; "500 Dr" → -500).
5. Dates: Standardize all dates to ISO format "YYYY-MM-DD". Use {current_year} as the assumed year for dates missing a year (e.g. "15 May" → "{current_year}-05-15"). If date is completely missing for a row, use the date of the preceding line item.
6. Corrections & Struck-Through Text: If a value on the page is struck through or crossed out and replaced with a correction, use ONLY the corrected value. Do not emit the struck-through original as a separate transaction.
7. Running Balances: If a row includes a running balance/total column in addition to the transaction amount, extract only the individual transaction amount — ignore the running balance.
8. Confidence Level: For each transaction, evaluate confidence as "high" or "low". Mark "low" for any row where handwriting, smudging, or ambiguity makes you uncertain about the date, amount, or direction — do not silently guess with high confidence.
9. Non-tabular / Messy Layouts: Entries may be written across margins, in informal lines, or in two-column book layouts. Read every line item accurately.

### LEGIBILITY & REJECTION CRITERIA:
- If the image is NOT a financial ledger, notebook, invoice, receipt, or transaction sheet (e.g., a photo of a person, landscape, object, or unrelated document), OR if the handwriting/text is completely unreadable/blurry:
  Return JSON with an empty transactions list and a clear error explanation:
  {{"error": "Image is not a readable financial ledger or receipt. Please upload a clear photo of your paper ledger page.", "transactions": []}}

### REQUIRED OUTPUT FORMAT:
Return ONLY a raw JSON object (no markdown formatting, no ```json ``` code fences, no introductory or trailing text) matching this exact JSON schema:

{{
  "transactions": [
    {{
      "date": "YYYY-MM-DD",
      "description": "Clear description of transaction",
      "amount": float_value,
      "confidence": "high"
    }}
  ]
}}
"""

        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=[image_part, prompt_text]
        )

        resp_text = (response.text or "").strip()
        if resp_text.startswith("```"):
            resp_text = re.sub(r'^```(?:json)?\s*', '', resp_text)
            resp_text = re.sub(r'\s*```$', '', resp_text)

        try:
            data = json.loads(resp_text)
        except Exception as json_err:
            logger.error("[LEDGER OCR JSON ERROR] Failed to parse model output (%s): %r", json_err, resp_text)
            return {"error": "Could not parse transactions from photo. Please try a clearer picture of your ledger."}

        if data.get("error"):
            return {"error": data["error"]}

        raw_txns = data.get("transactions", [])
        if not raw_txns:
            return {"error": "No valid financial transactions could be detected in this photo. Please ensure the image shows ledger entries clearly."}

        valid_rows = []
        for item in raw_txns:
            dt_str = str(item.get("date", "")).strip()
            desc_str = str(item.get("description", "")).strip() or "Ledger Transaction"
            try:
                amt_val = float(item.get("amount", 0.0))
            except (ValueError, TypeError):
                amt_val = 0.0

            conf = "low" if str(item.get("confidence", "")).lower() == "low" else "high"

            try:
                dt_clean = dt_str.split(" ")[0].split("T")[0].replace("/", "-").strip()
                parts = dt_clean.split("-")
                if len(parts) == 3:
                    if len(parts[0]) == 4:
                        norm_d = f"{int(parts[0]):04d}-{int(parts[1]):02d}-{int(parts[2]):02d}"
                    elif len(parts[2]) == 4:
                        norm_d = f"{int(parts[2]):04d}-{int(parts[1]):02d}-{int(parts[0]):02d}"
                    else:
                        norm_d = dt_clean
                else:
                    norm_d = f"{current_year}-01-01"
                date.fromisoformat(norm_d)
            except Exception:
                norm_d = f"{current_year}-01-01"

            valid_rows.append({
                "date": norm_d,
                "description": desc_str,
                "amount": amt_val,
                "confidence": conf
            })

        logger.info("[ANALYZE LEDGER PHOTO] Successfully extracted %d rows from %s", len(valid_rows), filename)
        return {
            "filename": filename,
            "extracted_count": len(valid_rows),
            "transactions": valid_rows
        }

    except Exception as exc:
        logger.error("[ANALYZE LEDGER PHOTO ERROR] %s", exc)
        return {"error": f"Error analyzing ledger photo: {str(exc)}"}


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
