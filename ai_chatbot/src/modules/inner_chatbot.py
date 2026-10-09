import json
from datetime import datetime
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from langgraph.graph import StateGraph, START, END
from langgraph.types import Checkpointer
import logging
import operator
from typing import Annotated, Literal
from typing_extensions import TypedDict
from langchain_core.tools import tool
from bson import ObjectId
from pymongo import ASCENDING
import tiktoken
from qdrant_client import models

from get_llm_response import get_answer, get_answer_with_schema, get_answer_with_websearch
from utils import get_mongodb_client, get_admin_vector_db, markdownify_keep_images, get_embeddings

from ai_chatbot.src.schemas.research_agent import QueryTool, ChosenSections
from ai_chatbot.src.modules.utils import tool_matching
from ai_chatbot.src.configs.app import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@tool
async def get_document_config(state: dict) -> tuple[str, int, int, int, int]:
    """
    Retrieves the complete configuration for a given document_id from the database.
    This includes:
    - Field: Research field of the report
    - Domain: Domain of the report
    - Subdomain: Subdomain of the report
    - References style: Report's references style
    - Research type: Report's research type (Qualitative, Quantitative, Mixed)
    - Research type's reason: Reason why choose to research using this type
    - Title: Report's title
    - Main keywords: main keywords from the report title
    - Supplement keywords: Supplement keywords from the report title
    - Problem statement: Problem statement for the report
    - Motivation: Motivation for the report
    - Web search: Web search result for the current problem
    - Research gap: Research gap that the report try to address
    - Variables (Optional): Variables for the survey questions
    - Final model (Optional): Relationship model
    - Hypothesis (Optional): Hypothesis for the report
    - Survey questions (Optional): List of questions that are used to survey
    - Research questions (Optional): List of research questions that are used for analyzing
    Use this tool to get the foundational information and plan for a document.
    """
    document_id = state["document_id"]
    mongo_client = get_mongodb_client()
    logger.info(f"[{state["_id"]} Tool 'get_document_config' called for document_id: {document_id}")
    try:
        admin_db = mongo_client["admin"]
        articles_collection = admin_db["articles"]
        article = await articles_collection.find_one({"_id": ObjectId(document_id)})
        
        documents_collection = admin_db["document_configurations"]
        doc_config = await documents_collection.find_one({"documentId": document_id})
        RESEARCH_TYPE = {
            0: "Qualitative Research",
            1: "Quantitative Research",
            2: "Mix of Qualitative Research and Quantitative Research",
        }
        proposal_str = f"""
            My field: {article["docsPrepare"].get("field", "Not provided yet")}
            My domain: {article["docsPrepare"].get("domain", "Not provided yet")}
            My subdomains: {article["docsPrepare"].get("subDomain", "Not provided yet")}
            My main keywords: {doc_config["keywords"]["mainKeywords"] or "Not provided yet"}
            My supplement keywords: {doc_config["keywords"]["subKeywords"] or "Not provided yet"}
            My references style: {doc_config["referencesStyle"] or "Not provided yet"}
        """
        if "researchType" in doc_config:
            proposal_str += f"""
            My research type: {RESEARCH_TYPE[doc_config["researchType"]["type"]]}
            My research type's reason: {doc_config["researchType"]["reason"]}
        """
        proposal_collection = admin_db["proposal_titles"]
        if "title" in article:
            title_id = article["title"] 
            proposal = await proposal_collection.find_one({"_id": ObjectId(title_id)})
            if proposal:
                proposal_str += f"""
                My report's title: {proposal["title"]}
                My problem's statement: {proposal["problemStatement"]}
                My motivation: {proposal["motivation"]}
                My web search: {proposal["webSearch"]}
                My research gap: {proposal["researchGap"]}
                My variables: {proposal.get("variables", "Not provided yet")}
                My final model: {proposal.get("finalModel", "Not provided yet")}
                My hypothesis: {proposal.get("hypothesis", "Not provided yet")}
                My survey questions: {proposal.get("surveyQuestions", "Not provided yet")}
                My research questions: {proposal.get("questions", "Not provided yet")}
            """
        return proposal_str, 0, 0, 0, 0

    except Exception as e:
        logger.error(f"[{state["_id"]} Error in get_document_config: {e}")
        return f"An unexpected error occurred while fetching document configuration for ID {document_id}.", 0, 0, 0, 0


