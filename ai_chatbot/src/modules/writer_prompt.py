CATEGORIES = """Analyze the user's query and classify into one of these following group
Group 1: User Has a Topic Title
- The user's starting point is a phrase they consider to be a research topic title.
- Example: "The impact of climate change on agricultural production in the Mekong Delta.", "Climate change."
Group 2: User Has an Idea, Not a Topic
- The user's starting point is a thought or a problem, not a title.
- Example: "I want to research the impact of AI.", "I'm interested in the impact of AI on foreign language learning for university students, specifically in Vietnam, and want to compare it with international studies."
Group 3: User Requests Content Generation
- The user gives a direct command to create content.
- Example: "Write me a research paper on the impact of sustainable tourism in Vietnam.", "Write the literature review for this topic."
Group 4: User Requests Revision or Updating of an existant content
- The user has existing text and wants to improve it.
- Example: "I have a research paper, help me improve its logic and citations.", "Update the 2024 data for this paper."
Group 5: None of the above
"""

SUBCATEGORY_1 = """Analyze the user's query and category and classify into one of these following subcategory
User's category: The user's starting point is a phrase they consider to be a research topic title.
Subcategory 1: Well-Formed & Clear Topic
- Example: "The impact of climate change on agricultural production in the Mekong Delta."
- Core User Intent: The user is confident in their topic and is ready to start outlining and planning the research paper.
- Input Characteristics: A full statement containing a clear subject, action/impact, and specific scope (geographic, demographic, or otherwise).
- Distinguishing Factor: This is the only case where the topic is already viable and research-ready. The user is moving from "what" to "how."
Subcategory 2: Vague or Overly Broad Topic
- Example: "Climate change."
- Core User Intent: The user has a general area of interest but has mistaken a broad keyword for a research topic.
- Input Characteristics: A short phrase or a single concept, lacking specific scope or context. It's presented as a title, not as an idea (which distinguishes it from Group 2).
- Distinguishing Factor: The user presents a "title" that is not yet a researchable topic. The chatbot's first job is to help the user narrow it down.
"""

SUBCATEGORY_2 = """Analyze the user's query and category and classify into one of these following subcategory
User's category: The user's starting point is a thought or a problem, not a title.
Subcategory 1: Brief, Undeveloped Idea
- Example: "I want to research the impact of AI."
- Core User Intent: The user has a nascent interest and is looking for help exploring possibilities.
- Input Characteristics: An "I want to..." or "I'm interested in..." statement that is open-ended.
- Distinguishing Factor: This is purely exploratory. Unlike 1.2, the user isn't claiming to have a topic yet. The chatbot's role is to be a brainstorming partner.
Subcategory 2: Detailed, Multi-faceted Idea
- Original Example: "I'm interested in the impact of AI on foreign language learning for university students, specifically in Vietnam, and want to compare it with international studies."
- Core User Intent: The user has thought through multiple components of an idea but hasn't synthesized them into a formal topic.
- Input Characteristics: A longer description connecting several concepts, populations, and contexts.
- Distinguishing Factor: The user provides all the necessary ingredients for a topic, but hasn't written the recipe. The chatbot's job is synthesis.
"""

SUBCATEGORY_3 = """Analyze the user's query and category and classify into one of these following subcategory
User's category: The user gives a direct command to create content.
Subcategory 1: Request to Write a Full Paper
- Original Example: "Write me a research paper on the impact of sustainable tourism in Vietnam."
- Core User Intent: The user wants the chatbot to produce a complete research document.
- Input Characteristics: A direct command ("Write," "Create") for a full-length, complex output.
- Distinguishing Factor: The user is asking the AI to do the work, not to assist them in doing it. The primary response must be to reframe the relationship.
Subcategory 2: Request to Write a Specific Section
- Original Example: "Write the literature review for this topic."
- Core User Intent: The user wants the chatbot to draft a specific, defined part of their paper.
- Input Characteristics: A command to write a component (e.g., "introduction," "literature review," "conclusion").
- Distinguishing Factor: This is a more feasible generative task, but it requires significant context to be done well. The chatbot's job is to gather that context.
"""

SUBCATEGORY_4 = """Analyze the user's query and category and classify into one of these following subcategory
User's category: The user has existing text and wants to improve it.
Subcategory 1: General Editing and Improvement
- Original Example: "I have a research paper, help me improve its logic and citations."
- Core User Intent: The user wants to enhance the quality of their own writing.
- Input Characteristics: A request to "check," "improve," "fix," or "refine" an existing text.
- Distinguishing Factor: The user is providing the source material. The chatbot's task is modification, not creation. The key is to understand the criteria for improvement.
Subcategory 2: Specific Data Update
- Original Example: "Update the 2024 data for this paper."
- Core User Intent: The user needs to refresh outdated information in their document.
- Input Characteristics: A direct request to find and insert new, specific data points (usually numerical).
- Distinguishing Factor: This is a focused, data-driven task. The chatbot acts as a fact-checker and data retriever.
"""

SUBCATEGORY = [SUBCATEGORY_1, SUBCATEGORY_2, SUBCATEGORY_3, SUBCATEGORY_4]

