import os
import asyncio
from typing_extensions import Annotated
import operator
from typing import TypedDict

from langgraph.graph import StateGraph, START, END
import logging
from langgraph.types import interrupt, Checkpointer, Command

from get_llm_response import get_answer, get_answer_with_schema, get_llm

from ai_chatbot.src.modules.writer_prompt import (
    CATEGORIES_2,
    WRITE_REPORT_INFO, 
    CLARIFY_REPORT,
    UPDATE_SECTION_INFO,
    OUTLINE_GENERATION,
    OUTLINE_CONFIRMATION,
    CONFIRMATION,
    WRITE_SECTION_INFO,
    SUMMARY_NOTE_REPORT,
    CLARIFY_SECTION_INFO,
    CONFIRM_SECTION_PLAN,
    CONFIRM_UPDATE_PLAN,
    CLARIFY_UPDATE_INFO,
    UNDEFINED_CATE_2,
)
from ai_chatbot.src.modules.utils import (
    _get_summary, 
    _get_summary_status, 
    _get_summary_action,
    _is_ask_clarify, 
    _get_clarify_question, 
    _is_ask_intent,
    _get_clarify_intent_question,
    _get_intent_status,
    _check_intent,
    reset_or_add,
    DataHelper
)
from ai_chatbot.src.schemas.writer import (
    UserCategory, 
    Intent,
    SummaryAction,
    Status, 
    WriteReport, 
    WriteSection, 
    UpdateSection, 
    OutlineWriteReport,
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)


class State(TypedDict):
    _id: str
    conv_id: str
    user_id: str
    user_query: str
    language: str
    model_id: str
    llm_key: str
    summary: str
    category: int
    short_answer: bool
    subcategory: int
    chat_history: Annotated[str, operator.add]
    current_question_key: str
    status: bool
    intent: Intent
    intent_status: bool
    summary_status: bool
    max_tokens: int
    outline_status: bool
    question: str
    outline: str
    outline_history: Annotated[str, operator.add]
    subcategory: int
    dependencies: WriteReport | WriteSection | UpdateSection
    input_tokens: Annotated[int, reset_or_add]
    output_tokens: Annotated[int, reset_or_add]
    final_report: str
    summary_action: SummaryAction
    template_key: str


async def init_user_history(state: State):
    return {
        "chat_history": f"- User\n:{state['user_query']}\n",
        "_id": state["conv_id"][:8],
    }


async def classify_user_category(state: State):
    llm = get_llm(state["model_id"], state["llm_key"], state["max_tokens"])
    input_context, context_input_tokens, context_output_tokens = await DataHelper(
        state["user_id"], 
        state["model_id"], 
        state["llm_key"], 
        state["conv_id"], 
        state["max_tokens"]
    ).load_file_content()
    error, success, category, input_tokens, output_tokens = await get_answer_with_schema(
        state["_id"], 
        llm, 
        CATEGORIES_2, 
        state["chat_history"] + input_context, 
        UserCategory
    )
    if not success:
        if error.status_code in [401, 403, 429, 500]:
            raise error
        category = UserCategory(user_category=4)
    logger.info(f"[{state["_id"]}] User's category: {category.user_category}")
    return {
        "category": category.user_category,
        "input_tokens": input_tokens + context_input_tokens,
        "output_tokens": output_tokens + context_output_tokens,
        "dependencies": {},
        "outline_history": "",
        "intent_status": False,
    }


def is_categorized(state: State) -> bool:
    return state["category"] < 4


async def undefined_cate(state: State):
    logger.info(f"[{state["_id"]}] undefined_cate")
    llm = get_llm(state["model_id"], state["llm_key"], state["max_tokens"])
    short_answer_prompt = "\nKeep the generated content clear and concise." if state["short_answer"] else ""
    input_context, context_input_tokens, context_output_tokens = await DataHelper(
        state["user_id"], 
        state["model_id"], 
        state["llm_key"], 
        state["conv_id"], 
        state["max_tokens"]
    ).load_file_content()
    error, success, question, input_tokens, output_tokens = await get_answer(
        state["_id"],
        llm, 
        UNDEFINED_CATE_2 + "\n" + state["chat_history"] + input_context + short_answer_prompt
    )
    if not success:
        raise error
    return {
        "question": question,
        "chat_history": f"- Assistant:\n{question}\n",
        "input_tokens": input_tokens + context_input_tokens,
        "output_tokens": output_tokens + context_output_tokens,
    }


async def get_response_undefined_cate(state: State):
    logger.info(f"[{state["_id"]}] get_response_undefined_cate")
    answer = interrupt(state["question"])
    llm = get_llm(answer["model_id"], answer["llm_key"], state["max_tokens"])
    input_context, context_input_tokens, context_output_tokens = await DataHelper(
        state["user_id"], 
        state["model_id"], 
        state["llm_key"], 
        state["conv_id"], 
        state["max_tokens"]
    ).load_file_content()
    content = f"Chat history:\n{state["chat_history"]}\n- User:\n{answer["question"]}\n"
    error, success, status, input_tokens, output_tokens = await get_answer_with_schema(state["_id"], llm, CONFIRMATION, content + input_context, Status)
    if success:
        return {
            "chat_history": f"- User:\n{answer["question"]}\n",
            "model_id": answer["model_id"],
            "llm_key": answer["llm_key"],
            "status": status.status,
            "input_tokens": f"RESET_{input_tokens + context_input_tokens}",
            "output_tokens": f"RESET_{output_tokens + context_output_tokens}",
        }
    else:
        raise error


def is_end_undefined_cate(state: State):
    logger.info(f"[{state["_id"]}] is_end_undefined_cate")
    return state["status"] and "summary" in state


