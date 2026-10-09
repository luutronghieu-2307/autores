# Document Setup Module

This module provides tools for assisting in the document creation process, including searching for relevant information, generating ideas, creating proposals, and outlining documents.

## Folder Structure

```
.
├── .env                 # Environment variables (sensitive data like API keys)
├── README.md            # This file
├── requirements.txt     # Python dependencies
└── src/                 # Source code
    ├── configs/         # Configuration files
    │   ├── app.py
    │   └── structure.py
    ├── modules/         # Core logic modules
    │   ├── idea_generation.py
    │   ├── knowledge_prompt_bank.py
    │   ├── outline_generation.py
    │   ├── outline_prompt_bank.py
    │   ├── search_journals.py
    │   ├── search_papers.py
    │   └── search_web.py
    └── schemas/         # Data schemas/models
        ├── outline.py
        ├── proposal.py
        ├── search_papers.py
        └── search_web.py
```

## Setup

1.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
2.  **Configure environment variables:**
    - Copy or rename `.env.example` to `.env` (if an example file exists).
    - Add necessary API keys or configurations to the `.env` file.

## Usage

The primary way to interact with this project is through Kafka.
Task is sent to topic `document_setup_request` (cloud) and `document_setup_request_local` (local)
Result is sent to topic `document_setup_response` (cloud) and `document_setup_response_local` (local)

### Generate domains

For this task, set `event_type` to "generate_domains"

**Input message:**

```
message = {
  "user_id": str,
  "language": str,
  "model_id": str,
  "event_type": str,
  "field": str,
  "domains_num": int
}
```

**Output message:**

```
message = {
  "user_id": str,
  "model_id": str,
  "event_type": str,
  "input_tokens": int,
  "output_tokens": int,
  "field": str,
  "domains": list[str]
} | Exception
```

### Generate subdomains

For this task, set `event_type` to "generate_subdomains"

**Input message:**

```
message = {
  "user_id": str,
  "language": str,
  "model_id": str,
  "event_type": str,
  "field": str,
  "domain": str,
  "subdomains_num": int
}
```

**Output message:**

```
message = {
  "user_id": str,
  "model_id": str,
  "event_type": str,
  "input_tokens": int,
  "output_tokens": int,
  "field": str,
  "subdomains": list[str]
} | Exception
```

### Generate titles

For this task, set `event_type` to "generate_titles"

**Input message:**

```
message = {
  "user_id": str,
  "language": str,
  "model_id": str,
  "document_id": str,
  "event_type": str,
  "field": str,
  "domain": str,
  "subdomains": list[str],
  "level": Literal["CHUYEN_DE", "LUAN_AN_TIEN_SI", "LUAN_VAN_THAC_SI", "KHOA_LUAN", "TIEU_LUAN", "BAI_BAO_KHOA_HOC"]
}
```

**Output message:**

```
message = {
  "user_id": str,
  "document_id": str,
  "model_id": str,
  "event_type": str,
  "input_tokens": int,
  "output_tokens": int,
  "proposals": list[Proposal],
  "knowledge_base": list[dict]
} | Exception

Proposal = {
  "title": str,
  "problem_statement": str,
  "motivation": str,
  "proposed_method": str,
  "experiment_plan": str,
  "web_search": str,
  "research_gap": str
}
```

### Generate title description

For this task, set `event_type` to "generate_title_description"

**Input message:**

```
message = {
  "user_id": str,
  "language": str,
  "model_id": str,
  "document_id": str,
  "event_type": str,
  "field": str,
  "domain": str,
  "knowledge_base": dict,
  "title": str,
  "level": Literal["CHUYEN_DE", "LUAN_AN_TIEN_SI", "LUAN_VAN_THAC_SI", "KHOA_LUAN", "TIEU_LUAN", "BAI_BAO_KHOA_HOC"]
}
```

**Output message:**

```
message = {
  "user_id": str,
  "document_id": str,
  "model_id": str,
  "event_type": str,
  "input_tokens": int,
  "output_tokens": int,
  "proposal": Proposal
} | Exception
```

### Mix titles

