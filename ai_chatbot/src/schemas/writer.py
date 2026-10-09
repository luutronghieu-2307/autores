from pydantic import BaseModel, Field
from typing import Literal, Optional


# Categories
class UserCategory(BaseModel):
    user_category: int = Field(description="User's category based on user's query, from 1 to 4")


class UserSubcategory(BaseModel):
    user_subcategory: int = Field(description="User's subcategory based on user's query, from 1 and 2")


# Intent
class Intent(BaseModel):
    change_intent: bool = Field(description="Does the user want to change intent?")
    new_intent: int = Field(description="User's intent, from 0 to 3 (0 for unchanged intent)")
    message_type: Literal["field_answer", "new_topic", "off_topic"] = Field(
        default="field_answer",
        description="Classify the latest user message while collecting report information.",
    )


class IntentStatus(BaseModel):
    intent_status: bool


# Write report
class WriteReport(BaseModel):
    """
    A data model to hold all the necessary information for writing a research report.
    The description of each field is the question the chatbot should ask to get the information.
    """
    research_topic: str = Field(
        description="What is the topic that you want to write about?"
    )
    main_keywords: list[str] = Field(
        description="What are the main keywords in your research topic?",
    )
    supplement_keywords: Optional[list[str]] = Field(
        default=None,
        description="What are the supplemental or related keywords for your research topic?"
    )
    research_questions: list[str] = Field(
        description="What are the specific questions you are trying to answer in this report?",
    )
    research_type: str = Field(
        description="What is your research type? (e.g., Quantitative, Qualitative, Mix of Quantitative and Qualitative)"
    )
    scope: str = Field(
        description="What is the scope of your research? (e.g., A particular application? A specific location? A specific outcome to measure?)"
    )
    word_count: Optional[int] = Field(
        default=None,
        description="How long do you want the report to be (in words)?",
    )
    references_style: str = Field(
        description="What reference style do you need to use?"
    )


class Outline(BaseModel):
    outline: list[str]


class SummaryStatus(BaseModel):
    summary_status: bool


class SummaryAction(BaseModel):
    action: Literal["approve_plan", "write_section", "revise_plan", "change_template"] = Field(
        description="Next action after the report plan: approve_plan when the user approves, write_section when the user requests a section, revise_plan when the user changes research information, and change_template when the user changes the requested output template."
    )
    template_key: str = Field(
        default="",
        description="The exact template identifier supplied by the user or caller when changing templates. Do not invent one; leave empty when unchanged or not supplied."
    )


class OutlineWriteReport(BaseModel):
    outline_status: bool


# Undefined case
class Status(BaseModel):
    status: bool


# Write section
class WriteSection(BaseModel):
    research_topic: str = Field(
        description="What is the topic that your report is about?"
    )
    research_questions: list[str] = Field(
        description="What are the specific questions you are trying to answer in this report?",
    )
    scope: str = Field(
        description="What is the scope of your research? (e.g., A particular application? A specific location? A specific outcome to measure?)"
    )
    word_count: Optional[int] = Field(
        default=None,
        description="How long do you want the report to be (in words)?",
    )
    user_request: str = Field(
        default="",
        description="What is the specific section the user wants to write?"
    )


# Update section
class UpdateSection(BaseModel):
    original_content: str = Field(
        default="",
        description="The targeted content"
    )
    revision_goal: str = Field(
        default="",
        description="How the user want to update the targeted content"
    )


# Report
class Report(BaseModel):
    report: str


class UserInfo(BaseModel):
    field: str
    domain: str