def route_category(state: State) -> str:
    logger.info(f"[{state["_id"]}] route_category")
    if state["category"] == 1:
        return "write_report" 
    elif state["category"] == 2:
        return "write_section"
    elif state["category"] == 3:
        return "update_section"
    else:
        return "undefined_cate"


async def update_dependencies_write_report(state: State):
    logger.info(f"[{state["_id"]}] update_dependencies_write_report")
    llm = get_llm(state["model_id"], state["llm_key"], state["max_tokens"])
    input_context, context_input_tokens, context_output_tokens = await DataHelper(
        state["user_id"], 
        state["model_id"], 
        state["llm_key"], 
        state["conv_id"], 
        state["max_tokens"]
    ).load_file_content()
    existing_note = f"Existing note:\n{state['dependencies']}" if state.get("dependencies") else ""
    topic_reset = "The latest user message starts a new research topic. Ignore the previous topic and rebuild the note from the latest topic." if state.get("intent") and state["intent"].message_type == "new_topic" else ""
    content = f"""Chat history:
    {state["chat_history"]}
    {existing_note}
    {topic_reset}
    """
    error, success, write_report, input_tokens, output_tokens = await get_answer_with_schema(
        state["_id"], 
        llm, 
        WRITE_REPORT_INFO, 
        content + input_context, 
        WriteReport
    )
    if success:
        return {
            "dependencies": write_report,
            "input_tokens": input_tokens + context_input_tokens,
            "output_tokens": output_tokens + context_output_tokens,
        }
    else:
        raise error


def is_ask_clarify_question_write_report(state: State):
    logger.info(f"[{state["_id"]}] is_ask_clarify_question_write_report")
    return _is_ask_clarify(state)


async def generate_clarify_question_write_report(state: State):
    logger.info(f"[{state["_id"]}] generate_clarify_question_write_report")
    logger.info(state["dependencies"])
    remaining_keys: list[str] = []
    for key, value in state["dependencies"].model_dump().items():
        if isinstance(value, list) or isinstance(value, str):
            if len(value):
                continue
        elif isinstance(value, int):
            # For word_count, treat 0 and None as unfilled (0 is not meaningful)
            if key == "word_count":
                if value is not None and value > 0:
                    continue
        else:
            if value:
                continue
        remaining_keys.append(key)
    input_context, context_input_tokens, context_output_tokens = await DataHelper(
        state["user_id"], 
        state["model_id"], 
        state["llm_key"], 
        state["conv_id"], 
        state["max_tokens"]
    ).load_file_content()
    error, success, question, input_tokens, output_tokens = await _get_clarify_question(
        state,
        remaining_keys,
        CLARIFY_REPORT,
        input_context,
        include_summary=False,
    )
    if not success:
        raise error
    return {
        "question": question,
        "chat_history": f"- Assistant:\n{question}\n",
        "input_tokens": input_tokens + context_input_tokens,
        "output_tokens": output_tokens + context_output_tokens,
    }


async def ask_clarify_question_write_report(state: State):
    logger.info(f"[{state["_id"]}] ask_clarify_question_write_report")
    answer = interrupt(state["question"])
    intent, input_tokens, output_tokens = await _check_intent(state, answer)
    update = {
        "chat_history": f"- User:\n{answer["question"]}\n",
        "input_tokens": f"RESET_{input_tokens}",
        "output_tokens": f"RESET_{output_tokens}",
        "model_id": answer["model_id"],
        "llm_key": answer["llm_key"],
        "intent": intent
    }
    if intent.message_type == "new_topic":
        update["dependencies"] = {}
    elif intent.message_type == "off_topic":
        llm = get_llm(answer["model_id"], answer["llm_key"], state["max_tokens"])
        reply_prompt = f"""You are a helpful chat assistant. Reply naturally to the user's latest message in {state["language"]}.
Do not ask for the missing report information in this reply. Answer the user's message briefly,
then invite them to continue providing the requested report details when ready.

User message:
{answer["question"]}
"""
        error, success, reply, reply_input_tokens, reply_output_tokens = await get_answer(
            state["_id"], llm, reply_prompt
        )
        if not success:
            raise error
        update.update({
            "question": reply,
            "chat_history": f"- User:\n{answer["question"]}\n- Assistant:\n{reply}\n",
            "input_tokens": f"RESET_{input_tokens + reply_input_tokens}",
            "output_tokens": f"RESET_{output_tokens + reply_output_tokens}",
        })
    return update


async def resume_after_off_topic_write_report(state: State):
    answer = interrupt(state["question"])
    return {
        "chat_history": f"- User:\n{answer["question"]}\n",
        "model_id": answer["model_id"],
        "llm_key": answer["llm_key"],
    }


def route_after_clarify_write_report(state: State):
    if _is_ask_intent(state):
        return "generate_check_intent_question_write_report"
    if state["intent"].message_type == "off_topic":
        return "resume_after_off_topic_write_report"
    return "update_dependencies_write_report"


async def generate_check_intent_question_write_report(state: State):
    logger.info(f"[{state["_id"]}] generate_check_intent_question_write_report")

    _, _, question, input_tokens, output_tokens = await _get_clarify_intent_question(state)
    return {
        "question": question,
        "chat_history": f"- Assistant:\n{question}\n",
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }


async def ask_clarify_intent_write_report(state: State):
    logger.info(f"[{state["_id"]}] ask_clarify_intent_write_report")

    answer = interrupt(state["question"])
    error, success, intent_status, input_tokens, output_tokens = await _get_intent_status(state, answer)
    if success:
        update = {
            "intent_status": intent_status.intent_status,
            "chat_history": f"- User:\n{answer['question']}\n",
            "model_id": answer["model_id"],
            "llm_key": answer["llm_key"],
            "input_tokens": f"RESET_{input_tokens}",
            "output_tokens": f"RESET_{output_tokens}",
        }
        if intent_status.intent_status:
            update.update({
                "category": state["intent"].new_intent,
                "dependencies": {},
            })
        return update
    else:
        raise error


