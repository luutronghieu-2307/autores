from pydantic import BaseModel, Field
from typing import Literal, Type


class Domains(BaseModel):
    domains: list[str] = Field(None, description="List of hot domains")


class SubDomains(BaseModel):
    subdomains: list[str] = Field(None, description="List of hot subdomains")


class Keywords(BaseModel):
    main_keywords: list[str]
    supplementary_keywords: list[str]


class Idea(BaseModel):
    thinking: str = Field(None, description="LLM thinking process")
    idea: str = Field(None, description="LLM generated idea")
    rationale: str = Field(None, description="How did LLM come to conclusion")


class IdeaV2(BaseModel):
    thinking: str = Field(None, description="LLM thinking process")
    idea: str = Field(None, description="LLM generated idea")
    rationale: str = Field(None, description="How did LLM come to conclusion")
    web_search_result: str = Field(None, description="Systhesize web_search result")


class Ideas(BaseModel):
    ideas: list[IdeaV2]


class FinalProposal(BaseModel):
    title: str
    problem_statement: str
    motivation: str


class FinalProposalWithWebSearch(BaseModel):
    title: str
    problem_statement: str
    motivation: str
    web_search: str


class FinalProposalEval(BaseModel):
    evaluation: str = Field(None, description="Strength and weakness of the proposal based on the corresponding criteria")


class CriteriaUndergrad(BaseModel):
    clear_and_simple: str = Field(
        description='Is it easy to understand, with a clear focus (e.g., "The impact of A on B")?'
    )
    narrow_in_scope: str = Field(
        description="Is it focused on a single organization, local area, or well-defined group?"
    )
    feasible: str = Field(
        description="Can it be researched using accessible data such as surveys, public reports, or a single case study?"
    )
    grounded_in_practice: str = Field(
        description='Does it aim to describe or evaluate a straightforward, observable issue (e.g., "Student satisfaction with university services")?'
    )


class CriteriaMaster(BaseModel):
    highly_practical: str = Field(
        description="Does it address a specific, real-world problem for a particular industry, organization, or locality?"
    )
    clear_novelty: str = Field(
        description="Does it apply an existing theory to a new context or explore a relationship not extensively studied?"
    )
    clear_research_model: str = Field(
        description='Does it clearly show relationships between variables (e.g., "Factors affecting employee retention in the fintech sector")?'
    )
    methodologically_sound: str = Field(
        description="Is it suitable for established methods allowing for robust data analysis?"
    )


class CriteriaPhD(BaseModel):
    high_originality: str = Field(
        description="Does it address a significant and clearly stated research gap, aiming to extend or challenge existing knowledge?"
    )
    major_contribution: str = Field(
        description="Does it promise a major theoretical or practical contribution?"
    )
    global_relevance_and_scope: str = Field(
        description='Is it globally relevant or advanced in scope (comparative, interdisciplinary, or longitudinal)?'
    )
    methodological_rigor: str = Field(
        description="Does it use advanced analytical methods (SEM, ML, meta-analysis) and is it feasible in data collection and measurement?"
    )


CRITERIA_MAP: dict[str, Type[BaseModel]] = {
    'CHUYEN_DE': CriteriaPhD,
    'LUAN_AN_TIEN_SI': CriteriaPhD,
    'BAI_BAO_KHOA_HOC': CriteriaPhD,
    'LUAN_VAN_THAC_SI': CriteriaMaster,
    'KHOA_LUAN': CriteriaUndergrad,
    'TIEU_LUAN': CriteriaUndergrad,
}


class FinalProposals(BaseModel):
    final_proposals: list[FinalProposal]


class ResearchGap(BaseModel):
    research_gap: str
    description: str


class ResearchGaps(BaseModel):
    research_gaps: list[ResearchGap]


class UserInfo(BaseModel):
    field: str
    domain: str
    subdomains: list[str]


class ResearchType(BaseModel):
    type: int = Field(None, description="0 for Qualitative research, 1 for Quantitative research, 2 for Mix of both")
    reason: str = Field(None, description="Explaination of why choose the corresponding research")


class Title(BaseModel):
    title: str


class Phrases(BaseModel):
    phrases: list[str] = Field(None, description="List of meaningful non-overlapping nouns and noun phrases")


class KeywordType(BaseModel):
    keyword_type: Literal["main_keywords", "supplementary_keywords", "gibberish"] = Field(None, description="Keyword's category")