def format_paper_summaries(refs) -> list[str]:
    summaries: list[str] = []
    for paper in refs:
        if isinstance(paper.summary, dict):
            key_points = [f"{k}: {v}\n---\n" for k, v in paper.summary.items()]
        else:
            key_points = str(paper.summary)
        summaries.append(f"Paper's title: {paper.title}\nPaper key points:\n{key_points}")
    return summaries


def format_outline_summary(outline: dict) -> list[str]:
    return [
        f"Section {i + 1}. {section['heading']}: {section['overview']}\n"
        for i, section in enumerate(outline["outline"])
    ]


def build_ref_integration_prompt(blocks_str: str, refs_str: str, last_block_idx: int) -> str:
    return f"""
    You are an expert academic editor. Your task is to insert specific 'Integration Paragraphs' (citations/evidence) into a 'Main Text' to create a cohesive flow.

    **MAIN TEXT BLOCKS:**
    {blocks_str}

    **INTEGRATION PARAGRAPHS TO INSERT:**
    {refs_str}

    **INSTRUCTIONS:**
    1. Analyze the content of each INTEGRATION paragraph.
    2. Determine the best logical position in the MAIN TEXT to insert it.
    3. Return a plan mapping each `integration_idx` to an `insert_after_block_idx`.
    4. If a paragraph introduces a topic, place it early. If it supports a point, place it after that point.
    5. If it doesn't fit perfectly, place it at the end (index {last_block_idx}).
    
    Return the JSON plan.
    """


def build_write_subsection_content(
    state: dict,
    current_report: str,
    user_content: str,
    extra_content: str,
) -> str:
    return f"""
            Provided research papers:
            {format_paper_summaries(state["subsection"].refs)}
            Report proposal:
            {state["proposal"]}
            Overall outline:
            {format_outline_summary(state["outline"])}
            {current_report}
            Current Section name:
            {state["section"].heading}
            Current Section description:
            {state["section"].overview}
            Current Subsection heading:
            {state["subsection"].subheading}
            Current Subsection description:
            {state["subsection"].detail_description}
            Current Subsection word limit:
            {state["subsection"].subheading_word_count}
            User's language:
            {state["language"]}
            User's field:
            {state["field"]}
            User's domain:
            {state["domain"]}
            {user_content}
            {extra_content}
            """


def build_write_section_content(
    state: dict,
    current_report: str,
    refs,
    user_content: str,
    extra_content: str,
) -> str:
    return f"""
            Provided research papers:
            {format_paper_summaries(refs)}
            Report proposal:
            {state["proposal"]}
            Overall outline:
            {format_outline_summary(state["outline"])}
            {current_report}
            Current Section name:
            {state["section"].heading}
            Current Section description:
            {state["section"].overview}
            User's language:
            {state["language"]}
            User's field:
            {state["field"]}
            User's domain:
            {state["domain"]}
            {user_content}
            {extra_content}
            """


def build_literature_review_section_prompt(headings: list[str]) -> str:
    return f"""Outline:
    {headings}
    Return from 0 to {len(headings)}, base on the order that the literature review section appear in the outline
    If the outline does not contain the literature review section, return 0
    """


def build_proposed_method_section_prompt(headings: list[str]) -> str:
    return f"""Outline:
    {headings}
    Return from 0 to {len(headings)}, base on the order that the research methodology section first appear in the outline
    If the outline does not contain the research methodology section, return 0
    """


def build_result_section_prompt(headings: list[str]) -> str:
    return f"""Outline:
    {headings}
    Return from 0 to {len(headings) - 1}, base on the order that the research methodology section first appear in the outline
    If the outline does not contain the Result section, return 0
    """


def build_file_matching_content(draft_section: str, log_context: str, files_context: str) -> str:
    return f"""

    ---
    {draft_section}
    ---
    {log_context}
    ---
    Available file keys from data analysis:
    {files_context}
    ---

    Match each placeholder description to the most appropriate file key based on the context provided in the logs and draft structure.
    """


def build_comment_expansion_content(
    comment_description: str,
    state: dict,
    current_report: str,
    extra_content: str,
    extra_data: str,
) -> str:
    return f"""
    Outline point to expand:
    {comment_description}

    Research context:
    Report proposal: {state["proposal"]}
    Overall outline: {format_outline_summary(state["outline"])}
    {current_report}
    {extra_content}{extra_data}
    Current Section: {state["section"].heading}
    Section description: {state["section"].overview}
    Current Subsection: {state["subsection"].subheading}
    Subsection description: {state["subsection"].detail_description}
    Word count range: {state["subsection"].subheading_word_count}

    Provided research papers:
    {format_paper_summaries(state["subsection"].refs)}

    Language: {state["language"]}
    Field: {state["field"]}
    Domain: {state["domain"]}
    """