WRITE_REPORT_INFO = """Extract user's information to write a scientific report
Base on the chat history between the user and the assistant, jot down a note contains answer for these information::
1. Research topic: What is the topic that the user want to write about?
2. Main keywords: What are the main keywords in the research topic? (if research topic is given) - Extract only the core subject keywords directly from the research topic itself
3. Supplement keywords: What are the supplement keywords in the research topic? (if research topic is given) Do NOT extract any keywords from context, venue, or format information.
4. Research questions: What are the questions that the user is trying to answer while doing the report?
5. Research type: What is the user research type? (Quantitative, Qualitative, Mix of Quantitative and Qualitative)
6. Scope: What is the user's scope? (A particular application? A specific location? A specific outcome you want to measure?)
7. Word count: How long does the user want the report to be?
8. References style: What type of references style does the user want?

**PARSING RULES**:
- When parsing user's multi-line responses (e.g., "1. answer1\n2. answer2\n3. answer3"), match each numbered answer to the corresponding question that was asked.
- If you are given an existing note, update the existing note with the correct information
- If the user say they want to change a field in general, set that field to its default value
- If the user say they want to change a field to another value, set that field to that value
- If the user say they want to remove or refuse to give information about a field, set it to "N/A" for string, ["N/A"] for list
- ONLY set the field to None when the user has not given any information about it
- If the latest user message introduces a new research topic, discard the previous topic and rebuild the note from the latest topic.
For example:
- Example 1:
Current research topic: "Global warming"
User's query: "I want to change the research topic"
-> Research topic: "" (default value for research topic is "")
- Example 2:
Current research topic: "Global warming"
User's query: "I want to change the research topic to AI in medical field"
-> Research topic: "AI in medical field"
- Example 3 (CRITICAL for supplement_keywords):
User's query: "I would like to write a proposal to present at an international conference on the rise of the digital age."
-> research_topic: "The rise of the digital age"
-> main_keywords: ["digital age", "digital technology"]
-> supplement_keywords: null (because user did not explicitly mention supplement keywords)
NOTE: "international conference" and "presentation" are NOT supplement keywords, they describe the context/venue.
- Example 4 (Explicit refusal for supplement_keywords):
Chat history:
- Assistant: "Can you suggest additional or related keywords to the topic?"
- User: "Not needed" OR "No need" OR "None" OR "Skip"
-> supplement_keywords: ["N/A"] (user explicitly refused, so use placeholder value)

---
Clearly distinguish between missing information and explicit refusal.
If a field was not mentioned or asked about, treat it as missing. Do not infer values. Return only schema-level empty values:
* String fields: null
* List fields: []
* Numeric fields: 0
These mean the information has not been provided yet.

If the assistant asked about a field and the user explicitly refused (e.g., "no", "skip", "not applicable", "not needed", "none"), treat this as intentional absence and use placeholder values:
* String fields: "N/A"
* List fields: ["N/A"]
* word_count: 1500
Only use placeholder values for explicit refusal. Never use them for undisclosed fields.
"""

CLARIFY_REPORT = """You're an writing assistant, your task is to ask user clarify questions for target information, to complete a note of keypoints for later use to write report
The note contains answer for these information:
1. Research topic: What is the topic that the user want to write about?
2. Main keywords: What are the main keywords in the research topic? (if research topic is given)
3. Supplement keywords: What are the supplemental or related keywords for the research topic?
4. Research questions: What are the questions that the user is trying to answer while doing the report?
5. Research type: What is the user research type? (Quantitative, Qualitative, Mix of Quantitative and Qualitative)
6. Scope: What is the user's scope? (A particular application? A specific location? A specific outcome you want to measure?)
7. Word count: How long does the user want the report to be?
8. References style: What type of references style does the user want?
**Your Task:**
-   Analyze the current note and the target information fields that need to be filled.
-   You will be given a specific number of fields that need answers.
-   You must generate exactly that number of questions - one question for each missing field.
-   Do not skip any fields. Do not combine multiple fields into one question.
-   Do not restate the existing note, summary, or current intent.
-   Each question must be numbered clearly and in the user's specified language.
-   Always provide suggestions or examples for each field to help the user answer.
-   If the latest user's message is that they don't know or unsure, help them choose by providing examples.
-   If the user needs guidance, include 2-3 concrete options in the relevant question and ask them to choose one.
-   Return only the numbered questions; do not return a separate summary or introductory paragraph.
When the user does not know or asks for examples, provide concise suggestions in the user's language.
**Your response must be ONLY the questions themselves, nothing else.**
Return in user's language
"""

SUMMARY_NOTE_REPORT = """You're an writing assistant, your task is construct a summary of the given information
You will be given a note, which answers these following question:
1. Research topic: What is the topic that the user want to write about?
2. Main keywords: What are the main keywords in the research topic? (if research topic is given)
3. Supplement keywords: What are the supplemental or related keywords for the research topic?
4. Research questions: What are the questions that the user is trying to answer while doing the report?
5. Research type: What is the user research type? (Quantitative, Qualitative, Mix of Quantitative and Qualitative)
6. Scope: What is the user's scope? (A particular application? A specific location? A specific outcome you want to measure?)
7. Word count: How long does the user want the report to be?
8. References style: What type of references style does the user want?
9. Output document type/template: What kind of document does the user want (for example, master's thesis, essay, or report)?
**IMPORTANT**: If a field is set as "N/A", ignore it as it has been removed
If the output document type/template is provided, include it in the summary. Do not invent one when it is empty.
Beside that, you will also be given a conversation between the user and the assistant about how to write
**Your Task:**
1.  Present the information from the note back to the user in a clear, structured summary (e.g., using a bulleted list).
2.  Confirm that the current plan is ready to use.
3.  Do not ask whether the user wants to write the full report or a section.
4.  End with exactly one clear confirmation instruction in the user's specified language:
    - Vietnamese: "Nếu bạn đồng ý với kế hoạch và muốn bắt đầu viết, hãy bấm OK."
    - English: "If you agree with the plan and want to start writing, click OK."
5.  Do not add another question, another option, or English text when the user's specified language is not English.

**Example Output Structure:**
"[A brief confirmation in the user's language]
*   **Intent:** ...
*   **Topic:** ...
*   **Keywords:** ...
*   **Research Questions:** ...
*   **Methodology:** ...
*   **Scope:** ...
*   **Output type:** ...
*   **Format:** ... words, using ... citation style.

[One confirmation instruction in the user's language]"
"""

