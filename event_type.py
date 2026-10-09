from enum import Enum


class DocumentSetupEvent(str, Enum):
    SEARCH_PAPERS = "search_papers"
    GENERATE_DOMAINS = "generate_domains"
    GENERATE_SUBDOMAINS = "generate_subdomains"
    GENERATE_KEYWORDS = "generate_keywords"
    GENERATE_TITLES = "generate_titles"
    MIX_TITLES = "mix_titles"
    GENERATE_TITLE_DESCRIPTION = "generate_title_description"
    GENERATE_TITLE_DESCRIPTION_NO_INFO = "generate_title_description_no_info"
    GENERATE_OUTLINE = "generate_outline"
    GET_JOURNALS = "get_journals"
    ADMIN_DOCUMENTS = "admin_documents"
    USER_GUIDE_DOCUMENTS = "user_guide_documents"
    USER_DOCUMENTS = "user_documents"
    EMBED_USER_DOCUMENTS = "embed_user_documents"
    DELETE_DOCUMENTS = "delete_documents"
    GENERATE_OUTLINE_WITH_REFS = "generate_outline_with_refs"
    MODIFY_OUTLINE = "modify_outline"
    GET_RESEARCH_TYPE = "get_research_type"
    UPDATE_USER_REFS = "update_user_refs"
    SEARCH_USER_DOCUMENTS = "search_user_documents"


class AIEvent(str, Enum):
    OUTER_CHATBOT = "outer_chatbot"
    INNER_CHATBOT = "inner_chatbot"
    WRITER_CHATBOT = "writer_chatbot"
    WRITER = "writer"


class EnhancementEvent(str, Enum):
    AI_IN_DOC = "ai_in_doc"
    GET_SUGGESTIONS = "get_suggestions"
    ENHANCE = "enhance"
    ENHANCE_ALL = "enhance_all"


class WriteEvent(str, Enum):
    WRITE_CONTENT = "write_content"
    ANALYZER = "analyzer"
    CHUYEN_DE_1 = "chuyen_de_1"
    CHUYEN_DE_2 = "chuyen_de_2"
    CHUYEN_DE_3 = "chuyen_de_3"
    EDIT_REPORT = "edit_report"
    GEN_SLIDES = "gen_slides"
    COMMENT_DATA = "comment_data"
    ANALYZER_TOOL = "analyzer_tool"
    PROPOSE_METHOD = "propose_method"
    PARSED_VALUE = "parsed_value"
    DELETE_REPORT = "delete_report"
    TRANSLATE_REPORT = "translate_report"
    CHECK_LOGIC_DATA = "check_logic_data"