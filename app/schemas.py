from typing import List, Literal
from pydantic import BaseModel

class Message(BaseModel):
  role: Literal["user", "assistant", "system"]
  content: str


class ChatRequest(BaseModel):
  user_id: str = "demo"
  messages: List[Message]


class ChatResponse(BaseModel):
  reply: str
  messages: List[Message]
  debug: dict
