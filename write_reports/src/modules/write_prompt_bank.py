seminar_section_writer_instructions = """Write one section of a research report.

<Task>
1. Review the user field, domains, the report proposal (which contains title, proposed method, problem statement, motivation, focused research gap and a web search report about the research gap with up-to-date knowledge), seminar name, section heading, and section description carefully.
2. If present, review any existing section content. 
3. Then, look at the provided knowledge base (including web search result and research papers).
4. Use the provided knowledge base to help you to write a seminar section.
</Task>

<Writing Guidelines>
- If existing section content is not populated, write from scratch
- If existing section content is populated, synthesize it with the source material
- IMPORTANT: Strictly follow word limit, try to aim for the upper bound
- IMPORTANT: Generate in Markdown format, DO NOT GENERATE IN HTML
- Use "##" to indicate section title (## 2.), "###" to indicate subsection title ("### 2.1"), and so on.
- Use the provided heading for main heading, generate subheadings (2.1, 3.4, ...) for clearance if needed
- Do not use abbreviation
- Write strictly in user's language using the Latin alphabet.
</Writing Guidelines>

<Citation Rules>
- Must use all research paper from the provided research papers
- Only cite the provided research papers, do not cite other sources
- Assign each unique research papers a single citation number in your text
- Only use cite in singular (e.g. [1], [2], [3]), do not combine (e.g. [1, 2, 3])
- Return References list that lists cited research paper in order of usage in the content
- Return References list with key `ref`, do not include it in `content`
- Number research papers sequentially without gaps (1,2,3,4...) in the content
- Example format:
  references = [Source Title of [1], Source Title of [2]]
  **Note: Source Title of [1] is the title of the paper related to the content at [1], do not include `[1]` in the final reference list
- Correct citation:
Content: "This is an example of A [1]. This is an example of B [2]."
References list: [Source Title of [1], Source Title of [2]]

Incorrect citation 1: References list has unused citation
Content: "This is an example of A [1]. This is an example of B [2]."
References list: [Source Title of [1], Source Title of [2], [Source Title of [3], Source Title of [4]]]
Unused citation: Source Title of [3], Source Title of [4] -> Correction: References list: [Source Title of [1], Source Title of [2]]

Incorrect citation 3: Combined citation
Content: "This is an example of A. This is an example of B [1, 2]."
Combined cication: [1, 2] -> Correction: "This is an example of A [1]. This is an example of B [2]."

</Citation Rules>

<Final Check>
1. Verify that EVERY claim is grounded in the provided Source material
2. Confirm each URL appears ONLY ONCE in the Source list
3. Verify that sources are numbered sequentially (1,2,3...) without any gaps
</Final Check>
"""

section_grader_instructions = """Review a report section relative to the given topic:
<task>
Evaluate whether the section content adequately addresses the section heading and description.
If pass, return True and comment "N/A", else, return False with 1 comment of the following, you will get a chance to review again so just output 1 comment only.
- Review the knowledge base (including web search result and provided research papers) carefully, if the section content does not adequately address the section topic, description or is missing something, suggest what to do to improved ONLY based on the knowledge base. For example, if the knowledge base talks about using Python, DO NOT suggest to use HTML
- Review the Report section content to see if the writing language is consistant. If the writing language is inconsistant, return False and return comment "Inconsistant language"
- Ignore if the language of the Report section content is different from the instruction and research papers
If both of the checking return False, return False with comment "Inconsistant language"
</task>
"""

section_ref_adding_instructions = """Add references index to a report section:
<task>
The provided content is write based on all the provided research papers but it is missing references (e.g. [1], [2]).
Your task is use all the references and add them to the provided content. 
Return the updated section content and the References list with title only.
Make sure each title appears ONLY ONCE in the References list.
</task>
<Citation Rules>
- **Must use all research paper** from the provided research papers
- Assign each unique research papers a single citation number in your text
- Only use cite in singular (e.g. [1], [2], [3]), do not combine (e.g. [1, 2, 3])
- Return References list that lists the cited research paper in order of usage in the content
- Number research papers sequentially without gaps (1,2,3,4...) in the content
- Example format:
  references = [Source Title of [1], Source Title of [2]]
  **Note: Source Title of [1] is the title of the paper related to the content at [1], do not include `[1]` in the final reference list
- Correct citation:
Content: "This is an example of A [1]. This is an example of B [2]."
References list: [Source Title of [1], Source Title of [2]]

Incorrect citation 1: References list has unused citation
Content: "This is an example of A [1]. This is an example of B [2]."
References list: [Source Title of [1], Source Title of [2], [Source Title of [3], Source Title of [4]]]
Unused citation: Source Title of [3], Source Title of [4] -> Correction: References list: [Source Title of [1], Source Title of [2]]

Incorrect citation 3: Combined citation
Content: "This is an example of A. This is an example of B [1, 2]."
Combined cication: [1, 2] -> Correction: "This is an example of A [1]. This is an example of B [2]."

</Citation Rules>

<Final Check>
1. Verify that EVERY claim is grounded in the provided research papers
2. Confirm each Source Title appears ONLY ONCE in the References list
3. Verify that sources are numbered sequentially (1,2,3...) without any gaps
</Final Check>
"""

section_partial_ref_adding_instructions = """
Add missing references index to a report section that already has partial citations:
<task>
The provided content already includes some references (e.g. [1], [2]), but not all research papers have been cited.
Your task is to **preserve all existing reference indices** and **add new citations** for the missing research papers in relevant places.
Return the updated section content and the complete References list with titles only.
Do not remove or change the existing citation indices.
</task>

<Additional Context>
You will receive:
1. The provided content (which already includes partial citations).
2. The list of all research papers that *should* be referenced.
3. A list of references already cited (from the section content).
You must add citations for the remaining research papers that are not yet cited.
</Additional Context>

<Citation Rules>
- Keep all existing reference indices as they are.
- Assign new citation numbers **after the last existing reference index**.
- Only use singular citations (e.g. [3], [4]) — do not combine multiple citations like [3,4].
- Each research paper title must appear **exactly once** in the References list.
- Return the full References list ordered by citation number with the old list.
- Example:
  Current content: "Method A is effective [1]."
  Missing papers: 2 more papers.
  Output content: "Method A is effective [1]. Recent work also supports this [2]. Another study discusses X [3]."
  References list: [Title of [1], Title of [2], Title of [3]]
</Citation Rules>

<Final Check>
1. Verify all missing research papers have been added as new citations.
2. Confirm that existing citations remain unchanged.
3. Verify that references are numbered sequentially (no gaps or duplicates).
</Final Check>
"""

seminar_references_selection_instructions = """Choose a list of information to write one section for every section of a seminar for a research report of a given proposal.

<Task>
1. Review the user field, domains, the report proposal (which contains title, proposed method, problem statement, motivation, focused research gap and a web search report about the research gap with up-to-date knowledge), seminar name, section heading, and section description carefully.
3. Then, look at the provided research papers.
4. Decide which sources that you will use it to write a seminar section.
5. Use as many of references as possible for each section.
6. Return list of list of title of references research papers for every section
</Task>
"""


section_writer_with_seminar_instructions = """Write one section of a research report.

<Task>
1. You will be given a research report proposal, a seminar report on the topic covering a either literature review, methodology or result and discussion, a report outline with section and and subsection details
1. Review the user field, domains, the report proposal (which contains title, proposed method, problem statement, motivation, focused research gap and a web search report about the research gap with up-to-date knowledge), seminar, section heading, section description, subsection heading, subsection description carefully.
2. If present, review any existing section content. 
3. Then, look at the provided knowledge base (including web search result and research papers).
4. Use the provided knowledge base to help you to write a subsection.
</Task>

<Writing Guidelines>
- If existing subsection content is not populated, write from scratch
- If existing subsection content is populated, synthesize it with the source material
- IMPORTANT: Strictly follow word limit, try to aim for the upper bound
- IMPORTANT: Generate in Markdown format, DO NOT GENERATE IN HTML
- Do not generate any more headings, it has been generated in other taks
- If the subsection description does not related to any content in the seminar, generate normally based on the knowledge base
- Do not use abbreviation
- Write strictly in user's language using the Latin alphabet.
- Start with ### Subsection heading 
</Writing Guidelines>

<Citation Rules>
- Must use all research paper from the provided research papers
- Only cite the provided research papers, do not cite other sources
- Assign each unique research papers a single citation number in your text
- Only use cite in singular (e.g. [1], [2], [3]), do not combine (e.g. [1, 2, 3])
- Return References list that lists cited research paper in order of usage in the content
- Return References list with key `ref`, do not include it in `content`
- Number research papers sequentially without gaps (1,2,3,4...) in the content
- Example format:
  references = [Source Title of [1], Source Title of [2]]
  **Note: Source Title of [1] is the title of the paper related to the content at [1], do not include `[1]` in the final reference list
- Correct citation:
Content: "This is an example of A [1]. This is an example of B [2]."
References list: [Source Title of [1], Source Title of [2]]

Incorrect citation 1: References list has unused citation
Content: "This is an example of A [1]. This is an example of B [2]."
References list: [Source Title of [1], Source Title of [2], [Source Title of [3], Source Title of [4]]]
Unused citation: Source Title of [3], Source Title of [4] -> Correction: References list: [Source Title of [1], Source Title of [2]]

Incorrect citation 3: Combined citation
Content: "This is an example of A. This is an example of B [1, 2]."
Combined cication: [1, 2] -> Correction: "This is an example of A [1]. This is an example of B [2]."

</Citation Rules>

<Final Check>
1. Verify that EVERY claim is grounded in the provided Source material
2. Confirm each URL appears ONLY ONCE in the Source list
3. Verify that sources are numbered sequentially (1,2,3...) without any gaps
</Final Check>
"""

section_writer_without_seminar_instructions = """Write one section of a research report.

<Task>
1. You will be given a research report proposal and a report outline with section and and subsection details
1. Review the user field, domains, the report proposal (which contains title, proposed method, problem statement, motivation, focused research gap and a web search report about the research gap with up-to-date knowledge), section heading, section description, subsection heading, subsection description carefully.
2. If present, review any existing section content. 
3. Then, look at the provided knowledge base (including web search result and research papers).
4. Use the provided knowledge base to help you to write a subsection.
</Task>

<Writing Guidelines>
- If existing subsection content is not populated, write from scratch
- If existing subsection content is populated, synthesize it with the source material
- If other sections of the report are given, ensure the return content is coherence and cohesion with the given sections (tone, linking, ...)
- IMPORTANT: Strictly follow word limit, try to aim for the upper bound
- IMPORTANT: Generate in Markdown format, DO NOT GENERATE IN HTML
- Do not generate any more headings, it has been generated in other taks
- Do not use abbreviation
- Write strictly in user's language using the Latin alphabet. 
- Start with ### Subsection heading 
</Writing Guidelines>

<Citation Rules>
- Must use all research paper from the provided research papers
- If no references is given, DO NOT INPUT ANY REFERENCES OR CITE ANYTHING
- Only cite the provided research papers, do not cite other sources
- Assign each unique research papers a single citation number in your text
- Only use cite in singular (e.g. [1], [2], [3]), do not combine (e.g. [1, 2, 3])
- Return References list that lists cited research paper in order of usage in the content
- Return References list with key `ref`, DO NOT include it in `content`
- Number research papers sequentially without gaps (1,2,3,4...) in the content
- Example format:
  references = [Source Title of [1], Source Title of [2]]
  **Note: Source Title of [1] is the title of the paper related to the content at [1], do not include `[1]` in the final reference list
- Correct citation:
Content: "This is an example of A [1]. This is an example of B [2]."
References list: [Source Title of [1], Source Title of [2]]

Incorrect citation 1: References list has unused citation
Content: "This is an example of A [1]. This is an example of B [2]."
References list: [Source Title of [1], Source Title of [2], [Source Title of [3], Source Title of [4]]]
Unused citation: Source Title of [3], Source Title of [4] -> Correction: References list: [Source Title of [1], Source Title of [2]]

Incorrect citation 3: Combined citation
Content: "This is an example of A. This is an example of B [1, 2]."
Combined cication: [1, 2] -> Correction: "This is an example of A [1]. This is an example of B [2]."

</Citation Rules>

<Final Check>
1. Verify that EVERY claim is grounded in the provided Source material
2. Confirm each URL appears ONLY ONCE in the Source list
3. Verify that sources are numbered sequentially (1,2,3...) without any gaps
</Final Check>
"""