SUMMARY_CONFIRMATION = """Analyze the user's feedback about a summary and their plan
You will be given the current plan and the user's feedback
If the user approve the summary/plan, return True
If the user reject the summary/plan or provide new information/corrections to the plan, return False
Return JSON with `summary_status` key
"""

SUMMARY_ACTION = """Select the next action after the assistant has shown the current research plan.
The user's message may be Vietnamese or English. Use the whole conversation and the latest user message.
Return exactly one structured action:
- approve_plan: the user clearly confirms the plan or asks to begin/continue. Do not require the literal word "OK".
- write_section: the user directly asks to write a specific chapter or section.
- change_template: the user changes the requested output document type/template, for example from a master's thesis to an essay. Use this when the research topic and collected fields stay the same. Preserve the collected research information and put the requested type phrase in template_key.
- revise_plan: the user adds, removes, or changes research information, not only the output document type.
Do not ask a question and do not classify by isolated keywords.
"""

OUTLINE_GENERATION = """Generate an outline for a research report
<Task>
1. Review the research's note.
2. If there is an existing outline with feedback, follow them strictly and update the outline accordingly.
3. You must always generate the full updated outline, including ALL sections (both unchanged and revised ones).
4. Do not only show the updated parts; provide the complete, revised structure from start to finish.
5. Generate an outline with headings and their 1-level subheadings.
6. Do not generate "References" as it will be input manually by the user.
7. Ask if the user is satisfied with the full outline and wants to start writing or has any feedback about the outline.
</Task>
Return in user's language
"""

OUTLINE_CONFIRMATION = """Analyze the user's feedback about an outline and determine if they approve it or want to modify it.

**Return True ONLY if the user explicitly approves and wants to proceed:**
- Examples: "yes", "looks good", "perfect", "proceed", "start writing", "approved", "that's fine"

**Return False if the user provides ANY feedback, changes, modifications, or rejections:**
- Examples: "skip chapter X", "remove section Y", "add Z", "change this", "no", "I don't like it"
- Even small modifications like "skip chapters IV and V" means they want to update the outline that remove some chapters

**IMPORTANT:** Any request to modify, skip, add, remove, or change ANY part of the outline should return False.

Return JSON with `outline_status` key (boolean)
"""

CONFIRMATION = """You're an writing assistant bot, your task is to analyze the chat history and the user's answer to see if they wish to move on to writing
If the user want to move on to writing, return True
If the user doesnot want to move on to writing, return False
If the answer is uncertain, return False
Return JSON with `status` key
"""

WRITE_SECTION_INFO = """Extract the user's request and the necessary context to write a specific section of a scientific report.

Based on the chat history between the user and the assistant, identify the key information needed to fulfill the user's command. Your goal is to populate the following fields:

1.  **Research Topic**: What is the overall topic of the report the user is working on?
2.  **Research Questions**: What are the main questions the report aims to answer? This provides context for the section's purpose.
3.  **Scope**: What is the defined scope of the research? This helps set boundaries for the section's content.
4.  **Word Count**: How long should this specific section be? (Note: This may be different from the total report word count).
5.  **User Request**: What is the specific action or task the user wants you to perform? (e.g., "write the introduction", "find sources for the literature review", "draft a conclusion").

**PARSING RULES**:
- When parsing user's multi-line responses (e.g., "1. answer1\n2. answer2\n3. answer3"), match each numbered answer to the corresponding question that was asked.
- If you are given an existing note, update the existing note with the correct information
- If the user say they want to change a field in general, set that field to its default value
- If the user say they want to change a field to another value, set that field to that value
- If the user say they want to remove or refuse to give information about a field, set it to "N/A" for string, ["N/A"] for list
- ONLY set the field to None when the user has not given any information about it
For example:
- Example 1:
Current research topic: "Global warming"
User's query: "I want to change the research topic"
-> Research topic: "" (default value for research topic is "")
- Example 2:
Current research topic: "Global warming"
User's query: "I want to change the research topic to AI in medical field"
-> Research topic: "AI in medical field"
- Example 3 (CRITICAL for supplement_keywords):
User's query: "I would like to write a proposal to present at an international conference on the rise of the digital age."
-> research_topic: "The rise of the digital age"
-> main_keywords: ["digital age", "digital technology"]
-> supplement_keywords: null (because user did not explicitly mention supplement keywords)
NOTE: "international conference" and "presentation" are NOT supplement keywords, they describe the context/venue.
- Example 4:
Chat history:
- Assistant: "Can you suggest the Scope of the topic?"
- User: "Not needed" OR "No need" OR "None" OR "Skip"
-> supplement_keywords: ["N/A"] (user explicitly refused, so use placeholder value)

---
Clearly distinguish between missing information and explicit refusal.
If a field was not mentioned or asked about, treat it as missing. Do not infer values. Return only schema-level empty values:
* String fields: null
* List fields: []
* Numeric fields: 0
These mean the information has not been provided yet.

If the assistant asked about a field and the user explicitly refused (e.g., "no", "skip", "not applicable", "not needed", "none"), treat this as intentional absence and use placeholder values:
* String fields: "N/A"
* List fields: ["N/A"]
* word_count: 1500
Only use placeholder values for explicit refusal. Never use them for undisclosed fields.
"""

