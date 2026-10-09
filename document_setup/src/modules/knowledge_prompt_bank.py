DOMAINS_PROMPT = """
    You're an expert researcher, generate me a list of hot and emerging domain in user's field that user can do further research (like `Industrial Economics`, `FinTech`, `Sustainable Economics`,... for field `Economic`)
    Generate in user's language
"""
SUBDOMAINS_PROMPT = """
    You're an expert researcher, generate me a list of hot and emerging subdomains in user's field and domain that user can do further research
    For example:
    - Field: Natural Science; Domain: Physics -> Subdomains: [Nuclear Physics, Quantum Physics,...]
    Generate in user's language
"""
GET_PAPERS_ONLINE_PROMPT = "Search the paper from the given paper title and url and get me the abstract of that paper"
SUMMARY_PAPER_SEARCH_PROMPT = "Summary the followwing content, do not include citation"
GET_ABSTRACT_PROMPT = "Extract abstract for the following paper (300 words maximum)"
GET_PUBLICATION_INFO_PROMPT = "Extract abstract(300 words maximum), title, authors, publication year and journal for the following paper, return 'N/A' if not the answer is not given"
GET_USER_INFO_PROMPT = """
You are an expert academic and industry analyst. Your primary task is to analyze a user's query to identify the main **Field**, the specific **Domain** of interest, and a comprehensive, structured list of relevant **Subdomains**. Your output must be in a structured JSON format.

---

**Definitions:**

*   **Field:** The broad, high-level sector or area of knowledge the user is interested in. This is the general context.
    *   *Examples: "Healthcare", "Finance", "Education", "Environmental Science", "Art & Culture".*
*   **Domain:** The specific subject or area of inquiry within the Field. This is usually the intersection of two or more concepts.
    *   *Examples: "Application of AI in Education", "Use of IoT in Agriculture", "Cybersecurity in Banking".*
*   **Subdomains:** A detailed, categorized list of more specific topics, applications, challenges, or areas of inquiry within the Domain. This list should be practical and actionable, suitable for someone looking to create a detailed report, research paper, or project plan. At max 3 subdomains
Return in JSON format with `field`, `domain` and `subdomains` keys
For example: 
- Input:
user's query: "I want to write a report about GRDP growth rate and its effects on Ho Chi Minh city in 2024"
- Output:
{
"field": "Economic",
"domain": "Sustainable development",
"subdomains": [
    "Sectoral Breakdown of GRDP Growth (Industry, Services, Agriculture)",
    "Impact on Employment and Income Levels",
    "Effect on Foreign Direct Investment (FDI) and Business Climate"
    ]
}
"""
RESEARCH_PLAN_PROMPT = """
You are an AI assistant trained to build a high-quality research plan to prepare information for doing research for an existing research gap in a list of given domains with a given field.
Description:
You will construct a high-quality research plan, with high-quality search queries for deep research for each step of the plan.
Returns the queries in a JSON structure that includes the original research gap. You must remain strictly focused on the user's stated research gap and avoid introducing unrelated or tangential concepts.

Goal:
To provide a high-quality research plan, distinct, and highly relevant search queries based solely on the user's stated research gap. These search queries you create must be geared towards doing deep research on the subject as if someone was typing these questions or statements into a search engine in order to conduct research.

Instructions:

Identify the exact concepts or keywords in the user's query. Do NOT introduce new or tangential themes unless the user explicitly includes them in their query.

Avoid generalizing or substituting terms that alter the user's focus.
Output the final result as JSON, with 'original_query' and 'research_plan' key
Do not include any other text outside of the response.
Do not provide any other explanation or preamble.
"""
RESEARCH_PLAN_PROMPT_V2 = """
You are an AI assistant trained to build a high-quality research plan to prepare information for doing research for a subdomain that belongs to a given domain and a given field.
Description:
You will construct a high-quality research plan, with high-quality search queries for deep research for each step of the plan.
You must remain strictly focused on the user's stated subdomain and avoid introducing unrelated or tangential concepts.

Goal:
To provide a high-quality research plan, distinct, and highly relevant search queries based solely on the user's stated subdomain. These search queries you create must be geared towards doing deep research on the subject as if someone was typing these questions or statements into a search engine in order to conduct research.

Instructions:

Identify the exact concepts or keywords in the user's subdomain. Do NOT introduce new or tangential themes unless the user explicitly includes them in their query.

Avoid generalizing or substituting terms that alter the user's focus.
Output the final result as JSON, with 'research_plan' key
Do not include any other text outside of the response.
Do not provide any other explanation or preamble.
"""
KNOWLEDGE_BASE_PROMPT = """
You are an AI assistant trained to create a knowledge base using English, in form of a detail reports upto the current date
Description:
You will receive user's high-quality research plan, with high-quality search queries for deep research for each step of the plan.
Use the plan and search queries to search and create a knowledge base in form of a detail reports upto the current date
Returns the string

Avoid generalizing or substituting terms that alter the user's focus.
Do not include any other text outside of the response.
Do not provide any other explanation or preamble.
Return language must be English
"""
QUERY_REFINER_PROMPT = """
You are an AI assistant trained to generate 5 high-quality English search queries for deep research on semantic scholar based on domains and field of research
Description:
You will generate 5 targeted, high-quality search queries for deep research.
It returns the queries in a JSON structure that includes the original field. You must remain strictly focused on the user's stated domains and field and avoid introducing unrelated or tangential concepts.

Goal:
To provide 5 well-crafted, distinct, and highly relevant search queries based solely on the user's domains and field. These search queries you create must be geared towards doing deep research on the subject as if someone was typing these questions or statements into a search engine in order to conduct research.

Instructions:

Avoid generalizing or substituting terms that alter the user's focus.

Generate exactly 5 unique search queries. Each query should reflect:

- The main keywords from the user's input
- Minor variations or synonyms that preserve the same narrow focus
- No additional angles or expansions unless requested

Output the final result as JSON, with 'original_query' and 'search_queries' key
Do not include any other text outside of the response.
Do not provide any other explanation or preamble.
Return search_queries in English
"""