@tool
async def get_document_outline(state: dict) -> tuple[str, int, int, int, int]:
    """
    Retrieves the detailed outline, which contain the structure and what to write for search section of a document, for a document from the database using its document_id.
    Use this tool when you have a plan and need the specific structure of the document.
    """
    document_id = state["document_id"]
    mongo_client = get_mongodb_client()
    logger.info(f"[{state["_id"]} Tool 'get_document_outline' called for document_id: {document_id}")
    try:
        admin_db = mongo_client["admin"]
        articles_collection = admin_db["articles"]
        article = await articles_collection.find_one({"_id": ObjectId(document_id)})
        if not article:
            return f"Error: Article with document_id '{document_id}' not found.", 0, 0, 0, 0

        title_id = article["title"]
        documents_collection = admin_db["document_configurations"]
        doc_config = await documents_collection.find_one({"finalProposal": ObjectId(title_id)}) 
        detailed_outline = doc_config["processedOutline"]
        for section in detailed_outline["outline"]:
            for subsection in section["subheadings"]:
                try:
                    del subsection["refs"]
                except Exception:
                    pass
        return json.dumps(detailed_outline, indent=2, default=str), 0, 0, 0, 0

    except Exception as e:
        logger.error(f"[{state["_id"]} Error in get_document_outline: {e}")
        return f"An unexpected error occurred while fetching the outline for ID {document_id}.", 0, 0, 0, 0


@tool
async def get_document_content(state: dict) -> tuple[str, int, int, int, int]:
    """
    Retrieves the final, pre-written content of a report from the user_documents database.
    Use this tool to get the complete text of the document if it has already been generated to answer question related to the document like:
    - "What references are used in this report?"
    - "Summary section 2"
    """
    document_id = state["document_id"]
    mongo_client = get_mongodb_client()
    input_tokens, output_tokens = 0, 0
    logger.info(f"[{state["_id"]} Tool 'get_document_content' called for document_id: {document_id}")
    try:
        db = mongo_client["admin"]
        articles_collection = db["articles"]
        article = await articles_collection.find_one({"_id": ObjectId(document_id)})
        if not article:
            return f"Error: Article with document_id '{document_id}' not found.", 0, 0, 0, 0

        title_id = article["title"]
        documents_collection = db["document_configurations"]
        doc_config = await documents_collection.find_one({"finalProposal": ObjectId(title_id)}) 
        detailed_outline = doc_config["processedOutline"]
        if detailed_outline:
            outline_description = ""
            for section in detailed_outline["outline"]:
                outline_description += f"- Section {section["heading"]}: {section["overview"]}\n"
            outline_description += f"- Section {len(detailed_outline["outline"]) + 1} References: List of References papers"
            final_question = state["reformatted_question"].split("User's new query:")[-1].split("User's query:")[-1]
            prompt = """Based on the user's question and the provided list of sections, decide which sections are most relevant to answer the question.
            - The sections are provided with their number and a description.
            - You must return a list of the section numbers that are relevant.
            - For example:
                Input:
                - Section 1: Introduction
                - Section 2: Literature Review
                - Section 3: Research Design
                - Section 4: Methodology
                - Section 5: Result
                - Section 6: Conclusion
                - Section 7: References
                User's question: What papers are used in the research?
                -> Return [7] (References)

                User's question: What is the research about?
                -> Return [1, 6] (Introduction, Conclusion)
                
                User's question: What is section 2 about?
                -> Return [2] (Literature Review)
            """
            content = f"User's question: {final_question}\nReturn list of integer from 1 to {len(detailed_outline["outline"]) + 1}"
            error, success, sections, input_tokens, output_tokens = await get_answer_with_schema(
                state["_id"], 
                state["llm"], 
                prompt, 
                content, 
                ChosenSections
            )
            if success:
                raise error
            if not len(sections.chosen_sections):
                chosen_sections = [i + 1 for i in range(len(detailed_outline["outline"]) + 2)]
            else:
                chosen_sections = sections.chosen_sections
        else:
            chosen_sections = []
        content_collection = db["outlines"]
        user_report_caches = content_collection.find({"document_id": document_id}).sort("index", ASCENDING)
        user_report_cache = ""
        async for doc in user_report_caches:
            if chosen_sections:
                if doc["index"] in chosen_sections or not len(chosen_sections):
                    if doc["content"]:
                        user_report_cache += doc["content"] + "\n\n"
                    else:
                        if doc["contentArr"]:
                            section_content = ""
                            for subsection in doc["contentArr"]:
                                section_content += subsection["text"]
                            user_report_cache += section_content + "\n\n"
                        else:
                            break

        articles_collection = db["articles"]
        article = await articles_collection.find_one({"_id": ObjectId(state["document_id"])})
        if article and "topicRefs" in article:
            for seminar_id in article["topicRefs"]:
                user_report_caches = content_collection.find({"documentId": seminar_id}).sort("index", ASCENDING)
                async for doc in user_report_caches:
                    if doc["content"]:
                        user_report_cache += doc["content"] + "\n\n"
                    else:
                        if doc["contentArr"]:
                            section_content = ""
                            for subsection in doc["contentArr"]:
                                section_content += subsection["text"]
                            user_report_cache += section_content + "\n\n"
                        else:
                            break
        user_report_md = markdownify_keep_images(user_report_cache)
        return user_report_md.strip(), 0, 0, 0, 0
    except Exception as e:
        logger.error(f"[{state["_id"]} Error in get_document_content: {e}")
        return f"An unexpected error occurred while fetching content for ID {document_id}.", input_tokens, output_tokens, 0, 0


