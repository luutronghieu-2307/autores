# Prompt Case 2 — Write/Research Chatbot

> Tài liệu này chép lại prompt đang có trong source, để review riêng Case 2. Không phải prompt mới và không thay đổi logic runtime.

## 1. Phạm vi và luồng

Case 2 là luồng user trao đổi để thu thập/điều chỉnh thông tin nghiên cứu, sau đó xác nhận kế hoạch và mới chuyển sang tạo outline hoặc viết. Prompt chính nằm ở `ai_chatbot/src/modules/writer_prompt.py`; cách gọi nằm ở `ai_chatbot/src/modules/writer_chatbot.py` và các helper trong `ai_chatbot/src/modules/utils.py`.

Luồng report chính:

1. `CATEGORIES_2` phân loại yêu cầu.
2. `WRITE_REPORT_INFO` trích xuất/cập nhật thông tin nghiên cứu.
3. Nếu thiếu dữ kiện, `CLARIFY_REPORT` hỏi bổ sung.
4. Khi có summary, `SUMMARY_NOTE_REPORT` trình bày lại dữ kiện và hướng user bấm OK.
5. `SUMMARY_ACTION` phân loại phản hồi tiếp theo: duyệt kế hoạch, viết section, sửa kế hoạch hoặc đổi template.
6. Nếu được duyệt, `OUTLINE_GENERATION` tạo outline; `OUTLINE_CONFIRMATION` chuẩn hóa output outline.

Các prompt section/update và fallback cũng được giữ nguyên ở dưới vì chúng được import trong cùng chatbot.

## 2. Context động được truyền vào prompt

Các giá trị thường được chèn vào prompt tại runtime:

- `user_input`: tin nhắn mới nhất của user.
- `chat_history`: lịch sử hội thoại.
- `summary`: thông tin nghiên cứu đã thu thập trước đó.
- `outline_history`: outline hoặc lịch sử chỉnh outline nếu có.
- `template_key`: template hiện tại nếu user đã chọn/cung cấp.
- `language`: ngôn ngữ phản hồi, chủ yếu tiếng Việt hoặc tiếng Anh.
- `section_name` / `section_content`: dùng cho luồng viết hoặc cập nhật một section.

## 3. Prompt tĩnh trong writer_prompt.py

### WRITE_REPORT_INFO (line 75)

```text
Extract user's information to write a scientific report
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
- When parsing user's multi-line responses (e.g., "1. answer1
2. answer2
3. answer3"), match each numbered answer to the corresponding question that was asked.
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

```

### CLARIFY_REPORT (line 130)

```text
You're an writing assistant, your task is to ask user clarify questions for target information, to complete a note of keypoints for later use to write report
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

```

### SUMMARY_NOTE_REPORT (line 156)

```text
You're an writing assistant, your task is construct a summary of the given information
You will be given a note, which answers these following question:
1. Research topic: What is the topic that the user want to write about?
2. Main keywords: What are the main keywords in the research topic? (if research topic is given)
3. Supplement keywords: What are the supplemental or related keywords for the research topic?
4. Research questions: What are the questions that the user is trying to answer while doing the report?
5. Research type: What is the user research type? (Quantitative, Qualitative, Mix of Quantitative and Qualitative)
6. Scope: What is the user's scope? (A particular application? A specific location? A specific outcome you want to measure?)
7. Word count: How long does the user want the report to be?
8. References style: What type of references style does the user want?
**IMPORTANT**: If a field is set as "N/A", ignore it as it has been removed
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
*   **Format:** ... words, using ... citation style.

[One confirmation instruction in the user's language]"

```

### SUMMARY_CONFIRMATION (line 190)

```text
Analyze the user's feedback about a summary and their plan
You will be given the current plan and the user's feedback
If the user approve the summary/plan, return True
If the user reject the summary/plan or provide new information/corrections to the plan, return False
Return JSON with `summary_status` key

```

### SUMMARY_ACTION (line 197)

```text
Select the next action after the assistant has shown the current research plan.
The user's message may be Vietnamese or English. Use the whole conversation and the latest user message.
Return exactly one structured action:
- approve_plan: the user clearly confirms the plan or asks to begin/continue. Do not require the literal word "OK".
- write_section: the user directly asks to write a specific chapter or section.
- revise_plan: the user adds, removes, or changes information in the plan.
- change_template: the user changes the requested output template/type. Preserve the collected research information. Return the exact template identifier only when the user or caller supplied one; otherwise leave template_key empty.
Do not ask a question and do not classify by isolated keywords.

```

