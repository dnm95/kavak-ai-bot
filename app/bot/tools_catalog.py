import os
from typing import Optional, Dict, Any, List, Tuple

import pandas as pd
from rapidfuzz import fuzz, process

CATALOG_PATH = os.getenv("CATALOG_PATH", "app/data/sample_caso_ai_engineer.csv")

# In-memory caches
_df_cache: Optional[pd.DataFrame] = None
_makes_cache: Optional[List[str]] = None


def _load_catalog() -> pd.DataFrame:
  """
  Load the catalog CSV once and keep it cached in memory.

  We also add normalized helper columns to make filtering and fuzzy matching more stable.
  """
  global _df_cache, _makes_cache

  if _df_cache is None:
    df = pd.read_csv(CATALOG_PATH)

    # Basic normalization for fuzzy matching
    # (lowercase + trim) to reduce mismatch due to casing/spaces
    if "make" not in df.columns or "model" not in df.columns:
      raise ValueError("Catalog CSV must include 'make' and 'model' columns")

    df["make_norm"] = df["make"].astype(str).str.lower().str.strip()
    df["model_norm"] = df["model"].astype(str).str.lower().str.strip()

    _df_cache = df

    # Cache all unique makes for quick fuzzy matching
    _makes_cache = sorted(df["make_norm"].dropna().unique().tolist())

  return _df_cache


def _best_make_match(make_raw: str, makes: List[str]) -> Tuple[Optional[str], int]:
  """
  Fuzzy match the user-provided make against known makes.
  Returns: (best_match, score)
  """
  if not make_raw:
    return None, 0

  q = make_raw.lower().strip()
  best = process.extractOne(q, makes, scorer=fuzz.WRatio)
  if not best:
    return None, 0

  match, score, _ = best
  return match, int(score)


def _best_model_match(model_raw: str, models: List[str]) -> Tuple[Optional[str], int]:
  """
  Fuzzy match the user-provided model against candidate models.
  Returns: (best_match, score)
  """
  if not model_raw:
    return None, 0

  q = model_raw.lower().strip()
  best = process.extractOne(q, models, scorer=fuzz.WRatio)
  if not best:
    return None, 0

  match, score, _ = best
  return match, int(score)


def _truthy_yes(value: Any) -> bool:
  """
  Robust helper to interpret 'yes' values coming from CSV.
  Handles: "sí", "si", "yes", "true", "1", etc.
  """
  if value is None:
    return False
  s = str(value).strip().lower()
  return s in {"sí", "si", "yes", "true", "1", "y"}


def catalog_search(
  make: Optional[str] = None,
  model: Optional[str] = None,
  year: Optional[int] = None,
  budget_max: Optional[float] = None,
  km_max: Optional[int] = None,
  wants_car_play: Optional[bool] = None,
  wants_bluetooth: Optional[bool] = None,
  limit: int = 5,
) -> Dict[str, Any]:
  """
  Search a demo catalog using:
  - fuzzy match for make/model (to handle natural language typos)
  - deterministic filters for year/price/km and optional features
  - simple ranking (prefer newer year, lower km, lower price)

  Returns a dict compatible with the orchestrator tool_result_json.
  """
  df = _load_catalog().copy()
  makes = _makes_cache or []

  debug: Dict[str, Any] = {"make_input": make, "model_input": model}

  # --- 1) Make fuzzy matching ---
  if make:
    make_norm, make_score = _best_make_match(make, makes)
    debug["make_match"] = {"match": make_norm, "score": make_score}

    # Apply filter only if confidence is high enough (prevents over-filtering)
    if make_norm and make_score >= 80:
      df = df[df["make_norm"] == make_norm]

  # --- 2) Model fuzzy matching (only over the already filtered subset) ---
  if model and len(df) > 0:
    model_candidates = sorted(df["model_norm"].dropna().unique().tolist())
    model_norm, model_score = _best_model_match(model, model_candidates)
    debug["model_match"] = {"match": model_norm, "score": model_score}

    if model_norm and model_score >= 75:
      df = df[df["model_norm"] == model_norm]

  # --- 3) Deterministic filters ---
  if year is not None and "year" in df.columns:
    df = df[df["year"] == int(year)]

  if budget_max is not None and "price" in df.columns:
    df = df[df["price"] <= float(budget_max)]

  if km_max is not None and "km" in df.columns:
    df = df[df["km"] <= int(km_max)]

  # Optional features (only filter if user explicitly asked for them)
  if wants_car_play is True and "car_play" in df.columns:
    df = df[df["car_play"].apply(_truthy_yes)]

  if wants_bluetooth is True and "bluetooth" in df.columns:
    df = df[df["bluetooth"].apply(_truthy_yes)]

  # No results found
  if len(df) == 0:
    return {"results": [], "count": 0, "debug": debug}

  # --- 4) Simple ranking strategy ---
  # Newer year first, then lower km, then lower price
  sort_cols = [c for c in ["year", "km", "price"] if c in df.columns]
  ascending = [False, True, True][: len(sort_cols)]

  df_rank = df.sort_values(by=sort_cols, ascending=ascending).head(limit)

  # Build a clean response payload
  results: List[Dict[str, Any]] = []
  for _, r in df_rank.iterrows():
    results.append(
      {
        "stock_id": int(r["stock_id"]) if "stock_id" in r else None,
        "make": r.get("make", ""),
        "model": r.get("model", ""),
        "year": int(r["year"]) if "year" in r and pd.notna(r["year"]) else None,
        "version": r.get("version", ""),
        "price": float(r["price"]) if "price" in r and pd.notna(r["price"]) else None,
        "km": int(r["km"]) if "km" in r and pd.notna(r["km"]) else None,
        "bluetooth": r.get("bluetooth", None),
        "car_play": r.get("car_play", None),
      }
    )

  return {"results": results, "count": len(results), "debug": debug}