chunk_writer = """Write one chunk of a subsection of a section of a research report.

<Task>
1. You will be given a research report proposal and a report outline with section and and subsection details
1. Review the user field, domains, the report proposal (which contains title, proposed method, problem statement, motivation, focused research gap and a web search report about the research gap with up-to-date knowledge), section heading, section description, subsection heading, subsection description carefully.
2. If present, review any existing section content. 
3. Then, look at the provided knowledge base (including web search result and research papers).
4. Use the provided knowledge base to help you to write a subsection.
</Task>

<Writing Guidelines>
- If existing subsection content is not populated, write from scratch
- If existing subsection content is populated, synthesize it with the source material
- If other sections of the report are given, ensure the return content is coherence and cohesion with the given sections (tone, linking, ...)
- IMPORTANT: Strictly follow word limit, try to aim for the upper bound
- IMPORTANT: Generate in Markdown format, DO NOT GENERATE IN HTML
- Do not generate any more headings, it has been generated in other taks
- Do not use abbreviation
- Write strictly in user's language using the Latin alphabet. 
- Start with ### Subsection heading 
</Writing Guidelines>

<Citation Rules>
- Must use all research paper from the provided research papers
- If no references is given, DO NOT INPUT ANY REFERENCES OR CITE ANYTHING
- Only cite the provided research papers, do not cite other sources
- Assign each unique research papers a single citation number in your text
- Only use cite in singular (e.g. [1], [2], [3]), do not combine (e.g. [1, 2, 3])
- Return References list that lists cited research paper in order of usage in the content
- Return References list with key `ref`, DO NOT include it in `content`
- Number research papers sequentially without gaps (1,2,3,4...) in the content
- Example format:
  references = [Source Title of [1], Source Title of [2]]
  **Note: Source Title of [1] is the title of the paper related to the content at [1], do not include `[1]` in the final reference list
- Correct citation:
Content: "This is an example of A [1]. This is an example of B [2]."
References list: [Source Title of [1], Source Title of [2]]

Incorrect citation 1: References list has unused citation
Content: "This is an example of A [1]. This is an example of B [2]."
References list: [Source Title of [1], Source Title of [2], [Source Title of [3], Source Title of [4]]]
Unused citation: Source Title of [3], Source Title of [4] -> Correction: References list: [Source Title of [1], Source Title of [2]]

Incorrect citation 3: Combined citation
Content: "This is an example of A. This is an example of B [1, 2]."
Combined cication: [1, 2] -> Correction: "This is an example of A [1]. This is an example of B [2]."

</Citation Rules>

<Final Check>
1. Verify that EVERY claim is grounded in the provided Source material
2. Confirm each URL appears ONLY ONCE in the Source list
3. Verify that sources are numbered sequentially (1,2,3...) without any gaps
</Final Check>
"""

research_papers_references_selection_instructions = """Choose a list of information to write one section for every section of a research report of a given proposal.

<Task>
1. Review the user field, domains, the report proposal (which contains title, proposed method, problem statement, motivation, focused research gap and a web search report about the research gap with up-to-date knowledge), section heading, and section description carefully.
3. Then, look at the provided research papers.
4. Decide which sources that you will use it to write the section.
5. Use as many of references as possible for each section.
6. Return list of list of title of references research papers for every section
7. If the section does not need any references, return an empty list for that section
</Task>
"""


research_papers_seminar_references_selection_instructions = """Choose a list of information to write one section for every section of a research report of a given proposal.

<Task>
1. Review the user field, domains, the report proposal (which contains title, proposed method, problem statement, motivation, focused research gap and a web search report about the research gap with up-to-date knowledge), section heading, and section description carefully.
2. Then, look at the provided seminars.
3. You will be given 3 seminar reports: literature review; methodology; result and discussion, denoted as 'CHUYEN_DE_1', 'CHUYEN_DE_2', and 'CHUYEN_DE_3' respectively.
4. Decide which seminars that you will use to write the section.
5. Only use atmost 2 seminars for the section
6. If no seminar is selected for a section, return empty list
7. Return list of list of seminar's denote for every section
For example:
Section description:
[
{
  "heading": "Tóm tắt",
  "word_count": "150-250",
  "overview": "Phần này giới thiệu tổng quan về đề tài nghiên cứu, phương pháp và kết quả.",
},
{
  "heading": "Giới thiệu",
  "word_count": "200-1000",
  "overview": "Phần này giới thiệu tổng quan về đề tài nghiên cứu, lý do chọn đề tài, mục tiêu nghiên cứu, phạm vi, câu hỏi nghiên cứu và ý nghĩa thực tiễn của công trình.",
},
{
  "heading": "Phương pháp nghiên cứu",
  "word_count": "6000-30000",
  "overview": "Phần mô tả chi tiết thiết kế nghiên cứu, phương pháp mẫu, công cụ thu thập và phân tích dữ liệu, cùng phương pháp can thiệp số hóa tích hợp."
},
{ "heading": "Kết luận và kiến nghị",
  "word_count": "1800-9000",
  "overview": "Kết luận tổng quan, tóm tắt đóng góp, hạn chế và đề xuất các hướng nghiên cứu tiếp theo cũng như các kiến nghị ứng dụng."
}
]
Return:
[[], ['CHUYEN_DE_1'], ['CHUYEN_DE_2', 'CHUYEN_DE_3'], ['CHUYEN_DE_3']]
</Task>
"""

batch_prompt = """
You are an expert project manager AI responsible for optimizing complex writing workflows.
Your task is to analyze the list of subsections for a chapter and determine their execution dependencies.

Group consecutive subsections that can be written independently into a single "batch" for parallel execution.
Subsections that depend on the content of previous ones (e.g., summaries, conclusions, or subsections that logically follow another) MUST be in their own separate batch.
For example: 
- "Disadvantages of the Proposed method" section will be depended on "Proposed method" section
- "Research gaps" section will be depended on "Literature Review" section
Analyze the section and subsections descriptions carefully. A subsection like "Tóm tắt chương" (Chapter Summary) almost certainly depends on the content of the subsections that come before it.
Example:
- Input:
{
"heading": "Mở đầu",
"word_count": "562-862",
"overview": "Chương mở đầu làm rõ bối cảnh, lý do và tầm quan trọng của nghiên cứu về mối quan hệ giữa thiên kiến AI và hiệu quả can thiệp giáo dục bền vững trong cộng đồng đa văn hóa. Phân tích vấn đề nghiên cứu, câu hỏi, mục tiêu, phạm vi, phương pháp và ý nghĩa khoa học, thực tiễn của đề tài, đồng thời cung cấp cấu trúc tổng quan cho toàn bộ luận án.",
"subheadings": [
{
"detail_description": "Trình bày mục tiêu chính của chương mở đầu, giới thiệu tổng quan các nội dung và nhấn mạnh vai trò khởi đầu cho nghiên cứu.",
"subheading": "Giới thiệu chương",
"subheading_word_count": "50-100"
},
{
"detail_description": "Mô tả bối cảnh rộng lớn về AI trong giáo dục và các hệ thống xã hội, nhấn mạnh các vấn đề thực tiễn và lý luận liên quan đến thiên kiến AI và sự tác động lên các cộng đồng đa văn hóa. Giải thích lý do chọn đề tài và tầm quan trọng của việc nghiên cứu.",
"subheading": "Bối cảnh và lý do chọn đề tài",
"subheading_word_count": "100-150"
},
{
"detail_description": "Phân tích chi tiết vấn đề nghiên cứu liên quan đến tác động thiên kiến AI lên các cộng đồng thiệt thòi và hiệu quả can thiệp giáo dục bền vững. Trình bày các biểu hiện thực tiễn và khoảng trống nghiên cứu hiện tại.",
"subheading": "Vấn đề nghiên cứu",
"subheading_word_count": "80-120"
},
{
"detail_description": "Trình bày các câu hỏi nghiên cứu chính và nếu có, nêu rõ các giả thuyết khoa học cần kiểm định nhằm làm rõ mối quan hệ nhân quả và các yếu tố ảnh hưởng.",
"subheading": "Câu hỏi nghiên cứu / giả thuyết nghiên cứu",
"subheading_word_count": "80-100"
},
{
"detail_description": "Nêu rõ mục tiêu tổng quát của luận án và các mục tiêu cụ thể tương ứng với các khía cạnh chính của nghiên cứu như đánh giá thiên kiến AI, hiệu quả can thiệp giáo dục và phát triển khung đạo đức AI lấy cộng đồng làm trung tâm.",
"subheading": "Mục tiêu nghiên cứu",
"subheading_word_count": "70-100"
},
{
"detail_description": "Xác định đối tượng nghiên cứu (thiên kiến AI và can thiệp giáo dục trong các cộng đồng đa văn hóa), khách thể nghiên cứu (các nhóm thiệt thòi), cùng phạm vi không gian, thời gian và nội dung giới hạn phù hợp.",
"subheading": "Đối tượng và phạm vi nghiên cứu",
"subheading_word_count": "70-100"
},
{
"detail_description": "Tổng quan ngắn gọn các phương pháp nghiên cứu chính đã áp dụng, nhấn mạnh hướng tiếp cận kết hợp (nghiên cứu hỗn hợp, mô hình SEM, học máy, nghiên cứu hành động tham gia). Chi tiết phương pháp sẽ được trình bày ở chương phương pháp.",
"subheading": "Phương pháp nghiên cứu",
"subheading_word_count": "70-100"
},
{
"detail_description": "Phân tích ý nghĩa khoa học của nghiên cứu trong việc bổ sung kiến thức về thiên kiến AI và giáo dục bền vững, cũng như đóng góp thực tiễn qua phát triển khung đạo đức và cải thiện hiệu quả can thiệp.",
"subheading": "Ý nghĩa khoa học và thực tiễn của đề tài",
"subheading_word_count": "70-100"
},
{
"detail_description": "Tóm tắt cấu trúc các chương trong luận án, giải thích logic trình bày để người đọc hình dung rõ quá trình phát triển nghiên cứu.",
"subheading": "Cấu trúc luận án",
"subheading_word_count": "50-70"
},
{
"detail_description": "Tổng kết các nội dung đã trình bày trong chương mở đầu, tạo cầu nối chuyển tiếp sang chương tổng quan tài liệu.",
"subheading": "Tóm tắt chương",
"subheading_word_count": "50-70"
}
- Output:
[[0, 1, 2, 3, 4, 5, 6, 7], [8], [9]]
Return them in ascending order and no overlap
Example of wrong output:
- [[0, 1, 2, 3, 4, 5, 6, 9], [7], [8]] -> `9` is wrong (not ascending since 9 > 7)
- [[0, 1, 0, 3, 4, 5, 6, 7], [8], [9]] -> `0, 1, 0` is wrong (overlap 0)
"""


analyze_section_selection = """
You are an expert academic research assistant. Your task is to analyze a research paper outline and determine which sections require the presentation of a "data analysis log".

A "data analysis log" refers to the direct output, tables, or figures from statistical analysis software (like SPSS, R, Stata, Python). This includes:
- Descriptive statistics (mean, median, standard deviation, frequency tables).
- Results of inferential tests (t-tests, ANOVA, regression coefficients, p-values, factor loadings, Cronbach's Alpha).
- Any section that presents raw or calculated numbers directly from the dataset.
Sections that requires the data analysis log are Results, Discussion, Recommendation and Conclusion
You will be given a research outline. For each main section in the list, you must decide if it requires a data analysis log.
Return with JSON object with key `need_data`: bool (True if the section need data analysis log, else, False).
"""

analyze_subsection_selection = """
You are an expert academic research assistant. Your task is to analyze a research paper section outline and determine which subsections require the presentation of a "data analysis log".

A "data analysis log" refers to the results from statistical analysis software (like SPSS, R, Stata, Python). This includes:
- Descriptive statistics (mean, median, standard deviation).
- Results of inferential tests (t-tests, ANOVA, regression coefficients, p-values, factor loadings, Cronbach's Alpha).
- Any subsection that presents raw or calculated numbers directly from the dataset.
Subsections that requires the data analysis log are related to Results (for example: Analyze and Evaluate data quality, Discussion)
**IMPORTANT**: DATA DESCRIPTION (data properties, how to collect data, how to analyze data, ...) DOES NOT NEED THE DATA ANALYSIS LOG because they are used as guidance, not to analyze
**Introduction** and **Literature review** do not need the data analysis log because they do not need any calculation
You will be given a target research section outline. For each subsection in the list, you must decide if it requires a data analysis log.
Return with JSON object with key `need_data`: bool (True if the subsection need data analysis log, else, False)
"""

