from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
import logging
from pymongo import AsyncMongoClient
from redis.asyncio import Redis

from ai_chatbot.src.configs.app import settings
from ai_chatbot.src.schemas.response import Response, StandaloneQuestion
from ai_chatbot.src.modules.utils import DataHelper
from ai_chatbot.src.modules.inner_chatbot import get_graph

from get_llm_response import get_answer, get_answer_with_schema, get_answer_with_websearch
from utils import get_minio_client, get_async_redis_checkpoint, get_embeddings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)


class Chatbot(DataHelper):

    def __init__(
        self, 
        language: str,
        user_id: str,
        model_id: str,
        llm_key: str,
        db_key: str, 
        max_tokens: int,
        conv_id: str, 
        short_answer: bool, 
        use_web_search: bool,
        mongo_client: AsyncMongoClient,
        redis_client: Redis,
        search_web_key: str,
        document_id: str = "",
    ):
        self.language = language
        self.short_answer = short_answer
        self.conv_id = conv_id
        super().__init__(user_id, model_id, llm_key, self.conv_id, max_tokens, mongo_client)
        self.search_web_key = search_web_key
        self.document_id = document_id
        if self.document_id:
            self.k_per_query = 2
        else:
            self.k_per_query = 5
        self.redis_client = redis_client
        self.minioClient = get_minio_client()
        self.input_tokens = 0
        self.output_tokens = 0
        self.embed_tokens = 0
        self.use_web_search = use_web_search
        self.web_search_call = 0
        self.embeddings = get_embeddings(db_key)
        self.db_key = db_key

    @property
    def id(self):
        return f"{self.conv_id[:8]} - {self.document_id[:8]}" if self.document_id else self.conv_id[:8]

    def __str__(self):
        return self.id

    async def format_history(self, history: list[dict]) -> list[BaseMessage]:
        formatted_history: list[BaseMessage] = []
        for msg in history:
            if msg["role"] == "user":
                formatted_history.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                formatted_history.append(AIMessage(content=msg["content"]))
        return formatted_history
    
    async def get_standalone_query(self, question: str, formatted_history: list[BaseMessage]) -> str:
        system_prompt = """
        You are a query rewriting expert. Your SOLE task is to rephrase a follow-up question into a self-contained, standalone question. You must not answer the question. Your output must be ONLY the reformulated question.
        Here is an example:
        ---
        Chat History:
        Human: What are the main criteria for a PhD-level research proposal?
        AI: A PhD proposal needs high originality, a clear research gap, and methodological rigor.

        Follow-up User Question:
        What about feasibility?

        Standalone Question:
        What are the feasibility requirements for a PhD-level research proposal, in addition to originality, research gap, and methodological rigor?
        ---
        ** IMPORTANT **: ONLY REPHRASE FOLLOW-UP QUESTION, else, return the original question
        Now, perform this task for the following chat history and follow-up question.
        """
        content = f"""
        Chat History:
        {formatted_history},
        Follow-up User Question:
        {question}
        """
        error, success, result, input_tokens, output_tokens = await get_answer_with_schema(
            self.id, 
            self.llm,
            system_prompt,
            content,
            StandaloneQuestion
        )
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        if success:
            reformatted_question = result.standalone_question
        else: 
            if error.status_code in [401, 403, 429, 500]:
                raise error
            reformatted_question = question
            logger.error(f"[{self}] Fail to generate reformatted question, use the original question")
        return reformatted_question

    async def get_direct_answer(self, context: str) -> tuple[str, int, int, int, int]:
        short_answer_prompt = "\nUse three sentences maximum and keep the answer concise." if self.short_answer else ""
        websearch_context = f"Get up-to-date information for the following question: {context}"
        if self.use_web_search:
            error, success, response, retry, input_tokens, output_tokens = await get_answer_with_websearch(
                self.id,
                self.llm, 
                short_answer_prompt, 
                context, 
                self.search_web_key, 
                self.language,
                websearch_context,
                # True,
            )
            if not success:
                raise error
            self.web_search_call += retry
        else:
            error, success, response, input_tokens, output_tokens = await get_answer(self.id, self.llm, context + short_answer_prompt)
            if not success:
                raise error
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        return response, self.input_tokens, self.output_tokens, self.embed_tokens, self.web_search_call

    async def _get_answer(self, reformatted_question: str, input_context: str) -> tuple[str, int, int, int, int]:
        extra_context = f"Extra context:\n{input_context}\n"
        short_answer_prompt = "\nUse three sentences maximum and keep the answer concise." if self.short_answer else ""
        checkpointer = await get_async_redis_checkpoint()
        chatbot_agent = await get_graph(checkpointer)
        inp = {
            "_id": self.id,
            "conv_id": self.conv_id,
            "document_id": self.document_id,
            "model_id": self.model_id,
            "db_key": self.db_key,
            "k_per_query": self.k_per_query,
            "llm": self.llm,
            "search_web_key": self.search_web_key,
            "language": self.language,
            "reformatted_question": reformatted_question,
            "extra_context": extra_context,
            "short_answer_prompt": short_answer_prompt,
            "use_web_search": self.use_web_search,
        }
        result = await chatbot_agent.ainvoke(inp, config={"recursion_limit": 1000, "thread_id": self.conv_id})
        return (
            result["answer"], 
            self.input_tokens + result["input_tokens"], 
            self.output_tokens + result["output_tokens"], 
            self.embed_tokens + result["embed_tokens"], 
            self.web_search_call + result["web_search_call"]
        )

    async def get_answer(self, question: str, chat_history: list[dict], direct_answer: bool) -> tuple[str, int, int, int, int]:
        if len(chat_history):
            if len(chat_history) > 10:
                chat_history = chat_history[-10:]
            formatted_history = await self.format_history(chat_history)
            # standalone_question = await self.get_standalone_query(question, formatted_history)
            reformatted_question = f"Chat history:\n{formatted_history}\nUser's new query:{question}"
        else:
            reformatted_question = f"User's query: {question}"
        context = f"{reformatted_question}\nResponse in {self.language}"
        if direct_answer:
            return await self.get_direct_answer(context)
        else:
            system_prompt = """
                    You are a conversational AI designed to handle everyday conversations and domain-specific questions. Follow these rules:
                    1. Response in JSON object with `response` and `status` key
                    2. **Everyday Conversation**: For casual questions (e.g., "Hi", "How are you?", "How's the weather?", "What's up?"), respond naturally and concisely as a friendly AI, set `status` to True and answer in `response`. Keep responses short and appropriate. Example:
                    - "Hi" → {'status': True,
                    'response': "Hey there! Doing great, thanks for asking!"
                    }
                    3. **Domain-specific questions**: For questions need more thinking, or professional experiences, or you don't know how to answer (e.g., "Tell me about what happen to bank during covid"), set `status` to False and `response` to 'N/A'

                    4. **Ambiguous Cases**: If the question is vague (e.g., "What do you do?"), assume it's domain-specific and set `status` to False and `response` to 'N/A'.

                    5. **Require new knowledge cases**: For questions require up-to-date knowledge, ("What is today's date?", "What is today's the weather"), set `status` to False and `response` to 'N/A'.
                    6. **Tone**: Use a friendly, conversational tone for casual responses
                    """
            error, success, response, input_tokens, output_tokens = await get_answer_with_schema(self.id, self.llm, system_prompt, context, Response)
            self.input_tokens += input_tokens
            self.output_tokens += output_tokens
            if not success:
                if error.status_code in [401, 403, 429, 500]:
                    raise error
                response = Response(
                    status=False,
                    response=question,
                )
                logger.info(f"[{self}] Fail to get response for get answer for normal conversation, set status to false")
            if response.status:
                return response.response, self.input_tokens, self.output_tokens, self.embed_tokens, self.web_search_call
            else:
                input_context, input_tokens, output_tokens = await self.load_file_content()
                self.input_tokens += input_tokens
                self.output_tokens += output_tokens
                
                return await self._get_answer(reformatted_question, input_context)