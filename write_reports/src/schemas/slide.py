from pydantic import BaseModel
from typing import TypedDict


class Slides(BaseModel):
    full_slides: str
    

class SummaryChunk(BaseModel):
    summary: str


class ChunkContent(TypedDict):
    content: str
    chunk_index: int
    heading_level: str  # h2, h3, etc.
    section_title: str  # Track section title for context