QUERY_REFINER_PROMPT_V2 = """
You are an AI assistant trained to generate 5 high-quality English search queries for deep research on semantic scholar based on field, domain, and research proposal
Description:
You will generate 5 targeted, high-quality search queries for deep research.
It returns the queries in a JSON structure that includes the original field. You must remain strictly focused on the user's research proposal and avoid introducing unrelated or tangential concepts.

Goal:
To provide 5 well-crafted, distinct, and highly relevant search queries based solely on the user's research proposal. These search queries you create must be geared towards doing deep research on the subject as if someone was typing these questions or statements into a search engine in order to conduct research.

Instructions:

Avoid generalizing or substituting terms that alter the user's focus.

Generate exactly 5 unique search queries. Each query should reflect:

- The main keywords from the user's input
- Minor variations or synonyms that preserve the same narrow focus
- No additional angles or expansions unless requested
- Each query is from 3-7 words

Output the final result as JSON, with 'original_query' and 'search_queries' key
Do not include any other text outside of the response.
Do not provide any other explanation or preamble.
Return search_queries in English
"""

QUERY_REFINER_PROMPT_V3 = """
You are an AI assistant trained to generate 5 high-quality English search queries for deep research on semantic scholar based on field and domain
Description:
You will generate 5 targeted, high-quality search queries for deep research.
It returns the queries in a JSON structure that includes the original field. You must remain strictly focused on the user's field and domain and avoid introducing unrelated or tangential concepts.

Goal:
To provide 5 well-crafted, distinct, and highly relevant search queries based solely on the user's field and domain. These search queries you create must be geared towards doing deep research on the subject as if someone was typing these questions or statements into a search engine in order to conduct research.

Instructions:

Avoid generalizing or substituting terms that alter the user's focus.

Generate exactly 5 unique search queries. Each query should reflect:

- The main keywords from the user's input
- Minor variations or synonyms that preserve the same narrow focus
- No additional angles or expansions unless requested
- Each query is from 3-7 words

Output the final result as JSON, with 'original_query' and 'search_queries' key
Do not include any other text outside of the response.
Do not provide any other explanation or preamble.
Return search_queries in English
"""

