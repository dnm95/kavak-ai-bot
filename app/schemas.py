from typing import List, Literal
from pydantic import BaseModel

# Represents a single message in the conversation history.
# The role follows the OpenAI / chat standard:
# - "user": end user message
# - "assistant": AI response
# - "system": system-level instructions (rarely sent by clients)
class Message(BaseModel):
  role: Literal["user", "assistant", "system"]
  content: str


# Request schema for the REST /chat endpoint.
# The frontend (or tests) sends:
# - user_id: logical identifier for the user/session
# - messages: full conversation history so far
class ChatRequest(BaseModel):
  user_id: str = "demo"
  messages: List[Message]


# Response schema for the REST /chat endpoint.
# It returns:
# - reply: the latest assistant message
# - messages: updated conversation history (including assistant reply)
# - debug: routing/tooling metadata (useful for evaluation and debugging)
class ChatResponse(BaseModel):
  reply: str
  messages: List[Message]
  debug: dict