@tool
async def get_relevant_documents(state: dict) -> tuple[str, int]:
    """
    Searches the document's private, ingested references for specific information.
    Use this tool when the user asks a detailed question about the topic that requires
    citing specific sources or data from the provided reference materials.
    """

    logger.info(f"[{state["_id"]} Tool 'get_relevant_documents' called for document_id '{state["document_id"]}' with query: '{state["reformatted_question"]}'")
    final_question = state["reformatted_question"].split("User's new query:")[-1].split("User's query:")[-1]
    try:
        # Initialize the vector store client pointing to the existing collection
        embeddings = get_embeddings(state.get("db_key", ""))
        references_vector_store = QdrantVectorStore.from_existing_collection(
            url=settings.QDRANT_URL,
            collection_name=state["document_id"],
            embedding=embeddings
        )
        try:
            encoding = tiktoken.encoding_for_model(settings.EMBEDDING_MODEL)
        except Exception:
            encoding = tiktoken.get_encoding("cl100k_base")
        results = await references_vector_store.asimilarity_search(final_question, k=state["k_per_query"])

        if not results:
            return (
                "No relevant information found in the provided references for this query.", 
                0, 
                0, 
                0, 
                len(encoding.encode(state["reformatted_question"]))
            )

        formatted_chunks = "\n\n".join([f"Reference Chunk: {doc.page_content}" for doc in results])
        return (
            f"Found the following information in the references:\n\n{formatted_chunks}", 
            0, 
            0, 
            0, 
            len(encoding.encode(state["reformatted_question"]))
        )

    except Exception as e:
        logger.error(f"[{state["_id"]} Error in get_relevant_documents: {e}")
        return f"Could not access the reference vector store for document '{state["document_id"]}'. It may not have been created yet.", 0, 0, 0, 0


@tool
async def get_external_information_no_web_search(state: dict) -> tuple[str, int, int, int, int]:
    """
    A general-purpose search tool (Not web search). Use this as a fallback if you cannot find the
    information using other tools or if the user asks for general knowledge.
    """
    final_question = state["reformatted_question"].split("User's new query:")[-1].split("User's query:")[-1]
    logger.info(f"[{state["_id"]} Tool 'get_external_information_no_web_search' called with query: '{final_question}'")
    
    try:
        encoding = tiktoken.encoding_for_model(settings.EMBEDDING_MODEL)
    except Exception:
        encoding = tiktoken.get_encoding("cl100k_base")
    admin_vector_store = await get_admin_vector_db(state["db_key"])
    retrieved_docs_for_query = await admin_vector_store.asimilarity_search(
        query=final_question, 
        k=state["k_per_query"],
        filter=models.Filter(
            must=[
                models.FieldCondition(
                    key="metadata.source",
                    match=models.MatchValue(value="admin_user_guide")
                )
            ]
        )
    )
    print(f"--- get_external_information_no_web_search for query: '{final_question}' ---")
    return f"get_external_information_no_web_search result for '{final_question}': {retrieved_docs_for_query}", 0, 0, 0, len(encoding.encode(final_question))