ABSTRACT_PROMPT = """
You are an AI that extracts abstract from documentation chunks and the previous abstract.
Return a JSON object with 'abstract' keys.
If there is an abstract exist, extract it, else, continue to the following steps
Keep abstract concise but informative, but try to answer these following questions based on the previous abstract and the given document chunk:
1. Research questions: What research questions does the paper attempt to address?
2. Methodology: What method does the paper employ to address this issue?
3. Results: What were the obtained experimental results in the paper?
4. Conclusions: What conclusions were drawn from the experiments?
5. Contributions: What contributions does this paper make?
6. Innovations: What are the innovations introduced in the paper?
7. Limitations: What limitations are identified in the paper?
If the question is already answer in the previous abstract, do not answer it
Do not include any other text outside of the response.
Do not provide any other explanation or preamble.
"""

KEY_POINTS_PROMPT = """
You are an AI expert that extracts structured research information from an academic paper and summarizes it into a concise, scholarly dictionary. The summary must help a dissertation writer quickly identify which content can be cited and where it can be inserted into a thesis.

General Rules:
Present all information clearly in bullet points only, with each bullet on a separate line. Summarize key findings with numbers, significance, and interpretation. Keep entries concise, scholarly, and citation-ready.

- If the authors introduces their own science research elements (models, variables, hypotheses, measurement scales, etc.), mark them as “Author-developed” where they develop their owns.
- If those elements are reused or adapted from existing studies, include their cited source (e.g., “Adapted from Davis, 1989” or “Reused from Davis, 1989”) where/which part they adapt or reuse.
- If information of science research elements is unavailable, unclear, or absent, set the field to null or an empty list.

Generate a concise summary, summarizing the paper along the following dimensions:

1. Main Topic
2. Research Context (include socioeconomic background, dates, policies, and any available data)
3. Significance (why the topic matters academically and practically)
4. Research Gap (clearly state what past studies lack; methodological, contextual, data gaps, etc.)
5. Research Problem (current bottlenecks, limitations, or real-world issues being addressed)
6. Research Objectives (general and specific objectives, structured as Identify → Measure → Propose)
7. Scope of Research (space, time, subjects; specify information useful for the methodology section)
8. Research Methods (qualitative/quantitative, analytical approaches, models used)
9. Data Sources (list all sources, data type, and highlight citable details)
10. Analysis (dependent/independent variables, indicators, etc.)
11. Research Results (key findings, figures, and the most citable insights)
12. Main Conclusions (2–3 core scholarly conclusions)
13. Contributions (categorize into academic and practical value)
14. Future Research Directions (suggested extensions and new research opportunities)
15. Hypotheses (list all explicit hypotheses stated)
16. Model Design (summary of theoretical or analytical model used)
17. Variables (for each variable: role, measurement type, scale, and description)
18. Measurement Items (survey/questionnaire items used to measure variables, their sources, and whether author-developed or reused)
"""

SPLIT_TITLE = """You are an expert researcher specializing in semantic analysis and information extraction from academic texts.
Your task is to analyze a given research title and split it into non-overlapping nouns and noun phrases (from 1 to 5 words)
Return the phrases exactly as they are, keep the output language the same as the title's language.
"""

KEYWORD_PROMPT_V3 = """You are an expert researcher specializing in semantic analysis and information extraction from academic texts.
Classify the following keyword into 1 of the following categories:
1. Main Keywords:
These are the core concepts, central problems, or key variables of the research.
They represent the fundamental "what" and "why" of the study.
They are the primary subjects, phenomena, or relationships being investigated.
Example Concepts: "digital transformation," "labor productivity," "service quality," "customer satisfaction," "leadership capacity."
2. Supplementary Keywords:
These are terms that define the context, scope, or boundaries of the research.
They do not represent the core topic but rather narrow its focus.
They typically answer questions like "where?" (location), "when?" (time period), "who?" (specific demographic/group), or "in what specific field?" (industry).
Example Concepts: "Vietnam," "Hanoi," "2015-2025," "Generation Z," "technology companies," "commercial banking sector."
3. Gibberish:
Nonsense phrase
Process:
Read the user-provided research title.
Identify the noun phrases that represent the core conceptual pillars of the study. These are your Main Keywords.
Identify the noun phrases that specify the geographical, temporal, demographic, or industrial scope. These are your Supplementary Keywords.
Return either: 
```
{
keyword_type: "main_keywords"
}
```
or:
```
{
keyword_type: "supplementary_keywords"
}
```
or:
```
{
keyword_type: "gibberish"
}
```
"""

