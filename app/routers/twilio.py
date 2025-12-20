import logging
from fastapi import APIRouter, Request
from fastapi.responses import Response

from app.bot.orchestrator import chat
from app.schemas import Message

logger = logging.getLogger("twilio")
router = APIRouter(prefix="/twilio", tags=["twilio"])

# In-memory conversation store per WhatsApp sender.
# NOTE: Only in memory for demo. In production, we should use a DB
SESSIONS: dict[str, list[Message]] = {}

# Prevent unbounded memory growth per user
MAX_MESSAGES_PER_USER = 30  # roughly 15 user+assistant turns

@router.post("/webhook")
async def twilio_webhook(request: Request):
  """
  Twilio WhatsApp webhook.
  Twilio sends payload as application/x-www-form-urlencoded.
  We parse form fields, append the user message to a per-sender session,
  call the AI orchestrator, and return TwiML XML.
  """
  form = await request.form()

  # Twilio WhatsApp fields
  raw_from = str(form.get("From", "unknown"))      # e.g. "whatsapp:+521..."
  body = str(form.get("Body", "")).strip()         # message content
  msg_sid = str(form.get("MessageSid", ""))        # unique message id
  profile = str(form.get("ProfileName", ""))       # optional user profile name

  # Normalize the session key so it is consistent across requests
  # (keep the full raw identifier to avoid collisions)
  session_key = raw_from

  logger.info(
    "Incoming WhatsApp message | sid=%s | from=%s | profile=%s | body=%r",
    msg_sid, raw_from, profile, body
  )

  # If the message is empty, respond quickly without calling the LLM
  if not body:
    reply = "¿Me repites tu mensaje por favor? 🙂"
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
      <Response>
      <Message>{escape_xml(reply)}</Message>
      </Response>"""
    return Response(content=twiml, media_type="application/xml")

  # Retrieve conversation history for this sender
  history = SESSIONS.get(session_key, [])

  # Append the new user message
  history = history + [Message(role="user", content=body)]

  # Cap the history to prevent unbounded growth in memory
  if len(history) > MAX_MESSAGES_PER_USER:
    history = history[-MAX_MESSAGES_PER_USER:]

  # Call the orchestrator (router + tools + answer)
  reply, updated_messages, debug = await chat(user_id=session_key, messages=history)

  # Persist updated history back into memory, also capped
  if len(updated_messages) > MAX_MESSAGES_PER_USER:
    updated_messages = updated_messages[-MAX_MESSAGES_PER_USER:]
  SESSIONS[session_key] = updated_messages

  logger.info(
    "Reply | to=%s | text=%r | intent=%s | tool=%s",
    raw_from,
    reply,
    debug.get("intent"),
    (debug.get("route") or {}).get("tool")
  )

  # Return TwiML XML response (Twilio expects this format)
  twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
    <Response>
    <Message>{escape_xml(reply)}</Message>
    </Response>"""

  return Response(content=twiml, media_type="application/xml")


def escape_xml(text: str) -> str:
  """Minimal XML escaping to keep TwiML valid even with special characters."""
  return (
    text.replace("&", "&amp;")
      .replace("<", "&lt;")
      .replace(">", "&gt;")
      .replace('"', "&quot;")
      .replace("'", "&apos;")
  )