method_subsection_selection = """
You are an expert academic research assistant specializing in research methodology and structure. Your task is to analyze a research paper section outline and classify each subsection into one of two categories: "Theoretical Foundation" or "New Research Contribution".

- **Theoretical Foundation**: This category includes subsections that review, summarize, or synthesize existing knowledge from the literature. This is the "what we already know" part of the research.
  - This includes: Definitions of core concepts, reviews of established theories from various fields (economics, sociology, culture), and summaries of findings from previous empirical studies.
  - Essentially, any content that is abstract, foundational, and drawn from prior scholarly work belongs here.

- **New Research Contribution**: This category includes subsections that present the author's original approach, ideas, and specific plan for the current study. This is the "what I am proposing and how I will investigate it" part.
  - This includes: The specific research model being proposed, the conceptual/theoretical framework *constructed for this study*, the specific hypotheses to be tested, the chosen methodology and research design (e.g., SEM/PLS-SEM design), and the specific variables and measurement scales selected or adapted for this research.

**IMPORTANT DISTINCTION**:
- A general review **OF** existing theories (e.g., "A Review of Economic Theories in Migration") is **Theoretical Foundation**.
- The presentation of a specific framework **FOR** this study that integrates various theories (e.g., "The Proposed Conceptual Framework") is a **New Research Contribution**.
- The description of what previous studies have found is **Theoretical Foundation**.
- The formulation of specific hypotheses for the current study, even if based on previous findings, is a **New Research Contribution**.

You will be given a target research section outline. For each subsection in the outline, you must decide its classification.

Return a JSON object with the key `new_contribution` boolean.
- Set to `True` if the subsection describes the author's original proposed work for THIS specific study. 
- This includes the proposed research model, the conceptual framework constructed for this research, the specific hypotheses to be tested, the research design, and the chosen variables and measurement scales. 
- Set to `False` if the subsection is a review of existing, established knowledge, such as summarizing general theories, defining concepts, or discussing findings from prior literature.
"""


identify_literature_review = """Identify Literature Review section
You are an expert academic research assistant. Your task is to analyze a research paper outline, to identify the "Literature Review" section
The section can have different name, for example: "Literature Review", "Related Work", "Tổng quan tài liệu", "Tổng quan nghiên cứu", ...
Return the order that it appear in the outline, if you can't find it, return 0, as there will be those that does not have the Literature Review section
For example:
- Input: ["Introduction", "Literature Review", "Methodology", "Discussion and Result", "Conclusion"]
- Output: 2

- Input: ["Tóm tắt", "Phần mở đầu", "Tổng quan tài liệu", "Phương pháp nghiên cứu", "Kết quả và Kiến nghị", "Tổng kết"]
- Output: 3

- Input: ["Mở đầu", "Thiết kế nghiên cứu", "Quy trình thu thập và Phân tích dữ liệu", "Kế hoạch triển khai và tiến độ", "Kết cấu bài viết"]
- Output: 0
"""

identify_proposed_method = """Identify Research Methodology section
You are an expert academic research assistant. Your task is to analyze a research paper outline to identify the "Research Methodology" section.

The section can have various names, for example: "Methodology", "Research Methodology", "Methods", "Research Design", "Proposed Method", "Phương pháp nghiên cứu", "Thiết kế nghiên cứu", "Phương pháp luận".

Return the 1-based index of the section as it appears in the outline. If you cannot find a suitable section, return 0.

For example:
- Input: ["Introduction", "Literature Review", "Methodology", "Discussion and Result", "Conclusion"]
- Output: 3

- Input: ["Tóm tắt", "Phần mở đầu", "Tổng quan tài liệu", "Phương pháp nghiên cứu", "Kết quả và Kiến nghị", "Tổng kết"]
- Output: 4

- Input: ["Mở đầu", "Thiết kế nghiên cứu", "Quy trình thu thập và Phân tích dữ liệu", "Kế hoạch triển khai"]
- Output: 2

- Input: ["Introduction", "Literature Review", "Results"]
- Output: 0
"""

identify_results = """Identify the Results/Findings section
You are an expert academic research assistant. Your task is to analyze a research paper outline to identify the section that presents the research **results and findings**.

**Crucial Logic**: The Results section almost always appears **AFTER** the "Methodology" or "Research Design" section and **BEFORE** the final "Conclusion" or "Summary" section. Use this sequence as a primary rule.

1.  **Look for direct names**: First, search for common headings like "Results", "Findings", "Experimental Results", "Kết quả", "Kết quả nghiên cứu".
2.  **Look for combined names**: Also look for sections that combine results with discussion, such as "Results and Discussion", "Findings and Discussion", or "Kết quả và Bàn luận".
3.  **Use structural logic**: If no clear heading is found, identify the chapter that comes **immediately after the 'Methodology' section**. This chapter is almost always the one that presents the results of the methods just described.
4.  **Handle ambiguous headings**: Sometimes, results are presented within a chapter titled "Conclusions" or "Kết luận". You must identify the chapter that follows the methodology and is described as containing **data analysis, statistical tests, presentation of findings, tables, and figures.**

Return the 1-based index of the section as it appears in the outline. If no section fits this description, return 0.

For example:
- Input: ["Introduction", "Methodology", "Results", "Conclusion"]
- Output: 3

- Input: ["Mở đầu", "Phương pháp nghiên cứu", "Kết quả và Bàn luận", "Kết luận"]
- Output: 3

- Input: ["Mở đầu", "Phương pháp nghiên cứu", "Kết luận nghiên cứu"] (Where "Kết luận nghiên cứu" is described as containing data analysis and findings)
- Output: 3

- Input: ["Introduction", "Literature Review", "Methodology"]
- Output: 0
"""

select_detail_logs = """Select corresponding analyze logs for writing result section
You are an expert academic research assistant. Your task is select one or more of the given analyze logs to use as a guidance to write a result section

You will be given a detailed outline, a focused subsection description and a list of analyze logs
Return a list of number represent the order of the chosen log appear in the list, starting from 0 as the first position
For example:
- You are given 5 logs: log 0, log 1, log 2, log 3, log 4
- You choose log 0 and log 3
-> Return {
"chosen_logs": [0, 3]
}
"""

select_methodology_logs = """Select corresponding methodology logs for writing the research design section.

You are an expert academic research assistant. Your task is to select one or more of the given methodology logs to use as guidance to write a specific subsection of the research design/methodology chapter.

A "methodology log" contains the pre-defined components of the proposed research. It describes **what the study will do** and **how it will be done**.

The methodology logs include:
- **final_model** (log 0): The proposed conceptual or theoretical model, often including a diagram and an explanation of the relationships between components.
- **hypotheses** (log 1): A structured list of the specific research hypotheses that will be tested.
- **variables** (log 2): A detailed list of all variables in the study, including their definitions, roles (independent, dependent, etc.), and how they will be measured (their scales).
- **survey_questions** (log 3): The specific questions or items that will be used to measure the variables, forming the survey instrument.
- **questions** (log 4): The list of research questions to guide the research analysis

You will be given a detailed chapter outline (for context), a focused subsection description (your primary target), and a list of methodology logs. Your goal is to read the focused subsection description and determine which log(s) contain the specific information needed to write it.

Return a JSON object with a list of numbers representing the order of the chosen logs as they appear in the input list, starting from 0.
If no log needed, return empty list

For example:
- You are given 4 logs: `final_model` (log 0), `hypotheses` (log 1), `variables` (log 2), `survey_questions` (log 3), `questions` (log 4).
If the focused subsection is "Research Hypotheses and Variables".
- You should choose `hypotheses` (log 1) and `variables` (log 2).
-> Return:
{
  "chosen_logs": [1, 2]
}
If the focused subsection is "Research model".
- You should choose `final_model` (log 0).
-> Return:
{
  "chosen_logs": [0]
}
If the focused subsection is "Chapter Summary" or "Chapter Introduction".
- You should choose none.
-> Return:
{
  "chosen_logs": []
}
"""

methodology_writer = """You are an expert academic research methodology writer. Your task is to generate a professional, well-structured, and clear markdown-formatted methodology subsection based on the provided research proposal and methodology logs.

**Key Responsibilities and Guidelines:**

1.  **Writing Guidelines:**
    - You will be given a research report proposal, a report outline, and details for the specific subsection you need to write.
    - Review all provided materials carefully: the research proposal (title, problem statement, motivation, research gap), the overall outline, and the specific description for your target subsection.
    - If other sections of the report are given, ensure the returned content is coherent and cohesive with them (tone, logical flow, linking phrases).
    - **IMPORTANT**: Strictly follow the specified word limit, aiming for the upper bound.
    - Do not generate any new headings; they are handled in a separate task.
    - Do not use abbreviations unless they are standard in academic writing and defined on first use.
    - Write strictly in the user's language using the Latin alphabet.
    - Start the response directly with `### Subsection heading`.

2.  **Methodology Logs:**
    - Your writing will be based on a set of "methodology logs," which are structured objects defining the research plan. These logs include:
        - `final_model`: The proposed research model, its components, and their relationships (often with a diagram).
        - `hypotheses`: A list of the specific research hypotheses to be tested.
        - `variables`: A detailed list of research variables, including their names, definitions, roles, and measurement scales.
        - `survey_questions`: The specific items or questions used to measure the variables.

3.  **Synthesizing and Justifying Content:**
    - Your main task is to synthesize the information from the provided methodology logs into a coherent academic narrative.
    - **Do not just copy-paste the logs.** You must describe the components logically. For instance, present the research model first, then introduce the hypotheses derived from that model, and finally detail how the variables in the hypotheses will be measured.
    - **Provide Rationale:** Crucially, you must explain the *rationale* for the design choices. Use the research proposal's gap and motivation to justify *why* the proposed model is suitable, *how* the hypotheses logically address the research questions, and *why* the chosen variables and scales are appropriate for the study.

4.  **Variable and Scale Integration:**
    - When describing the model, hypotheses, or measurement instruments, use the `variables` log to provide full details.
    - Refer to variables by their full, descriptive names. Explain their roles (e.g., independent, dependent, mediating) and the type of scale used (e.g., "measured on a 5-point Likert scale from 'Strongly Disagree' to 'Strongly Agree'").
    - Reproduce any specific variable codes accurately if they are present.

Your goal is to transform the structured components from the methodology logs into a polished methodology subsection. This subsection must not only clearly outline the proposed research design but also rigorously justify its components in the context of the overall research objectives and problem statement.

<Citation Rules>
- Must use all research paper from the provided research papers
- If no references is given, DO NOT INPUT ANY REFERENCES OR CITE ANYTHING
- Only cite the provided research papers, do not cite other sources
- Assign each unique research papers a single citation number in your text
- Only use cite in singular (e.g. [1], [2], [3]), do not combine (e.g. [1, 2, 3])
- Return References list that lists cited research paper in order of usage in the content
- Return References list with key `ref`, do not include it in `content`
- Number research papers sequentially without gaps (1,2,3,4...) in the content
- Example format:
  references = [Source Title of [1], Source Title of [2]]
  **Note: Source Title of [1] is the title of the paper related to the content at [1], do not include `[1]` in the final reference list
- Correct citation:
Content: "This is an example of A [1]. This is an example of B [2]."
References list: [Source Title of [1], Source Title of [2]]

Incorrect citation 1: References list has unused citation
Content: "This is an example of A [1]. This is an example of B [2]."
References list: [Source Title of [1], Source Title of [2], [Source Title of [3], Source Title of [4]]]
Unused citation: Source Title of [3], Source Title of [4] -> Correction: References list: [Source Title of [1], Source Title of [2]]

Incorrect citation 3: Combined citation
Content: "This is an example of A. This is an example of B [1, 2]."
Combined cication: [1, 2] -> Correction: "This is an example of A [1]. This is an example of B [2]."

</Citation Rules>

<Final Check>
1. Verify that EVERY claim is grounded in the provided Source material
2. Confirm each URL appears ONLY ONCE in the Source list
3. Verify that sources are numbered sequentially (1,2,3...) without any gaps
</Final Check>
"""

GET_USER_INFO_PROMPT = """
You are an expert academic and industry analyst. Your primary task is to analyze a user's query to identify the main **Field**, the specific **Domain** of interest, and a comprehensive. Your output must be in a structured JSON format.

---

**Definitions:**

*   **Field:** The broad, high-level sector or area of knowledge the user is interested in. This is the general context.
    *   *Examples: "Healthcare", "Finance", "Education", "Environmental Science", "Art & Culture".*
*   **Domain:** The specific subject or area of inquiry within the Field. This is usually the intersection of two or more concepts.
    *   *Examples: "Application of AI in Education", "Use of IoT in Agriculture", "Cybersecurity in Banking".*
Return in JSON format with `field`, `domain` and `subdomains` keys
For example: 
- Input:
user's research brief: "I want to write a report about GRDP growth rate and its effects on Ho Chi Minh city in 2024"
- Output:
{
"field": "Economic",
"domain": "Sustainable development"
}
"""

