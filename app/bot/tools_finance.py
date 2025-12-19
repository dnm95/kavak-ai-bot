from dataclasses import dataclass
from typing import List, Dict

@dataclass
class FinanceOption:
  years: int
  monthly_payment: float
  total_paid: float
  total_interest: float

def monthly_payment(principal: float, annual_rate: float, years: int) -> float:
  """
  Standard amortized loan payment.
  principal: amount financed
  annual_rate: e.g. 0.10
  years: 3..6
  """
  r = annual_rate / 12.0
  n = years * 12
  if principal <= 0:
    return 0.0
  if r == 0:
    return principal / n
  factor = (r * (1 + r) ** n) / ((1 + r) ** n - 1)
  return principal * factor

def finance_quote(price: float, down_payment: float, annual_rate: float = 0.10, min_years: int = 3, max_years: int = 6) -> Dict:
  financed = max(price - down_payment, 0.0)
  options: List[FinanceOption] = []
  for years in range(min_years, max_years + 1):
    m = monthly_payment(financed, annual_rate, years)
    total = m * years * 12
    interest = max(total - financed, 0.0)
    options.append(FinanceOption(years=years, monthly_payment=m, total_paid=total, total_interest=interest))

  return {
    "price": price,
    "down_payment": down_payment,
    "financed_amount": financed,
    "annual_rate": annual_rate,
    "options": [
      {
        "years": o.years,
        "monthly_payment": round(o.monthly_payment, 2),
        "total_paid": round(o.total_paid, 2),
        "total_interest": round(o.total_interest, 2),
      }
      for o in options
    ],
  }