def route_after_intent_change_write_report(state: State):
    if not state["intent_status"]:
        return "update_dependencies_write_report"
    return {
        1: "update_dependencies_write_report",
        2: "update_dependencies_write_section",
        3: "update_dependencies_update_section",
    }.get(state["category"], "update_dependencies_write_report")


async def generate_summary_report(state: State):
    logger.info(f"[{state["_id"]}] generate_summary_report")

    input_context, context_input_tokens, context_output_tokens = await DataHelper(
        state["user_id"], 
        state["model_id"], 
        state["llm_key"], 
        state["conv_id"], 
        state["max_tokens"]
    ).load_file_content()
    summary, input_tokens, output_tokens = await _get_summary(state, SUMMARY_NOTE_REPORT, input_context)
    return {
        "summary": summary,
        "chat_history": f"- Assistant:\n{summary}\n",
        "input_tokens": input_tokens + context_input_tokens,
        "output_tokens": output_tokens + context_output_tokens,
    }
    

async def get_summary_status_report(state: State):
    logger.info(f"[{state["_id"]}] get_summary_status_report")
    answer = interrupt(state["summary"])
    error, success, action, input_tokens, output_tokens = await _get_summary_action(state, answer)
    if not success:
        raise error
    return {
        "chat_history": f"- User:\n{answer["question"]}\n",
        "input_tokens": f"RESET_{input_tokens}",
        "output_tokens": f"RESET_{output_tokens}",
        "model_id": answer["model_id"],
        "llm_key": answer["llm_key"],
        "summary_action": action,
        "template_key": action.template_key or state.get("template_key", ""),
    }


def route_after_summary_action(state: State) -> str:
    return {
        "approve_plan": "get_outline",
        "write_section": "update_dependencies_write_section",
        "revise_plan": "update_dependencies_write_report",
        "change_template": "generate_summary_report",
    }[state["summary_action"].action]


def is_ask_intent_summary_write_report(state: State):
    logger.info(f"[{state["_id"]}] is_ask_intent_summary_write_report")
    return _is_ask_intent(state)


async def generate_check_intent_question_summary_write_report(state: State):
    logger.info(f"[{state["_id"]}] generate_check_intent_question_summary_write_report")

    _, _, question, input_tokens, output_tokens = await _get_clarify_intent_question(state)
    return {
        "question": question,
        "chat_history": f"- Assistant:\n{question}\n",
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }


async def ask_clarify_intent_summary_write_report(state: State):
    logger.info(f"[{state["_id"]}] ask_clarify_intent_summary_write_report")

    answer = interrupt(state["question"])
    error, success, intent_status, input_tokens, output_tokens = await _get_intent_status(state, answer)
    if success:
        return {
            "intent_status": intent_status.intent_status,
            "chat_history": f"- User:\n{answer["question"]}\n",
            "model_id": answer["model_id"],
            "llm_key": answer["llm_key"],
            "input_tokens": f"RESET_{input_tokens}",
            "output_tokens": f"RESET_{output_tokens}",
        }
    else:
        raise error


def reset_summary_write_report(state: State):
    logger.info(f"[{state["_id"]}] reset_summary_write_report")
    return state["intent_status"]


async def check_summary_status_report(state: State):
    logger.info(f"[{state["_id"]}] check_summary_status_report")

    error, success, summary_status, input_tokens, output_tokens = await _get_summary_status(state, state["chat_history"].split("- User:\n")[-1])
    if success:
        return {
            "summary_status": summary_status.summary_status,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }
    else:
        raise error


def is_get_outline(state: State): 
    logger.info(f"[{state["_id"]}] is_get_outline")
    return state["summary_status"]


async def get_outline(state: State):
    logger.info(f"[{state["_id"]}] get_outline")

    llm = get_llm(state["model_id"], state["llm_key"], state["max_tokens"])
    short_answer_prompt = "\nKeep the generated content clear and concise." if state["short_answer"] else ""
    input_context, context_input_tokens, context_output_tokens = await DataHelper(
        state["user_id"], 
        state["model_id"], 
        state["llm_key"], 
        state["conv_id"], 
        state["max_tokens"]
    ).load_file_content()
    outline_history = f"\nOutline's history:\n{state.get('outline_history', '')}\n" if state.get("outline_history") else ""
    # word_count should always be provided now (users are explicitly asked)
    word_count = getattr(state["dependencies"], "word_count", 2000)
    if not isinstance(word_count, int) or word_count <= 0:
        word_count = 2000
        
    total_subheading = max(5, int(word_count / 2000))
        
    content = f"""Research's note:
    {state["summary"]}{outline_history}
    Template key:
    {state.get("template_key", "")}
    If a template key is present, keep its structure and chapter requirements.
    Generate a total of approximately {total_subheading} headings and subheadings.
    Generate the full updated outline in {state["language"]}{short_answer_prompt}. 
    Important: You must always output the entire outline from start to finish. 
    Do not just show the modified sections; provide the complete revised structure so the user can see the full context."""
    error, success, outline, input_tokens, output_tokens = await get_answer(state["_id"], llm, OUTLINE_GENERATION + "\n" + content + input_context)
    if not success:
        raise error
    return {
        "outline": outline,
        "outline_history": f"- Assistant:\n{outline}\n",
        "input_tokens": input_tokens + context_input_tokens,
        "output_tokens": output_tokens + context_output_tokens,
    }