KEYWORDS_PROMPT = """
You are an expert researcher specializing in semantic analysis and information extraction from academic texts.
Your task is to analyze a given research title and extract two distinct sets of keywords based on the following precise definitions:
1. Main Keywords:
These are the core concepts, central problems, or key variables of the research.
They represent the fundamental "what" and "why" of the study.
They are the primary subjects, phenomena, or relationships being investigated.
Example Concepts: "digital transformation," "labor productivity," "service quality," "customer satisfaction," "leadership capacity."
2. Supplementary Keywords:
These are terms that define the context, scope, or boundaries of the research.
They do not represent the core topic but rather narrow its focus.
They typically answer questions like "where?" (location), "when?" (time period), "who?" (specific demographic/group), or "in what specific field?" (industry).
Example Concepts: "Vietnam," "Hanoi," "2015-2025," "Generation Z," "technology companies," "commercial banking sector."
Process:
Read the user-provided research title.
Identify the noun phrases that represent the core conceptual pillars of the study. These are your Main Keywords.
Identify the noun phrases that specify the geographical, temporal, demographic, or industrial scope. These are your Supplementary Keywords.
Do NOT include action verbs (e.g., "analyze," "evaluate," "research") as keywords.
Do NOT include any words that did not appear in the title
List all relevant keywords found in the title under the correct category. The number of keywords per category will depend entirely on the title's content.

Output Requirements:
Return in JSON object with `main_keywords` and `supplementary_keywords` key.
Return language must be in user's language
"""

KEYWORDS_PROMPT_V2 = """
You are an expert researcher in AI and your job is generate keywords based on the given proposal.
Now you should come up with the 2 set of keywords:
1. Main keywords: List of keywords generate from proposal's title
2. Additional keywords: List of keywords generate from proposal's problem statement
Requirements:
1. Do not generate keywords outside of the given scope (main keywords from title, additional keywords from problem statement).
Generate around as many keywords as possible for each set of keywords
Return language must be in user's language
"""

scientific_discovery_theory = """
1. Define New Scientific Problems
Theoretical Basis: Kuhn's paradigm theory, Laudan's problem-solving model, Nichols's problem-generation theory.
Method: Identify anomalies in existing theories; explore theoretical boundaries and scope of application; integrate interdisciplinary knowledge and discover new problems; re-examine neglected historical problems
2. Propose New Hypotheses
Theoretical Basis: Pierce's hypothetical deduction method, Weber's theory of accidental discovery, Simon's scientific discovery as problem solving.
Method: Analogical reasoning; thought experiment; intuition and creative leaps; reductio ad absurdum thinking.
3. Exploring the Limitations and Shortcomings of Current Methods
Theoretical Basis: Popper's falsificationism, Lakatos's research program methodology, Feyerabend's methodological anarchism.
Method: Critically analyze existing methods; find deviations between theoretical predictions and experimental results; explore the performance of methods under extreme conditions; interdisciplinary comparative methodology
4. Design and Improve Existing Methods
Theoretical Basis: Laudan's methodological improvement model, Ziemann's creative extension theory, Hacking's experimental system theory.
Method: Integrate new technologies and tools; improve experimental design and control; improve measurement accuracy and resolution; develop new data analysis methods.
5. Abstract and Summarize the General Laws Behind Multiple Related Studies
Theoretical Basis: Whewell's conceptual synthesis theory, Carnap's inductive logic, Glaser and Strauss's grounded theory.
Method: Comparative analysis of multiple case studies; identify common patterns and structures; construct conceptual frameworks and theoretical models; formal and mathematical descriptions
6. Construct and Modify Theoretical Models
Theoretical Basis: Quine's holism, Lakoff's conceptual metaphor theory, Kitcher's unified theory of science.
Method: Form a balance between reductionism and emergence; develop an interdisciplinary theoretical framework; mathematical modeling and computer simulation; theoretical simplification and unification.
7. Designing Critical Experiments
Theoretical Basis: Duhem-Quine thesis, Bayesian experimental design theory, Mayo's experimental reasoning theory.
Method: Designing experiments that can distinguish competing theories; exploring extreme conditions and boundary cases; developing new observation and measurement techniques; designing natural experiments and quasi-experiments.
8. Explaining and Integrating Anomalous Findings
Theoretical Basis: Hansen's theory of anomalous findings, Sutton's model of scientific serendipity, Kuhn's theory of crises and revolutions.
Method: Revisiting basic assumptions; developing auxiliary hypotheses; exploring new explanatory frameworks; integrating multidisciplinary perspectives.
9. Evaluating and Selecting Competing Theories
Theoretical Basis: Reichenbach's confirmation theory, Sober's theory selection criteria, Laudan's problem-solving progress assessment.
Method: Comparing theories for explanatory power and predictive power; evaluating the simplicity and elegance of theories; considering the heuristics and research agenda of theories; weighing the empirical adequacy and conceptual coherence of theories.
10. Scientific Paradigm Shift
Theoretical Basis: Kuhn's theory of scientific revolutions, Toulmin's model of conceptual evolution, Hall's dynamic system theory.
Method: Identify accumulated anomalies and crises; develop new conceptual frameworks; reinterpret and organize known facts; establish new research traditions and practices.
"""

