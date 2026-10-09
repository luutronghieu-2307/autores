# Write Report Tool

This module provides tools for writing.

## Folder Structure

```
.
├── .env                 # Environment variables (sensitive data like API keys)
├── README.md            # This file
├── requirements.txt     # Python dependencies
└── src/                 # Source code
    ├── app/             # Application entry points (CLI)
    │   └── cli/
    │       └── main.py
    ├── configs/         # Configuration files
    │   └── app.py
    ├── modules/         # Core logic modules
    │   ├── docs.py
    │   ├── proposed_method_graph.py
    │   ├── seminar_graph_1.py
    │   ├── seminar_graph.py
    │   ├── write_prompt_bank.py
    │   └── utils.py
    └── schemas/         # Data schemas/models
        ├── proposed_method.py
        └── section.py
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
Task is sent to topic `write_section_request` (cloud) and `write_section_request_local` (local)
Result is sent to topic `write_section_response` (cloud) and `write_section_response_local` (local)

### Write seminar
For this task, set `event_type` to "CHUYEN_DE"

**Input message:**

```
message = {
  "user_id": str,
  "language": str,
  "model_id": str,
  "document_id": str,
  "event_type": str,
  "level": Literal["CHUYEN_DE_1", "CHUYEN_DE_2", "CHUYEN_DE_3"]
  "final_proposal": dict,
  "web_search": str,
  "papers_search": dict,
  "outline": dict
}
```

**Output message:**

```
message = {
  "user_id": str,
  "document_id": str,
  "event_type": str,
  "input_tokens": int,
  "output_tokens": int,
  "final_report": str
} | Exception
```

### Edit references
For this task, set `event_type` to "edit_ref"

**Input message:**

```
message = {
  "user_id": str,
  "document_id": str,
  "event_type": str,
  "pdf_path": str,
  "research_papers": dict
}
```

**Output message:**

```
message = {
  "user_id": str,
  "document_id": str,
  "event_type": str,
  "file_path": str
} | Exception
```