def build_subsection_log_assignment_content(
    state: dict,
    subsection_str: str,
    other_subsections_str: str,
    log_summaries_str: str,
) -> str:
    return f"""
    Section Information:
    Section heading: {state['section'].heading}
    Section description: {state['section'].overview}

    Target Subsection:
    {subsection_str}

    Other subsections in this section (context only, do NOT assign logs for them):
    {other_subsections_str}

    Log Summaries:
    {log_summaries_str}

    Research Context:
    Report proposal: {state.get('proposal', 'Not available')}

    Research field: {state.get('field', 'Not specified')}
    Research domain: {state.get('domain', 'Not specified')}

    Select the appropriate logs for the target subsection based on its description and the log contents.
    """


def build_block_selection_content(state: dict, blocks_summary: str) -> str:
    return f"""
    Section Information:
    Section heading: {state['section'].heading}
    Section description: {state['section'].overview}

    Target Subsection:
    Heading: {state['subsection'].subheading}
    Description: {state['subsection'].detail_description}
    Word count: {state['subsection'].subheading_word_count}

    Content Blocks:
    {blocks_summary}

    Research Context:
    Report proposal: {state.get('proposal', 'Not available')}

    Research field: {state.get('field', 'Not specified')}
    Research domain: {state.get('domain', 'Not specified')}

    Select the content blocks needed to write the target subsection.
    """


def build_block_writing_content(
    state: dict,
    selected_blocks_text: str,
    selected_files_str: str,
    current_report: str,
    extra_content: str,
    extra_data: str,
) -> str:
    return f"""
    Data analysis findings to write from:
    {selected_blocks_text}

    Generated files to include (tables and figures):
    {selected_files_str}

    Provided research papers:
    {format_paper_summaries(state["subsection"].refs)}

    Report proposal:
    {state["proposal"]}

    Overall outline:
    {format_outline_summary(state["outline"])}

    {current_report}

    Current Section name:
    {state["section"].heading}

    Current Section description:
    {state["section"].overview}

    Current Subsection heading:
    {state["subsection"].subheading}

    Current Subsection description:
    {state["subsection"].detail_description}

    Current Subsection word limit:
    {state["subsection"].subheading_word_count}

    User's language:
    {state["language"]}

    User's field:
    {state["field"]}

    User's domain:
    {state["domain"]}
    {extra_content}{extra_data}

    IMPORTANT: For EACH file listed in "Generated files to include", place its file key EXACTLY once on its own line, then immediately follow it with a separate, evidence-grounded interpretation paragraph for that artifact. Do not invent its caption or table/figure number; these are assigned after writing. Do not reformat, rename, or wrap the file key. Never omit a listed file or leave one without its interpretation.
    """


def build_method_log_selection_content(method_log: list[str]) -> str:
    method_logs_text = "\n".join(method_log)
    return f"""{method_logs_text}
    Select 1 or multiple logs from 0 to 4, where 0 the first log
    """


def build_method_write_content(
    state: dict,
    current_report: str,
    detailed_logs: str,
    extra_content: str,
) -> str:
    return f"""
            Provided research papers:
            {format_paper_summaries(state["subsection"].refs)}
            Report proposal:
            {state["proposal"]}
            Overall outline:
            {format_outline_summary(state["outline"])}
            {current_report}
            Current Section name:
            {state["section"].heading}
            Current Section description:
            {state["section"].overview}
            Current Subsection heading:
            {state["subsection"].subheading}
            Current Subsection description:
            {state["subsection"].detail_description}
            Current Subsection word limit:
            {state["subsection"].subheading_word_count}
            User's language:
            {state["language"]}
            User's field:
            {state["field"]}
            User's domain:
            {state["domain"]}
            {detailed_logs}
            {extra_content}
            **IMPORTANT**: If the subsection is about suggesting method for analyzing data, prioritize these following tools:
            - Single Factor Reliability Test
            - Reliability Analysis
            - EFA Analysis
            - ANOVA & T-Test Analysis
            - Regression Analysis
            - Logistic Regression Analysis
            - Clustering Analysis
            - CFA Analysis
            - CB-SEM Analysis
            - PLS-SEM Analysis
            - GSCA Analysis
            - Stationarity Assessment
            - Model Structure Identification
            - Model Estimation & Diagnostics
            - Panel Model Selection
            - Advanced Panel Analysis
            - Overview Charts Analysis
            - EFA - KMO & Bartlett Test
            - EFA - Factor Selection
            - EFA - PCA & Rotation
            - EFA - Loading Analysis
            - EFA - Variance Assessment
            - EFA - Scoring
            """