async def get_outline_status(state: State):
    logger.info(f"[{state["_id"]}] get_outline_status")

    answer = interrupt(state["outline"])
    intent, input_tokens, output_tokens = await _check_intent(state, answer)
    return {
        "outline_history": f"- User:\n{answer['question']}\n",
        "chat_history": f"- User:\n{answer['question']}\n",
        "input_tokens": f"RESET_{input_tokens}",
        "output_tokens": f"RESET_{output_tokens}",
        "model_id": answer["model_id"],
        "llm_key": answer["llm_key"],
        "intent": intent
    }


def is_ask_intent_outline_write_report(state: State):
    logger.info(f"[{state["_id"]}] is_ask_intent_outline_write_report")

    return _is_ask_intent(state)


async def generate_check_intent_question_outline_write_report(state: State):
    logger.info(f"[{state["_id"]}] generate_check_intent_question_outline_write_report")

    _, _, question, input_tokens, output_tokens = await _get_clarify_intent_question(state)
    return {
        "question": question,
        "chat_history": f"- Assistant:\n{question}\n",
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }


async def ask_clarify_intent_outline_write_report(state: State):
    logger.info(f"[{state["_id"]}] ask_clarify_intent_outline_write_report")

    answer = interrupt(state["question"])
    error, success, intent_status, input_tokens, output_tokens = await _get_intent_status(state, answer)
    if success:
        return {
            "intent_status": intent_status.intent_status,
            "chat_history": f"- User:\n{answer['question']}\n",
            "model_id": answer["model_id"],
            "llm_key": answer["llm_key"],
            "input_tokens": f"RESET_{input_tokens}",
            "output_tokens": f"RESET_{output_tokens}",
        }
    else:
        raise error


def reset_outline_write_report(state: State):
    logger.info(f"[{state["_id"]}] reset_outline_write_report")

    return state["intent_status"]


async def check_outline_status(state: State):
    logger.info(f"[{state["_id"]}] check_outline_status")

    llm = get_llm(state["model_id"], state["llm_key"], state["max_tokens"])
    content = f"""Chat history:
    {state["outline_history"]}
    User's answer:
    {state["chat_history"].split("- User:\n")[-1]}
    """
    error, success, outline_status, input_tokens, output_tokens = await get_answer_with_schema(state["_id"], llm, OUTLINE_CONFIRMATION, content, OutlineWriteReport)
    if success:
        return {
            "outline_status": outline_status.outline_status,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }
    else:
        raise error


def is_end_write_report(state: State):
    logger.info(f"[{state["_id"]}] is_end_write_report")

    return state["outline_status"]


async def update_dependencies_write_section(state: State):
    logger.info(f"[{state["_id"]}] update_dependencies_write_section")

    llm = get_llm(state["model_id"], state["llm_key"], state["max_tokens"])
    input_context, context_input_tokens, context_output_tokens = await DataHelper(
        state["user_id"], 
        state["model_id"], 
        state["llm_key"], 
        state["conv_id"], 
        state["max_tokens"]
    ).load_file_content()
    existing_note = f"Existing note:\n{state["dependencies"]}" if "dependencies" in state or not len(state["dependencies"]) else ""
    content = f"""Chat history:
    {state["chat_history"]}
    {existing_note}
    """
    error, success, write_section, input_tokens, output_tokens = await get_answer_with_schema(
        state["_id"], 
        llm, 
        WRITE_SECTION_INFO, 
        content + input_context, 
        WriteSection
    )
    if success:
        return {
            "dependencies": write_section,
            "input_tokens": input_tokens + context_input_tokens,
            "output_tokens": output_tokens + context_output_tokens,
        }
    else:
        raise error


def is_ask_clarify_question_write_section(state: State):
    logger.info(f"[{state["_id"]}] is_ask_clarify_question_write_section")

    return _is_ask_clarify(state)


async def generate_clarify_question_write_section(state: State):
    logger.info(f"[{state["_id"]}] generate_clarify_question_write_section")

    remaining_keys: list[str] = []
    for key, value in state["dependencies"].model_dump().items():
        if isinstance(value, list) or isinstance(value, str):
            if len(value):
                continue
        elif isinstance(value, int):
            # For word_count, treat 0 and None as unfilled (0 is not meaningful)
            if key == "word_count":
                if value is not None and value > 0:
                    continue
            # For other integers, only None means "not filled" (0 is valid)
            elif value is not None:
                continue
        else:
            if value:
                continue
        remaining_keys.append(key)
    input_context, context_input_tokens, context_output_tokens = await DataHelper(
        state["user_id"], 
        state["model_id"], 
        state["llm_key"], 
        state["conv_id"], 
        state["max_tokens"]
    ).load_file_content()
    error, success, question, input_tokens, output_tokens = await _get_clarify_question(state, remaining_keys, CLARIFY_SECTION_INFO, input_context)
    if not success:
        raise error
    return {
        "question": question,
        "chat_history": f"- Assistant:\n{question}\n",
        "input_tokens": input_tokens + context_input_tokens,
        "output_tokens": output_tokens + context_output_tokens,
    }


async def ask_clarify_question_write_section(state: State):
    logger.info(f"[{state["_id"]}] ask_clarify_question_write_section")

    answer = interrupt(state["question"])
    intent, input_tokens, output_tokens = await _check_intent(state, answer)
    return {
        "chat_history": f"- User:\n{answer['question']}\n",
        "input_tokens": f"RESET_{input_tokens}",
        "output_tokens": f"RESET_{output_tokens}",
        "model_id": answer["model_id"],
        "llm_key": answer["llm_key"],
        "intent": intent
    }


def is_ask_intent_write_section(state: State):
    logger.info(f"[{state["_id"]}] is_ask_intent_write_section")

    return _is_ask_intent(state)


async def generate_check_intent_question_write_section(state: State):
    logger.info(f"[{state["_id"]}] generate_check_intent_question_write_section")

    _, _, question, input_tokens, output_tokens = await _get_clarify_intent_question(state)
    return {
        "question": question,
        "chat_history": f"- Assistant:\n{question}\n",
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }


