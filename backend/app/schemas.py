from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

# Maximum number of past turns forwarded to every node prompt.
# Older turns are silently dropped on the frontend before sending.
HISTORY_WINDOW = 10   # 10 messages = 5 full exchange pairs

class ChatMessage(BaseModel):
    """A single turn in the conversation history."""
    role: str    # "user" or "assistant"
    content: str

class ChatRequest(BaseModel):
    user_query: str = Field(..., description="The user query or prompt")
    persona: Optional[str] = Field(default="Auto", description="Active persona: Auto, Financial Analyst, Legal Advisor, Technical Expert")
    client_id: Optional[str] = Field(default=None, description="WebSocket client ID for real-time node tracing")
    chat_history: List[ChatMessage] = Field(
        default_factory=list,
        description="Prior conversation turns (oldest first, newest last). Max HISTORY_WINDOW entries."
    )

class SourceMetadata(BaseModel):
    page_numbers: List[int] = []
    screenshots: List[str] = []
    generated_sql: Optional[str] = None
    math_code: Optional[str] = None

class ChatResponse(BaseModel):
    final_answer: str
    persona: str
    route_target: str
    source_metadata: Optional[Dict[str, Any]] = None
    suggested_queries: List[str] = []