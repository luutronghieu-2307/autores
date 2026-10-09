import asyncio
import logging
import httpx
import requests
from requests.auth import AuthBase
from redis.asyncio import Redis


from document_setup.src.modules.knowledge_prompt_bank import (
    QUERY_REFINER_PROMPT_V2,
    QUERY_REFINER_PROMPT_V3,
)
from document_setup.src.configs.app import settings
from document_setup.src.modules.search_journals import SearchJournal
from document_setup.src.schemas.search_papers import SearchQueries, PaperTitle

from get_llm_response import get_llm, get_answer_with_schema

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)


class OpenAlexAuth(AuthBase):

    def __init__(self, config: dict):
        self.config = config

    def __call__(self, r):
        if self.config.get("api_key"):
            r.headers["Authorization"] = f"Bearer {self.config['api_key']}"

        if self.config.get("email"):
            r.headers["From"] = self.config["email"]

        if self.config.get("user_agent"):
            r.headers["User-Agent"] = self.config["user_agent"]

        return r


class SearchPapers(SearchJournal):
    """
    Handles searching, downloading, and processing academic papers.

    Uses a language model client (initialized externally, typically Gemini)
    for refining queries and extracting key points. Interacts with Google CSE
    for searching papers and attempts to download PDFs.

    Attributes:
        client: An instance of the language model client (e.g., genai.Client).
        model_id (str): Identifier for the language model used by the client.
    """
    def __init__(
        self, 
        model_id: str, 
        document_id: str, 
        user_id: str, 
        use_web_search: bool, 
        redis_client: Redis, 
        language: str, 
        max_tokens: int, 
        llm_key: str = ""
    ):
        """
        Initializes the SearchPapers class.

        Args:
            model_id (str): The identifier of the language model to use.
            client: An initialized language model client instance.
        """
        self.model_id = model_id
        self.redis_client = redis_client
        super().__init__(self.redis_client)
        self.llm = get_llm(self.model_id, llm_key, max_tokens, 1.0)
        if "gemini" in self.model_id:
            self.llm_with_search = self.llm
        elif "gpt" in self.model_id:
            tool = {"type": "web_search_preview"}
            self.llm_with_search = self.llm.bind_tools([tool])
        self.input_tokens = 0
        self.output_tokens = 0
        self.web_search_call = 0
        self.use_web_search = use_web_search
        self.language = language
        self.document_id = document_id if document_id else user_id

    @property
    def id(self):
        return self.document_id[:8]

    def __str__(self):
        return self.id

    async def refine_query_v2(self, field: str, domain: str, subdomains: list[str], proposal: dict, query: str) -> SearchQueries:
        if proposal:
            user_proposal = f"User's proposal:\n{proposal}\n"
            prompt = QUERY_REFINER_PROMPT_V2
        else:
            user_proposal = f"User's query:\n{query}" if query else ""
            prompt = QUERY_REFINER_PROMPT_V3
        content = f"""
        User's field:
        {field}
        User's domain:
        {domain}
        User's subdomains:
        {subdomains}
        {user_proposal}"""
        error, success, result, input_tokens, output_tokens = await get_answer_with_schema(
            self.id, 
            self.llm,
            prompt,
            content,
            SearchQueries
        )
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        if not success:
            raise error
        return result
    
    async def _search_papers(
        self,
        query: str,
        list_papers_title: set,
        list_papers: list[dict],
        country_filter: str,
        oa_filter: bool,
        is_oa: bool,
        cut_off_year_low: int,
        cut_off_year_high: int,
        search_range: str,
        search_num: int = 50,
    ) -> tuple[list[str], list[dict]]:
        config = {
            "max_retries": 10,
            "email": settings.OPEN_ALEX_EMAIL,
            "user_agent": settings.OPEN_ALEX_USER,
            "api_key": settings.OPEN_ALEX_KEY,
            "backoff_factor": 0.1,
            "status_forcelist": [429, 500, 503],
        }
        limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
        transport = httpx.AsyncHTTPTransport(retries=3)

        # Prepare search query (supports Vietnamese and all languages directly)
        search_query = query
        if len(search_range):
            if search_range != "all":
                search_query += " " + search_range

        logger.info(f"[{self}] Search query: {search_query}")

        # Build country filters
        filter_parts = []

        if country_filter == "both":
            filter_parts.append("institutions.is_global_south:true")
        elif country_filter == "out":
            filter_parts.append("institutions.is_global_south:true")
            filter_parts.append("authorships.countries:!VN")
        elif country_filter == "in":
            filter_parts.append("authorships.countries:VN")

        # Build open access filter
        if oa_filter:
            if is_oa:
                filter_parts.append("open_access.is_oa:true")
            else:
                filter_parts.append("open_access.is_oa:false")

        # Build year filters
        if cut_off_year_low:
            filter_parts.append(f"from_publication_date:{cut_off_year_low}-01-01")
        if cut_off_year_high:
            filter_parts.append(f"to_publication_date:{cut_off_year_high}-12-31")

        # Combine filters
        filter_string = ",".join(filter_parts) if filter_parts else None

        # Build URL with search parameter (supports Vietnamese directly)
        # Use search= parameter for multilingual support including Vietnamese
        url_parts = ["https://api.openalex.org/works"]
        params = []

        # Add search query
        params.append(f"search={search_query.replace(' ', '+')}")

        # Add filters if any
        if filter_string:
            params.append(f"filter={filter_string}")

        # Add pagination and sorting
        params.append(f"per_page={search_num}")
        params.append("sort=relevance_score:desc")

        url = url_parts[0] + "?" + "&".join(params)

        logger.info(f"[{self}] OpenAlex URL: {url}")

        try:
            async with httpx.AsyncClient(limits=limits, transport=transport, auth=OpenAlexAuth(config), timeout=(5.0, 10.0)) as client:
                result = await client.get(url)
                result.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
                res = result.json()
            for work in res["results"]:
                if work["title"] not in list_papers_title:
                    paper = {}
                    if work["title"] == "Unknown" or work["title"] == "None" or not work["title"]:
                        continue
                    paper["title"] = work["title"]
                    paper["source"] = "open_alex"
                    try:
                        paper["abs"] = " ".join(list(work["abstract_inverted_index"].keys())) if len(list(work["abstract_inverted_index"].keys())) > 100 else ""
                    except Exception:
                        paper["abs"] = ""
                    if cut_off_year_low:
                        if int(work["publication_year"]) < cut_off_year_low:
                            continue
                    if cut_off_year_high:
                        if int(work["publication_year"]) > cut_off_year_high:
                            continue
                    if work["open_access"]["is_oa"]:
                        paper["open_access"] = True
                        paper["url"] = work["open_access"]["oa_url"]
                    else:
                        paper["open_access"] = False
                        paper["url"] = work["primary_location"]["landing_page_url"]
                    paper["isDownloaded"] = False
                    paper["authors"] = []
                    for author in work["authorships"]:
                        paper["authors"].append(author["author"]["display_name"])
                    if not len(paper["authors"]):
                        paper["authors"] = ["Author"]
                    paper["year"] = work["publication_year"]
                    if work["primary_location"]["source"]:
                        paper["journal"] = work["primary_location"]["source"]["display_name"]
                        paper["publisher"] = work["primary_location"]["source"]["host_organization_name"]
                        paper["issn"] = work["primary_location"]["source"]["issn_l"]
                    else:
                        paper["journal"] = ""
                        paper["publisher"] = ""
                        paper["issn"] = ""
                    biblio = work["biblio"]
                    paper["volume"] = biblio["volume"] or ""
                    paper["issue"] = biblio["issue"] or ""
                    paper["pages"] = f'{biblio["first_page"]}-{biblio["last_page"]}' if biblio["first_page"] and int(biblio["first_page"]) < int(biblio["last_page"]) else ""
                    if paper["journal"] != "":
                        q, issn = await self.get_q_issn(
                            paper["journal"].replace(" ", "_").replace(":", "_").lower(),
                            paper["year"]
                        )
                        paper["q"] = q
                        if paper["issn"] != "":
                            paper["issn"] = issn
                    else:
                        paper["q"] = 'N/A'
                    paper["citation"] = work["cited_by_count"] or 0
                    paper["language"] = work["language"] or "Unknown"
                    paper["type"] = work["type"] or "Unknown"
                    if paper["type"] == "preprint":
                        paper["status"] = "Preprint"
                    else:
                        paper["status"] = "Peer-reviewed"
                    list_papers.append(paper)
                    # logger.info(work["title"])
                    list_papers_title.add(work["title"])
        except requests.exceptions.Timeout:
            logger.info(f"[{self}] Timeout for query {query}")
        finally:
            return list_papers_title, list_papers

    async def search_papers(
        self, 
        field: str,
        domain: str,
        subdomains: list[str],
        proposal: dict,
        downloaded_papers: list[str],
        country_filter: str,
        oa_filter: bool,
        is_oa: bool,
        cut_off_year_low: int, 
        cut_off_year_high: int, 
        search_range: str,
        query: str = ""
    ) -> tuple[list[dict], bool]:
        """
        Searches for academic papers based on refined queries, filters by year,
        and enriches them with publication details and journal rankings.

        The process involves:
        1. Refining the initial domain(s) into specific search queries using an LLM.
        2. Searching Google Scholar for each query, applying year cut-offs if provided.
        3. Extracting paper details (title, URL, open access status).
        4. Enriching the paper list with author, year, journal name, SJR Quartile, and ISSN.

        Args:
            domains (list[str]): A list of research domains to search within.
            cut_off_year_low (int | None): The earliest publication year to include.
            cut_off_year_high (int | None): The latest publication year to include.
            start (int, optional): The starting index for search results (for pagination).
                                   Defaults to 0.

        Returns:
            list[dict]: A list of dictionaries, each representing a found and enriched
                        academic paper, sorted by journal ranking. Returns a maximum
                        of 50 papers.
        """
        list_papers: list[dict] = []
        list_papers_title = set(downloaded_papers)
        if query:
            list_papers_title, list_papers = await self._search_papers(
                query,
                list_papers_title,
                list_papers,
                country_filter,
                oa_filter,
                is_oa,
                cut_off_year_low,
                cut_off_year_high,
                search_range,
                50,
            )
        search_num = 50 if len(subdomains) == 1 else 20
        for subdomain in subdomains:
            list_papers_title, list_papers = await self._search_papers(
                subdomain,
                list_papers_title,
                list_papers,
                country_filter,
                oa_filter,
                is_oa,
                cut_off_year_low,
                cut_off_year_high,
                search_range,
                search_num,
            )
        if len(list_papers) < 100:
            logger.info(f"[{self}] Not enough papers: {len(list_papers)}/100")       
            queries = await self.refine_query_v2(field, domain, subdomains, proposal, query)
            logger.info(f"[{self}] {queries.search_queries}")
            for search_query in queries.search_queries:
                list_papers_title, list_papers = await self._search_papers(
                    search_query,
                    list_papers_title,
                    list_papers,
                    country_filter,
                    oa_filter,
                    is_oa,
                    cut_off_year_low,
                    cut_off_year_high,
                    search_range,
                )
            if len(list_papers) < 100:
                if field:
                    logger.info(f"[{self}] Not enough papers: {len(list_papers)}/100")
                    list_papers_title, list_papers = await self._search_papers(
                        field,
                        list_papers_title,
                        list_papers,
                        country_filter,
                        oa_filter,
                        is_oa,
                        cut_off_year_low,
                        cut_off_year_high,
                        search_range,
                    )
                    list_papers_title, list_papers = await self._search_papers(
                        domain,
                        list_papers_title,
                        list_papers,
                        country_filter,
                        oa_filter,
                        is_oa,
                        cut_off_year_low,
                        cut_off_year_high,
                        search_range,
                    )     
        # sorted_papers = sorted(list_papers, key=lambda x: x['open_access'], reverse=True)
        tasks = [self.add_user_language_title(paper["title"]) for paper in list_papers]
        usage_results = await asyncio.gather(*tasks)
        for paper, (user_language_title, in_tokens, out_tokens) in zip(list_papers, usage_results):
            paper["user_language_title"] = user_language_title
            self.input_tokens += in_tokens
            self.output_tokens += out_tokens
        logger.info(f"[{self}] Total papers: {len(list_papers)}/100")
        return list_papers

    async def add_user_language_title(self, title: str) -> tuple[PaperTitle, int, int]:
        title_prompt = f"Translate the following research paper's title into the {self.language}"
        _, success, title, input_tokens, output_tokens = await get_answer_with_schema(self.id, self.llm, title_prompt, title, PaperTitle)
        if not success:
            return "Unknown", input_tokens, output_tokens
        else:
            return title.title, input_tokens, output_tokens