async def ask_clarify_intent_write_section(state: State):
    logger.info(f"[{state["_id"]}] ask_clarify_intent_write_section")

    answer = interrupt(state["question"])
    error, success, intent_status, input_tokens, output_tokens = await _get_intent_status(state, answer)
    if success:
        return {
            "intent_status": intent_status.intent_status,
            "chat_history": f"- User:\n{answer['question']}\n",
            "model_id": answer["model_id"],
            "llm_key": answer["llm_key"],
            "input_tokens": f"RESET_{input_tokens}",
            "output_tokens": f"RESET_{output_tokens}",
        }
    else:
        raise error


def reset_write_section(state: State):
    logger.info(f"[{state["_id"]}] reset_write_section")

    return state["intent_status"]


async def generate_summary_section(state: State):
    logger.info(f"[{state["_id"]}] generate_summary_section")

    input_context, context_input_tokens, context_output_tokens = await DataHelper(
        state["user_id"], 
        state["model_id"], 
        state["llm_key"], 
        state["conv_id"], 
        state["max_tokens"]
    ).load_file_content()
    summary, input_tokens, output_tokens = await _get_summary(state, CONFIRM_SECTION_PLAN, input_context)
    return {
        "summary": summary,
        "chat_history": f"- Assistant:\n{summary}\n",
        "input_tokens": input_tokens + context_input_tokens,
        "output_tokens": output_tokens + context_output_tokens,
    }
    

async def get_summary_status_section(state: State):
    logger.info(f"[{state["_id"]}] get_summary_status_section")

    answer = interrupt(state["summary"])
    intent, input_tokens, output_tokens = await _check_intent(state, answer)
    return {
        "chat_history": f"- User:\n{answer['question']}\n",
        "input_tokens": f"RESET_{input_tokens}",
        "output_tokens": f"RESET_{output_tokens}",
        "model_id": answer["model_id"],
        "llm_key": answer["llm_key"],
        "intent": intent
    }


async def generate_check_intent_question_summary_write_section(state: State):
    logger.info(f"[{state["_id"]}] generate_check_intent_question_summary_write_section")

    _, _, question, input_tokens, output_tokens = await _get_clarify_intent_question(state)
    return {
        "question": question,
        "chat_history": f"- Assistant:\n{question}\n",
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }


async def ask_clarify_intent_summary_write_section(state: State):
    logger.info(f"[{state["_id"]}] ask_clarify_intent_summary_write_section")

    answer = interrupt(state["question"])
    error, success, intent_status, input_tokens, output_tokens = await _get_intent_status(state, answer)
    if success:
        return {
            "intent_status": intent_status.intent_status,
            "chat_history": f"- User:\n{answer['question']}\n",
            "model_id": answer["model_id"],
            "llm_key": answer["llm_key"],
            "input_tokens": f"RESET_{input_tokens}",
            "output_tokens": f"RESET_{output_tokens}",
        }
    else:
        raise error


def reset_write_section_summary(state: State):
    logger.info(f"[{state["_id"]}] reset_write_section_summary")

    return state["intent_status"]


async def check_summary_status_section(state: State):
    logger.info(f"[{state["_id"]}] check_summary_status_section")

    error, success, summary_status, input_tokens, output_tokens = await _get_summary_status(state, state["chat_history"].split("- User:\n")[-1])
    if success:
        return {
            "summary_status": summary_status.summary_status,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }
    else:
        raise error


def is_end_write_section(state: State):
    logger.info(f"[{state["_id"]}] is_end_write_section")

    return state["summary_status"]


async def update_dependencies_update_section(state: State):
    logger.info(f"[{state["_id"]}] update_dependencies_update_section")

    """
    Parses the chat history to populate the UpdateSection model.
    This node's logic is unique and is not covered by the helpers.
    """
    llm = get_llm(state["model_id"], state["llm_key"], state["max_tokens"])
    input_context, context_input_tokens, context_output_tokens = await DataHelper(
        state["user_id"], 
        state["model_id"], 
        state["llm_key"], 
        state["conv_id"], 
        state["max_tokens"]
    ).load_file_content()
    existing_note = f"Existing note:\n{state["dependencies"]}" if "dependencies" in state or not len(state["dependencies"]) else ""
    content = f"""Chat history:
    {state["chat_history"]}
    {existing_note}
    """
    error, success, update_section, input_tokens, output_tokens = await get_answer_with_schema(
        state["_id"], 
        llm, 
        UPDATE_SECTION_INFO, 
        content + input_context, 
        UpdateSection
    )
    if success:
        return {
            "dependencies": update_section,
            "input_tokens": input_tokens + context_input_tokens,
            "output_tokens": output_tokens + context_output_tokens,
        }
    else:
        raise error


def is_ask_clarify_question_update_section(state: State):
    logger.info(f"[{state["_id"]}] is_ask_clarify_question_update_section")

    return _is_ask_clarify(state)


async def generate_clarify_question_update_section(state: State):
    logger.info(f"[{state["_id"]}] generate_clarify_question_update_section")
    remaining_keys: list[str] = []
    for key, value in state["dependencies"].model_dump().items():
        if isinstance(value, list) or isinstance(value, str):
            if len(value):
                continue
        elif isinstance(value, int):
            # For word_count, treat 0 and None as unfilled (0 is not meaningful)
            if key == "word_count":
                if value is not None and value > 0:
                    continue
            # For other integers, only None means "not filled" (0 is valid)
            elif value is not None:
                continue
        else:
            if value:
                continue
        remaining_keys.append(key)
    input_context, context_input_tokens, context_output_tokens = await DataHelper(
        state["user_id"], 
        state["model_id"], 
        state["llm_key"], 
        state["conv_id"], 
        state["max_tokens"]
    ).load_file_content()
    error, success, question, input_tokens, output_tokens = await _get_clarify_question(state, remaining_keys, CLARIFY_UPDATE_INFO, input_context)
    if not success:
        raise error
    return {
        "question": question,
        "chat_history": f"- Assistant:\n{question}\n",
        "input_tokens": input_tokens + context_input_tokens,
        "output_tokens": output_tokens + context_output_tokens,
    }