@tool
async def get_external_information_web_search(state: dict) -> tuple[str, int, int, int, int]:
    """
    Accesses a real-time web search engine to find up-to-date information on any topic.
    Use this tool for questions about current events, recent discoveries, or any subject
    where the most current information is essential and is unlikely to be found in the
    static, internal document sources.
    """
    final_question = state["reformatted_question"].split("User's new query:")[-1].split("User's query:")[-1]
    logger.info(f"[{state["_id"]} Tool 'get_external_information_web_search' called with query: '{final_question}'")
    prompt = f"""You are an assistant for question-answering tasks, answer the question based on the user's notes.
    {state["short_answer_prompt"]}
    Current date: {datetime.now().strftime("%a %b %-d, %Y")}
    Response in {state["language"]}    
    """
    retry = 0
    if state["use_web_search"]:
        websearch_context = f"Get up-to-date information for the following question: {final_question}"
        error, success, response, retry, input_tokens, output_tokens = await get_answer_with_websearch(
            state["_id"], 
            state["llm"], 
            prompt, 
            state["reformatted_question"], 
            state["search_web_key"], 
            state["language"], 
            websearch_context
        )
        if not success:
            raise error
    else:
        error, success, response, input_tokens, output_tokens = await get_answer(state["_id"], state["llm"], final_question, prompt)
        if not success:
            raise error

    print(f"--- get_external_information_web_search for query: '{final_question}' ---")
    return f"get_external_information_web_search result for '{final_question}': {response}", input_tokens, output_tokens, retry, 0


class State(TypedDict):
    _id: str
    conv_id: str
    document_id: str
    model_id: str
    db_key: str
    llm: ChatGoogleGenerativeAI | ChatOpenAI
    search_web_key: str
    reformatted_question: str
    language: str
    extra_context: str
    short_answer_prompt: str
    use_web_search: bool
    # Core research state
    notes: Annotated[str, operator.add]
    answer: str
    available_tools: list[str]
    tools_def: dict
    k_per_query: int
    
    # Control flow state
    next_tool: Literal["get_document_config", "get_document_outline", "get_document_content", "get_external_information_web_search", "finish"]
    turn_count: int
    max_turns: int
    input_tokens: Annotated[int, operator.add]
    output_tokens: Annotated[int, operator.add]
    embed_tokens: Annotated[int, operator.add]
    web_search_call: int


async def initial_value(state: State):
    logger.info(f"[{state["_id"]} - Setting initial value...")
    if state["document_id"]:
        return {
            "notes": "",
            "turn_count": 0,
            "max_turns": 6,
            "available_tools": [
                "get_document_config", 
                "get_document_outline", 
                "get_document_content", 
                "get_relevant_documents", 
                "get_external_information_no_web_search", 
                "get_external_information_web_search"
            ],
            "tools_def": {
                "get_document_config": "get_document_config(state: dict): Retrieves the high-level plan, scope, and keywords for a document.",
                "get_document_outline": "get_document_outline(state: dict): Retrieves the detailed chapter/section outline for the document.",
                "get_document_content": "get_document_content(state: dict): Retrieves the final, pre-written text of a document.",
                "get_relevant_documents": "get_relevant_documents(state: dict): Retrieves the document's private, ingested references for specific information. Use this when the user asks a detailed question about the topic that requires citing specific sources or data from the provided reference materials.",
                "get_external_information_no_web_search": "get_external_information_no_web_search(state: dict): A general-purpose search tool for internal knowledge. Use this as a fallback if you cannot find the information using other tools or if the user asks for general knowledge.",
                "get_external_information_web_search": "get_external_information_web_search(state: dict): Accesses a real-time web search engine to find up-to-date information. Use this for questions about current events, recent discoveries, or when the most current information is essential."
            }
        }
    else:
        return {
            "notes": "",
            "turn_count": 0,
            "max_turns": 2,
            "available_tools": [
                "get_external_information_no_web_search", 
                "get_external_information_web_search"
            ],
            "tools_def": {
                "get_external_information_no_web_search": "get_external_information_no_web_search(state: dict): A general-purpose search tool. Use this for general knowledge or if you don't know what tool to use.",
                "get_external_information_web_search": "get_external_information_web_search(state: dict): Accesses a real-time web search engine to find up-to-date information. Use this for questions about current events, recent discoveries, or when the most current information is essential."
            }
        }


