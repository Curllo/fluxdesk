from pydantic import BaseModel, Field
from typing import Optional, Any


class ApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: Any = None


class ChatMessage(BaseModel):
    message: str = Field(..., max_length=10000)
    history: list[dict] = Field(default_factory=list, max_length=50)


class StreamEvent(BaseModel):
    event: str
    data: dict


class CreateWindowRequest(BaseModel):
    window_type: str = Field(..., alias="type")
    position: Optional[dict] = None
    size: Optional[dict] = None
    data: Optional[dict] = None

    class Config:
        populate_by_name = True