async def ask_clarify_question_update_section(state: State):
    logger.info(f"[{state["_id"]}] ask_clarify_question_update_section")

    answer = interrupt(state["question"])
    intent, input_tokens, output_tokens = await _check_intent(state, answer)
    return {
        "chat_history": f"- User:\n{answer['question']}\n",
        "input_tokens": f"RESET_{input_tokens}",
        "output_tokens": f"RESET_{output_tokens}",
        "model_id": answer["model_id"],
        "llm_key": answer["llm_key"],
        "intent": intent
    }


def is_ask_intent_update_section(state: State):
    logger.info(f"[{state["_id"]}] is_ask_intent_update_section")

    return _is_ask_intent(state)


async def generate_check_intent_question_update_section(state: State):
    logger.info(f"[{state["_id"]}] generate_check_intent_question_update_section")

    _, _, question, input_tokens, output_tokens = await _get_clarify_intent_question(state)
    return {
        "question": question,
        "chat_history": f"- Assistant:\n{question}\n",
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }


async def ask_clarify_intent_update_section(state: State):
    logger.info(f"[{state["_id"]}] ask_clarify_intent_update_section")

    answer = interrupt(state["question"])
    error, success, intent_status, input_tokens, output_tokens = await _get_intent_status(state, answer)
    if success:
        return {
            "intent_status": intent_status.intent_status,
            "chat_history": f"- User:\n{answer['question']}\n",
            "model_id": answer["model_id"],
            "llm_key": answer["llm_key"],
            "input_tokens": f"RESET_{input_tokens}",
            "output_tokens": f"RESET_{output_tokens}",
        }
    else:
        raise error


def reset_update_section(state: State):
    logger.info(f"[{state["_id"]}] reset_update_section")

    return state["intent_status"]


async def generate_summary_update(state: State):
    logger.info(f"[{state["_id"]}] generate_summary_update")

    input_context, context_input_tokens, context_output_tokens = await DataHelper(
        state["user_id"], 
        state["model_id"], 
        state["llm_key"], 
        state["conv_id"], 
        state["max_tokens"]
    ).load_file_content()
    summary, input_tokens, output_tokens = await _get_summary(state, CONFIRM_UPDATE_PLAN, input_context)
    
    return {
        "summary": summary,
        "chat_history": f"- Assistant:\n{summary}\n",
        "input_tokens": input_tokens + context_input_tokens,
        "output_tokens": output_tokens + context_output_tokens,
    }


async def get_summary_status_update(state: State):
    logger.info(f"[{state["_id"]}] get_summary_status_update")

    answer = interrupt(state["summary"])
    intent, input_tokens, output_tokens = await _check_intent(state, answer)
    return {
        "chat_history": f"- User:\n{answer['question']}\n",
        "input_tokens": f"RESET_{input_tokens}",
        "output_tokens": f"RESET_{output_tokens}",
        "model_id": answer["model_id"],
        "llm_key": answer["llm_key"],
        "intent": intent
    }


def is_ask_intent_summary_update(state: State):
    logger.info(f"[{state["_id"]}] is_ask_intent_summary_update")

    return _is_ask_intent(state)


async def generate_check_intent_question_summary_update(state: State):
    logger.info(f"[{state["_id"]}] generate_check_intent_question_summary_update")

    _, _, question, input_tokens, output_tokens = await _get_clarify_intent_question(state)
    return {
        "question": question,
        "chat_history": f"- Assistant:\n{question}\n",
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }


async def ask_clarify_intent_summary_update(state: State):
    logger.info(f"[{state["_id"]}] ask_clarify_intent_summary_update")

    answer = interrupt(state["question"])
    error, success, intent_status, input_tokens, output_tokens = await _get_intent_status(state, answer)
    if success:
        return {
            "intent_status": intent_status.intent_status,
            "chat_history": f"- User:\n{answer['question']}\n",
            "model_id": answer["model_id"],
            "llm_key": answer["llm_key"],
            "input_tokens": f"RESET_{input_tokens}",
            "output_tokens": f"RESET_{output_tokens}",
        }
    else:
        raise error


def reset_summary_update(state: State):
    logger.info(f"[{state["_id"]}] reset_summary_update")

    return state["intent_status"]


async def check_summary_status_update(state: State):
    logger.info(f"[{state["_id"]}] check_summary_status_update")

    error, success, summary_status, input_tokens, output_tokens = await _get_summary_status(state, state["chat_history"].split("- User:\n")[-1])
    if success:
        return {
            "summary_status": summary_status.summary_status,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }
    else:
        raise error


def is_end_update_section(state: State):
    logger.info(f"[{state["_id"]}] is_end_update_section")

    return state["summary_status"]


