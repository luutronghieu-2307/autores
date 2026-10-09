from typing import Dict, Any, List, Optional, Annotated
from pydantic import BaseModel, Field
from enum import Enum

# Reducer Functions
def append_list(left: List, right: List) -> List:
    """Append right list to left list."""
    return left + right

def unique_list(left: List, right: List) -> List:
    """Return a list with unique items, preserving order."""
    seen = set(left)
    result = left.copy()
    for item in right:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result

# State Schema Components
class DataType(str, Enum):
    TIME_SERIES = "time_series"
    CROSS_SECTIONAL = "cross_sectional"
    CATEGORICAL = "categorical"
    PANEL = "panel"
    SPATIAL = "spatial"
    EVENT = "event"
    LIKERT = "likert"
    HYBRID = "hybrid"
    MIXED = "mixed"

class ResearchPurposeType(str, Enum):
    FORECASTING = "forecasting"
    CAUSAL_INFERENCE = "causal_inference"
    DESCRIPTIVE = "descriptive"
    EXPLORATORY = "exploratory"
    COMPARATIVE = "comparative"
    PREDICTIVE = "predictive"
    ANOMALY_DETECTION = "anomaly_detection"
    SPATIAL_ANALYSIS = "spatial_analysis"
    SURVIVAL_ANALYSIS = "survival_analysis"
    PANEL_ANALYSIS = "panel_analysis"
    STRUCTURAL_EQUATION = "structural_equation_modeling"
    MULTI_METHOD = "multi_method"

class VariableRole(str, Enum):
    DEPENDENT = "dependent"
    INDEPENDENT = "independent"
    CONTROL = "control"
    MODERATOR = "moderator"
    MEDIATOR = "mediator"
    CONFOUNDER = "confounder"

class VariableFeature(str, Enum):
    TIME_STAMPED = "time_stamped"
    SEASONAL = "seasonal"
    LIKERT = "likert"
    PANEL = "panel"
    TREATMENT = "treatment"
    CONTROL_GROUP = "control_group"
    SPATIAL = "spatial"
    CENSORED = "censored"
    MULTIDIMENSIONAL = "multidimensional"
    DEMOGRAPHIC = "demographic"

class Query(BaseModel):
    section_ids: Optional[List[str]] = Field(default_factory=list)
    method: Optional[str] = None
    keywords: Optional[List[str]] = Field(default_factory=list)

class ResearchPurpose(BaseModel):
    type: str
    description: str

class MethodSuggestion(BaseModel):
    name: str
    justification: str

class Variable(BaseModel):
    name: str
    code: str
    variable_type: str
    role: str
    parent_code: Optional[str] = None
    statement: Optional[str] = None
    values: Optional[str] = None
    scale: str
    unit: Optional[str] = None
    collection_method: str

class Variables(BaseModel):
    variables: Annotated[list[Variable], append_list]

class Subsection(BaseModel):
    id: str
    title: str

class Doc(BaseModel):
    id: str
    title: str
    keywords: List[str] = Field(default_factory=list)
    content: str
    variable_content: Optional[str] = None
    subsections: List[Subsection] = Field(default_factory=list)

class InitialAnalysis(BaseModel):
    research_purposes: Annotated[list[ResearchPurpose], append_list]
    high_level_elements: Annotated[list[str], unique_list]
    recommended_methods: Annotated[list[MethodSuggestion], append_list]

class FinalReport(BaseModel):
    content: str


class Mermaid(BaseModel):
    mermaid_code: str


class Source(BaseModel):
    source_index: int = Field(description="The index of the chosen paper")