draft_outline_instructions = """Create a structured draft outline for a data analysis section of a research report.

<Task>
You are writing a research report section that includes data analysis results with tables and figures.
Your task is to create a well-structured outline showing the logical flow of content and where visualizations should be placed.

Output to structure your outline:
- {{comment: description of text content to write}} - Use this for text paragraphs or explanations
- {{table: description of what table to show}} - Use this for data tables
- {{image: description of what image/figure to show}} - Use this for charts, plots, diagrams

The outline should integrate text and visualizations in a logical, professional manner.
</Task>

<Guidelines>
1. Start with an introduction that explains what will be presented
2. Place tables and images at appropriate points to support your narrative
3. Add commentary before and after visualizations to explain their significance
4. End with a conclusion or summary of key findings
5. Follow the subsection description and word count requirements
6. Ensure coherence with other sections if provided
7. Write in the user's specified language
</Guidelines>

<Example Structure>
{{comment: Introduce the correlation analysis and explain its purpose}}
{{table: correlation matrix showing relationships between all variables}}
{{comment: Discuss the key findings from the correlation analysis, highlighting significant relationships}}
{{image: heatmap visualization of the correlation matrix}}
{{comment: Explain implications of the correlation patterns for the research hypotheses}}
{{comment: Transition to regression analysis results}}
{{table: regression coefficients and significance values}}
{{comment: Interpret the regression results and their meaning for the study}}
</Example Structure>

<Citation Rules>
- Cite research papers where appropriate using [1], [2], etc.
- Include citations when discussing theoretical frameworks, prior findings, or methodological choices
- Return a list of cited paper titles in the `ref` field
</Citation Rules>

<Output Format>
Return a structured JSON with:
- `items`: List of DraftItem objects with type ("comment", "table", or "image") and content (description)
- `ref`: List of cited research paper titles
- `original_draft`: The full draft in markdown format with {{type: description}} placeholders
</Output Format>
"""

file_matching_instructions = """
Match placeholder descriptions to actual available files from data analysis.

<Task>
You will receive:
1. A list of placeholder descriptions from a draft outline (what the report needs to include)
2. A list of available file keys from data analysis results (actual files that were generated)

Your task is to match each placeholder description to the most appropriate file key.
Return the best match for each placeholder, or null if no suitable match exists.
</Task>

<Matching Guidelines>
1. Understand semantic similarity - the description and filename don't need to match exactly
   - Example: "correlation table" should match "correlation_matrix.csv"
   - Example: "scatter plot of X vs Y" should match "plots/scatter_x_y.png"
   - Example: "regression results" should match "regression_coefficients.csv"

2. Consider the context:
   - Table descriptions should match .csv files
   - Image descriptions should match .png files
   - Understand statistical terms (e.g., "ANOVA table" matches "anova_results.csv")

3. Return the full file key exactly as provided:
   - File keys may include folder prefixes (e.g., "plots/chart1.png")
   - Always return the full exact key including any prefixes

4. Be conservative:
   - If you're not confident about a match, return null
   - Don't force matches when the description and file seem unrelated

5. Return one match per placeholder:
   - Each placeholder should have exactly one matched_key or null
   - Don't reuse the same file key for multiple placeholders unless they're clearly the same
</Matching Guidelines>

<Examples>
Input placeholder: "correlation matrix showing relationships between variables"
Available files: ["tables/correlation_matrix.csv", "descriptive_stats.csv", "plots/summary_plot.png"]
Best match: "tables/correlation_matrix.csv"

Input placeholder: "bar chart comparing group means"
Available files: ["tables/correlation_matrix.csv", "charts/group_comparison_plot.png", "regression.csv"]
Best match: "charts/group_comparison_plot.png"

Input placeholder: "detailed breakdown of demographic characteristics"
Available files: ["correlation.csv", "test_results.csv"]
Best match: null (no clear match)
</Examples>

<Output Format>
Return a FileMapping object with:
- `mappings`: List of FileMappingItem objects, each containing:
  - `placeholder_description`: The original description
  - `matched_key`: The matched filename or null
</Output Format>
"""

comment_expansion_instructions = """Expand a brief outline point into full academic content for a data analysis section.

<Task>
You will receive:
1. A brief description of what content should be written (the outline point)
2. Context about the research (proposal, outline, section details)
3. Available research papers for citation
4. Other sections of the report for coherence

Your task is to expand the outline point into well-written, detailed academic content.
</Task>

<Writing Guidelines>
1. **Content Development:**
   - Transform the brief outline description into 2-4 well-structured paragraphs
   - Provide detailed explanations, not just surface-level statements
   - Connect the content to the research objectives and hypotheses
   - Ensure logical flow and smooth transitions

2. **Academic Quality:**
   - Use formal academic language appropriate for research reports
   - Support claims with citations from provided research papers
   - Demonstrate critical thinking and analysis, not just description
   - Maintain objectivity and precision

3. **Context Integration:**
   - Align with the overall research proposal and objectives
   - Ensure coherence with other sections if provided
   - Reference previous findings or upcoming sections when appropriate
   - Use terminology consistent with the field and domain

4. **Technical Precision:**
   - When discussing data analysis, be specific about methods and interpretations
   - Explain statistical concepts clearly for the target audience
   - Balance technical detail with readability

5. **Language and Style:**
   - Write in the user's specified language
   - Do not use abbreviations unless standard in academic writing
   - Aim for the upper bound of the specified word count range
   - Use markdown formatting (no HTML)
</Writing Guidelines>

<Citation Rules>
- Cite research papers using [1], [2], [3], etc.
- Only cite provided research papers, not external sources
- Use singular citations only: [1], not [1, 2]
- Return references list with titles only
- Number citations sequentially without gaps
</Citation Rules>

<Example>
Input outline point: "Introduce the correlation analysis and explain its purpose"

Expanded content:
"The correlation analysis serves as a fundamental step in understanding the relationships between the key variables identified in this study. This analytical approach allows researchers to quantify the strength and direction of linear associations, providing crucial insights into potential causal pathways before conducting more advanced statistical tests [1]. In the context of this research, examining correlations is particularly important given the theoretical framework proposed, which suggests multiple interconnected relationships between independent and dependent variables [2].

The Pearson correlation coefficient was selected as the primary measure due to the continuous nature of the variables under investigation. This statistical technique produces values ranging from -1 to +1, where values closer to the extremes indicate stronger relationships, while values near zero suggest weak or negligible associations [3]. The analysis examines all pairwise combinations of variables, creating a comprehensive picture of the data structure and helping to identify potential multicollinearity issues that could affect subsequent regression analyses.

Furthermore, the correlation analysis provides an initial empirical test of the hypothesized relationships outlined in the research model. By examining the significance levels of the correlation coefficients, we can determine whether the observed associations are likely to reflect true population-level relationships or merely chance occurrences in our sample data [4]. This preliminary evidence helps to validate the theoretical foundations of the study and guides the interpretation of more complex analytical results."
</Example>

<Output Format>
Return a SectionContent object with:
- `content`: The expanded markdown text with citations
- `ref`: List of cited research paper titles in order of usage
</Output Format>
"""
seminar_section_writer_instructions = """Write one section of a research report.

<Task>
1. Review the user field, domains, the report proposal (which contains title, proposed method, problem statement, motivation, focused research gap and a web search report about the research gap with up-to-date knowledge), seminar name, section heading, and section description carefully.
2. If present, review any existing section content. 
3. Then, look at the provided knowledge base (including web search result and research papers).
4. Use the provided knowledge base to help you to write a seminar section.
</Task>

<Writing Guidelines>
- If existing section content is not populated, write from scratch
- If existing section content is populated, synthesize it with the source material
- IMPORTANT: Strictly follow word limit, try to aim for the upper bound
- IMPORTANT: Generate in Markdown format, DO NOT GENERATE IN HTML
- Use "##" to indicate section title (## 2.), "###" to indicate subsection title ("### 2.1"), and so on.
- Use the provided heading for main heading, generate subheadings (2.1, 3.4, ...) for clearance if needed
- Do not use abbreviation
- Write strictly in user's language using the Latin alphabet.
</Writing Guidelines>

<Citation Rules>
- Must use all research paper from the provided research papers
- Only cite the provided research papers, do not cite other sources
- Assign each unique research papers a single citation number in your text
- Only use cite in singular (e.g. [1], [2], [3]), do not combine (e.g. [1, 2, 3])
- Return References list that lists cited research paper in order of usage in the content
- Return References list with key `ref`, do not include it in `content`
- Number research papers sequentially without gaps (1,2,3,4...) in the content
- Example format:
  references = [Source Title of [1], Source Title of [2]]
  **Note: Source Title of [1] is the title of the paper related to the content at [1], do not include `[1]` in the final reference list
- Correct citation:
Content: "This is an example of A [1]. This is an example of B [2]."
References list: [Source Title of [1], Source Title of [2]]

Incorrect citation 1: References list has unused citation
Content: "This is an example of A [1]. This is an example of B [2]."
References list: [Source Title of [1], Source Title of [2], [Source Title of [3], Source Title of [4]]]
Unused citation: Source Title of [3], Source Title of [4] -> Correction: References list: [Source Title of [1], Source Title of [2]]

Incorrect citation 3: Combined citation
Content: "This is an example of A. This is an example of B [1, 2]."
Combined cication: [1, 2] -> Correction: "This is an example of A [1]. This is an example of B [2]."

</Citation Rules>

<Final Check>
1. Verify that EVERY claim is grounded in the provided Source material
2. Confirm each URL appears ONLY ONCE in the Source list
3. Verify that sources are numbered sequentially (1,2,3...) without any gaps
</Final Check>
"""

section_grader_instructions = """Review a report section relative to the given topic:
<task>
Evaluate whether the section content adequately addresses the section heading and description.
If pass, return True and comment "N/A", else, return False with 1 comment of the following, you will get a chance to review again so just output 1 comment only.
- Review the knowledge base (including web search result and provided research papers) carefully, if the section content does not adequately address the section topic, description or is missing something, suggest what to do to improved ONLY based on the knowledge base. For example, if the knowledge base talks about using Python, DO NOT suggest to use HTML
- Review the Report section content to see if the writing language is consistant. If the writing language is inconsistant, return False and return comment "Inconsistant language"
- Ignore if the language of the Report section content is different from the instruction and research papers
If both of the checking return False, return False with comment "Inconsistant language"
</task>
"""

section_ref_adding_instructions = """Add references index to a report section:
<task>
The provided content is write based on all the provided research papers but it is missing references (e.g. [1], [2]).
Your task is use all the references and add them to the provided content. 
Return the updated section content and the References list with title only.
Make sure each title appears ONLY ONCE in the References list.
</task>
<Citation Rules>
- **Must use all research paper** from the provided research papers
- Assign each unique research papers a single citation number in your text
- Only use cite in singular (e.g. [1], [2], [3]), do not combine (e.g. [1, 2, 3])
- Return References list that lists the cited research paper in order of usage in the content
- Number research papers sequentially without gaps (1,2,3,4...) in the content
- Example format:
  references = [Source Title of [1], Source Title of [2]]
  **Note: Source Title of [1] is the title of the paper related to the content at [1], do not include `[1]` in the final reference list
- Correct citation:
Content: "This is an example of A [1]. This is an example of B [2]."
References list: [Source Title of [1], Source Title of [2]]

Incorrect citation 1: References list has unused citation
Content: "This is an example of A [1]. This is an example of B [2]."
References list: [Source Title of [1], Source Title of [2], [Source Title of [3], Source Title of [4]]]
Unused citation: Source Title of [3], Source Title of [4] -> Correction: References list: [Source Title of [1], Source Title of [2]]

Incorrect citation 3: Combined citation
Content: "This is an example of A. This is an example of B [1, 2]."
Combined cication: [1, 2] -> Correction: "This is an example of A [1]. This is an example of B [2]."

</Citation Rules>

<Final Check>
1. Verify that EVERY claim is grounded in the provided research papers
2. Confirm each Source Title appears ONLY ONCE in the References list
3. Verify that sources are numbered sequentially (1,2,3...) without any gaps
</Final Check>
"""

section_partial_ref_adding_instructions = """
Add missing references index to a report section that already has partial citations:
<task>
The provided content already includes some references (e.g. [1], [2]), but not all research papers have been cited.
Your task is to **preserve all existing reference indices** and **add new citations** for the missing research papers in relevant places.
Return the updated section content and the complete References list with titles only.
Do not remove or change the existing citation indices.
</task>

<Additional Context>
You will receive:
1. The provided content (which already includes partial citations).
2. The list of all research papers that *should* be referenced.
3. A list of references already cited (from the section content).
You must add citations for the remaining research papers that are not yet cited.
</Additional Context>

<Citation Rules>
- Keep all existing reference indices as they are.
- Assign new citation numbers **after the last existing reference index**.
- Only use singular citations (e.g. [3], [4]) — do not combine multiple citations like [3,4].
- Each research paper title must appear **exactly once** in the References list.
- Return the full References list ordered by citation number with the old list.
- Example:
  Current content: "Method A is effective [1]."
  Missing papers: 2 more papers.
  Output content: "Method A is effective [1]. Recent work also supports this [2]. Another study discusses X [3]."
  References list: [Title of [1], Title of [2], Title of [3]]
</Citation Rules>

<Final Check>
1. Verify all missing research papers have been added as new citations.
2. Confirm that existing citations remain unchanged.
3. Verify that references are numbered sequentially (no gaps or duplicates).
</Final Check>
"""

seminar_references_selection_instructions = """Choose a list of information to write one section for every section of a seminar for a research report of a given proposal.

<Task>
1. Review the user field, domains, the report proposal (which contains title, proposed method, problem statement, motivation, focused research gap and a web search report about the research gap with up-to-date knowledge), seminar name, section heading, and section description carefully.
3. Then, look at the provided research papers.
4. Decide which sources that you will use it to write a seminar section.
5. Use as many of references as possible for each section.
6. Return list of list of title of references research papers for every section
</Task>
"""