async def get_graph(checkpointer: Checkpointer):
    writer_builder = StateGraph(State)

    writer_builder.add_node("init_user_history", init_user_history)
    writer_builder.add_node("classify_user_category", classify_user_category)

    writer_builder.add_node("undefined_cate", undefined_cate)
    writer_builder.add_node("get_response_undefined_cate", get_response_undefined_cate)

    # writer_builder.add_node("classify_user_subcategory", classify_user_subcategory)
    
    writer_builder.add_node("update_dependencies_write_report", update_dependencies_write_report)
    writer_builder.add_node("generate_clarify_question_write_report", generate_clarify_question_write_report)
    writer_builder.add_node("ask_clarify_question_write_report", ask_clarify_question_write_report)
    writer_builder.add_node("resume_after_off_topic_write_report", resume_after_off_topic_write_report)
    writer_builder.add_node("generate_check_intent_question_write_report", generate_check_intent_question_write_report)
    writer_builder.add_node("ask_clarify_intent_write_report", ask_clarify_intent_write_report)
    writer_builder.add_node("generate_summary_report", generate_summary_report)
    writer_builder.add_node("get_summary_status_report", get_summary_status_report)
    writer_builder.add_node("generate_check_intent_question_summary_write_report", generate_check_intent_question_summary_write_report)
    writer_builder.add_node("ask_clarify_intent_summary_write_report", ask_clarify_intent_summary_write_report)
    writer_builder.add_node("check_summary_status_report", check_summary_status_report)
    writer_builder.add_node("get_outline", get_outline)
    writer_builder.add_node("get_outline_status", get_outline_status)
    writer_builder.add_node("generate_check_intent_question_outline_write_report", generate_check_intent_question_outline_write_report)
    writer_builder.add_node("ask_clarify_intent_outline_write_report", ask_clarify_intent_outline_write_report)
    writer_builder.add_node("check_outline_status", check_outline_status)

    writer_builder.add_node("update_dependencies_write_section", update_dependencies_write_section)
    writer_builder.add_node("generate_clarify_question_write_section", generate_clarify_question_write_section)
    writer_builder.add_node("ask_clarify_question_write_section", ask_clarify_question_write_section)
    writer_builder.add_node("generate_check_intent_question_write_section", generate_check_intent_question_write_section)
    writer_builder.add_node("ask_clarify_intent_write_section", ask_clarify_intent_write_section)
    writer_builder.add_node("generate_summary_section", generate_summary_section)
    writer_builder.add_node("get_summary_status_section", get_summary_status_section)
    writer_builder.add_node("generate_check_intent_question_summary_write_section", generate_check_intent_question_summary_write_section)
    writer_builder.add_node("ask_clarify_intent_summary_write_section", ask_clarify_intent_summary_write_section)
    writer_builder.add_node("check_summary_status_section", check_summary_status_section)

    writer_builder.add_node("update_dependencies_update_section", update_dependencies_update_section)
    writer_builder.add_node("ask_clarify_question_update_section", ask_clarify_question_update_section)
    writer_builder.add_node("generate_clarify_question_update_section", generate_clarify_question_update_section)
    writer_builder.add_node("generate_check_intent_question_update_section", generate_check_intent_question_update_section)
    writer_builder.add_node("ask_clarify_intent_update_section", ask_clarify_intent_update_section)
    writer_builder.add_node("generate_summary_update", generate_summary_update)
    writer_builder.add_node("get_summary_status_update", get_summary_status_update)
    writer_builder.add_node("generate_check_intent_question_summary_update", generate_check_intent_question_summary_update)
    writer_builder.add_node("ask_clarify_intent_summary_update", ask_clarify_intent_summary_update)
    writer_builder.add_node("check_summary_status_update", check_summary_status_update)

    writer_builder.add_edge(START, "init_user_history")
    writer_builder.add_edge("init_user_history", "classify_user_category")
    writer_builder.add_conditional_edges(
        "classify_user_category", route_category, {
            "write_report": "update_dependencies_write_report", 
            "write_section": "update_dependencies_write_section",
            "update_section": "update_dependencies_update_section",
            "undefined_cate": "undefined_cate",
        }
    )
    # Undefine
    writer_builder.add_edge("undefined_cate", "get_response_undefined_cate")
    writer_builder.add_conditional_edges(
        "get_response_undefined_cate", is_end_undefined_cate, {
            True: END, 
            False: "classify_user_category",
        }
    )

    # writer_builder.add_conditional_edges(
    #     "classify_user_subcategory", route_category, {
    #         "write_report": "update_dependencies_write_report", 
    #         "write_section": "update_dependencies_write_section",
    #         "update_section": "update_dependencies_update_section",
    #         }
    # )
    # Write report
    writer_builder.add_conditional_edges(
        "update_dependencies_write_report",
        is_ask_clarify_question_write_report,
        {
            True: "generate_clarify_question_write_report",
            False: "generate_summary_report",
        }
    )
    writer_builder.add_edge("generate_clarify_question_write_report", "ask_clarify_question_write_report")
    writer_builder.add_conditional_edges(
        "ask_clarify_question_write_report",
        route_after_clarify_write_report,
        {
            "generate_check_intent_question_write_report": "generate_check_intent_question_write_report",
            "resume_after_off_topic_write_report": "resume_after_off_topic_write_report",
            "update_dependencies_write_report": "update_dependencies_write_report",
        }
    )
    writer_builder.add_edge("resume_after_off_topic_write_report", "generate_clarify_question_write_report")
    writer_builder.add_edge("generate_check_intent_question_write_report", "ask_clarify_intent_write_report")
    writer_builder.add_conditional_edges(
        "ask_clarify_intent_write_report",
        route_after_intent_change_write_report,
        {
            "update_dependencies_write_report": "update_dependencies_write_report",
            "update_dependencies_write_section": "update_dependencies_write_section",
            "update_dependencies_update_section": "update_dependencies_update_section",
        }
    )

    writer_builder.add_edge("generate_summary_report", "get_summary_status_report")
    writer_builder.add_conditional_edges(
        "get_summary_status_report",
        route_after_summary_action,
        {
            "get_outline": "get_outline",
            "generate_summary_report": "generate_summary_report",
            "update_dependencies_write_section": "update_dependencies_write_section",
            "update_dependencies_write_report": "update_dependencies_write_report",
        }
    )
    writer_builder.add_conditional_edges(
        "check_summary_status_report",
        is_get_outline,
        {
            True: "get_outline",
            False: "update_dependencies_write_report",
        }
    )
    writer_builder.add_edge("get_outline", "get_outline_status")
    writer_builder.add_conditional_edges(
        "get_outline_status",
        is_ask_intent_outline_write_report,
        {
            True: "generate_check_intent_question_outline_write_report",
            False: "check_outline_status",
        }
    )
    writer_builder.add_edge("generate_check_intent_question_outline_write_report", "ask_clarify_intent_outline_write_report")
    writer_builder.add_conditional_edges(
        "ask_clarify_intent_outline_write_report",
        reset_outline_write_report,
        {
            True: "classify_user_category",
            False: "check_outline_status",
        }
    )
    writer_builder.add_conditional_edges(
        "check_outline_status",
        is_end_write_report,
        {
            True: END,
            False: "get_outline",
        }
    )
    # Write section
    writer_builder.add_conditional_edges(
        "update_dependencies_write_section",
        is_ask_clarify_question_write_section,
        {
            True: "generate_clarify_question_write_section",
            False: "generate_summary_section",
        }
    )
    writer_builder.add_edge("generate_clarify_question_write_section", "ask_clarify_question_write_section")
    writer_builder.add_conditional_edges(
        "ask_clarify_question_write_section",
        is_ask_intent_write_section,
        {
            True: "generate_check_intent_question_write_section",
            False: "update_dependencies_write_section",
        }
    )
    writer_builder.add_edge("generate_check_intent_question_write_section", "ask_clarify_intent_write_section")
    writer_builder.add_conditional_edges(
        "ask_clarify_intent_write_section",
        reset_write_section,
        {
            True: "classify_user_category",
            False: "update_dependencies_write_section",
        }
    )

    writer_builder.add_edge("generate_summary_section", "get_summary_status_section")
    writer_builder.add_conditional_edges(
        "get_summary_status_section",
        is_ask_intent_write_section,
        {
            True: "generate_check_intent_question_summary_write_section",
            False: "check_summary_status_section",
        }
    )
    writer_builder.add_edge("generate_check_intent_question_summary_write_section", "ask_clarify_intent_summary_write_section")
    writer_builder.add_conditional_edges(
        "ask_clarify_intent_summary_write_section",
        reset_write_section_summary,
        {
            True: "classify_user_category",
            False: "check_summary_status_section",
        }
    )
    writer_builder.add_conditional_edges(
        "check_summary_status_section",
        is_end_write_section,
        {
            True: END,
            False: "generate_summary_section",
        }
    )
    # Update section
    writer_builder.add_conditional_edges(
        "update_dependencies_update_section",
        is_ask_clarify_question_update_section,
        {
            True: "generate_clarify_question_update_section",
            False: "generate_summary_update",
        }
    )
    writer_builder.add_edge("generate_clarify_question_update_section", "ask_clarify_question_update_section")
    writer_builder.add_conditional_edges(
        "ask_clarify_question_update_section",
        is_ask_intent_update_section,
        {
            True: "generate_check_intent_question_update_section",
            False: "update_dependencies_update_section",
        }
    )
    writer_builder.add_edge("generate_check_intent_question_update_section", "ask_clarify_intent_update_section")
    writer_builder.add_conditional_edges(
        "ask_clarify_intent_update_section",
        reset_update_section,
        {
            True: "classify_user_category",
            False: "update_dependencies_update_section",
        }
    )
    writer_builder.add_edge("generate_summary_update", "get_summary_status_update")
    writer_builder.add_conditional_edges(
        "get_summary_status_update",
        is_ask_intent_summary_update,
        {
            True: "generate_check_intent_question_summary_update",
            False: "check_summary_status_update",
        }
    )
    writer_builder.add_edge("generate_check_intent_question_summary_update", "ask_clarify_intent_summary_update")
    writer_builder.add_conditional_edges(
        "ask_clarify_intent_summary_update",
        reset_summary_update,
        {
            True: "classify_user_category",
            False: "check_summary_status_update",
        }
    )
    writer_builder.add_conditional_edges(
        "check_summary_status_update",
        is_end_update_section,
        {
            True: END,
            False: "update_dependencies_update_section",
        }
    )
    return writer_builder.compile(checkpointer=checkpointer)