CLARIFY_SECTION_INFO = """You are a helpful writing assistant. Your goal is to ask clear follow-up questions to get the information needed to write a specific section of a report.

You will be given the current note and the specific fields that need to be filled.

The note is based on this structure:
1.  **Research Topic**: The overall topic of the report.
2.  **Research Questions**: The main questions the report aims to answer.
3.  **Scope**: The defined scope of the research.
4.  **Word Count**: The desired length for this section.
5.  **User Request**: The specific action the user wants to perform (e.g., "write the introduction").

**Your Task:**
-   Analyze the current note and the target information fields that need to be filled.
-   You will be given a specific number of fields that need answers.
-   You must generate exactly that number of questions - one question for each missing field.
-   Do not skip any fields. Do not combine multiple fields into one question.
-   Before generate the questions, state the user's current intent.
-   Each question must be numbered clearly and in the user's specified language.
-   Always provide suggestions or examples for each field to help the user answer.
-   If the latest user's message is that they don't know or unsure, help them choose by providing examples.
For example:
- Assistant: '"What research questions do you want to answer for topic "Global warming"'?
- User: "I don't know"
-> 'How about "The affect of global warming to water shortage in Africa"?'

**Your response must be ONLY the questions themselves, nothing else.**
"""

CONFIRM_SECTION_PLAN = """You are a writing assistant. Your task is to create a concise summary of the user's request for writing a report section and ask for their final confirmation before you begin writing.

You will be given a completed note that contains the following information:
1.  **Research Topic**: The overall topic of the report.
2.  **Research Questions**: The main questions the report aims to answer.
3.  **Scope**: The defined scope of the research.
4.  **Word Count**: The desired length for this section.
5.  **User Request**: The specific action the user wants you to perform.

**Your Task:**
1.  Present the information from the note back to the user in a clear, structured summary (e.g., using a bulleted list).
2.  Confirm you understand their request.
3.  End your summary with a direct question asking for permission to proceed, such as "Does this plan look correct?" or "Shall I proceed with writing this section for you?"
4.  The entire response must be in the user's specified language.
5.  Remember to state the user's intent (Write a full report - Write a section of a report - Update a section)

**Example Output Structure:**
"Okay, I'm ready to start. Here is my understanding of the task:
*   **Intent** Write a section of a report
*   **Action:** Write the Introduction section.
*   **Topic:** The Impact of Renewable Energy on Global Economies.
*   **Scope:** Focusing on solar and wind power in G20 nations.
*   **Length:** Approximately 500 words.

Does this look correct?"
"""

UPDATE_SECTION_INFO = """Extract the user's revision goal and the original content they want to modify.

Based on the chat history, your goal is to populate the following fields:

1.  **revision_goal**: What is the user's specific instruction for changing the text? (e.g., "check grammar", "make it more academic", "shorten it").
2.  **original_content**: What is the actual text the user has provided for revision?
If you are given an existing note, update the existing note with the correct information
If the user say they want to change a field in general, set that field to its default value
If the user say they want to chagne a field to another value, set that field to that value
For example:
- Example 1:
Current research topic: "Global warming"
User's query: "I want to change the research topic"
-> Research topic: "" (default value for research topic is "")
- Example 2:
Current research topic: "Global warming"
User's query: "I want to change the research topic to AI in medical field"
-> Research topic: "AI in medical field"

---
Clearly distinguish between missing information and explicit refusal.
If a field was not mentioned or asked about, treat it as missing. Do not infer values. Return only schema-level empty values:
* String fields: null
* List fields: []
* Numeric fields: 0
These mean the information has not been provided yet.

If the assistant asked about a field and the user explicitly refused (e.g., "no", "skip", "not applicable", "not needed", "none"), treat this as intentional absence and use placeholder values:
* String fields: "No specification provided"
* List fields: ["Not specified"]
* word_count: 1500
Only use placeholder values for explicit refusal. Never use them for undisclosed fields.

IMPORTANT for supplement_keywords: If user says "not needed", "no need", "none", "skip", etc., you MUST set supplement_keywords to ["Not specified"], NOT to empty list [] or null.
"""

CLARIFY_UPDATE_INFO = """You are a helpful writing assistant. Your goal is to ask clear questions to get the information needed to revise a piece of text.

You will be given the current note and the specific fields that need to be filled.

The note has two parts:
1.  **revision_goal**: The user's instruction.
2.  **original_content**: The user's text.

**Your Task:**
-   If the **original_content** is the target, ask the user to provide their text.
-   If the **revision_goal** is the target, ask the user what they want to do with the text they have already provided.
-   You will be given a specific number of fields that need answers.
-   You must generate exactly that number of questions - one question for each missing field.
-   Do not skip any fields. Do not combine multiple fields into one question.
-   Before generate the questions, state the user's current intent.
-   Each question must be numbered clearly and in the user's specified language.
-   Always provide suggestions or examples for each field to help the user answer.
-   If the latest user's message is that they don't know or unsure, help them choose by providing examples.
For example:
- Assistant: '"What research questions do you want to answer for topic "Global warming"'?
- User: "I don't know"
-> 'How about "The affect of global warming to water shortage in Africa"?'

**Your response must be ONLY the questions themselves.**
"""

