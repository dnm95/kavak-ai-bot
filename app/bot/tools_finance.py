from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any


# hard rules
FIXED_ANNUAL_RATE: float = 0.10
ALLOWED_TERMS_YEARS: List[int] = [3, 4, 5, 6]

@dataclass(frozen=True)
class FinanceOption:
  """One loan option for a given term length."""
  years: int
  months: int
  monthly_payment: float
  total_paid: float
  total_interest: float


def monthly_payment(principal: float, annual_rate: float, years: int) -> float:
  """
  Compute the fixed monthly payment for an amortized loan.

  principal: amount financed (>= 0)
  annual_rate: e.g. 0.10 for 10% yearly
  years: loan term length (e.g. 3..6)

  Formula: payment = P * (r(1+r)^n) / ((1+r)^n - 1)
    where r is monthly rate, n is number of payments.
  """
  if principal <= 0:
    return 0.0

  r = annual_rate / 12.0
  n = years * 12

  # Degenerate case: zero interest
  if r == 0:
    return principal / n

  factor = (r * (1 + r) ** n) / ((1 + r) ** n - 1)
  return principal * factor


def finance_quote(price: float, down_payment: float) -> Dict[str, Any]:
  """
  Generate financing options for the Kavak sales bot.

  HARD requirements from the challenge:
  - Annual interest rate is fixed at 10%
  - Allowed terms are only 3, 4, 5, 6 years

  Returns a JSON-serializable dict for the orchestrator tool_result_json.
  """
  # Basic sanitization: avoid negative inputs
  price = max(float(price), 0.0)
  down_payment = max(float(down_payment), 0.0)

  # If down payment exceeds the price, cap it (financed amount becomes 0)
  down_payment = min(down_payment, price)

  financed = price - down_payment

  options: List[FinanceOption] = []
  for years in ALLOWED_TERMS_YEARS:
    m = monthly_payment(financed, FIXED_ANNUAL_RATE, years)
    months = years * 12
    total = m * months
    interest = max(total - financed, 0.0)

    options.append(
      FinanceOption(
        years=years,
        months=months,
        monthly_payment=m,
        total_paid=total,
        total_interest=interest,
      )
    )

  return {
    "price": round(price, 2),
    "down_payment": round(down_payment, 2),
    "financed_amount": round(financed, 2),
    "annual_rate": FIXED_ANNUAL_RATE,
    "terms_years": ALLOWED_TERMS_YEARS,
    "options": [
      {
        "years": o.years,
        "months": o.months,
        "monthly_payment": round(o.monthly_payment, 2),
        "total_paid": round(o.total_paid, 2),
        "total_interest": round(o.total_interest, 2),
      }
      for o in options
    ],
  }