section_writer_with_seminar_instructions = """Write one section of a research report.

<Task>
1. You will be given a research report proposal, a seminar report on the topic covering a either literature review, methodology or result and discussion, a report outline with section and and subsection details
1. Review the user field, domains, the report proposal (which contains title, proposed method, problem statement, motivation, focused research gap and a web search report about the research gap with up-to-date knowledge), seminar, section heading, section description, subsection heading, subsection description carefully.
2. If present, review any existing section content. 
3. Then, look at the provided knowledge base (including web search result and research papers).
4. Use the provided knowledge base to help you to write a subsection.
</Task>

<Writing Guidelines>
- If existing subsection content is not populated, write from scratch
- If existing subsection content is populated, synthesize it with the source material
- IMPORTANT: Strictly follow word limit, try to aim for the upper bound
- IMPORTANT: Generate in Markdown format, DO NOT GENERATE IN HTML
- Do not generate any more headings, it has been generated in other taks
- If the subsection description does not related to any content in the seminar, generate normally based on the knowledge base
- Do not use abbreviation
- Write strictly in user's language using the Latin alphabet.
- Start with ### Subsection heading 
</Writing Guidelines>

<Citation Rules>
- Must use all research paper from the provided research papers
- Only cite the provided research papers, do not cite other sources
- Assign each unique research papers a single citation number in your text
- Only use cite in singular (e.g. [1], [2], [3]), do not combine (e.g. [1, 2, 3])
- Return References list that lists cited research paper in order of usage in the content
- Return References list with key `ref`, do not include it in `content`
- Number research papers sequentially without gaps (1,2,3,4...) in the content
- Example format:
  references = [Source Title of [1], Source Title of [2]]
  **Note: Source Title of [1] is the title of the paper related to the content at [1], do not include `[1]` in the final reference list
- Correct citation:
Content: "This is an example of A [1]. This is an example of B [2]."
References list: [Source Title of [1], Source Title of [2]]

Incorrect citation 1: References list has unused citation
Content: "This is an example of A [1]. This is an example of B [2]."
References list: [Source Title of [1], Source Title of [2], [Source Title of [3], Source Title of [4]]]
Unused citation: Source Title of [3], Source Title of [4] -> Correction: References list: [Source Title of [1], Source Title of [2]]

Incorrect citation 3: Combined citation
Content: "This is an example of A. This is an example of B [1, 2]."
Combined cication: [1, 2] -> Correction: "This is an example of A [1]. This is an example of B [2]."

</Citation Rules>

<Final Check>
1. Verify that EVERY claim is grounded in the provided Source material
2. Confirm each URL appears ONLY ONCE in the Source list
3. Verify that sources are numbered sequentially (1,2,3...) without any gaps
</Final Check>
"""

section_writer_without_seminar_instructions = """Write one section of a research report.

<Task>
1. You will be given a research report proposal and a report outline with section and and subsection details
1. Review the user field, domains, the report proposal (which contains title, proposed method, problem statement, motivation, focused research gap and a web search report about the research gap with up-to-date knowledge), section heading, section description, subsection heading, subsection description carefully.
2. If present, review any existing section content. 
3. Then, look at the provided knowledge base (including web search result and research papers).
4. Use the provided knowledge base to help you to write a subsection.
</Task>

<Writing Guidelines>
- If existing subsection content is not populated, write from scratch
- If existing subsection content is populated, synthesize it with the source material
- If other sections of the report are given, ensure the return content is coherence and cohesion with the given sections (tone, linking, ...)
- IMPORTANT: Strictly follow word limit, try to aim for the upper bound
- IMPORTANT: Generate in Markdown format, DO NOT GENERATE IN HTML
- Do not generate any more headings, it has been generated in other taks
- Do not use abbreviation
- Write strictly in user's language using the Latin alphabet. 
- Start with ### Subsection heading 
</Writing Guidelines>

<Citation Rules>
- Must use all research paper from the provided research papers
- If no references is given, DO NOT INPUT ANY REFERENCES OR CITE ANYTHING
- Only cite the provided research papers, do not cite other sources
- Assign each unique research papers a single citation number in your text
- Only use cite in singular (e.g. [1], [2], [3]), do not combine (e.g. [1, 2, 3])
- Return References list that lists cited research paper in order of usage in the content
- Return References list with key `ref`, DO NOT include it in `content`
- Number research papers sequentially without gaps (1,2,3,4...) in the content
- Example format:
  references = [Source Title of [1], Source Title of [2]]
  **Note: Source Title of [1] is the title of the paper related to the content at [1], do not include `[1]` in the final reference list
- Correct citation:
Content: "This is an example of A [1]. This is an example of B [2]."
References list: [Source Title of [1], Source Title of [2]]

Incorrect citation 1: References list has unused citation
Content: "This is an example of A [1]. This is an example of B [2]."
References list: [Source Title of [1], Source Title of [2], [Source Title of [3], Source Title of [4]]]
Unused citation: Source Title of [3], Source Title of [4] -> Correction: References list: [Source Title of [1], Source Title of [2]]

Incorrect citation 3: Combined citation
Content: "This is an example of A. This is an example of B [1, 2]."
Combined cication: [1, 2] -> Correction: "This is an example of A [1]. This is an example of B [2]."

</Citation Rules>

<Final Check>
1. Verify that EVERY claim is grounded in the provided Source material
2. Confirm each URL appears ONLY ONCE in the Source list
3. Verify that sources are numbered sequentially (1,2,3...) without any gaps
</Final Check>
"""

chunk_writer = """Write one chunk of a subsection of a section of a research report.

<Task>
1. You will be given a research report proposal and a report outline with section and and subsection details
1. Review the user field, domains, the report proposal (which contains title, proposed method, problem statement, motivation, focused research gap and a web search report about the research gap with up-to-date knowledge), section heading, section description, subsection heading, subsection description carefully.
2. If present, review any existing section content. 
3. Then, look at the provided knowledge base (including web search result and research papers).
4. Use the provided knowledge base to help you to write a subsection.
</Task>

<Writing Guidelines>
- If existing subsection content is not populated, write from scratch
- If existing subsection content is populated, synthesize it with the source material
- If other sections of the report are given, ensure the return content is coherence and cohesion with the given sections (tone, linking, ...)
- IMPORTANT: Strictly follow word limit, try to aim for the upper bound
- IMPORTANT: Generate in Markdown format, DO NOT GENERATE IN HTML
- Do not generate any more headings, it has been generated in other taks
- Do not use abbreviation
- Write strictly in user's language using the Latin alphabet. 
- Start with ### Subsection heading 
</Writing Guidelines>

<Citation Rules>
- Must use all research paper from the provided research papers
- If no references is given, DO NOT INPUT ANY REFERENCES OR CITE ANYTHING
- Only cite the provided research papers, do not cite other sources
- Assign each unique research papers a single citation number in your text
- Only use cite in singular (e.g. [1], [2], [3]), do not combine (e.g. [1, 2, 3])
- Return References list that lists cited research paper in order of usage in the content
- Return References list with key `ref`, DO NOT include it in `content`
- Number research papers sequentially without gaps (1,2,3,4...) in the content
- Example format:
  references = [Source Title of [1], Source Title of [2]]
  **Note: Source Title of [1] is the title of the paper related to the content at [1], do not include `[1]` in the final reference list
- Correct citation:
Content: "This is an example of A [1]. This is an example of B [2]."
References list: [Source Title of [1], Source Title of [2]]

Incorrect citation 1: References list has unused citation
Content: "This is an example of A [1]. This is an example of B [2]."
References list: [Source Title of [1], Source Title of [2], [Source Title of [3], Source Title of [4]]]
Unused citation: Source Title of [3], Source Title of [4] -> Correction: References list: [Source Title of [1], Source Title of [2]]

Incorrect citation 3: Combined citation
Content: "This is an example of A. This is an example of B [1, 2]."
Combined cication: [1, 2] -> Correction: "This is an example of A [1]. This is an example of B [2]."

</Citation Rules>

<Final Check>
1. Verify that EVERY claim is grounded in the provided Source material
2. Confirm each URL appears ONLY ONCE in the Source list
3. Verify that sources are numbered sequentially (1,2,3...) without any gaps
</Final Check>
"""

research_papers_references_selection_instructions = """Choose a list of information to write one section for every section of a research report of a given proposal.

<Task>
1. Review the user field, domains, the report proposal (which contains title, proposed method, problem statement, motivation, focused research gap and a web search report about the research gap with up-to-date knowledge), section heading, and section description carefully.
3. Then, look at the provided research papers.
4. Decide which sources that you will use it to write the section.
5. Use as many of references as possible for each section.
6. Return list of list of title of references research papers for every section
7. If the section does not need any references, return an empty list for that section
</Task>
"""


research_papers_seminar_references_selection_instructions = """Choose a list of information to write one section for every section of a research report of a given proposal.

<Task>
1. Review the user field, domains, the report proposal (which contains title, proposed method, problem statement, motivation, focused research gap and a web search report about the research gap with up-to-date knowledge), section heading, and section description carefully.
2. Then, look at the provided seminars.
3. You will be given 3 seminar reports: literature review; methodology; result and discussion, denoted as 'CHUYEN_DE_1', 'CHUYEN_DE_2', and 'CHUYEN_DE_3' respectively.
4. Decide which seminars that you will use to write the section.
5. Only use atmost 2 seminars for the section
6. If no seminar is selected for a section, return empty list
7. Return list of list of seminar's denote for every section
For example:
Section description:
[
{
  "heading": "Tóm tắt",
  "word_count": "150-250",
  "overview": "Phần này giới thiệu tổng quan về đề tài nghiên cứu, phương pháp và kết quả.",
},
{
  "heading": "Giới thiệu",
  "word_count": "200-1000",
  "overview": "Phần này giới thiệu tổng quan về đề tài nghiên cứu, lý do chọn đề tài, mục tiêu nghiên cứu, phạm vi, câu hỏi nghiên cứu và ý nghĩa thực tiễn của công trình.",
},
{
  "heading": "Phương pháp nghiên cứu",
  "word_count": "6000-30000",
  "overview": "Phần mô tả chi tiết thiết kế nghiên cứu, phương pháp mẫu, công cụ thu thập và phân tích dữ liệu, cùng phương pháp can thiệp số hóa tích hợp."
},
{ "heading": "Kết luận và kiến nghị",
  "word_count": "1800-9000",
  "overview": "Kết luận tổng quan, tóm tắt đóng góp, hạn chế và đề xuất các hướng nghiên cứu tiếp theo cũng như các kiến nghị ứng dụng."
}
]
Return:
[[], ['CHUYEN_DE_1'], ['CHUYEN_DE_2', 'CHUYEN_DE_3'], ['CHUYEN_DE_3']]
</Task>
"""