CONFIRM_UPDATE_PLAN = """You are a writing assistant. Your task is to summarize the revision plan and ask for the user's final confirmation before you proceed.

You will be given a completed note containing:
1.  **revision_goal**: The user's instruction.
2.  **original_content**: The user's text.

**Your Task:**
1.  State the revision goal clearly.
2.  Include a short snippet of the original text to confirm you have the right content.
3.  End with a direct question asking for permission to proceed.
4.  The entire response must be in the user's specified language.

**Example Output:**
"Okay, I'm ready to begin. Just to confirm, I will **[revision_goal]** the text you provided, which starts with:

'[First 15-20 words of the original_content]...'

Shall I proceed?"
"""

UNDEFINED_CATE = """You are a writing assistant. Your task is to ask the user question that can help the user choose their group from these following groups
Group 1: User Has a Topic Title
- The user's starting point is a phrase they consider to be a research topic title.
- Example: "The impact of climate change on agricultural production in the Mekong Delta.", "Climate change."
Group 2: User Has an Idea, Not a Topic
- The user's starting point is a thought or a problem, not a title.
- Example: "I want to research the impact of AI.", "I'm interested in the impact of AI on foreign language learning for university students, specifically in Vietnam, and want to compare it with international studies."
Group 3: User Requests Content Generation
- The user gives a direct command to create content.
- Example: "Write me a research paper on the impact of sustainable tourism in Vietnam.", "Write the literature review for this topic."
Group 4: User Requests Revision or Updating of an existant content
- The user has existing text and wants to improve it.
- Example: "I have a research paper, help me improve its logic and citations.", "Update the 2024 data for this paper."
**Your response must be ONLY the question itself.**
Response in user's language
"""

WRITER = """Based on all the research conducted, create a comprehensive, well-structured answer to the overall research brief:
<Research Brief>
{research_brief}
</Research Brief>

For more context, here is all of the messages so far. Focus on the research brief above, but consider these messages as well for more context.
<Messages>
{messages}
</Messages>
CRITICAL: Make sure the answer is written in the same language as the human messages!
For example, if the user's messages are in English, then MAKE SURE you write your response in English. If the user's messages are in Chinese, then MAKE SURE you write your entire response in Chinese.
This is critical. The user will only understand the answer if it is written in the same language as their input message.

Please create a detailed answer to the overall research brief that:
1. Is well-organized with proper headings (# for title, ## for sections, ### for subsections)
2. Includes specific facts and insights from the research
3. Provides a balanced, thorough analysis. Be as comprehensive as possible, and include all information that is relevant to the overall research question. People are using you for deep research and will expect detailed, comprehensive answers.
4. Includes a "References" section at the end with all referenced links

You can structure your report in a number of different ways. Here are some examples:

To answer a question that asks you to compare two things, you might structure your report like this:
1/ intro
2/ overview of topic A
3/ overview of topic B
4/ comparison between A and B
5/ conclusion

To answer a question that asks you to return a list of things, you might only need a single section which is the entire list.
1/ list of things or table of things
Or, you could choose to make each item in the list a separate section in the report. When asked for lists, you don't need an introduction or conclusion.
1/ item 1
2/ item 2
3/ item 3

To answer a question that asks you to summarize a topic, give a report, or give an overview, you might structure your report like this:
1/ overview of topic
2/ concept 1
3/ concept 2
4/ concept 3
5/ conclusion

If you think you can answer the question with a single section, you can do that too!
1/ answer

REMEMBER: Section is a VERY fluid and loose concept. You can structure your report however you think is best, including in ways that are not listed above!
Make sure that your sections are cohesive, and make sense for the reader. If an OUTLINE is GIVEN, follow that OUTLINE

For each section of the report, do the following:
- Use simple, clear language
- Use ## for section title (Markdown format) for each section of the report
- Do NOT ever refer to yourself as the writer of the report. This should be a professional report without any self-referential language. 
- Do not say what you are doing in the report. Just write the report without any commentary from yourself.
- Each section should be as long as necessary to deeply answer the question with the information you have gathered. It is expected that sections will be fairly long and verbose. You are writing a deep research report, and users will expect a thorough answer.
- Use bullet points to list out information when appropriate, but by default, write in paragraph form.

REMEMBER:
The brief and research may be in English, but you need to translate this information to the right language when writing the final answer.
Make sure the final answer report is in the SAME language as the human messages in the message history.

Format the report in clear markdown with proper structure and include source references where appropriate.

IMPORTANT:
If word limit is mentioned, strictly follow word limit

<Citation Rules>
- Assign each unique URL a single citation number in your text
- End with ### Sources that lists each source with corresponding numbers
- IMPORTANT: Number sources sequentially without gaps (1,2,3,4...) in the final list regardless of which sources you choose
- Each source should be a separate line item in a list, so that in markdown it is rendered as a list.
- Citations are extremely important. Make sure to include these, and pay a lot of attention to getting these right. Users will often use these citations to look into more information.
</Citation Rules>
"""
 
CATEGORIES_2 = """Analyze the user's query and classify into one of these following group
Group 1: User want to write a full report
- The user's starting point is a phrase they consider to be a research topic title.
+ Example: "The impact of climate change on agricultural production in the Mekong Delta.", "Climate change."
- The user's starting point is a thought or a problem, not a title.
+ Example: "I want to research the impact of AI.", "I'm interested in the impact of AI on foreign language learning for university students, specifically in Vietnam, and want to compare it with international studies."
- The user directly requests to Write a Full Paper
+ Example: "Write me a research paper on the impact of sustainable tourism in Vietnam."
+ Example: "Write me a Capstone report"
Group 2: User want to write a section of a report
- The user gives a direct command to create content for a topic/report. Unless the user specifically mention a section, it is group 1, not group 2 
+ Example: "Write the literature review for this topic."
Group 3: User Requests Revision or Updating of an existant content
- The user has existing text and wants to improve it.
- Example: "I have a research paper, help me improve its logic and citations.", "Update the 2024 data for this paper."
Group 4: None of the above
- Example: "Hello", "Alo", "How do you do?"
Answer from 1 to 4
"""

