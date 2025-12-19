from typing import List, Tuple
import os, json
from openai import OpenAI

from app.schemas import Message
from app.bot.tools_finance import finance_quote
from app.bot.tools_catalog import catalog_search
from app.bot.prompts import ROUTER_PROMPT, ANSWER_PROMPT, KAVAK_CONTEXT

MODEL = os.getenv("MODEL", "gpt-5-mini")

def get_openai_client() -> OpenAI:
  api_key = os.getenv("OPENAI_API_KEY")
  if not api_key:
    raise RuntimeError("OPENAI_API_KEY is not set")
  return OpenAI(api_key=api_key)


def _last_user_text(conversation: List[dict]) -> str:
  for m in reversed(conversation):
    if m.get("role") == "user":
      return m.get("content", "")
  return ""


def _coerce_number(x):
  """Best-effort parse for numbers coming as strings like '350000' or '350,000'."""
  if isinstance(x, (int, float)):
    return float(x)
  if isinstance(x, str):
    cleaned = x.replace(",", "").strip()
    try:
      return float(cleaned)
    except Exception:
      return None
  return None


async def chat(user_id: str, messages: List[Message]) -> Tuple[str, List[Message], dict]:
  client = get_openai_client()

  # Convert incoming Pydantic messages to OpenAI chat format
  conversation = [{"role": m.role, "content": m.content} for m in messages]

  # ROUTER sees last N turns (helps with context, but stays small)
  router_context = conversation[-6:] if len(conversation) > 6 else conversation
  last_user_message = _last_user_text(conversation)

  r = client.responses.create(
    model=MODEL,
    input=[
      {"role": "system", "content": ROUTER_PROMPT},
      *router_context,
    ],
    reasoning={"effort": "minimal"},
  )

  raw = (r.output_text or "").strip()
  try:
    route = json.loads(raw)
  except Exception:
    route = {"intent": "other", "extracted": {}, "tool": "none", "raw": raw}

  intent = route.get("intent", "other")
  extracted = route.get("extracted", {}) or {}
  tool = route.get("tool", "none")

  tool_result = {"tool": "none"}

  # ---- TOOLS ----
  if tool == "finance_quote":
    price = _coerce_number(extracted.get("price"))
    down = _coerce_number(extracted.get("down_payment"))

    if price is not None and down is not None:
      tool_result = {
        "tool": "finance_quote",
        "result": finance_quote(price=price, down_payment=down),
      }
    else:
      tool_result = {
        "tool": "finance_quote",
        "missing": {"price": price is None, "down_payment": down is None},
        "extracted": extracted,
      }

  elif tool == "catalog_search":
    tool_result = {
      "tool": "catalog_search",
      "result": catalog_search(
        make=extracted.get("make"),
        model=extracted.get("model"),
        year=extracted.get("year"),
        budget_max=extracted.get("budget_max"),
        km_max=extracted.get("km_max"),
        wants_car_play=extracted.get("wants_car_play"),
        wants_bluetooth=extracted.get("wants_bluetooth"),
        limit=5,
      ),
    }

  # ---- ANSWER (for value_prop/catalog/finance/other) ----
  a = client.responses.create(
    model=MODEL,
    input=[
      {"role": "system", "content": ANSWER_PROMPT},
      {"role": "system", "content": f"KAVAK_CONTEXT:\n{KAVAK_CONTEXT}"},
      *conversation,
      {
        "role": "system",
        "content": f"tool_result_json: {json.dumps(tool_result, ensure_ascii=False)}",
      },
    ],
    reasoning={"effort": "minimal"},
  )

  reply = (a.output_text or "").strip()

  updated_messages = list(messages) + [Message(role="assistant", content=reply)]
  debug = {"intent": intent, "route": route, "tool_result": tool_result}

  return reply, updated_messages, debug
