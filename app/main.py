import logging
from fastapi import FastAPI
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

# Request / response schemas for the REST chat endpoint
from app.schemas import ChatRequest, ChatResponse

# Core orchestration logic (LLM router + tools)
from app.bot.orchestrator import chat

# Twilio WhatsApp webhook router
from app.routers.twilio import router as twilio_router

# Load environment variables from .env file
# (OPENAI_API_KEY,etc.)
load_dotenv()

# Basic logging configuration for the app
logging.basicConfig(level=logging.INFO)

# FastAPI application instance
app = FastAPI(title="Kavak AI Sales Bot")

# CORS configuration
# This is mainly for local development (e.g. Next.js frontend)
# Twilio webhooks do NOT require CORS, but the /chat endpoint does.
app.add_middleware(
  CORSMiddleware,
  allow_origins=["http://localhost:3000", "https://kavak-ai-web.vercel.app"],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

# Register Twilio webhook routes
# Example: POST /twilio/webhook
app.include_router(twilio_router)

# Simple health check (root)
@app.get("/")
def health():
  return {"ok": True}

# Explicit health endpoint (useful for monitoring / load balancers)
@app.get("/health")
def health():
  return {"ok": True}

# Main REST chat endpoint (non-Twilio)
# This endpoint is useful for:
# - Local testing
# - Frontend integrations
# - Automated tests
#
# It receives:
# - user_id: logical user/session identifier
# - messages: conversation history (role + content)
#
# It returns:
# - assistant reply
# - updated conversation
# - debug info (intent, tool routing, extracted fields)
@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
  reply, updated_messages, debug = await chat(
    user_id=req.user_id,
    messages=req.messages
  )

  return ChatResponse(
    reply=reply,
    messages=updated_messages,
    debug=debug
  )
