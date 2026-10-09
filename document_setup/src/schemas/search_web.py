from pydantic import BaseModel, Field


class ResearchPlanStep(BaseModel):
    step: int = Field(None, description="Step order")
    description: str = Field(None, description="Describe what the current step does")
    search_queries: list[str] = Field(None, description="List of query to search web to do deep research")


class ResearchPlan(BaseModel):
    research_plan: list[ResearchPlanStep] = Field(None, description="Step to do deep research for original query")