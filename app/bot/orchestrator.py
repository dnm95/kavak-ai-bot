from typing import List, Tuple, Dict, Any
import os, json, logging
from openai import OpenAI

from app.schemas import Message
from app.bot.tools_finance import finance_quote
from app.bot.tools_catalog import catalog_search
from app.bot.prompts import ROUTER_PROMPT, ANSWER_PROMPT, KAVAK_CONTEXT

logger = logging.getLogger("orchestrator")

MODEL = os.getenv("MODEL", "gpt-5-mini")

# Keep the router context small and predictable
ROUTER_CONTEXT_MAX = int(os.getenv("ROUTER_CONTEXT_MAX", "6"))

# Prevent memory growth when a client keeps sending the entire chat forever
MAX_HISTORY_MESSAGES = int(os.getenv("MAX_HISTORY_MESSAGES", "30"))


def get_openai_client() -> OpenAI:
  """
  Create an OpenAI client using the OPENAI_API_KEY env var.
  """
  api_key = os.getenv("OPENAI_API_KEY")
  if not api_key:
    raise RuntimeError("OPENAI_API_KEY is not set")
  return OpenAI(api_key=api_key)


def _last_user_text(conversation: List[dict]) -> str:
  """
  Return the most recent user message content from a conversation list.
  """
  for m in reversed(conversation):
    if m.get("role") == "user":
      return m.get("content", "")
  return ""


def _coerce_number(x):
  """
  Best-effort parse numbers coming from the router JSON.
  Handles strings like "350000" or "350,000".
  """
  if isinstance(x, (int, float)):
    return float(x)
  if isinstance(x, str):
    cleaned = x.replace(",", "").strip()
    try:
      return float(cleaned)
    except Exception:
      return None
  return None


def _cap_history(messages: List[Message]) -> List[Message]:
  """
  Cap the conversation length to avoid unbounded growth.
  For a demo, last ~30 messages is usually enough.
  """
  if len(messages) <= MAX_HISTORY_MESSAGES:
    return messages
  return messages[-MAX_HISTORY_MESSAGES:]


async def chat(user_id: str, messages: List[Message]) -> Tuple[str, List[Message], dict]:
  """
  Main chat entrypoint:
  1) Convert messages to OpenAI format
  2) Run router to select intent/tool + extract fields
  3) Execute tool (if any)
  4) Run answer model with KAVAK_CONTEXT + tool_result_json + conversation
  5) Return reply + updated conversation + debug metadata
  """
  client = get_openai_client()

  # Cap the incoming history (especially important for WhatsApp / long chats)
  messages = _cap_history(messages)

  # Convert Pydantic models to OpenAI chat format
  conversation = [{"role": m.role, "content": m.content} for m in messages]

  # Router only sees last N messages to reduce cost and keep it focused
  router_context = conversation[-ROUTER_CONTEXT_MAX:] if len(conversation) > ROUTER_CONTEXT_MAX else conversation
  last_user_message = _last_user_text(conversation)

  # -------------------------
  # 1) ROUTER CALL
  # -------------------------
  try:
    r = client.responses.create(
      model=MODEL,
      input=[
        {"role": "system", "content": ROUTER_PROMPT},
        *router_context,
      ],
      reasoning={"effort": "minimal"},
    )
    raw = (r.output_text or "").strip()
    route = json.loads(raw)
  except Exception as e:
    # If router fails, we fall back to a safe default
    logger.exception("Router failed: %s", e)
    route = {"intent": "other", "extracted": {}, "tool": "none", "raw": ""}

  intent = route.get("intent", "other")
  extracted = route.get("extracted", {}) or {}
  tool = route.get("tool", "none")

  # Extra safety: accept only known tools
  if tool not in {"finance_quote", "catalog_search", "none", "kb_answer"}:
    tool = "none"

  # Small guardrails (optional):
  # - If intent looks like finance but tool was none, still attempt finance tool
  if intent == "finance" and tool == "none":
    tool = "finance_quote"
  if intent == "catalog" and tool == "none":
    tool = "catalog_search"

  tool_result: Dict[str, Any] = {"tool": "none"}

  # -------------------------
  # 2) TOOL EXECUTION
  # -------------------------
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

  # -------------------------
  # 3) ANSWER CALL
  # -------------------------
  try:
    a = client.responses.create(
      model=MODEL,
      input=[
        {"role": "system", "content": ANSWER_PROMPT},
        # Static grounded context for Kavak (value prop, processes, locations, docs)
        {"role": "system", "content": f"KAVAK_CONTEXT:\n{KAVAK_CONTEXT}"},
        # Full conversation so the assistant can be coherent
        *conversation,
        # Tool output is passed as system context to keep it "source of truth"
        {
          "role": "system",
          "content": f"tool_result_json: {json.dumps(tool_result, ensure_ascii=False)}",
        },
      ],
      reasoning={"effort": "minimal"},
    )
    reply = (a.output_text or "").strip()
  except Exception as e:
    # If model call fails, we return a safe user-facing error
    logger.exception("Answer generation failed: %s", e)
    reply = "Por ahora tuve un problema técnico al generar la respuesta. ¿Puedes intentar de nuevo en un momento?"

  updated_messages = list(messages) + [Message(role="assistant", content=reply)]
  updated_messages = _cap_history(updated_messages)

  debug = {"intent": intent, "route": route, "tool_result": tool_result}

  return reply, updated_messages, debug