def get_search_context(search_phase: int) -> str:
    if search_phase == 1:
        return """
        PURPOSES:
            - **Foundation**: Macro context, policies, global trends.
            - **Specific Data**: Real numbers, proof of reality, specific status.
        SEARCH CASES:
            *Purpose Foundation/Macro:*
                - **International Context**: Global trends, reports from WB/IMF/OECD.
                - **National Context**: Government policies, resolutions, decrees, GSO macro reports.

            *Purpose Specific Data/Evidence*
                - **Country Practice**: General reality of the industry in country.
                - **Recent Fluctuations**: Changes/Shocks in last 1-2 years (Tech, Law changes, Crisis).
        """
    if search_phase == 2:
        return """
        PURPOSES:
            - **Comparison**: Benchmarking against others.
            - **Scope & Methodology**: Determine sample size or research boundary.
        SEARCH CASES:
            *Purpose Comparison*
                - **Local/Industry Status**: Specific performance metrics of the study subject (e.g., specific City or Industry growth).

            *Purpose Scope & Methodology*
                - **Object & Scope Definition**: Data used to define the "Universe" or "Population" for the study.
        """
    if search_phase == 3:
        return """
        PURPOSES:
            - **Proposals**: Solutions, future forecast
        SEARCH CASES:
            *Purpose Proposals*
                - **Recommendations**: Future strategies, 2030 visions, academic proposals.
        """
    if search_phase == 4:
        return """
        PURPOSES:
            - **Foundation**: Macro context, policies, global trends.
            - **Specific Data**: Real numbers, proof of reality, specific status.
            - **Comparison**: Benchmarking against others.
            - **Scope & Methodology**: Determine sample size or research boundary.
            - **Proposals**: Solutions, future forecast
        SEARCH CASES:
            *Purpose Foundation/Macro:*
                - **International Context**: Global trends, reports from WB/IMF/OECD.
                - **National Context**: Government policies, resolutions, decrees, GSO macro reports.

            *Purpose Specific Data/Evidence*
                - **Country Practice**: General reality of the industry in country.
                - **Recent Fluctuations**: Changes/Shocks in last 1-2 years (Tech, Law changes, Crisis).

            *Purpose Comparison*
                - **Local/Industry Status**: Specific performance metrics of the study subject (e.g., specific City or Industry growth).

            *Purpose Scope & Methodology*
                - **Object & Scope Definition**: Data used to define the "Universe" or "Population" for the study.

            *Purpose Proposals*
                - **Recommendations**: Future strategies, 2030 visions, academic proposals.
        """
    return ""


def build_search_strategy_content(state: dict, search_context: str) -> str:
    return f"""
    You are an expert Academic Research Assistant. Your task is to analyze a "Subsection" from a thesis outline and determine the optimal Web Search Strategy for the target subsection.

    ### INPUT DATA:
    1. Thesis proposal: {state["proposal"]}
    2. Section: {state["section"].heading} - {state["section"].overview}
    3. Subsection: {state["subsection"].subheading} - {state["subsection"].detail_description}

    ### STEP 1: DECIDE "NEEDS SEARCH?"
    Analyze the description's intent.
    - **NO SEARCH (False)**: If the content is purely theoretical, definitional, or historical knowledge that is static (e.g., "Explain Porter's 5 Forces", "Define Consumer Behavior").
    - **NO SEARCH (False)**: If the subsection is Chapter's Introduction, Chapter's Summary, ...
    - **NEEDS SEARCH (True)**: If the content requires dynamic, up-to-date, or specific real-world evidence, that can classify into the **PURPOSES**
    
    ### STEP 2: DETERMINE "SEARCH PURPOSE" ans "SEARCH CASES (Only if Needs Search = True)
    Classify into ONE of the following:
    {search_context}
    
    ### OUTPUT FORMAT
    Return a JSON object with:
    - needs_search: bool
    - reasoning: str (Explain why based on keywords in description)
    - search_purpose: str (Exact name from list above)
    - search_case: str (Exact name from list above)
    """


def build_websearch_research_context(state: dict, search_obj) -> str:
    return f"""
            ### INPUT CONTEXT:
            1. Thesis proposal: {state["proposal"]}
            2. Section: {state["section"].heading} - {state["section"].overview}
            3. Subsection: {state["subsection"].subheading} - {state["subsection"].detail_description}
            4. Search reasoning: {search_obj.reasoning}
            5. Search purpose: {search_obj.search_purpose}
            5. Search case: {search_obj.search_case}
            """


def build_websearch_content(state: dict) -> str:
    return f"""Get up-to-date information for writing the following subsection of the report
            ### INPUT CONTEXT:
            1. Thesis proposal: {state["proposal"]}
            2. Section: {state["section"].heading} - {state["section"].overview}
            3. Subsection: {state["subsection"].subheading} - {state["subsection"].detail_description}
            """