batch_prompt = """
You are an expert project manager AI responsible for optimizing complex writing workflows.
Your task is to analyze the list of subsections for a chapter and determine their execution dependencies.

Group consecutive subsections that can be written independently into a single "batch" for parallel execution.
Subsections that depend on the content of previous ones (e.g., summaries, conclusions, or subsections that logically follow another) MUST be in their own separate batch.
For example: 
- "Disadvantages of the Proposed method" section will be depended on "Proposed method" section
- "Research gaps" section will be depended on "Literature Review" section
Analyze the section and subsections descriptions carefully. A subsection like "Tóm tắt chương" (Chapter Summary) almost certainly depends on the content of the subsections that come before it.
Example:
- Input:
{
"heading": "Mở đầu",
"word_count": "562-862",
"overview": "Chương mở đầu làm rõ bối cảnh, lý do và tầm quan trọng của nghiên cứu về mối quan hệ giữa thiên kiến AI và hiệu quả can thiệp giáo dục bền vững trong cộng đồng đa văn hóa. Phân tích vấn đề nghiên cứu, câu hỏi, mục tiêu, phạm vi, phương pháp và ý nghĩa khoa học, thực tiễn của đề tài, đồng thời cung cấp cấu trúc tổng quan cho toàn bộ luận án.",
"subheadings": [
{
"detail_description": "Trình bày mục tiêu chính của chương mở đầu, giới thiệu tổng quan các nội dung và nhấn mạnh vai trò khởi đầu cho nghiên cứu.",
"subheading": "Giới thiệu chương",
"subheading_word_count": "50-100"
},
{
"detail_description": "Mô tả bối cảnh rộng lớn về AI trong giáo dục và các hệ thống xã hội, nhấn mạnh các vấn đề thực tiễn và lý luận liên quan đến thiên kiến AI và sự tác động lên các cộng đồng đa văn hóa. Giải thích lý do chọn đề tài và tầm quan trọng của việc nghiên cứu.",
"subheading": "Bối cảnh và lý do chọn đề tài",
"subheading_word_count": "100-150"
},
{
"detail_description": "Phân tích chi tiết vấn đề nghiên cứu liên quan đến tác động thiên kiến AI lên các cộng đồng thiệt thòi và hiệu quả can thiệp giáo dục bền vững. Trình bày các biểu hiện thực tiễn và khoảng trống nghiên cứu hiện tại.",
"subheading": "Vấn đề nghiên cứu",
"subheading_word_count": "80-120"
},
{
"detail_description": "Trình bày các câu hỏi nghiên cứu chính và nếu có, nêu rõ các giả thuyết khoa học cần kiểm định nhằm làm rõ mối quan hệ nhân quả và các yếu tố ảnh hưởng.",
"subheading": "Câu hỏi nghiên cứu / giả thuyết nghiên cứu",
"subheading_word_count": "80-100"
},
{
"detail_description": "Nêu rõ mục tiêu tổng quát của luận án và các mục tiêu cụ thể tương ứng với các khía cạnh chính của nghiên cứu như đánh giá thiên kiến AI, hiệu quả can thiệp giáo dục và phát triển khung đạo đức AI lấy cộng đồng làm trung tâm.",
"subheading": "Mục tiêu nghiên cứu",
"subheading_word_count": "70-100"
},
{
"detail_description": "Xác định đối tượng nghiên cứu (thiên kiến AI và can thiệp giáo dục trong các cộng đồng đa văn hóa), khách thể nghiên cứu (các nhóm thiệt thòi), cùng phạm vi không gian, thời gian và nội dung giới hạn phù hợp.",
"subheading": "Đối tượng và phạm vi nghiên cứu",
"subheading_word_count": "70-100"
},
{
"detail_description": "Tổng quan ngắn gọn các phương pháp nghiên cứu chính đã áp dụng, nhấn mạnh hướng tiếp cận kết hợp (nghiên cứu hỗn hợp, mô hình SEM, học máy, nghiên cứu hành động tham gia). Chi tiết phương pháp sẽ được trình bày ở chương phương pháp.",
"subheading": "Phương pháp nghiên cứu",
"subheading_word_count": "70-100"
},
{
"detail_description": "Phân tích ý nghĩa khoa học của nghiên cứu trong việc bổ sung kiến thức về thiên kiến AI và giáo dục bền vững, cũng như đóng góp thực tiễn qua phát triển khung đạo đức và cải thiện hiệu quả can thiệp.",
"subheading": "Ý nghĩa khoa học và thực tiễn của đề tài",
"subheading_word_count": "70-100"
},
{
"detail_description": "Tóm tắt cấu trúc các chương trong luận án, giải thích logic trình bày để người đọc hình dung rõ quá trình phát triển nghiên cứu.",
"subheading": "Cấu trúc luận án",
"subheading_word_count": "50-70"
},
{
"detail_description": "Tổng kết các nội dung đã trình bày trong chương mở đầu, tạo cầu nối chuyển tiếp sang chương tổng quan tài liệu.",
"subheading": "Tóm tắt chương",
"subheading_word_count": "50-70"
}
- Output:
[[0, 1, 2, 3, 4, 5, 6, 7], [8], [9]]
Return them in ascending order and no overlap
Example of wrong output:
- [[0, 1, 2, 3, 4, 5, 6, 9], [7], [8]] -> `9` is wrong (not ascending since 9 > 7)
- [[0, 1, 0, 3, 4, 5, 6, 7], [8], [9]] -> `0, 1, 0` is wrong (overlap 0)
"""

analyze_data_writer = """You are an expert data analysis report writer. Your task is to generate a professional, concise, and accurate markdown-formatted report section based on the provided execution logs and variable information. The report should be suitable for a technical audience.

**Key Responsibilities and Guidelines:**

1. **Writing Guidelines:**
  - You will be given a research report proposal and a report outline with section and subsection details,
  - Review the user field, domains, the report proposal (which contains title, proposed method, problem statement, motivation, focused research gap and a web search report about the research gap with up-to-date knowledge), section heading, section description, subsection heading, subsection description carefully.
  - Review the data analyze log, which details step by step execution to analyze the given problem
  - Then, look at the provided knowledge base (including web search result and research papers).
  - Use all the given information to help you to write a subsection.
  - If other sections of the report are given, ensure the return content is coherence and cohesion with the given sections (tone, linking, ...)
  - IMPORTANT: Strictly follow word limit, try to aim for the upper bound
- IMPORTANT: Generate in Markdown format, DO NOT GENERATE IN HTML
  - Do not generate any more headings, it has been generated in other taks
  - Do not use abbreviation
  - Write strictly in user's language using the Latin alphabet.
  - Start with ### Subsection heading

2. **Content from Logs - CRITICAL FILTERING:**
  - **REMOVE ALL technical log metadata** from your writing. Filter out:
    * Log structure markers: "Raw report of log X", "Summary for Plan X", "Execution Logs:", etc.
    * Technical metadata: "Type: AnalysisStepType.TOOL", "Variable Codes:", "Tool:", "Step:", etc.
    * System messages: Debug statements, status messages, procedural logging
    * Section numbering from logs: Any hierarchical numbering like "5.3.6.1", "5.3.6.2", etc.
  - **ONLY extract the actual analytical substance**: findings, results, interpretations, statistical values, and insights
  - Accurately transcribe all important details, including statistical results, interpretations, tool outputs, and specific values (after filtering metadata)
  - Omit any sections or lines explicitly titled or identifiable as "Suggestion" or "Suggestions"
  - **Write as continuous academic prose**, NOT as transcribed logs - treat all content as parts of ONE seamless narrative
  - Summarize highly repetitive, simple action logs if necessary, but preserve all details for logs containing unique findings, results, or file outputs

3. **Variable Integration:**
  - Use the `variable_summary` to provide context by referring to variables' full names, roles, or scales.
  - Reproduce variable codes (e.g., `VAR001`, `Q1_A`) exactly. Improve variable name readability if needed (e.g., "GIỚI TÍNH" to "Giới Tính") without altering their meaning.

4. **Analytical Insights:**
  - You will be given detailed analyze logs that note important key points and findings, use them to guide you to add brief, insightful comments on implications, rationales, consequences, or relationships based on the log content and variable information.
  - Transform raw log content into polished academic writing that reads as if written by a human author, not extracted from logs
  - Write in a coherent, flowing narrative style suitable for academic publication

5. **Tables, statistical decisions, and numerical fidelity:**
  - Every generated table or figure must be introduced and followed by an interpretation paragraph. Never leave an artifact without explaining its result.
  - Do not invent table/figure numbers or captions; the writer assigns captions after generation. Discuss each artifact by its supplied description.
  - For reliability, validity, correlation, regression, ANOVA, t-test, or hypothesis-testing results, state the applicable decision rule, the observed result, and whether the related hypothesis or criterion is supported/not supported. Use only thresholds and decisions present in the analysis logs or proposal; do not invent them.
  - Preserve every reported number exactly as provided in the analysis logs. Do not recalculate, approximate, substitute, or reconcile conflicting values. If the source logs conflict, explicitly report the conflict instead of choosing a value.
  - Use the supplied description for each generated file as its table/figure meaning. Do not invent a title from a different analysis and do not create a second table from the same result.
  - Do not output a manually recreated Markdown/HTML table for a generated file. Place its exact file key once on its own line, then immediately follow it with a separate, evidence-grounded interpretation paragraph for that artifact. State the criterion, observed value, and decision only where the logs provide them. Never omit a listed file or leave its key as the last content in the subsection.

Your goal is to transform raw log data analysis, variable information, and processing steps into a polished report subsection that accurately reflects the analysis findings and key outputs, while completely removing all technical metadata and log structure markers. The final content should read as seamless academic prose that integrates naturally with the subsection description and project proposal.

<Citation Rules>
- Must use all research paper from the provided research papers
- If no references is given, DO NOT INPUT ANY REFERENCES OR CITE ANYTHING
- Only cite the provided research papers, do not cite other sources
- Assign each unique research papers a single citation number in your text
- Only use cite in singular (e.g. [1], [2], [3]), do not combine (e.g. [1, 2, 3])
- Return References list that lists cited research paper in order of usage in the content
- Return References list with key `ref`, do not include it in `content`
- Number research papers sequentially without gaps (1,2,3,4...) in the content
- Example format:
  references = [Source Title of [1], Source Title of [2]]
  **Note: Source Title of [1] is the title of the paper related to the content at [1], do not include `[1]` in the final reference list
- Correct citation:
Content: "This is an example of A [1]. This is an example of B [2]."
References list: [Source Title of [1], Source Title of [2]]

Incorrect citation 1: References list has unused citation
Content: "This is an example of A [1]. This is an example of B [2]."
References list: [Source Title of [1], Source Title of [2], [Source Title of [3], Source Title of [4]]]
Unused citation: Source Title of [3], Source Title of [4] -> Correction: References list: [Source Title of [1], Source Title of [2]]

Incorrect citation 3: Combined citation
Content: "This is an example of A. This is an example of B [1, 2]."
Combined cication: [1, 2] -> Correction: "This is an example of A [1]. This is an example of B [2]."

</Citation Rules>

<Final Check>
1. Verify that EVERY claim is grounded in the provided Source material
2. Confirm each URL appears ONLY ONCE in the Source list
3. Verify that sources are numbered sequentially (1,2,3...) without any gaps
</Final Check>
"""

analyze_section_selection = """
You are an expert academic research assistant. Your task is to analyze a research paper outline and determine which sections require the presentation of a "data analysis log".

A "data analysis log" refers to the direct output, tables, or figures from statistical analysis software (like SPSS, R, Stata, Python). This includes:
- Descriptive statistics (mean, median, standard deviation, frequency tables).
- Results of inferential tests (t-tests, ANOVA, regression coefficients, p-values, factor loadings, Cronbach's Alpha).
- Any section that presents raw or calculated numbers directly from the dataset.
Sections that requires the data analysis log are Results, Discussion, Recommendation and Conclusion
You will be given a research outline. For each main section in the list, you must decide if it requires a data analysis log.
Return with JSON object with key `need_data`: bool (True if the section need data analysis log, else, False).
"""

analyze_subsection_selection = """
You are an expert academic research assistant. Your task is to analyze a research paper section outline and determine which subsections require the presentation of a "data analysis log".

A "data analysis log" refers to the results from statistical analysis software (like SPSS, R, Stata, Python). This includes:
- Descriptive statistics (mean, median, standard deviation).
- Results of inferential tests (t-tests, ANOVA, regression coefficients, p-values, factor loadings, Cronbach's Alpha).
- Any subsection that presents raw or calculated numbers directly from the dataset.
Subsections that requires the data analysis log are related to Results (for example: Analyze and Evaluate data quality, Discussion)
**IMPORTANT**: DATA DESCRIPTION (data properties, how to collect data, how to analyze data, ...) DOES NOT NEED THE DATA ANALYSIS LOG because they are used as guidance, not to analyze
**Introduction** and **Literature review** do not need the data analysis log because they do not need any calculation
You will be given a target research section outline. For each subsection in the list, you must decide if it requires a data analysis log.
Return with JSON object with key `need_data`: bool (True if the subsection need data analysis log, else, False)
"""

method_subsection_selection = """
You are an expert academic research assistant specializing in research methodology and structure. Your task is to analyze a research paper section outline and classify each subsection into one of two categories: "Theoretical Foundation" or "New Research Contribution".

- **Theoretical Foundation**: This category includes subsections that review, summarize, or synthesize existing knowledge from the literature. This is the "what we already know" part of the research.
  - This includes: Definitions of core concepts, reviews of established theories from various fields (economics, sociology, culture), and summaries of findings from previous empirical studies.
  - Essentially, any content that is abstract, foundational, and drawn from prior scholarly work belongs here.

- **New Research Contribution**: This category includes subsections that present the author's original approach, ideas, and specific plan for the current study. This is the "what I am proposing and how I will investigate it" part.
  - This includes: The specific research model being proposed, the conceptual/theoretical framework *constructed for this study*, the specific hypotheses to be tested, the chosen methodology and research design (e.g., SEM/PLS-SEM design), and the specific variables and measurement scales selected or adapted for this research.

**IMPORTANT DISTINCTION**:
- A general review **OF** existing theories (e.g., "A Review of Economic Theories in Migration") is **Theoretical Foundation**.
- The presentation of a specific framework **FOR** this study that integrates various theories (e.g., "The Proposed Conceptual Framework") is a **New Research Contribution**.
- The description of what previous studies have found is **Theoretical Foundation**.
- The formulation of specific hypotheses for the current study, even if based on previous findings, is a **New Research Contribution**.

You will be given a target research section outline. For each subsection in the outline, you must decide its classification.

Return a JSON object with the key `new_contribution` boolean.
- Set to `True` if the subsection describes the author's original proposed work for THIS specific study. 
- This includes the proposed research model, the conceptual framework constructed for this research, the specific hypotheses to be tested, the research design, and the chosen variables and measurement scales. 
- Set to `False` if the subsection is a review of existing, established knowledge, such as summarizing general theories, defining concepts, or discussing findings from prior literature.
"""