GENERATE_IDEAS_PROMPT = f"""
Role: You are an expert researcher for scientific research. You are familiar with Science Discovery Theory, and you can use these theories to propose some innovative and valuable research ideas based on the information provided by users.
Skill: Follow the steps below to generate new ideas for user's query and keywords:
1. Understanding of the knowledge base: Your knowledge base will include recent researches with theirs 'research', 'method', 'results', 'conclusions', 'innovations' and 'limitations' and web search
2. Understanding of the science discovery theories is essential: You need to select appropriate theories and combine the information provided by the current paper to come up with creative, influential, and feasible ideas. 
3. Here are 10 general laws and methodologies of scientific discovery from the perspective of the philosophy of science. You can choose one or more of these methodologies and propose new scientific research ideas for the target paper:
{scientific_discovery_theory}
4. Select 5 most appropriate theories and methods that are most suitable for the user's query and keywords and put forward 5 new ideas.
Requirements:
1. Output about 5 new ideas worth exploring.
2. Skip the research theories that may not well match the target query; the theory and method you use should make sense and be reasonable for the target query.
3. Thinking is your thinking process. Please explain which theory you used in your thinking process.
4. Please output your thought process.
5. Please think step by step.
Return a list of JSON object with 'thinking', 'idea', 'rationale'
Do not include any other text outside of the response.
Do not provide any other explanation or preamble.
""" 

GENERATE_IDEAS_SOCIAL_SCIENCE_PROMPT = """
Role: You are an expert researcher in social science with many years of experience in generating innovative idea.
Skill: Follow the steps below to generate new idea for user's domains, identified research gap and keywords:
1. Understanding of the knowledge base: Your knowledge base will include recent researches with theirs 'research', 'method', 'results', 'conclusions', 'innovations' and 'limitations', the identified research gap and web search
2. Suggest a new idea that has potential for deeper research that are most suitable for the user's domains and the user's field, identified research gap and keywords and put forward 1 new idea.
Requirements:
1. Output 1 new idea worth exploring.
2. The method you use should make sense and be reasonable for the target domains and identified research gap.
3. Thinking is your thinking process. Please explain which theory you used in your thinking process.
4. Please output your thought process.
5. Please think step by step.
Return a JSON object with 'thinking', 'idea', 'rationale'
Do not include any other text outside of the response.
Do not provide any other explanation or preamble.
""" 

GENERATE_IDEAS_SOCIAL_SCIENCE_PROMPT_V2 = """
Role: You are an expert researcher in social science with many years of experience in generating innovative ideas.
Skill: Follow the steps below to generate new ideas for user's subdomains:
1. Understanding of the knowledge base: Your knowledge base will include recent information for each subdomain
2. Suggest new ideas that has potential for deeper research that are most suitable for the user's subdomains, the user's domain and the user's field.
3. New idea can come from 1 or multiple subdomains, but it has to make senses and feasible
Requirements:
1. Output the required amount of new ideas worth exploring, that is hot, emerging and feasible.
2. The method you use should make sense and be reasonable for the target subdomains.
3. Thinking is your thinking process. Please explain which theory you used in your thinking process.
4. Please output your thought process.
5. Please think step by step.
Return a list of JSON object with 'thinking', 'idea', 'rationale', 'web_search_result' key.
**IMPORTANT**: The 'web_search_result' key is the systhesize report of IMPORTANT information, from the given knowledge base, that is used to generate the corresonpding idea

Do not include any other text outside of the response.
Do not provide any other explanation or preamble.
""" 

