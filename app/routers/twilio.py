import logging
from fastapi import APIRouter, Request
from fastapi.responses import Response
from app.bot.orchestrator import chat
from app.schemas import Message

logger = logging.getLogger("twilio")
router = APIRouter(prefix="/twilio", tags=["twilio"])

SESSIONS: dict[str, list[Message]] = {}

@router.post("/webhook")
async def twilio_webhook(request: Request):
  form = await request.form()

  from_number = str(form.get("From", "unknown"))
  body = str(form.get("Body", "")).strip()
  msg_sid = str(form.get("MessageSid", ""))
  profile = str(form.get("ProfileName", ""))

  logger.info("Incoming WhatsApp message | sid=%s | from=%s | profile=%s | body=%r",
    msg_sid, from_number, profile, body)

  history = SESSIONS.get(from_number, [])
  history = history + [Message(role="user", content=body)]

  reply, updated_messages, debug = await chat(user_id=from_number, messages=history)
  SESSIONS[from_number] = updated_messages

  logger.info("Reply | to=%s | text=%r | intent=%s | tool=%s",
    from_number, reply, debug.get("intent"), (debug.get("route") or {}).get("tool"))

  twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
    <Response>
      <Message>{escape_xml(reply)}</Message>
    </Response>"""

  return Response(content=twiml, media_type="application/xml")


def escape_xml(text: str) -> str:
  return (
    text.replace("&", "&amp;")
      .replace("<", "&lt;")
      .replace(">", "&gt;")
      .replace('"', "&quot;")
      .replace("'", "&apos;")
  )