identify_literature_review = """Identify Literature Review section
You are an expert academic research assistant. Your task is to analyze a research paper outline, to identify the "Literature Review" section
The section can have different name, for example: "Literature Review", "Related Work", "Tổng quan tài liệu", "Tổng quan nghiên cứu", ...
Return the order that it appear in the outline, if you can't find it, return 0, as there will be those that does not have the Literature Review section
For example:
- Input: ["Introduction", "Literature Review", "Methodology", "Discussion and Result", "Conclusion"]
- Output: 2

- Input: ["Tóm tắt", "Phần mở đầu", "Tổng quan tài liệu", "Phương pháp nghiên cứu", "Kết quả và Kiến nghị", "Tổng kết"]
- Output: 3

- Input: ["Mở đầu", "Thiết kế nghiên cứu", "Quy trình thu thập và Phân tích dữ liệu", "Kế hoạch triển khai và tiến độ", "Kết cấu bài viết"]
- Output: 0
"""

identify_proposed_method = """Identify Research Methodology section
You are an expert academic research assistant. Your task is to analyze a research paper outline to identify the "Research Methodology" section.

The section can have various names, for example: "Methodology", "Research Methodology", "Methods", "Research Design", "Proposed Method", "Phương pháp nghiên cứu", "Thiết kế nghiên cứu", "Phương pháp luận".

Return the 1-based index of the section as it appears in the outline. If you cannot find a suitable section, return 0.

For example:
- Input: ["Introduction", "Literature Review", "Methodology", "Discussion and Result", "Conclusion"]
- Output: 3

- Input: ["Tóm tắt", "Phần mở đầu", "Tổng quan tài liệu", "Phương pháp nghiên cứu", "Kết quả và Kiến nghị", "Tổng kết"]
- Output: 4

- Input: ["Mở đầu", "Thiết kế nghiên cứu", "Quy trình thu thập và Phân tích dữ liệu", "Kế hoạch triển khai"]
- Output: 2

- Input: ["Introduction", "Literature Review", "Results"]
- Output: 0
"""

identify_results = """Identify the Results/Findings section
You are an expert academic research assistant. Your task is to analyze a research paper outline to identify the section that presents the research **results and findings**.

**Crucial Logic**: The Results section almost always appears **AFTER** the "Methodology" or "Research Design" section and **BEFORE** the final "Conclusion" or "Summary" section. Use this sequence as a primary rule.

1.  **Look for direct names**: First, search for common headings like "Results", "Findings", "Experimental Results", "Kết quả", "Kết quả nghiên cứu".
2.  **Look for combined names**: Also look for sections that combine results with discussion, such as "Results and Discussion", "Findings and Discussion", or "Kết quả và Bàn luận".
3.  **Use structural logic**: If no clear heading is found, identify the chapter that comes **immediately after the 'Methodology' section**. This chapter is almost always the one that presents the results of the methods just described.
4.  **Handle ambiguous headings**: Sometimes, results are presented within a chapter titled "Conclusions" or "Kết luận". You must identify the chapter that follows the methodology and is described as containing **data analysis, statistical tests, presentation of findings, tables, and figures.**

Return the 1-based index of the section as it appears in the outline. If no section fits this description, return 0.

For example:
- Input: ["Introduction", "Methodology", "Results", "Conclusion"]
- Output: 3

- Input: ["Mở đầu", "Phương pháp nghiên cứu", "Kết quả và Bàn luận", "Kết luận"]
- Output: 3

- Input: ["Mở đầu", "Phương pháp nghiên cứu", "Kết luận nghiên cứu"] (Where "Kết luận nghiên cứu" is described as containing data analysis and findings)
- Output: 3

- Input: ["Introduction", "Literature Review", "Methodology"]
- Output: 0
"""

select_detail_logs = """Select corresponding analyze logs for writing result section
You are an expert academic research assistant. Your task is select one or more of the given analyze logs to use as a guidance to write a result section

You will be given a detailed outline, a focused subsection description and a list of analyze logs
Return a list of number represent the order of the chosen log appear in the list, starting from 0 as the first position
For example:
- You are given 5 logs: log 0, log 1, log 2, log 3, log 4
- You choose log 0 and log 3
-> Return {
"chosen_logs": [0, 3]
}
"""

assign_logs_to_subsections = """
You are an expert academic research assistant. Your task is to review one full section containing multiple subsections and decide which analysis logs should be used for each subsection. This is a one-time strategic planning step completed before any writing begins.

You will be given:

* The section title and description
* A list of all subsections with their titles and descriptions
* A set of analysis log summaries, each with a log index, a brief description, and a list of generated files
* The overall research proposal and objectives

Your job is to match logs to subsections based strictly on what each subsection actually needs to present.

Follow these principles:

1. First, understand the purpose and content requirements of each subsection.
2. Assign a log only if it provides necessary and relevant analytical support.
3. Logs often contain highly detailed analysis, so use them selectively.
4. If a subsection does not need any log, explicitly assign “no logs. (None)”
5. Detailed analysis subsections may require many or all logs; conceptual or summary subsections may require few or none.
6. The same log may be assigned to multiple subsections if it genuinely supports them.
7. When multiple logs apply, prioritize reliability, robustness, or validation-related logs first.
8. Avoid repetitive reasoning and think strategically about the narrative flow of the full section.
9. You must make a decision for every subsection, in the original order given.

For each subsection, provide:

* The selected log numbers (or “no logs (None)”)
* A brief justification for why those logs apply

Your final output should be a clear, natural-language list of subsections with their assigned logs and short justifications, with no technical formatting, coding language, or schemas.
"""

assign_logs_to_subsection = """
You are an expert academic research assistant. Your task is to review ONE target subsection and decide which analysis logs should be used to write it. This is a strategic planning step completed before any writing begins.

You will be given:

* The section title and description
* The target subsection with its title, description, and word count
* The headings of the other subsections in the same section (for boundary awareness only — do NOT select logs for them)
* A set of analysis log summaries, each with a log index, a brief description, and a list of generated files
* The overall research proposal and objectives

Your job is to match logs to the target subsection based strictly on what it actually needs to present.

Follow these principles:

1. First, understand the purpose and content requirements of the target subsection.
2. Assign a log only if it provides necessary and relevant analytical support for THIS subsection.
3. Logs often contain highly detailed analysis, so use them selectively.
4. If the target subsection does not need any log (e.g., conceptual, introduction, or summary subsections), return an empty list.
5. Detailed analysis subsections may require many or all logs.
6. If a log clearly belongs to one of the OTHER subsections rather than the target, do not assign it to the target.
7. When multiple logs apply, prioritize reliability, robustness, or validation-related logs first.

Return the chosen log indices and a brief justification for why those logs apply.
"""

select_content_blocks = """
You are an expert academic research assistant. Your task is to review content blocks extracted from data analysis logs and choose which blocks should be used to write ONE target subsection.

You will be given:

* The section and target subsection with their titles, descriptions, and word count
* An ordered list of content blocks, each with an index and a preview:
  - text blocks: analytical findings, interpretations, or technical logging from the analysis
  - file blocks: generated tables (.csv) or charts (.png) referenced by their file key

Selection principles:

1. First, understand the purpose and content requirements of the target subsection.
2. CHOOSE text blocks that contain findings, results, statistical values, or interpretations the subsection needs to present.
3. CHOOSE file blocks whose tables or charts provide key evidence supporting the subsection's narrative. Every generated file referenced by the assigned analysis logs belongs to this subsection's evidence; include its file block even if only some text blocks are selected.
4. DO NOT choose blocks that are purely technical metadata, procedural logging, debug output, or redundant repetition of other chosen blocks.
5. DO NOT choose files that are intermediate or irrelevant outputs.
6. Keep the selection proportional to the subsection's word count: a short subsection needs only the most essential blocks.
7. If no block is relevant to the target subsection, return an empty list.

Return the chosen block indices in ascending order and a brief justification.
"""

select_methodology_logs = """Select corresponding methodology logs for writing the research design section.

You are an expert academic research assistant. Your task is to select one or more of the given methodology logs to use as guidance to write a specific subsection of the research design/methodology chapter.

A "methodology log" contains the pre-defined components of the proposed research. It describes **what the study will do** and **how it will be done**.

The methodology logs include:
- **final_model** (log 0): The proposed conceptual or theoretical model, often including a diagram and an explanation of the relationships between components.
- **hypotheses** (log 1): A structured list of the specific research hypotheses that will be tested.
- **variables** (log 2): A detailed list of all variables in the study, including their definitions, roles (independent, dependent, etc.), and how they will be measured (their scales).
- **survey_questions** (log 3): The specific questions or items that will be used to measure the variables, forming the survey instrument.
- **questions** (log 4): The list of research questions to guide the research analysis

You will be given a detailed chapter outline (for context), a focused subsection description (your primary target), and a list of methodology logs. Your goal is to read the focused subsection description and determine which log(s) contain the specific information needed to write it.

Return a JSON object with a list of numbers representing the order of the chosen logs as they appear in the input list, starting from 0.
If no log needed, return empty list

For example:
- You are given 4 logs: `final_model` (log 0), `hypotheses` (log 1), `variables` (log 2), `survey_questions` (log 3), `questions` (log 4).
If the focused subsection is "Research Hypotheses and Variables".
- You should choose `hypotheses` (log 1) and `variables` (log 2).
-> Return:
{
  "chosen_logs": [1, 2]
}
If the focused subsection is "Research model".
- You should choose `final_model` (log 0).
-> Return:
{
  "chosen_logs": [0]
}
If the focused subsection is "Chapter Summary" or "Chapter Introduction".
- You should choose none.
-> Return:
{
  "chosen_logs": []
}
"""

methodology_writer = """You are an expert academic research methodology writer. Your task is to generate a professional, well-structured, and clear markdown-formatted methodology subsection based on the provided research proposal and methodology logs.

**Key Responsibilities and Guidelines:**

1.  **Writing Guidelines:**
    - You will be given a research report proposal, a report outline, and details for the specific subsection you need to write.
    - Review all provided materials carefully: the research proposal (title, problem statement, motivation, research gap), the overall outline, and the specific description for your target subsection.
    - If other sections of the report are given, ensure the returned content is coherent and cohesive with them (tone, logical flow, linking phrases).
    - **IMPORTANT**: Strictly follow the specified word limit, aiming for the upper bound.
    - Do not generate any new headings; they are handled in a separate task.
    - Do not use abbreviations unless they are standard in academic writing and defined on first use.
    - Write strictly in the user's language using the Latin alphabet.
    - Start the response directly with `### Subsection heading`.

2.  **Methodology Logs:**
    - Your writing will be based on a set of "methodology logs," which are structured objects defining the research plan. These logs include:
        - `final_model`: The proposed research model, its components, and their relationships (often with a diagram).
        - `hypotheses`: A list of the specific research hypotheses to be tested.
        - `variables`: A detailed list of research variables, including their names, definitions, roles, and measurement scales.
        - `survey_questions`: The specific items or questions used to measure the variables.

3.  **Synthesizing and Justifying Content:**
    - Your main task is to synthesize the information from the provided methodology logs into a coherent academic narrative.
    - **Do not just copy-paste the logs.** You must describe the components logically. For instance, present the research model first, then introduce the hypotheses derived from that model, and finally detail how the variables in the hypotheses will be measured.
    - **Provide Rationale:** Crucially, you must explain the *rationale* for the design choices. Use the research proposal's gap and motivation to justify *why* the proposed model is suitable, *how* the hypotheses logically address the research questions, and *why* the chosen variables and scales are appropriate for the study.

4.  **Variable and Scale Integration:**
    - When describing the model, hypotheses, or measurement instruments, use the `variables` log to provide full details.
    - Refer to variables by their full, descriptive names. Explain their roles (e.g., independent, dependent, mediating) and the type of scale used (e.g., "measured on a 5-point Likert scale from 'Strongly Disagree' to 'Strongly Agree'").
    - Reproduce any specific variable codes accurately if they are present.

Your goal is to transform the structured components from the methodology logs into a polished methodology subsection. This subsection must not only clearly outline the proposed research design but also rigorously justify its components in the context of the overall research objectives and problem statement.

<Citation Rules>
- Must use all research paper from the provided research papers
- If no references is given, DO NOT INPUT ANY REFERENCES OR CITE ANYTHING
- Only cite the provided research papers, do not cite other sources
- Assign each unique research papers a single citation number in your text
- Only use cite in singular (e.g. [1], [2], [3]), do not combine (e.g. [1, 2, 3])
- Return References list that lists cited research paper in order of usage in the content
- Return References list with key `ref`, do not include it in `content`
- Number research papers sequentially without gaps (1,2,3,4...) in the content
- Example format:
  references = [Source Title of [1], Source Title of [2]]
  **Note: Source Title of [1] is the title of the paper related to the content at [1], do not include `[1]` in the final reference list
- Correct citation:
Content: "This is an example of A [1]. This is an example of B [2]."
References list: [Source Title of [1], Source Title of [2]]

Incorrect citation 1: References list has unused citation
Content: "This is an example of A [1]. This is an example of B [2]."
References list: [Source Title of [1], Source Title of [2], [Source Title of [3], Source Title of [4]]]
Unused citation: Source Title of [3], Source Title of [4] -> Correction: References list: [Source Title of [1], Source Title of [2]]

Incorrect citation 3: Combined citation
Content: "This is an example of A. This is an example of B [1, 2]."
Combined cication: [1, 2] -> Correction: "This is an example of A [1]. This is an example of B [2]."

</Citation Rules>

<Final Check>
1. Verify that EVERY claim is grounded in the provided Source material
2. Confirm each URL appears ONLY ONCE in the Source list
3. Verify that sources are numbered sequentially (1,2,3...) without any gaps
</Final Check>
"""

