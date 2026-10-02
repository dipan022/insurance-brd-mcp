# Project Runbook

This file contains the terminal commands required to set up, test, and run the complete Insurance BRD MCP project.

Project folder:

```text
C:\Users\ASUS\OneDrive\Desktop\Ai initiative\brd-mcp
```

---

## 1. Open the project

Open PowerShell and run:

```powershell
cd "C:\Users\ASUS\OneDrive\Desktop\Ai initiative\brd-mcp"
```

---

## 2. Verify the project files

Run:

```powershell
dir
```

The important files should include:

```text
server.py
llm_mcp_client.py
jira_service.py
validator.py
brd_generator.py
prompts.yaml
requirements.txt
README.md
.gitignore
.env
```

`.env` is required locally but must NOT be uploaded to GitHub.

---

## 3. Create the virtual environment

Only required if `.venv` does not already exist:

```powershell
python -m venv .venv
```

---

## 4. Install / update dependencies

Use the Python executable inside the virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

This avoids the PowerShell `Activate.ps1` execution-policy problem.

---

## 5. Verify environment configuration

The local `.env` file should contain the required configuration:

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

Never commit the real `.env` file to GitHub.

---

## 6. Optional: test Jira connectivity

If the project contains the Jira hierarchy/check script, run:

```powershell
.\.venv\Scripts\python.exe .\check_jira_hierarchy.py
```

This is useful for checking the Jira project and issue-type hierarchy before publishing.

---

## 7. Run the complete BRD → Jira workflow

This is the main command:

```powershell
.\.venv\Scripts\python.exe .\llm_mcp_client.py
```

When the program asks:

```text
What do you want to do?
>
```

enter a request containing the source Jira issue key.

Example:

```text
Create a BRD from Jira issue KAN-1
```

---

## 8. What the main command does

The complete workflow is:

```text
User Request
     |
     v
Extract Jira Issue Key
     |
     v
Connect to MCP Server
     |
     v
LLM receives available MCP tools
     |
     v
LLM selects get_jira_issue
     |
     v
Read Jira KAN-1
     |
     v
Generate Insurance BRD
     |
     v
Validate BRD
     |
     v
If required, revise BRD
     |
     v
Generate Jira Backlog JSON
     |
     v
Validate Backlog
     |
     v
Publish to IBRD
     |
     +----> Epic
     |
     +----> Features
     |
     +----> Feature Subtasks
     |
     v
Generate BRD PDF
     |
     v
Attach BRD PDF to Jira Epic
```

---

## 9. Expected Jira hierarchy

The current project is designed for:

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

Example:

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

The issue keys above are examples from a previous run. New runs will generate different Jira issue keys.

---

## 10. Useful individual checks

### Check Python version

```powershell
.\.venv\Scripts\python.exe --version
```

### Check installed packages

```powershell
.\.venv\Scripts\python.exe -m pip list
```

### Check that the MCP client starts

```powershell
.\.venv\Scripts\python.exe .\llm_mcp_client.py
```

### Check Jira hierarchy

```powershell
.\.venv\Scripts\python.exe .\check_jira_hierarchy.py
```

---

## 11. If PowerShell activation fails

You may see:

```text
Activate.ps1 cannot be loaded because running scripts is disabled
```

You do NOT need to change the Windows execution policy for this project.

Use:

```powershell
.\.venv\Scripts\python.exe .\llm_mcp_client.py
```

and:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

---

## 12. If dependencies are missing

Run:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Then run:

```powershell
.\.venv\Scripts\python.exe .\llm_mcp_client.py
```

---

## 13. If `.env` is missing

Create `.env` in the same folder as:

```text
llm_mcp_client.py
server.py
jira_service.py
```

The application expects the configuration file here:

```text
brd-mcp\.env
```

Do not put the API keys directly into Python source files.

---

## 14. One-command daily run

After the project has already been installed and configured, the main command you normally need is:

```powershell
cd "C:\Users\ASUS\OneDrive\Desktop\Ai initiative\brd-mcp"
.\.venv\Scripts\python.exe .\llm_mcp_client.py
```

Then enter:

```text
Create a BRD from Jira issue KAN-1
```

---

## 15. First-time setup command sequence

For a fresh clone of the GitHub repository:

```powershell
cd "C:\Users\ASUS\OneDrive\Desktop\Ai initiative\brd-mcp"

python -m venv .venv

.\.venv\Scripts\python.exe -m pip install -r requirements.txt

.\.venv\Scripts\python.exe .\check_jira_hierarchy.py

.\.venv\Scripts\python.exe .\llm_mcp_client.py
```

Then provide the Jira request:

```text
Create a BRD from Jira issue KAN-1
```

---

## 16. Files that must exist before running

```text
server.py
llm_mcp_client.py
jira_service.py
validator.py
brd_generator.py
prompts.yaml
requirements.txt
.env
```

The following are recommended documentation/repository files:

```text
README.md
RUNBOOK.md
.gitignore
.env.example
```

---

## 17. Files that must NOT be committed

```text
.env
.venv/
__pycache__/
*.pyc
```

Also avoid committing private generated BRDs or logs if they contain confidential business information.

---

## 18. Quick command reference

| Purpose | Command |
|---|---|
| Open project | `cd "C:\Users\ASUS\OneDrive\Desktop\Ai initiative\brd-mcp"` |
| Create venv | `python -m venv .venv` |
| Install dependencies | `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` |
| Check Jira hierarchy | `.\.venv\Scripts\python.exe .\check_jira_hierarchy.py` |
| Run complete project | `.\.venv\Scripts\python.exe .\llm_mcp_client.py` |
| Python version | `.\.venv\Scripts\python.exe --version` |
| Installed packages | `.\.venv\Scripts\python.exe -m pip list` |

---

## 19. Short version

After everything is configured, the complete project can be started with:

```powershell
cd "C:\Users\ASUS\OneDrive\Desktop\Ai initiative\brd-mcp"
.\.venv\Scripts\python.exe .\llm_mcp_client.py
```

Then:

```text
Create a BRD from Jira issue KAN-1
```

This is the main command for the complete MCP → LLM → BRD → Jira workflow.
