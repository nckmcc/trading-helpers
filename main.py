#!/usr/bin/env python3
"""
Trading Helpers API — persistent service for the Agentic Trading Account (v1.8.4)

Endpoints:
  GET  /health
  POST /size/option
  POST /size/equity
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from dataclasses import dataclass

app = FastAPI(
    title="Trading Helpers API",
    description="Mechanical helpers for Agentic Trading Account v1.8.4",
    version="0.1.0",
)


# ---------- Models ----------

class OptionSizeRequest(BaseModel):
    account_value: float = Field(..., gt=0, description="Current account equity")
    max_risk: float = Field(75.0, gt=0, description="Desired max risk for this idea")
    premium_per_share: float = Field(..., gt=0, description="Option price per share")
    is_index_etf_exemption: bool = Field(False, description="True for SPY/QQQ/IBIT single-contract $100 exemption")
    current_open_risk: float = Field(0.0, ge=0, description="Total $ risk already open")


class EquitySizeRequest(BaseModel):
    account_value: float = Field(..., gt=0)
    max_risk: float = Field(75.0, gt=0)
    price: float = Field(..., gt=0)
    stop_price: float = Field(..., description="Invalidation / stop price")
    current_open_risk: float = Field(0.0, ge=0)
    current_notional: float = Field(0.0, ge=0)
    allow_fractional: bool = Field(True)


class SizingResponse(BaseModel):
    instrument_type: str
    max_risk_allowed: float
    size: float
    total_premium_or_notional: float
    actual_risk: float
    notes: List[str]


# ---------- Core logic (same as standalone script) ----------

def calculate_option_size(
    account_value: float,
    max_risk: float,
    premium_per_share: float,
    is_index_etf_exemption: bool = False,
    current_open_risk: float = 0.0,
) -> SizingResponse:
    notes = []
    contract_cost = premium_per_share * 100

    if is_index_etf_exemption:
        max_risk = min(max_risk, 100.0)
        notes.append("Index ETF single-contract exemption applied (max $100 risk, sole position only).")
    else:
        max_risk = min(max_risk, 75.0)

    aggregate_cap = account_value * 0.40
    remaining_risk_budget = max(0.0, aggregate_cap - current_open_risk)
    effective_max_risk = min(max_risk, remaining_risk_budget)

    if effective_max_risk <= 0:
        return SizingResponse(
            instrument_type="option",
            max_risk_allowed=0.0,
            size=0.0,
            total_premium_or_notional=0.0,
            actual_risk=0.0,
            notes=["No remaining risk budget under 40% aggregate cap."]
        )

    max_contracts = effective_max_risk / contract_cost
    contracts = int(max_contracts)

    if contracts < 1:
        notes.append(
            f"Even 1 contract costs ${contract_cost:.2f}, which exceeds the "
            f"effective max risk of ${effective_max_risk:.2f}."
        )
        return SizingResponse(
            instrument_type="option",
            max_risk_allowed=round(effective_max_risk, 2),
            size=0.0,
            total_premium_or_notional=0.0,
            actual_risk=0.0,
            notes=notes
        )

    if is_index_etf_exemption and contracts > 1:
        notes.append("Exemption allows only a single contract — capped at 1.")
        contracts = 1

    actual_risk = contracts * contract_cost
    return SizingResponse(
        instrument_type="option",
        max_risk_allowed=round(effective_max_risk, 2),
        size=float(contracts),
        total_premium_or_notional=round(actual_risk, 2),
        actual_risk=round(actual_risk, 2),
        notes=notes
    )


def calculate_equity_size(
    account_value: float,
    max_risk: float,
    price: float,
    stop_price: float,
    current_open_risk: float = 0.0,
    current_notional: float = 0.0,
    allow_fractional: bool = True,
) -> SizingResponse:
    notes = []
    max_risk = min(max_risk, 75.0)

    risk_per_share = abs(price - stop_price)
    if risk_per_share <= 0:
        raise HTTPException(status_code=400, detail="Stop must be different from entry price.")

    aggregate_cap = account_value * 0.40
    remaining_risk_budget = max(0.0, aggregate_cap - current_open_risk)
    effective_max_risk = min(max_risk, remaining_risk_budget)

    if effective_max_risk <= 0:
        return SizingResponse(
            instrument_type="equity",
            max_risk_allowed=0.0,
            size=0.0,
            total_premium_or_notional=0.0,
            actual_risk=0.0,
            notes=["No remaining risk budget under 40% aggregate cap."]
        )

    shares_from_risk = effective_max_risk / risk_per_share
    notional_cap = account_value * 1.0
    remaining_notional = max(0.0, notional_cap - current_notional)
    shares_from_notional = remaining_notional / price if price > 0 else 0.0

    shares = min(shares_from_risk, shares_from_notional)

    if not allow_fractional:
        shares = float(int(shares))

    if shares <= 0:
        notes.append("Position size rounded to zero after applying risk and notional caps.")
        return SizingResponse(
            instrument_type="equity",
            max_risk_allowed=round(effective_max_risk, 2),
            size=0.0,
            total_premium_or_notional=0.0,
            actual_risk=0.0,
            notes=notes
        )

    actual_risk = shares * risk_per_share
    notional = shares * price

    if shares_from_notional < shares_from_risk:
        notes.append("Size limited by 100% notional exposure cap.")

    return SizingResponse(
        instrument_type="equity",
        max_risk_allowed=round(effective_max_risk, 2),
        size=round(shares, 4) if allow_fractional else float(int(shares)),
        total_premium_or_notional=round(notional, 2),
        actual_risk=round(actual_risk, 2),
        notes=notes
    )


# ---------- Endpoints ----------

@app.get("/health")
def health():
    return {"status": "ok", "service": "trading-helpers", "version": "0.1.0"}


@app.post("/size/option", response_model=SizingResponse)
def size_option(req: OptionSizeRequest):
    return calculate_option_size(
        account_value=req.account_value,
        max_risk=req.max_risk,
        premium_per_share=req.premium_per_share,
        is_index_etf_exemption=req.is_index_etf_exemption,
        current_open_risk=req.current_open_risk,
    )


@app.post("/size/equity", response_model=SizingResponse)
def size_equity(req: EquitySizeRequest):
    return calculate_equity_size(
        account_value=req.account_value,
        max_risk=req.max_risk,
        price=req.price,
        stop_price=req.stop_price,
        current_open_risk=req.current_open_risk,
        current_notional=req.current_notional,
        allow_fractional=req.allow_fractional,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