async def supervisor_router(state: State):
    # (This node remains mostly the same, but the prompt is updated for clarity)
    logger.info(f"[{state["_id"]} - Supervisor is thinking...")
    if state["turn_count"] >= state["max_turns"]:
        logger.warning(f"[{state["_id"]} Max turns reached. Forcing failure.")
        return {"next_tool": "finish"}

    prompt = f"""You are a research project manager. Your goal is to fulfill the user's question by intelligently using database tools.

        USER'S QUESTION:
        {state["reformatted_question"]}
        {state["extra_context"]}
        CURRENT RESEARCH NOTES (from previous tool calls):
        {state.get("notes") or "No notes yet."}

        AVAILABLE DATABASE TOOLS:
        {state["tools_def"]}

        Based on the user's question and the notes, what is the single best tool to use next?
        - If the question seems fully addressed or none of the AVAILABLE DATABASE TOOLS will be helpful, respond with "finish".
        - Otherwise, respond with the exact name of the tool to use.
        
        Your response must be one of the following: {state["available_tools"] + ["finish"]}.
        """
    
    error, success, tool, input_tokens, output_tokens = await get_answer_with_schema(state["_id"], state["llm"], "", prompt, QueryTool)
    if not success:
        raise error
    selected_tool = tool_matching(tool.selected_tool, state["available_tools"] + ["finish"])
    logger.info(f"[{state["_id"]} - Supervisor decision: '{selected_tool}'")
    
    return {"next_tool": selected_tool, "turn_count": state["turn_count"] + 1, "input_tokens": input_tokens, "output_tokens": output_tokens}


async def execute_tool(state: State):
    tool_name = state["next_tool"]
    logger.info(f"[{state["_id"]} - Executing tool: {tool_name}")
    
    tool_map = {
        "get_document_config": get_document_config,
        "get_document_outline": get_document_outline,
        "get_document_content": get_document_content,
        "get_relevant_documents": get_relevant_documents,
        "get_external_information_no_web_search": get_external_information_no_web_search,
        "get_external_information_web_search": get_external_information_web_search,
    }
    tool_to_call = tool_map[tool_name]

    observation, input_tokens, output_tokens, web_search_call, embed_tokens = await tool_to_call.ainvoke({"state": state})

    state["available_tools"].remove(state["next_tool"])
    del state["tools_def"][state["next_tool"]]
    new_note = f"\n\n--- Step {state['turn_count']}: Used tool '{tool_name.replace('get_', '').replace('_', ' ')}' ---\n{observation}"
    
    # MODIFIED: Return all accumulated values to correctly update the graph state
    return {
        "notes": new_note,
        "available_tools": state["available_tools"],
        "tools_def": state["tools_def"],
        "embed_tokens": embed_tokens,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "web_search_call": web_search_call,
    }


def route_from_supervisor(state: State) -> Literal["execute_tool", "get_final_answer"]:
    next_tool = state.get("next_tool")
    if next_tool == "finish":
        return "get_final_answer"
    return "execute_tool"


async def get_final_answer(state: State):
    prompt = f"""You are an assistant for question-answering tasks, answer the question based on the user's notes.
        {state["short_answer_prompt"]}
        Current date: {datetime.now().strftime("%a %b %-d, %Y")}
        Response in {state["language"]}    
        """
    content = f"""Here are my notes:
    RESEARCH NOTES:
    {state.get("notes") or "No notes yet."}
    {state["extra_context"]}
    Question:
    {state["reformatted_question"]}
    Response in {state["language"]} 
    """
    error, success, response, input_tokens, output_tokens = await get_answer(state["_id"], state["llm"], content, prompt)
    if not success:
        raise error
    return {"answer": response, "web_search_call": 0, "input_tokens": input_tokens, "output_tokens": output_tokens}


async def get_graph(checkpointer: Checkpointer):
    builder = StateGraph(State)

    builder.add_node("initial_value", initial_value)
    builder.add_node("supervisor_router", supervisor_router)
    builder.add_node("execute_tool", execute_tool)
    builder.add_node("get_final_answer", get_final_answer)

    builder.add_edge(START, "initial_value")
    builder.add_edge("initial_value", "supervisor_router")

    builder.add_conditional_edges(
        "supervisor_router", route_from_supervisor, {"execute_tool": "execute_tool", "get_final_answer": "get_final_answer"}
    )
    builder.add_edge("execute_tool", "supervisor_router")
    builder.add_edge("get_final_answer", END)

    return builder.compile(checkpointer=checkpointer)