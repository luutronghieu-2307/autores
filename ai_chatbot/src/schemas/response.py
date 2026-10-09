from pydantic import BaseModel, Field


class Response(BaseModel):
    status: bool
    response: str


class FunctionRoute(BaseModel):
    qa: bool
    generative_writing: bool


class StandaloneQuestion(BaseModel):
    """A standalone question that can be understood without the chat history."""
    standalone_question: str = Field(
        ...,
        description="The reformulated, self-contained question.",
    )