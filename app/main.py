from fastapi import FastAPI
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import ChatRequest, ChatResponse
from app.bot.orchestrator import chat

load_dotenv()

app = FastAPI(title="Kavak AI Sales Bot")
app.add_middleware(
  CORSMiddleware,
  allow_origins=["http://localhost:3000"],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

@app.get("/health")
def health():
  return {"ok": True}


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
  reply, updated_messages, debug = await chat(user_id=req.user_id, messages=req.messages)
  return ChatResponse(reply=reply, messages=updated_messages, debug=debug)