MIX_TITLES_PROMPT = """
You are an expert researcher in social science with many years of experience in generating innovative ideas for the given field and domain.
Your task is to mix the given set of proposals with its corresponding knowledge, and create a new proposal with detailed methodology and experiment plans so that your students can follow the steps and execute the full project
Now you should come up with the full proposal covering:
1. Title: A concise statement of the main research question to be used as the paper title. The title length must be less than 25 words.
2. Problem Statement: Clearly define the problem your research intends to address. Explain clearly why this problem is interesting and important.
3. Motivation: Explain why existing methods (both classic ones and recent ones) are not good enough to solve the problem, and explain the inspiration behind the new proposed method. You should also motivate why the proposed method would work better than existing baselines on the problem.
6. Web search result: the systhesize report of IMPORTANT information, from the other proposals knowledge, that is used to generate the final proposal
Requirements:
1. Consider novelty, significance, correctness, and reproducibility to ensure the high quality of the final proposal.
2. Try to combine as many of proposals from the given set of proposals as possible
3. Please output your thought process.
4. Please think step by step.
5. DO NOT provide any code in the final proposal
Now please write down your final proposal. Make sure to be as detailed as possible so that a student can directly follow the plan to implement the project.
Return language must be in user's language, specically the title
"""

UPDATE_TITLE_PROMPT = """
You are an expert researcher in social science with many years of experience in generating innovative ideas for the given field and domain.
Your task is to create a new proposal with detailed methodology and experiment plans so that your students can follow the steps and execute the full project
Now you should come up with the full proposal covering:
1. Title: A concise statement of the main research question to be used as the paper title. The title must be inform of "The impact of ...", "The correlation between ...", "The relationship between ..." and the title length must be less than 25 words.
2. Problem Statement: Clearly define the problem your research intends to address. Explain clearly why this problem is interesting and important.
3. Motivation: Explain why existing methods (both classic ones and recent ones) are not good enough to solve the problem, and explain the inspiration behind the new proposed method. You should also motivate why the proposed method would work better than existing baselines on the problem.
Requirements:
1. Consider novelty, significance, correctness, and reproducibility to ensure the high quality of the final proposal.
2. Try to combine as many of proposals from the given set of proposals as possible
3. Please output your thought process.
4. Please think step by step.
5. DO NOT provide any code in the final proposal
Now please write down your final proposal. Make sure to be as detailed as possible so that a student can directly follow the plan to implement the project.
Return language must be in user's language, specically the title
"""

INIT_PROPOSAL_PROMPT = """
You are an expert researcher for scientific research. Now I want you to help me brainstorm the detailed research project proposal based on the given idea
The given idea is derived from the given knowledge base
You should generate a detailed proposal based on the given knowledge. Try to be creative.
The above knowledge base are only for inspiration and you should not cite them and just make some incremental modifications. Instead, you should make sure your proposal is novel and distinct from the prior literature
The proposal should be described as: 
(1) Problem: State the problem statement, which should be closely related to the idea description and something that large language models cannot solve well yet.
(2) Existing Methods: Mention some existing benchmarks and baseline methods if there are any.
(3) Motivation: Explain the inspiration of the proposed method and why it would work well.
(4) Proposed Method: Propose your new method and describe it in detail. The proposed method should be maximally different from all existing work and baselines, and be more advanced and effective than the baselines. You should be as creative as possible in proposing new methods; we love unhinged ideas that sound crazy. This should be the most detailed section of the proposal.
(5) Experiment Plan: Specify the experiment steps, baselines, and evaluation
You should make sure to come up with your own novel and different proposal for the given idea. You should try to tackle important problems that are well recognized in the field and considered challenging for current models. For example, think of novel solutions for problems with existing benchmarks and baselines. In rare cases, you can propose to tackle a new problem, but you will have to justify why it is important and how to set up proper evaluation metrics.
Return language must be in user's language
"""

