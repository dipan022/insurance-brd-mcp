# Insurance BRD MCP Server

An MCP-based automation project that reads a business requirement from Jira, uses an LLM through OpenRouter to generate an Insurance Business Requirement Document (BRD), validates the BRD, converts it into a Jira delivery backlog, and publishes the result back to Jira.

## Project Overview

```text
Jira Source Requirement
        |
        v
   MCP Client
        |
        v
     LLM
   OpenRouter
        |
        v
    MCP Server
        |
        +--------------------+
        |                    |
        v                    v
   BRD Generation       Jira Integration
        |                    |
        v                    v
   BRD Validation      Epic / Features / Subtasks
        |
        v
   BRD Markdown + PDF
```

The current Jira delivery structure is:

```text
Epic
  |
  +-- Feature
  |     |
  |     +-- Subtask
  |     +-- Subtask
  |
  +-- Feature
        |
        +-- Subtask
```

## Main Features

- Read a business requirement from Jira.
- Use an MCP server to expose business-process tools.
- Use an LLM through OpenRouter.
- Allow the LLM to select and call MCP tools.
- Generate a structured Insurance BRD.
- Keep BRD and backlog instructions in `prompts.yaml`.
- Validate BRD sections, insurance-domain content, functional requirements and acceptance criteria.
- Convert the BRD into a Jira backlog.
- Publish the backlog into a separate Jira project.
- Create an Epic.
- Create Features under the Epic.
- Create Subtasks under the relevant Features.
- Generate a BRD PDF.
- Attach the generated BRD PDF to the Jira Epic.
- Add a reference/comment back to the source Jira issue.

## Technology Stack

- Python
- Model Context Protocol (MCP) SDK 2.x
- OpenRouter
- OpenAI Python SDK
- Jira REST API
- HTTPX
- PyYAML
- ReportLab
- JSON Repair
- python-dotenv

## Project Structure

```text
brd-mcp/
|
|-- server.py
|-- llm_mcp_client.py
|-- jira_service.py
|-- validator.py
|-- brd_generator.py
|-- prompts.yaml
|-- requirements.txt
|-- .gitignore
|-- README.md
|
|-- .env                  # Local only - NEVER commit
|
|-- brd_output/           # Generated local files, if used
|
`-- .venv/                # Local virtual environment - NEVER commit
```

### File Responsibilities

#### `server.py`

The MCP server and workflow layer.

It exposes tools such as:

- `get_jira_issue`
- `create_brd`
- `validate_brd`
- `publish_brd_hierarchy`
- `save_brd_file`

The server is responsible for MCP/API/workflow operations rather than storing the detailed BRD prompts.

#### `llm_mcp_client.py`

The LLM-facing MCP client.

It:

1. Reads the user's request.
2. Extracts the Jira issue key.
3. Connects to the MCP server.
4. Sends the available MCP tools to the LLM.
5. Allows the LLM to select MCP tools.
6. Generates the BRD.
7. Validates the BRD.
8. Generates the Jira backlog JSON.
9. Validates the backlog.
10. Publishes the final hierarchy to Jira.

#### `jira_service.py`

Contains Jira REST API operations such as:

- Reading Jira issues.
- Reading project information.
- Reading Jira issue types.
- Creating Jira issues.
- Creating subtasks.
- Uploading attachments.
- Adding comments.
- Validating the Jira hierarchy.

#### `validator.py`

Validates the generated BRD against the configuration in `prompts.yaml`.

The validation includes:

- Required BRD sections.
- Insurance-domain keywords.
- Functional requirement IDs such as `FR-001`.
- Acceptance criteria IDs such as `AC-001`.
- Minimum BRD content length.

#### `brd_generator.py`

Contains BRD file/PDF generation logic.

#### `prompts.yaml`

Contains the business and LLM instructions.

This file is intentionally separate from Python so that BRD structure, Insurance-domain rules and Jira backlog rules can be changed without modifying the Python workflow.

The backlog format is designed around:

```text
Epic
  |
  +-- Feature
        |
        +-- Subtask
```

#### `requirements.txt`

Contains the Python packages required by the project.

## Environment Configuration

Create a local `.env` file in the project directory.

Example structure:

```env
OPENROUTER_API_KEY=your_openrouter_key
OPENROUTER_MODEL=openrouter/free

JIRA_URL=https://your-domain.atlassian.net
JIRA_EMAIL=your-jira-email
JIRA_API_TOKEN=your-jira-api-token

JIRA_SOURCE_PROJECT_KEY=KAN
JIRA_OUTPUT_PROJECT_KEY=IBRD