For this task, set `event_type` to "mix_titles"

**Input message:**

```
message = {
  "user_id": str,
  "language": str,
  "model_id": str,
  "document_id": str,
  "event_type": str,
  "field": str,
  "domain": str,
  "level": Literal["CHUYEN_DE", "LUAN_AN_TIEN_SI", "LUAN_VAN_THAC_SI", "KHOA_LUAN", "TIEU_LUAN", "BAI_BAO_KHOA_HOC"],
  "proposals": list[Proposal]
}
```

**Output message:**

```
message = {
  "user_id": str,
  "document_id": str,
  "model_id": str,
  "event_type": str,
  "input_tokens": int,
  "output_tokens": int,
  "proposal": Proposal
} | Exception
```

### Generate keywords

For this task, set `event_type` to "generate_keywords"

**Input message:**

```
message = {
  "user_id": str,
  "language": str,
  "model_id": str,
  "document_id": str,
  "event_type": str,
  "proposal": Proposal
}
```

**Output message:**

```
message = {
  "user_id": str,
  "document_id": str,
  "model_id": str,
  "event_type": str,
  "input_tokens": int,
  "output_tokens": int,
  "keywords": Keywords
} | Exception

Keywords = {
  "main_keywords": list[str],
  "addition_keywords": list[str]
}
```

### Get research papers

For this task, set `event_type` to "search_papers"

**Input message:**

```
message = {
  "user_id": str,
  "model_id": str,
  "document_id": str,
  "event_type": str,
  "field": str,
  "domains": list[str],
  "country_filter": str,
  "oa_filter": bool,
  "is_oa": bool,
  "start": int,
  "cut_off_year_low": int,
  "cut_off_year_high": int,
  "search_range": str
}
```

**Output message:**

```
message = {
  "user_id": str,
  "document_id": str,
  "model_id": str,
  "event_type": str,
  "input_tokens": int,
  "output_tokens": int,
  "papers": list[Paper],
  "isExpired": bool
} | Exception

Paper = {
  "title": str,
  "source": str,
  "open_access": bool,
  "url": str,
  "isDownloaded": bool,
  "authors": list[str],
  "journal": str,
  "year": int,
  "issn": str,
  "q": str,
  "abs": str,
  "volume": str,
  "issue": str,
  "pages": str
}
```

### Generate outline

For this task, set `event_type` to "generate_outline"

**Input message:**

```
message = {
  "user_id": str,
  "language": str,
  "model_id": str,
  "document_id": str,
  "event_type": str,
  "word_count_str": str,
  "headings": list[str],
  "headings_percent": list[float],
  "final_proposal": Proposal
}
```

**Output message:**

```
message = {
  "user_id": str,
  "document_id": str,
  "model_id": str,
  "event_type": str,
  "input_tokens": int,
  "output_tokens": int,
  "outline": Outline
} | Exception

Outline = {
  "title": str,
  "outline": list[Heading]
}
Heading = {
  "heading": str,
  "word_count": str,
  "overview": str,
  "subheadings": list[SubHeading]
}
SubHeading = {
  "subheading_level": str,
  "detail_description": str,
  "subheading": str
}
```

### Generate seminar outline

For this task, set `event_type` to "generate_outline_seminar"

**Input message:**

```
message = {
  "user_id": str,
  "model_id": str,
  "document_id": str,
  "event_type": str,
  "level": str,
  "word_count_str": str,
  "headings": list[str],
  "headings_percent": list[float],
  "final_proposal": Proposal
}
```

**Output message:**

```
message = {
  "user_id": str,
  "document_id": str,
  "model_id": str,
  "event_type": str,
  "input_tokens": int,
  "output_tokens": int,
  "outline": Outline
} | Exception

Outline = {
  "name": str,
  "outline": list[Heading]
}
Heading = {
  "heading": str,
  "word_count": str,
  "description": str
}
```

### Update journals Q and ISSN

For this task, set `event_type` to "get_journals"

**Input message:**

```
message = {
  "last_updated": int
}
```

**Output message:**

```
message = "Finish crawling ISSN and Q information" | Exception
```