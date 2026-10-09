from pydantic import BaseModel, Field


class ResearchQuestion(BaseModel):
    """Schema for research brief generation."""
    research_brief: str = Field(
        description="A research question that will be used to guide the research.",
    )


class SearchQueries(BaseModel):
    search_queries: list[str] = Field(
        description="List of search queries"
    )


class EndResearch(BaseModel):
    should_end: bool = Field(description="End the research")


class QueryTool(BaseModel):
    selected_tool: str
    

class ChosenSections(BaseModel):
    chosen_sections: list[int] = Field(description="List of sections are used to answer the user question")