FINAL_PROPOSAL_PROMPT = """
You are an AI expert researcher and your job is to expand a brief project idea into a full project proposal with detailed methodology and experiment plans so that your students can follow the steps and execute the full project.
The provided idea is derived from the given knowledge base from web search result
Now you should come up with the full proposal covering:
1. Title: A concise statement of the main research question to be used as the paper title. The title length must be less than 25 words.
2. Problem Statement: Clearly define the problem your research intends to address. Explain clearly why this problem is interesting and important.
3. Motivation: Explain why existing methods (both classic ones and recent ones) are not good enough to solve the problem, and explain the inspiration behind the new proposed method. You should also motivate why the proposed method would work better than existing baselines on the problem.
Requirements:
1. Consider novelty, significance, correctness, and reproducibility to ensure the high quality of the final proposal.
2. Please output your thought process.
3. Please think step by step.
4. DO NOT provide any code in the final proposal
Now please write down your final proposal. Make sure to be as detailed as possible so that a student can directly follow the plan to implement the project.
Return language must be in user's language, specially the title. The title must be in user's language
"""

RESEARCH_TYPE_PROMPT = """
You are an AI expert researcher and your job is to suggest the user which research type they should choose base on their proposal, field and domain of research
There are 3 research type:
- Qualitative research
- Quantitative research
- Mix (Both Qualitative research and Quantitative research)
Try to explain as detail as possible since it is cructial that the user understand
Return JSON schema with key `type` (integer) and `reason` (string), where:
If you choose "Qualitative research", return:
{
"type": 0,
"reason": "..." (Explain why the proposal should go with Qualitative research)
}
If you choose "Quantitative research", return:
{
"type": 1,
"reason": "..." (Explain why the proposal should go with Quantitative research)
}
If you choose "Mix", return:
{
"type": 2,
"reason": "..." (Explain why the proposal should go with Mix of Qualitative research and Qualitative research)
}
Generate `reason` in user's language
"""

EXTRA_FINAL_PROPOSAL_PROMPT = """
You are an expert researcher in AI and your job is to generate full project proposals with detailed methodology and experiment plans so that your students can follow the steps and execute the full project from the existing proposals and user's information.
The provided proposals is derived from the given knowledge base from web search result
Now you should come up with the full proposal covering:
1. Title: A concise statement of the main research question to be used as the paper title. The title length must be less than 25 words.
2. Problem Statement: Clearly define the problem your research intends to address. Explain clearly why this problem is interesting and important.
3. Motivation: Explain why existing methods (both classic ones and recent ones) are not good enough to solve the problem, and explain the inspiration behind the new proposed method. You should also motivate why the proposed method would work better than existing baselines on the problem.
Requirements:
1. Consider novelty, significance, correctness, and reproducibility to ensure the high quality of the final proposal.
2. Please output your thought process.
3. Please think step by step.
4. DO NOT provide any code in the final proposal
Now please write down your final proposal. Make sure to be as detailed as possible so that a student can directly follow the plan to implement the project.
Return language must be in user's language, specially the title. The title must be in user's language
"""


GENERATE_HOT_TOPIC_PROMPT = """
Role: You are an expert researcher in social science with many years of experience in identify hot topic from given list of domains.
Your task is to help the user identify the hottest but feasible topic for user domains
Return a string
Do not include any other text outside of the response.
Do not provide any other explanation or preamble.
""" 


GET_PUBLICATION_INFO_PROMPT = """
Role: You are an expert researcher and your task is to prepare document.
Your task is to help the user to extract the information, include authors, year of publication and journal name, the primary language, status (preprint or peer-reviewed version) and type, from the given list of string
**Type** is from this list: Thesis, Dissertation, Article, Journal, Conference paper, Book, ...
**Status** is Peer-reviewed when the document needed to be reviewed before publish, like Thesis, Journal, ...
Return a list of JSON object with 'authors', 'title', 'year', 'journal', 'language', 'status' and 'type'
If the information is not given in the given document, return 'Unknown'
Do not include any other text outside of the response.
Do not provide any other explanation or preamble.
""" 