### OUTLINE_GENERATION (line 207)

```text
Generate an outline for a research report
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

```

### OUTLINE_CONFIRMATION (line 220)

```text
Analyze the user's feedback about an outline and determine if they approve it or want to modify it.

**Return True ONLY if the user explicitly approves and wants to proceed:**
- Examples: "yes", "looks good", "perfect", "proceed", "start writing", "approved", "that's fine"

**Return False if the user provides ANY feedback, changes, modifications, or rejections:**
- Examples: "skip chapter X", "remove section Y", "add Z", "change this", "no", "I don't like it"
- Even small modifications like "skip chapters IV and V" means they want to update the outline that remove some chapters

**IMPORTANT:** Any request to modify, skip, add, remove, or change ANY part of the outline should return False.

Return JSON with `outline_status` key (boolean)

```

### CONFIRMATION (line 234)

```text
You're an writing assistant bot, your task is to analyze the chat history and the user's answer to see if they wish to move on to writing
If the user want to move on to writing, return True
If the user doesnot want to move on to writing, return False
If the answer is uncertain, return False
Return JSON with `status` key

```

### WRITE_SECTION_INFO (line 241)

```text
Extract the user's request and the necessary context to write a specific section of a scientific report.

Based on the chat history between the user and the assistant, identify the key information needed to fulfill the user's command. Your goal is to populate the following fields:

1.  **Research Topic**: What is the overall topic of the report the user is working on?
2.  **Research Questions**: What are the main questions the report aims to answer? This provides context for the section's purpose.
3.  **Scope**: What is the defined scope of the research? This helps set boundaries for the section's content.
4.  **Word Count**: How long should this specific section be? (Note: This may be different from the total report word count).
5.  **User Request**: What is the specific action or task the user wants you to perform? (e.g., "write the introduction", "find sources for the literature review", "draft a conclusion").

**PARSING RULES**:
- When parsing user's multi-line responses (e.g., "1. answer1
2. answer2
3. answer3"), match each numbered answer to the corresponding question that was asked.
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

```

### CLARIFY_SECTION_INFO (line 294)

```text
You are a helpful writing assistant. Your goal is to ask clear follow-up questions to get the information needed to write a specific section of a report.

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

```

### CONFIRM_SECTION_PLAN (line 322)

```text
You are a writing assistant. Your task is to create a concise summary of the user's request for writing a report section and ask for their final confirmation before you begin writing.

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

```

### UPDATE_SECTION_INFO (line 349)

```text
Extract the user's revision goal and the original content they want to modify.

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

```

### CLARIFY_UPDATE_INFO (line 385)

```text
You are a helpful writing assistant. Your goal is to ask clear questions to get the information needed to revise a piece of text.

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

```

### CONFIRM_UPDATE_PLAN (line 411)

```text
You are a writing assistant. Your task is to summarize the revision plan and ask for the user's final confirmation before you proceed.

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

```

### CATEGORIES_2 (line 522)

```text
Analyze the user's query and classify into one of these following group
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

```

### UNDEFINED_CATE_2 (line 542)

```text
You are a writing assistant. Your task is to ask the user question that can help the user choose their group from these following groups
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

```

### CATEGORY_1 (line 563)

```text
Intent 1: User want to write a full report
```

### CATEGORY_2 (line 565)

```text
Intent 2: User want to write a section of a report
```

### CATEGORY_3 (line 567)

```text
Intent 3: User Requests Revision or Updating of an existant content
```

### CATEGORY (line 569)

```text
[CATEGORY_1, CATEGORY_2, CATEGORY_3]
```

### CHECK_INTENT (line 571)

```text
Analyze the user's query and the chat history to see if they want to change their writing intent
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

```

### CLARIFY_INTENT (line 630)

```text
You are a helpful writing assistant. Your goal is to ask a single, clear question to get the user's confirmation about changing intent
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

```

### INTENT_CONFIRMATION (line 649)

```text
Analyze the user's feedback about a changing intent
If the user confirm they want to change their intent, return True
If the user deny they want to change their intent, return False
If you're not sure, return False
Return JSON with `intent_status` key

```

## 4. Prompt động/wrapper trong runtime

### `_get_summary`

Dùng prompt `WRITE_REPORT_INFO`/prompt tương ứng của loại yêu cầu để đọc lịch sử chat và cập nhật summary có cấu trúc. Input chính là lịch sử hội thoại và thông tin đã thu thập trước đó; không được làm mất dữ kiện cũ khi user chỉ bổ sung một trường.

