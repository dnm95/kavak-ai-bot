import os
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Tuple

import pandas as pd
from rapidfuzz import fuzz, process

CATALOG_PATH = os.getenv("CATALOG_PATH", "app/data/sample_caso_ai_engineer.csv")

_df_cache: Optional[pd.DataFrame] = None
_makes_cache: Optional[List[str]] = None

def _load_catalog() -> pd.DataFrame:
  global _df_cache, _makes_cache
  if _df_cache is None:
    df = pd.read_csv(CATALOG_PATH)

    # Normalizaciones básicas
    df["make_norm"] = df["make"].astype(str).str.lower().str.strip()
    df["model_norm"] = df["model"].astype(str).str.lower().str.strip()

    _df_cache = df
    _makes_cache = sorted(df["make_norm"].dropna().unique().tolist())
  return _df_cache

def _best_make_match(make_raw: str, makes: List[str]) -> Tuple[Optional[str], int]:
  if not make_raw:
    return None, 0
  q = make_raw.lower().strip()
  best = process.extractOne(q, makes, scorer=fuzz.WRatio)
  if not best:
    return None, 0
  match, score, _ = best
  return match, int(score)

def _best_model_match(model_raw: str, models: List[str]) -> Tuple[Optional[str], int]:
  if not model_raw:
    return None, 0
  q = model_raw.lower().strip()
  best = process.extractOne(q, models, scorer=fuzz.WRatio)
  if not best:
    return None, 0
  match, score, _ = best
  return match, int(score)

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
  df = _load_catalog().copy()
  makes = _makes_cache or []

  debug = {"make_input": make, "model_input": model}

  # 1) Fuzzy match marca
  make_norm = None
  make_score = 0
  if make:
    make_norm, make_score = _best_make_match(make, makes)
    debug["make_match"] = {"match": make_norm, "score": make_score}
    if make_norm and make_score >= 80:
        df = df[df["make_norm"] == make_norm]

  # 2) Fuzzy match modelo (sobre los modelos ya filtrados por marca si aplica)
  if model and len(df) > 0:
    model_candidates = sorted(df["model_norm"].dropna().unique().tolist())
    model_norm, model_score = _best_model_match(model, model_candidates)
    debug["model_match"] = {"match": model_norm, "score": model_score}
    if model_norm and model_score >= 75:
      df = df[df["model_norm"] == model_norm]

  # 3) Filtros determinísticos
  if year is not None:
    df = df[df["year"] == int(year)]
  if budget_max is not None:
    df = df[df["price"] <= float(budget_max)]
  if km_max is not None:
    df = df[df["km"] <= int(km_max)]

  if wants_car_play is True:
    df = df[df["car_play"].astype(str).str.lower().str.contains("sí")]
  if wants_bluetooth is True:
    df = df[df["bluetooth"].astype(str).str.lower().str.contains("sí")]

  # 4) Ranking simple: (precio bajo) + (km bajo) + (año alto)
  if len(df) == 0:
    return {"results": [], "count": 0, "debug": debug}

  df_rank = df.sort_values(by=["year", "km", "price"], ascending=[False, True, True]).head(limit)

  results = []
  for _, r in df_rank.iterrows():
    results.append({
      "stock_id": int(r["stock_id"]),
      "make": r["make"],
      "model": r["model"],
      "year": int(r["year"]),
      "version": r.get("version", ""),
      "price": float(r["price"]),
      "km": int(r["km"]),
      "bluetooth": r.get("bluetooth", None),
      "car_play": r.get("car_play", None),
    })

  return {"results": results, "count": len(results), "debug": debug}