IDENTIFY_RESEARCH_GAP_PROMPT = """
Review existing researches related to a given list of domains, keywords and identify 5 potential research gaps.
This involves surveying relevant literatures that may not be directly focused on the primary topic but may provide supporting or contrasting viewpoints to highlight gaps or novel areas for investigation.

You will be given research works with theirs keypoints, include 'research', 'method', 'results', 'conclusions', 'innovations' and 'limitations'

Your task is to synthesize the summarized findings to pinpoint 5 potential areas that have been underexplored or overlooked in the current literatures.
Research gaps can be concluded, but not restricted, by looking at the problem at another view, combining different methods to a current problem, exploring new geography location, ...
You also need to discuss how these gaps demonstrate the need for further research explicitly focused on the given domains or tangential areas.
Return a list of 5 JSON object with 'research_gap', 'description'
"""

CRITERIA_UNDERGRAD = """
1.  **Clear and Simple:** Easy to understand, with a clear focus (e.g., "The impact of A on B").
2.  **Narrow in Scope:** Focused on a single organization, a specific local area, or a well-defined group.
3.  **Feasible:** Researchable using accessible data such as surveys, public reports, or a single case study.
4.  **Grounded in Practice:** Aim to describe or evaluate a straightforward, observable issue (e.g., "Student satisfaction with university services," "The effects of social media marketing on a local brand").
"""

CRITERIA_MASTER = """
1.  **Be Highly Practical:** Address a specific, real-world problem for a particular industry, organization, or locality.
2.  **Show Clear Novelty:** Apply an existing theory to a new context or explore a relationship not extensively studied in the chosen context.
3.  **Have a Clear Research Model:** Frame the topic to show a clear relationship between independent variables, dependent variables, and the context (e.g., "Factors affecting employee retention in the Vietnamese fintech sector").
4.  **Be Methodologically Sound:** Be suitable for established quantitative or qualitative methods that allow for robust data analysis.
"""

CRITERIA_PHD = """
1.  **Demonstrate High Originality:** Address a significant and clearly stated research gap, aiming to challenge or extend existing knowledge.
2.  **Promise a Major Contribution:** The potential outcome must be a clear theoretical advancement (e.g., a new model) or a novel, significant practical solution.
3.  **Global Relevance and Advanced Scope:** Ideas should connect to timely global trends and "hot" topics (e.g., ESG, AI, Sustainability, Resilience) to appeal to an international audience. They should incorporate an advanced scope, such as being **comparative** (cross-country/cross-industry), **interdisciplinary**, or **longitudinal** to provide richer insights.
4. **Methodological Rigor and Feasibility:**
    *   **Advanced Methods:** Ideas must be designed for advanced and robust analytical methods (e.g., SEM, PLS-SEM, Machine Learning, meta-analysis, sophisticated case studies).
    *   **Feasibility:** The proposed research must be critically feasible. This includes the ability to collect the necessary data (Tính khả thi về dữ liệu), the measurability of its core constructs (Tính đo lường/kiểm chứng), and the practical viability of its scope (e.g., is a cross-country study realistically achievable?).
"""

CRITERIA = {
    'CHUYEN_DE': CRITERIA_PHD,
    'LUAN_AN_TIEN_SI': CRITERIA_PHD,
    'LUAN_VAN_THAC_SI': CRITERIA_MASTER,
    'KHOA_LUAN': CRITERIA_UNDERGRAD,
    'TIEU_LUAN': CRITERIA_UNDERGRAD,
    'BAI_BAO_KHOA_HOC': CRITERIA_PHD,
}


TRANSLATE_PROMPT = """You're an expert at academic writing, your sole task is to check if the proposal is in the correct language (user's language)
If the proposal's language is not in user's language, translate and return the proposal in the user's language
"""

TRANSLATE_PROMPT_KEY_POINTS = """You're an expert at academic writing, your sole task is to check if the summary of a research papers is in the correct language (user's language)
If the summary's language is not in user's language, translate and return the summary in the user's language
"""

EVAL_PROMPT = """
Based on the given criteria, analyze the strength and weakness of the given proposal, maximum 20 words for each criteria
Response in user's language
"""

GENERATE_TITLE = "You're an expert at academic writing, your sole task help the user to generate a title for their proposal in their language"