### `_get_summary_status`

Gọi `SUMMARY_CONFIRMATION` để xác định summary hiện tại đã đủ để chuyển bước hay vẫn cần hỏi thêm.

### `_get_summary_action`

Gọi `SUMMARY_ACTION` với toàn bộ conversation và tin nhắn mới nhất. Kết quả phải là một action có cấu trúc, không hỏi lại user trong prompt phân loại:

```text
Select the next action after the assistant has shown the current research plan.
The user's message may be Vietnamese or English. Use the whole conversation and the latest user message.
Return exactly one structured action:
- approve_plan: user accepts/approves the current plan, including natural confirmations; do not require literal OK.
- write_section: user asks to write a particular chapter/section now.
- revise_plan: user asks to change or add research information.
- change_template: user explicitly asks to change the template; preserve collected research information and return only an exact supplied template id when available, otherwise empty.
Do not ask a question and do not classify by isolated keywords.
```

### `_get_clarify_question`

Khi summary chưa đủ, wrapper gọi prompt clarify của đúng loại flow. Với report tổng quát, dùng `CLARIFY_REPORT` và không chèn summary confirmation làm câu hỏi lặp lại (`include_summary=False`).

### `_check_intent` và `_get_clarify_intent_question`

Dùng `CHECK_INTENT` để kiểm tra user đang tiếp tục cùng mục tiêu hay đổi ý định. Nếu cần hỏi rõ ý định thì dùng `CLARIFY_INTENT`; kết quả cuối dùng `INTENT_CONFIRMATION`. Các prompt này chỉ phục vụ intent/clarify, không tự tạo outline hoặc viết bài.

### `get_outline`

Wrapper ghép summary, outline history và template key vào prompt tạo outline:

```text
Research's note:
{summary}{outline_history}
Template key:
{template_key}
If template key is present, keep its structure and chapter requirements.
Generate approximately {total_subheading} headings/subheadings.
Generate full updated outline from start to finish; do not return only modified sections.
```

### Reply ngoài phạm vi

Reply fallback được tạo từ category/fallback prompt khi input không khớp Case 2; không dùng fallback này để thay thế bước thu thập dữ kiện của report.

## 5. Mapping prompt → model/tool

| Prompt | Nơi dùng | Output/schema liên quan |
|---|---|---|
| `CATEGORIES_2` | phân loại yêu cầu Case 2 | `UserCategory` |
| `WRITE_REPORT_INFO` | trích xuất/cập nhật dữ kiện report | `WriteReport` |
| `CLARIFY_REPORT` | hỏi các dữ kiện còn thiếu | clarify question |
| `SUMMARY_CONFIRMATION` | kiểm tra summary đã đủ | summary status |
| `SUMMARY_NOTE_REPORT` | hiển thị summary cho user trước khi bắt đầu | text confirmation |
| `SUMMARY_ACTION` | đọc phản hồi sau summary | `SummaryAction` |
| `OUTLINE_GENERATION` | sinh outline đầy đủ | outline text |
| `OUTLINE_CONFIRMATION` | chuẩn hóa outline | `OutlineWriteReport` |
| `CHECK_INTENT`, `CLARIFY_INTENT`, `INTENT_CONFIRMATION` | nhận diện/clarify intent | intent status/question |
| `*_SECTION_*`, `CONFIRMATION`, `UNDEFINED_CATE_2` | section/update/fallback paths | schema tương ứng trong chatbot |

## 6. Điểm cần review của Case 2

- Không dùng một prompt clarify chung cho mọi trạng thái: report tổng quát, viết section và update section có prompt riêng.
- Summary đã đủ thì phải chuyển sang bước trình bày plan/đợi user xác nhận; không quay lại gọi prompt thu thập dữ kiện chỉ vì user nói tự nhiên như “được”, “ok”, “viết đi”.
- `SUMMARY_ACTION` phải đọc toàn bộ hội thoại và latest message, không match cứng một câu duy nhất.
- Khi user đổi từ đề tài sang đề cương hoặc đổi template, giữ các dữ kiện đã thu thập và chỉ thu thập lại phần bị ảnh hưởng.
- Outline phải dùng đúng `template_key` đã lưu nếu có; không tự chọn thêm model/template ngoài danh sách đã thiết lập.
- Tài liệu này chỉ gom prompt hiện tại và call context; chưa sửa prompt hay code.