UNDEFINED_CATE_2 = """You are a writing assistant. Your task is to ask the user question that can help the user choose their group from these following groups
Group 1: User want to write a full report
- The user's starting point is a phrase they consider to be a research topic title.
+ Example: "The impact of climate change on agricultural production in the Mekong Delta.", "Climate change."
- The user's starting point is a thought or a problem, not a title.
+ Example: "I want to research the impact of AI.", "I'm interested in the impact of AI on foreign language learning for university students, specifically in Vietnam, and want to compare it with international studies."
- The user directly requests to Write a Full Paper
+ Example: "Write me a research paper on the impact of sustainable tourism in Vietnam."
Group 2: User want to write a section of a report
- The user gives a direct command to create content for a topic/report.
+ Example: "Write the literature review for this topic."
Group 3: User Requests Revision or Updating of an existant content
- The user has existing text and wants to improve it.
- Example: "I have a research paper, help me improve its logic and citations.", "Update the 2024 data for this paper."
Group 4: None of the above
- Example: "Hello", "Alo", "How do you do?"
**Your response must be ONLY the question itself.**
Be specific, ask whether write a report, write a section or update a section
Response in user's language
"""

CATEGORY_1 = "Intent 1: User want to write a full report"

CATEGORY_2 = "Intent 2: User want to write a section of a report"

CATEGORY_3 = "Intent 3: User Requests Revision or Updating of an existant content"

CATEGORY = [CATEGORY_1, CATEGORY_2, CATEGORY_3]

CHECK_INTENT = """Analyze the user's query and the chat history to see if they want to change their writing intent
Intent 1: User want to write a full report
Intent 2: User want to write a section of a report
Intent 3: User Requests Revision or Updating of an existant content

Your task is to classify the latest user message while the assistant is collecting missing report information.
Return `message_type` as one of:
- `field_answer`: the user is answering or refining the requested report fields.
- `new_topic`: the user introduces a different research topic but still wants to write a report.
- `off_topic`: the user is chatting about something unrelated to the report and is not answering the requested fields.

Also return `change_intent` and `new_intent` for a real switch between full report, section writing, and revision.
Response in JSON schema with `change_intent` boolean, `new_intent` integer from 0 to 3, and `message_type`.
If the user's query is answer the latest question in the chat history, set `change_intent` to False and `new_intent` to 0 
If you're not sure, answer "No", set `change_intent` to False and `new_intent` to 0 
Use `message_type=field_answer` when uncertain between a field answer and a new topic; use `off_topic` only when the message is clearly unrelated.
** IMPORTANT ** There are 2 things you need to differentiate: change intent vs change idea
Example 1:
Chat history: 
- User: "I want to write a report about AI"
- Assistant: "Sure, what topic do you want to cover in AI?"
User's query: "I want to update a literature review section in my report"
-> Yes (user intent was to write a full report but change into update/revise)
-> {
"change_intent": True,
"new_intent": 3
}
Example 2:
Chat history: 
- User: "I want to write a report about AI"
- Assistant: "Sure, what topic do you want to cover in AI?"
User's query: "I want to write about AI in medical field"
-> No (user intent remain the same - write a full report)
-> {
"change_intent": False,
"new_intent": 0
}
Example 3:
Chat history: 
- User: "I want to write a report about AI"
- Assistant: "Sure, what topic do you want to cover in AI?"
User's query: "I want to write about biology"
-> No (user intent remain the same, only change idea - write a full report)
-> {
"change_intent": False,
"new_intent": 0
}
Example 4:
Chat history: 
- User: "I want to write a result section for my annual finance report"
- Assistant: "Sure, how many words do you want for that section?"
User's query: "I want to write a conclusion section for my annual finance report"
-> No (user intent remain the same, only change idea - write a section of a report)
-> {
"change_intent": False,
"new_intent": 0
}
"""

CLARIFY_INTENT = """You are a helpful writing assistant. Your goal is to ask a single, clear question to get the user's confirmation about changing intent
Intent 1: User want to write a full report
- The user's starting point is a phrase they consider to be a research topic title.
+ Example: "The impact of climate change on agricultural production in the Mekong Delta.", "Climate change."
- The user's starting point is a thought or a problem, not a title.
+ Example: "I want to research the impact of AI.", "I'm interested in the impact of AI on foreign language learning for university students, specifically in Vietnam, and want to compare it with international studies."
- The user directly requests to Write a Full Paper
+ Example: "Write me a research paper on the impact of sustainable tourism in Vietnam."
+ Example: "Write me a Capstone report"
Intent 2: User want to write a section of a report
- The user gives a direct command to create content for a topic/report. Unless the user specifically mention a section, it is group 1, not group 2 
+ Example: "Write the literature review for this topic."
Intent 3: User Requests Revision or Updating of an existant content
- The user has existing text and wants to improve it.
- Example: "I have a research paper, help me improve its logic and citations.", "Update the 2024 data for this paper."
Generate response in user's language
**Your response must be ONLY the question itself, nothing else.**
"""

INTENT_CONFIRMATION = """Analyze the user's feedback about a changing intent
If the user confirm they want to change their intent, return True
If the user deny they want to change their intent, return False
If you're not sure, return False
Return JSON with `intent_status` key
"""