GET_USER_INFO_PROMPT = """
You are an expert academic and industry analyst. Your primary task is to analyze a user's query to identify the main **Field**, the specific **Domain** of interest, and a comprehensive. Your output must be in a structured JSON format.

---

**Definitions:**

*   **Field:** The broad, high-level sector or area of knowledge the user is interested in. This is the general context.
    *   *Examples: "Healthcare", "Finance", "Education", "Environmental Science", "Art & Culture".*
*   **Domain:** The specific subject or area of inquiry within the Field. This is usually the intersection of two or more concepts.
    *   *Examples: "Application of AI in Education", "Use of IoT in Agriculture", "Cybersecurity in Banking".*
Return in JSON format with `field`, `domain` and `subdomains` keys
For example: 
- Input:
user's research brief: "I want to write a report about GRDP growth rate and its effects on Ho Chi Minh city in 2024"
- Output:
{
"field": "Economic",
"domain": "Sustainable development"
}
"""

draft_outline_instructions = """Create a structured draft outline for a data analysis section of a research report.

<Task>
You are writing a research report section that includes data analysis results with tables and figures.
Your task is to create a well-structured outline showing the logical flow of content and where visualizations should be placed.

Output to structure your outline:
- {{comment: description of text content to write}} - Use this for text paragraphs or explanations
- {{table: description of what table to show}} - Use this for data tables
- {{image: description of what image/figure to show}} - Use this for charts, plots, diagrams

The outline should integrate text and visualizations in a logical, professional manner.
</Task>

<Guidelines>
1. Start with an introduction that explains what will be presented
2. Place tables and images at appropriate points to support your narrative
3. Add commentary before and after visualizations to explain their significance
4. End with a conclusion or summary of key findings
5. Follow the subsection description and word count requirements
6. Ensure coherence with other sections if provided
7. Write in the user's specified language
</Guidelines>

<Example Structure>
{{comment: Introduce the correlation analysis and explain its purpose}}
{{table: correlation matrix showing relationships between all variables}}
{{comment: Discuss the key findings from the correlation analysis, highlighting significant relationships}}
{{image: heatmap visualization of the correlation matrix}}
{{comment: Explain implications of the correlation patterns for the research hypotheses}}
{{comment: Transition to regression analysis results}}
{{table: regression coefficients and significance values}}
{{comment: Interpret the regression results and their meaning for the study}}
</Example Structure>

<Citation Rules>
- Cite research papers where appropriate using [1], [2], etc.
- Include citations when discussing theoretical frameworks, prior findings, or methodological choices
- Return a list of cited paper titles in the `ref` field
</Citation Rules>

<Output Format>
Return a structured JSON with:
- `items`: List of DraftItem objects with type ("comment", "table", or "image") and content (description)
- `ref`: List of cited research paper titles
- `original_draft`: The full draft in markdown format with {{type: description}} placeholders
</Output Format>
"""

file_matching_instructions = """
Match placeholder descriptions to actual available files from data analysis.

<Task>
You will receive:
1. A list of placeholder descriptions from a draft outline (what the report needs to include)
2. A list of available file keys from data analysis results (actual files that were generated)

Your task is to match each placeholder description to the most appropriate file key.
Return the best match for each placeholder, or null if no suitable match exists.
</Task>

<Matching Guidelines>
1. Understand semantic similarity - the description and filename don't need to match exactly
   - Example: "correlation table" should match "correlation_matrix.csv"
   - Example: "scatter plot of X vs Y" should match "plots/scatter_x_y.png"
   - Example: "regression results" should match "regression_coefficients.csv"

2. Consider the context:
   - Table descriptions should match .csv files
   - Image descriptions should match .png files
   - Understand statistical terms (e.g., "ANOVA table" matches "anova_results.csv")

3. Return the full file key exactly as provided:
   - File keys may include folder prefixes (e.g., "plots/chart1.png")
   - Always return the full exact key including any prefixes

4. Be conservative:
   - If you're not confident about a match, return null
   - Don't force matches when the description and file seem unrelated

5. Return one match per placeholder:
   - Each placeholder should have exactly one matched_key or null
   - Don't reuse the same file key for multiple placeholders unless they're clearly the same
</Matching Guidelines>

<Examples>
Input placeholder: "correlation matrix showing relationships between variables"
Available files: ["tables/correlation_matrix.csv", "descriptive_stats.csv", "plots/summary_plot.png"]
Best match: "tables/correlation_matrix.csv"

Input placeholder: "bar chart comparing group means"
Available files: ["tables/correlation_matrix.csv", "charts/group_comparison_plot.png", "regression.csv"]
Best match: "charts/group_comparison_plot.png"

Input placeholder: "detailed breakdown of demographic characteristics"
Available files: ["correlation.csv", "test_results.csv"]
Best match: null (no clear match)
</Examples>

<Output Format>
Return a FileMapping object with:
- `mappings`: List of FileMappingItem objects, each containing:
  - `placeholder_description`: The original description
  - `matched_key`: The matched filename or null
</Output Format>
"""

fusion_writing_instructions = """Create a mapping to transform raw data analysis logs into a continuous academic narrative.

<Task & Input>
Analyze an ordered sequence of content blocks (text or file references) alongside the Research Context. Your goal is to filter out technical noise and synthesize analytical findings into a cohesive report section.

<Critical Filtering>
**STRICTLY REMOVE** all technical metadata, log structure markers (e.g., "5.3.6.1", "Execution Logs"), system messages, debug statements, and variable codes. **Extract ONLY** the actual analytical findings, results, and interpretations.

<Decision Logic>
1. **Text Blocks**:
   - **SKIP**: If the content is purely metadata, procedural logging, redundant, or low-level technical details.
   - **INCLUDE**: If the content contains findings, results, or insights.
   - **WRITING**: For included blocks, write fused, formal academic prose.
     * Transform raw content into a seamless, continuous narrative (do not preserve log structure).
     * Connect findings to research objectives.
     * **Ensure NO technical log syntax remains.**
     * Treat adjacent blocks as parts of a single flowing paragraph or section.

2. **File Blocks**:
   - **SKIP**: If the file is irrelevant, redundant, or an intermediate/temporary output.
   - **INCLUDE**: If the file contains key tables, charts, or visual evidence supporting the narrative.

<Output Requirements>
Return a list of items corresponding exactly to the input order. For each item, indicate whether it should be skipped or included. If a text block is included, provide the rewritten, fused academic text. If a file is included or a block is skipped, the text field should be empty.
"""

fusion_writing_instructions_enhanced = """Create a mapping to transform raw data analysis logs into a continuous academic narrative.

<Task & Input>
Analyze an ordered sequence of content blocks (text or file references) alongside the Research Context. Your goal is to filter out technical noise and synthesize analytical findings into a cohesive report section.

<Critical Filtering>
**STRICTLY REMOVE** all technical metadata, log structure markers, system messages, debug statements, and variable codes. **Extract ONLY** the actual analytical findings, results, and interpretations.

**STATISTICAL MARKERS TO REMOVE:**
- Column names like "Cronbach's Alpha if Item Deleted", "Scale Mean if Item Deleted", "Corrected Item-Total Correlation"
- Code markers like ": ``", "``value``"
- Raw table headers containing diagnostic terminology
- Technical variable codes (e.g., "DN1", "BC2") unless contextually explained
- Statistical output headers like "Scale Variance if Item Deleted", "Squared Multiple Correlation"

**LOG STRUCTURE TO REMOVE:**
- Section markers like "## Raw report of log X", "## AI report of log X"
- Type labels like "**Type:** TOOL", "**Type:** ACTION"
- Execution log headers like "#### Execution Logs:"
- Technical numbering like "5.3.6.1", "Log 1:", "Step 1:"
- Procedural markers and timestamps

<Decision Logic>
1. **Text Blocks**:
   - **SKIP**: If the content is purely metadata, procedural logging, redundant, or low-level technical details.
   - **INCLUDE**: If the content contains findings, results, or insights.
   - **WRITING**: For included blocks, write fused, formal academic prose.
     * Transform raw content into a seamless, continuous narrative (do not preserve log structure).
     * Connect findings to research objectives.
     * **Ensure NO technical log syntax remains.**
     * **CRITICAL: DO NOT use markdown headers (# ## ###) in your written content.** The section structure is already defined.
     * Write in continuous paragraph form, not as separate sections with headers.
     * Treat adjacent blocks as parts of a single flowing narrative.
     * If the raw text is purely technical/diagnostic with no actual findings, SKIP it instead.

2. **File Blocks**:
   - **SKIP**: If the file is irrelevant, redundant, or an intermediate/temporary output.
   - **INCLUDE**: If the file contains key tables, charts, or visual evidence supporting the narrative.

<Output Requirements>
Return a mapping for each content block. For each item:
1. **index**: Set this to exactly match the `index` of the block you are processing.
2. **skip**: True to skip, False to include.
3. **comment**: 
   - For INCLUDED TEXT blocks: Provide rewritten, fused academic text.
   - For FILE blocks or SKIPPED blocks: Leave as an empty string.

**CRITICAL: You must preserve the correct index for every item to ensure the content is correctly mapped back to the report structure.**

"""

comment_expansion_instructions = """Expand a brief outline point into full academic content for a data analysis section.

<Task>
You will receive:
1. A brief description of what content should be written (the outline point)
2. Context about the research (proposal, outline, section details)
3. Available research papers for citation
4. Other sections of the report for coherence

Your task is to expand the outline point into well-written, detailed academic content.
</Task>

<Writing Guidelines>
1. **Content Development:**
   - Transform the brief outline description into 2-4 well-structured paragraphs
   - Provide detailed explanations, not just surface-level statements
   - Connect the content to the research objectives and hypotheses
   - Ensure logical flow and smooth transitions

2. **Academic Quality:**
   - Use formal academic language appropriate for research reports
   - Support claims with citations from provided research papers
   - Demonstrate critical thinking and analysis, not just description
   - Maintain objectivity and precision

3. **Context Integration:**
   - Align with the overall research proposal and objectives
   - Ensure coherence with other sections if provided
   - Reference previous findings or upcoming sections when appropriate
   - Use terminology consistent with the field and domain

4. **Technical Precision:**
   - When discussing data analysis, be specific about methods and interpretations
   - Explain statistical concepts clearly for the target audience
   - Balance technical detail with readability

5. **Language and Style:**
   - Write in the user's specified language
   - Do not use abbreviations unless standard in academic writing
   - Aim for the upper bound of the specified word count range
   - Use markdown formatting (no HTML)
</Writing Guidelines>

<Citation Rules>
- Cite research papers using [1], [2], [3], etc.
- Only cite provided research papers, not external sources
- Use singular citations only: [1], not [1, 2]
- Return references list with titles only
- Number citations sequentially without gaps
</Citation Rules>

<Example>
Input outline point: "Introduce the correlation analysis and explain its purpose"

Expanded content:
"The correlation analysis serves as a fundamental step in understanding the relationships between the key variables identified in this study. This analytical approach allows researchers to quantify the strength and direction of linear associations, providing crucial insights into potential causal pathways before conducting more advanced statistical tests [1]. In the context of this research, examining correlations is particularly important given the theoretical framework proposed, which suggests multiple interconnected relationships between independent and dependent variables [2].

The Pearson correlation coefficient was selected as the primary measure due to the continuous nature of the variables under investigation. This statistical technique produces values ranging from -1 to +1, where values closer to the extremes indicate stronger relationships, while values near zero suggest weak or negligible associations [3]. The analysis examines all pairwise combinations of variables, creating a comprehensive picture of the data structure and helping to identify potential multicollinearity issues that could affect subsequent regression analyses.

Furthermore, the correlation analysis provides an initial empirical test of the hypothesized relationships outlined in the research model. By examining the significance levels of the correlation coefficients, we can determine whether the observed associations are likely to reflect true population-level relationships or merely chance occurrences in our sample data [4]. This preliminary evidence helps to validate the theoretical foundations of the study and guides the interpretation of more complex analytical results."
</Example>

<Output Format>
Return a SectionContent object with:
- `content`: The expanded markdown text with citations
- `ref`: List of cited research paper titles in order of usage
</Output Format>
"""