async def main():
    from langgraph.checkpoint.memory import InMemorySaver
    checkpointer = InMemorySaver()
    graph = await get_graph(checkpointer)
    resume = False
    inp = {
        "model_id": "gpt-4.1-nano",
        "llm_key": os.getenv("OPEN_AI_KEY", ""),
        "event_type": "writer_chatbot",
        "language": "Tiếng Việt",
        "user_id": "68df50d2e59b11f3f50cdad9",
        "conv_id": "696a0df9923bedb1b0749319",
        "user_query": "Tôi muốn viết 1 report",
        "use_web_search_chatbot": False,
        "max_tokens": 1000,
        "short_answer": False,
        "resume": resume
    }
    user_input = ""
    while True:
        if not resume:
            graph_output = await graph.ainvoke(inp, config={"recursion_limit": 1000, "thread_id": "test"})
            interruptted = graph_output.get("__interrupt__")
            if interruptted:
                interrupt_message = interruptted[-1].value
                logger.info(interrupt_message)
            resume = True
        else:
            resume_inp = {
                "model_id": "gpt-4.1-nano",
                "llm_key": os.getenv("OPEN_AI_KEY", ""),
                "question": user_input,
            }
            graph_output = await graph.ainvoke(Command(resume=resume_inp), config={"recursion_limit": 1000, "thread_id": "test"})
            interruptted = graph_output.get("__interrupt__")
            if interruptted:
                interrupt_message = interruptted[-1].value
                logger.info(interrupt_message)
        user_input = input(interrupt_message)


if __name__ == "__main__":
    asyncio.run(main())
