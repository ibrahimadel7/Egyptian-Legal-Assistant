from pydantic import BaseModel, Field
from typing import Literal


class ChatRequest(BaseModel):
    message: str = Field(min_length=2, max_length=8000)
    conversation_id: str | None = None


class SourceItem(BaseModel):
    source_id: str
    law_name: str
    categories: str = ""
    unit_label: str = ""
    unit_type: str = ""
    article_number: str = ""
    excerpt: str
    expanded: bool = False


class ChatResponse(BaseModel):
    conversation_id: str
    status: Literal["answered", "needs_clarification"]
    answer: str
    sources: list[SourceItem] = Field(default_factory=list)
    retrieval_query: str = ""
