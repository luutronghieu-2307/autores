from pydantic import BaseModel, Field


class SearchQueries(BaseModel):
    search_queries: list[str]


class ModifiedParagraphs(BaseModel):
    new_paragraphs: str


class ParagraphsSuggestions(BaseModel):
    suggestions: list[str]


class ParagraphsComment(BaseModel):
    comment: str


class NoContextParagraphsComment(BaseModel):
    paragraphs: str
    comment: str


class NoContextParagraphsComments(BaseModel):
    output: list[NoContextParagraphsComment]


class EnhancedParagraphs(BaseModel):
    new_content: str


class NeedEnhanceParagraphs(BaseModel):
    score: int


class LitSection(BaseModel):
    lit_review: int = Field(description="The order of literature review section")


class LitSectionComment(BaseModel):
    need_enhance: bool
    comment: str