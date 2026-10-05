from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class Quest(BaseModel):
    """Matches the Java Quest DTO (supports both conversationId and conversation_id)."""
    question: str = Field(..., description="The user query or question")
    conversationId: Optional[str] = Field(None, alias="conversation_id", description="Session identifier for multi-turn chat memory")

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "question": "What is Shepreneur?",
                "conversationId": "session-101"
            }
        }
    }

class AskResponse(BaseModel):
    """Response returned for user questions."""
    answer: str
    conversation_id: str
    sources: List[str]
    retrieved_count: int

class UploadResponse(BaseModel):
    """Response returned after processing and indexing a PDF."""
    message: str
    filename: str
    pages_processed: int
    chunks_stored: int
    parent_document_id: str

class MemoryClearRequest(BaseModel):
    conversation_id: Optional[str] = Field("default-session", description="Conversation session to clear")

class MemoryClearResponse(BaseModel):
    """Response returned after clearing chat memory."""
    message: str
    conversation_id: str
    status: str = "success"

class HealthResponse(BaseModel):
    """Health status of the service."""
    status: str
    database_connected: bool
    chat_model: str
    embedding_model: str
    vector_dimension: int
