from pydantic import BaseModel


class TranslatedChunk(BaseModel):
    translated_text: str