transform_messages_into_research_topic_prompt = """You will be given a set of messages and a summary that have been exchanged so far between yourself and the user. 
Your job is to translate these messages into a more detailed and concrete research question that will be used to guide the research.

The messages that have been exchanged so far between yourself and the user are:
<Messages>
{messages}
</Messages>

You will return a single research question that will be used to guide the research.

Guidelines:
1. Maximize Specificity and Detail
- Include all known user preferences and explicitly list key attributes or dimensions to consider.
- It is important that all details from the user are included in the instructions.

2. Handle Unstated Dimensions Carefully
- When research quality requires considering additional dimensions that the user hasn't specified, acknowledge them as open considerations rather than assumed preferences.
- Example: Instead of assuming "budget-friendly options," say "consider all price ranges unless cost constraints are specified."
- Only mention dimensions that are genuinely necessary for comprehensive research in that domain.

3. Avoid Unwarranted Assumptions
- Never invent specific user preferences, constraints, or requirements that weren't stated.
- If the user hasn't provided a particular detail, explicitly note this lack of specification.
- Guide the researcher to treat unspecified aspects as flexible rather than making assumptions.

4. Distinguish Between Research Scope and User Preferences
- Research scope: What topics/dimensions should be investigated (can be broader than user's explicit mentions)
- User preferences: Specific constraints, requirements, or preferences (must only include what user stated)
- Example: "Research coffee quality factors (including bean sourcing, roasting methods, brewing techniques) for San Francisco coffee shops, with primary focus on taste as specified by the user."

5. Use the First Person
- Phrase the request from the perspective of the user.

6. Sources
- For academic or scientific queries, prefer linking directly to the original paper or official journal publication rather than survey papers or secondary summaries.
- If the query is in a specific language, prioritize sources published in that language.
"""

lead_researcher_prompt = """You are a research supervisor. Your job is to conduct research by calling the "ConductResearch" tool. For context, today's date is {date}.

<Task>
Your focus is to call the "ConductResearch" tool to conduct research against the overall research question passed in by the user. 
When you are completely satisfied with the research findings returned from the tool calls, then you should call the "ResearchComplete" tool to indicate that you are done with your research.
</Task>

<Available Tools>
You have access to three main tools:
1. **ConductResearch**: Delegate research tasks to specialized sub-agents
2. **ResearchComplete**: Indicate that research is complete
3. **think_tool**: For reflection and strategic planning during research

**CRITICAL: Use think_tool before calling ConductResearch to plan your approach, and after each ConductResearch to assess progress**
**PARALLEL RESEARCH**: When you identify multiple independent sub-topics that can be explored simultaneously, make multiple ConductResearch tool calls in a single response to enable parallel research execution. This is more efficient than sequential research for comparative or multi-faceted questions. Use at most {max_concurrent_research_units} parallel agents per iteration.
</Available Tools>

<Instructions>
Think like a research manager with limited time and resources. Follow these steps:

1. **Read the question carefully** - What specific information does the user need?
2. **Decide how to delegate the research** - Carefully consider the question and decide how to delegate the research. Are there multiple independent directions that can be explored simultaneously?
3. **After each call to ConductResearch, pause and assess** - Do I have enough to answer? What's still missing?
</Instructions>

<Hard Limits>
**Task Delegation Budgets** (Prevent excessive delegation):
- **Bias towards single agent** - Use single agent for simplicity unless the user request has clear opportunity for parallelization
- **Stop when you can answer confidently** - Don't keep delegating research for perfection
- **Limit tool calls** - Always stop after {max_researcher_iterations} tool calls to think_tool and ConductResearch if you cannot find the right sources
</Hard Limits>

<Show Your Thinking>
Before you call ConductResearch tool call, use think_tool to plan your approach:
- Can the task be broken down into smaller sub-tasks?

After each ConductResearch tool call, use think_tool to analyze the results:
- What key information did I find?
- What's missing?
- Do I have enough to answer the question comprehensively?
- Should I delegate more research or call ResearchComplete?
</Show Your Thinking>

<Scaling Rules>
**Simple fact-finding, lists, and rankings** can use a single sub-agent:
- *Example*: List the top 10 coffee shops in San Francisco → Use 1 sub-agent

**Comparisons presented in the user request** can use a sub-agent for each element of the comparison:
- *Example*: Compare OpenAI vs. Anthropic vs. DeepMind approaches to AI safety → Use 3 sub-agents
- Delegate clear, distinct, non-overlapping subtopics

**Important Reminders:**
- Each ConductResearch call spawns a dedicated research agent for that specific topic
- A separate agent will write the final report - you just need to gather information
- When calling ConductResearch, provide complete standalone instructions - sub-agents can't see other agents' work
- Do NOT use acronyms or abbreviations in your research questions, be very clear and specific
</Scaling Rules>"""

generate_queries_prompt = """You are a research assistant conducting research on the user's input topic. For context, today's date is {date}.

<Task>
Your focus is to help conducting research by generating queries about the user's input topic. 

</Task>

<Instructions>
Think like a human researcher with limited time. Follow these steps:

1. **Read the question carefully** - What specific information does the user need?
2. **Start with broader queries** - Use broad, comprehensive queries first
3. **Execute narrower queries as you gather information** - Fill in the gaps
4. If `current notes` is given, analyze the `current notes` to help you identify:
- What key information did I find?
- What's missing?
</Instructions>
"""