BUSINESS_DOMAIN=insurance
```

### Important Security Rule

**Never commit `.env` to GitHub.**

The `.env` file contains API credentials and must remain local.

Use `.env.example` if you want to show the required variable names publicly:

```env
OPENROUTER_API_KEY=
OPENROUTER_MODEL=openrouter/free

JIRA_URL=
JIRA_EMAIL=
JIRA_API_TOKEN=

JIRA_SOURCE_PROJECT_KEY=KAN
JIRA_OUTPUT_PROJECT_KEY=IBRD

BUSINESS_DOMAIN=insurance
```

## Installation

Open PowerShell in the project directory:

```powershell
cd "C:\Users\ASUS\OneDrive\Desktop\Ai initiative\brd-mcp"
```

Create the virtual environment if it does not already exist:

```powershell
python -m venv .venv
```

Install dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

If PowerShell blocks `Activate.ps1`, activation is not required. The project can be run directly with:

```powershell
.\.venv\Scripts\python.exe .\llm_mcp_client.py
```

## Running the Project

Run:

```powershell
.\.venv\Scripts\python.exe .\llm_mcp_client.py
```

Then enter a request containing a Jira issue key.

Example:

```text
Create a BRD from Jira issue KAN-1
```

The application can then:

1. Read `KAN-1`.
2. Generate the Insurance BRD.
3. Validate the BRD.
4. Generate the Jira backlog.
5. Validate the backlog.
6. Create the Jira Epic.
7. Create Jira Features.
8. Create Feature Subtasks.
9. Generate the BRD PDF.
10. Attach the BRD PDF to the Jira Epic.

## Jira Flow

The source Jira project contains the original business requirement.

Example:

```text
KAN-1
```

The generated delivery backlog is published into:

```text
IBRD
Insurance BRD Management
```

Example resulting hierarchy:

```text
IBRD-47  Insurance Policy Management System
|
+-- IBRD-48  Customer and Policyholder Profile Management
|   |
|   +-- IBRD-49  Create customer profile functionality
|   +-- IBRD-50  Implement policyholder profile management
|   `-- IBRD-51  ...
|
+-- IBRD-53  New Policy Creation with Coverage
|
+-- IBRD-58  Premium Calculation and Recording
|
+-- IBRD-63  Policyholder Self-Service
|
+-- IBRD-68  Policy Renewal Support
|
`-- IBRD-73  Agent Policy Administration
```

The exact issue keys will be different for every new Jira run.

## BRD-to-Jira Traceability

The BRD contains functional requirement IDs such as:

```text
FR-001
FR-002
FR-003
```

The generated Jira Features can reference the applicable BRD requirement IDs.

This provides traceability from:

```text
Source Jira Requirement
        |
        v
BRD Functional Requirement
        |
        v
Jira Feature
        |
        v
Jira Subtask
```

## MCP Tools

The MCP server exposes workflow tools that the LLM can use.

### `get_jira_issue`

Reads the source Jira requirement.

### `create_brd`

Passes the business requirement into the BRD-generation workflow.

### `validate_brd`

Checks whether the generated BRD satisfies the configured validation rules.

### `publish_brd_hierarchy`

Publishes the generated backlog into the Jira output project.

### `save_brd_file`

Saves the generated BRD locally.

## Design Principles

### Prompts are externalized

Detailed business instructions are kept in:

```text
prompts.yaml
```

Python code handles:

```text
MCP
API calls
workflow
validation execution
file generation
Jira publishing
```

The prompt file handles:

```text
BRD instructions
Insurance-domain instructions
BRD structure
backlog-generation instructions
backlog JSON format
```

### No credentials in source code

Credentials are loaded from `.env`.

### No unnecessary manual MCP calls

The LLM receives the available MCP tools and can select the appropriate tool during the workflow.

## Security

Do not publish:

- `.env`
- Jira API tokens
- OpenRouter API keys
- Passwords
- Personal access tokens
- Private credentials
- Local `.venv` files

If a credential is ever committed to a public or shared Git repository, revoke/rotate it immediately.

## Recommended GitHub Repository Contents

Commit:

```text
server.py
llm_mcp_client.py
jira_service.py
validator.py
brd_generator.py
prompts.yaml
requirements.txt
.gitignore
README.md
```

Do not commit:

```text
.env
.venv/
__pycache__/
*.pyc
generated BRD files containing private information
local logs
editor-specific files
```

## Current Project Status

The implemented pipeline has been tested against Jira and has successfully created an Epic → Feature → Subtask structure in the `IBRD` project.

The next development focus is verification, cleanup, documentation and repository packaging.

## Disclaimer

This project is a development/learning implementation. Jira configuration, issue types, API permissions, OpenRouter model availability and MCP SDK behavior can vary between environments.