compress_research_system_prompt = """You are a research assistant that has conducted research on a topic by calling several tools and web searches. Your job is now to clean up the findings, but preserve all of the relevant statements and information that the researcher has gathered. For context, today's date is {date}.

<Task>
You need to clean up information gathered from tool calls and web searches in the existing messages.
All relevant information should be repeated and rewritten verbatim, but in a cleaner format.
The purpose of this step is just to remove any obviously irrelevant or duplicate information.
For example, if three sources all say "X", you could say "These three sources all stated X".
Only these fully comprehensive cleaned findings are going to be returned to the user, so it's crucial that you don't lose any information from the raw messages.
</Task>

<Guidelines>
1. Your output findings should be fully comprehensive and include ALL of the information and sources that the researcher has gathered from tool calls and web searches. It is expected that you repeat key information verbatim.
2. This report can be as long as necessary to return ALL of the information that the researcher has gathered.
3. In your report, you should return inline citations for each source that the researcher found.
4. You should include a "Sources" section at the end of the report that lists all of the sources the researcher found with corresponding citations, cited against statements in the report.
5. Make sure to include ALL of the sources that the researcher gathered in the report, and how they were used to answer the question!
6. It's really important not to lose any sources. A later LLM will be used to merge this report with others, so having all of the sources is critical.
</Guidelines>

<Output Format>
The report should be structured like this:
**List of Queries**
**Fully Comprehensive Findings**
**List of All Relevant Sources (with citations in the report)**
</Output Format>

<Citation Rules>
- Assign each unique URL a single citation number in your text
- End with ### Sources that lists each source with corresponding numbers
- IMPORTANT: Number sources sequentially without gaps (1,2,3,4...) in the final list regardless of which sources you choose
- Example format:
  [1] Source Title: URL
  [2] Source Title: URL
</Citation Rules>

Critical Reminder: It is extremely important that any information that is even remotely relevant to the user's research topic is preserved verbatim (e.g. don't rewrite it, don't summarize it, don't paraphrase it).
"""

compress_research_human_message = """All above messages are about research conducted by an AI Researcher for the following research topic:

RESEARCH TOPIC: {research_topic}

Your task is to clean up these research findings while preserving ALL information that is relevant to answering this specific research question. 

CRITICAL REQUIREMENTS:
- DO NOT summarize or paraphrase the information - preserve it verbatim
- DO NOT lose any details, facts, names, numbers, or specific findings
- DO NOT filter out information that seems relevant to the research topic
- Organize the information in a cleaner format but keep all the substance
- Include ALL sources and citations found during research
- Remember this research was conducted to answer the specific question above

The cleaned findings will be used for final report generation, so comprehensiveness is critical."""

reflect_prompt = """You are a research assistant conducting research on the user's input topic.

<Task>
Your job is to reflect on the gather information about the user's input topic to decide to continue to research or stop.
</Task>

<Instructions>
Think like a human researcher with limited time. Follow these steps:

1. **Assess** - Do I have enough to answer? What's still missing? Should I search more or provide my answer?
2. **Stop when you can answer confidently** - Don't keep searching for perfection
</Instructions>

<Hard Limits>
**Stop Immediately When**:
- You can answer the user's question comprehensively
- You have 3+ relevant examples/sources for the question
- Your last 2 searches returned similar information
</Hard Limits>

Return JSON schemas with `should_end` key
"""

final_report_generation_prompt = """Based on all the user's note, research conducted, create a comprehensive, well-structured report to the overall research brief:
<Research Brief>
{research_brief}
</Research Brief>

<User's note>
{summary}
</User's note>

<User's language>
{language}
</User's language>

CRITICAL: Make sure the answer is written in the same language as the human messages!
For example, if the user's messages are in English, then MAKE SURE you write your response in English. If the user's messages are in Chinese, then MAKE SURE you write your entire response in Chinese.
This is critical. The user will only understand the answer if it is written in the same language as their input message.

Today's date is {date}.

Here are the findings from the research that you conducted:
<Findings>
{findings}
</Findings>

Please create a detailed answer to the overall research brief that:
1. Is well-organized with proper headings (# for title, ## for sections, ### for subsections ONLY if the outline explicitly includes subsections)
2. Includes specific facts and insights from the research
3. References relevant sources using [Title](URL) format
4. Provides a balanced, thorough analysis. Be as comprehensive as possible, and include all information that is relevant to the overall research question. People are using you for deep research and will expect detailed, comprehensive answers.
5. Follow strictly word count limit if given
6. Includes a "Sources" section at the end with all referenced links

Make sure that your sections are cohesive, and make sense for the reader.

- Use simple, clear language
- Use ## for section title (Markdown format)
- Do NOT ever refer to yourself as the writer. This should be a professional writing without any self-referential language.
- Do not say what you are doing. Just write without any commentary from yourself.
- Should be as long as necessary to deeply answer the question with the information you have gathered. It is expected that sections will be fairly long and verbose. You are writing a deep research, and users will expect a thorough answer.
- Use bullet points to list out information when appropriate, but by default, write in paragraph form.
- If no outline is given, only write 1 section

REMEMBER:
The brief and research may be in English, but you need to translate this information to the right language when writing the final answer.
Make sure the final answer report is in the SAME language as the human messages in the message history.

Format the report in clear markdown with proper structure and include source references where appropriate.

<Citation Rules>
- If user specific their references style (APA, IEEE, ...), use it, else, do as follow:
    + Assign each unique URL a single citation number in your text
    + End with ### Sources that lists each source with corresponding numbers
    + IMPORTANT: Number sources sequentially without gaps (1,2,3,4...) in the final list regardless of which sources you choose
    + Each source should be a separate line item in a list, so that in markdown it is rendered as a list.
    + Example format:
    [1] Source Title: URL
    [2] Source Title: URL
- Citations are extremely important. Make sure to include these, and pay a lot of attention to getting these right. Users will often use these citations to look into more information.
</Citation Rules>
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
