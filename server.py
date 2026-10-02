import json
import os
import re
from pathlib import Path

import yaml
from dotenv import load_dotenv
from mcp.server import MCPServer

from brd_generator import create_brd_pdf
from jira_service import JiraService


# ============================================================
# LOAD CONFIGURATION
# ============================================================

ENV_FILE = Path(__file__).with_name(".env")

load_dotenv(
    dotenv_path=ENV_FILE,
    override=True
)


# ============================================================
# MCP SERVER
# ============================================================

mcp = MCPServer(
    "Insurance-BRD-Jira-Server"
)


# ============================================================
# JIRA CLIENT
# ============================================================

jira = JiraService()


# ============================================================
# CONFIGURATION
# ============================================================

BUSINESS_DOMAIN = os.getenv(
    "BUSINESS_DOMAIN",
    "insurance"
)

JIRA_OUTPUT_PROJECT_KEY = os.getenv(
    "JIRA_OUTPUT_PROJECT_KEY"
)

JIRA_URL = os.getenv(
    "JIRA_URL",
    ""
).rstrip("/")


# ============================================================
# PROMPT CONFIGURATION
# ============================================================

PROMPTS_FILE = Path(
    __file__
).with_name(
    "prompts.yaml"
)


def load_prompt_config():

    if not PROMPTS_FILE.exists():

        return {
            "brd_sections": [],
            "insurance_keywords": []
        }

    try:

        with PROMPTS_FILE.open(
            "r",
            encoding="utf-8"
        ) as file:

            return (
                yaml.safe_load(file)
                or {}
            )

    except Exception:

        return {
            "brd_sections": [],
            "insurance_keywords": []
        }


PROMPT_CONFIG = load_prompt_config()


# ============================================================
# ADF TEXT EXTRACTION
# ============================================================

def extract_adf_text(node):

    result = []

    if isinstance(
        node,
        dict
    ):

        if node.get(
            "type"
        ) == "text":

            result.append(
                node.get(
                    "text",
                    ""
                )
            )

        for child in node.get(
            "content",
            []
        ):

            child_text = extract_adf_text(
                child
            )

            if child_text:

                result.append(
                    child_text
                )

    elif isinstance(
        node,
        list
    ):

        for child in node:

            child_text = extract_adf_text(
                child
            )

            if child_text:

                result.append(
                    child_text
                )

    return "\n".join(
        result
    )


# ============================================================
# MARKDOWN CLEANING
# ============================================================

def clean_markdown(text):

    if not text:

        return ""

    text = (
        str(text)
        .replace(
            "**",
            ""
        )
        .replace(
            "__",
            ""
        )
        .replace(
            "`",
            ""
        )
    )

    return text.strip()


# ============================================================
# MARKDOWN → JIRA ADF
# ============================================================

def markdown_to_adf(
    markdown_text
):

    content = []

    for raw_line in markdown_text.splitlines():

        line = raw_line.strip()

        if not line:

            continue

        # ----------------------------------------------------
        # H1
        # ----------------------------------------------------

        if line.startswith(
            "# "
        ):

            content.append(
                {
                    "type": "heading",
                    "attrs": {
                        "level": 1
                    },
                    "content": [
                        {
                            "type": "text",
                            "text": clean_markdown(
                                line[2:]
                            )
                        }
                    ]
                }
            )

        # ----------------------------------------------------
        # H2
        # ----------------------------------------------------

        elif line.startswith(
            "## "
        ):

            content.append(
                {
                    "type": "heading",
                    "attrs": {
                        "level": 2
                    },
                    "content": [
                        {
                            "type": "text",
                            "text": clean_markdown(
                                line[3:]
                            )
                        }
                    ]
                }
            )

        # ----------------------------------------------------
        # H3
        # ----------------------------------------------------

        elif line.startswith(
            "### "
        ):

            content.append(
                {
                    "type": "heading",
                    "attrs": {
                        "level": 3
                    },
                    "content": [
                        {
                            "type": "text",
                            "text": clean_markdown(
                                line[4:]
                            )
                        }
                    ]
                }
            )

        # ----------------------------------------------------
        # H4
        # ----------------------------------------------------

        elif line.startswith(
            "#### "
        ):

            content.append(
                {
                    "type": "heading",
                    "attrs": {
                        "level": 3
                    },
                    "content": [
                        {
                            "type": "text",
                            "text": clean_markdown(
                                line[5:]
                            )
                        }
                    ]
                }
            )

        # ----------------------------------------------------
        # BULLET
        # ----------------------------------------------------

        elif (
            line.startswith("- ")
            or line.startswith("* ")
        ):

            content.append(
                {
                    "type": "bulletList",
                    "content": [
                        {
                            "type": "listItem",
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [
                                        {
                                            "type": "text",
                                            "text": clean_markdown(
                                                line[2:]
                                            )
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            )

        # ----------------------------------------------------
        # NUMBERED ITEM
        # ----------------------------------------------------

        elif re.match(
            r"^\d+\.\s+",
            line
        ):

            content.append(
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": clean_markdown(
                                line
                            )
                        }
                    ]
                }
            )

        # ----------------------------------------------------
        # NORMAL PARAGRAPH
        # ----------------------------------------------------

        else:

            content.append(
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": clean_markdown(
                                line
                            )
                        }
                    ]
                }
            )

    if not content:

        content.append(
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": "No description provided."
                    }
                ]
            }
        )

    return {
        "type": "doc",
        "version": 1,
        "content": content
    }


# ============================================================
# LABEL CLEANING
# ============================================================

def clean_label(value):

    value = str(
        value or ""
    ).strip().lower()

    value = re.sub(
        r"[^a-z0-9_-]",
        "-",
        value
    )

    value = re.sub(
        r"-+",
        "-",
        value
    )

    return value[:255]


# ============================================================
# BRD VALIDATION
# ============================================================

def validate_brd_content(
    brd_text
):

    required_sections = (
        PROMPT_CONFIG.get(
            "brd_sections",
            []
        )
    )

    insurance_keywords = (
        PROMPT_CONFIG.get(
            "insurance_keywords",
            []
        )
    )

    lower_text = brd_text.lower()

    missing_sections = [
        section
        for section in required_sections
        if section.lower()
        not in lower_text
    ]

    found_keywords = [
        keyword
        for keyword in insurance_keywords
        if keyword.lower()
        in lower_text
    ]

    functional_ids = set(
        re.findall(
            r"\bFR-\d+\b",
            brd_text.upper()
        )
    )

    acceptance_ids = set(
        re.findall(
            r"\bAC-\d+\b",
            brd_text.upper()
        )
    )

    problems = []

    if missing_sections:

        problems.append(
            "Missing BRD sections: "
            + ", ".join(
                missing_sections
            )
        )

    if len(
        found_keywords
    ) < 3:

        problems.append(
            "Insufficient Insurance-domain content."
        )

    if not functional_ids:

        problems.append(
            "No functional requirement IDs found."
        )

    if not acceptance_ids:

        problems.append(
            "No acceptance criteria IDs found."
        )

    if len(
        brd_text.strip()
    ) < 1800:

        problems.append(
            "BRD content is too short."
        )

    return {
        "valid": not problems,
        "missing_sections": missing_sections,
        "insurance_keywords_found": found_keywords,
        "functional_requirement_count": len(
            functional_ids
        ),
        "acceptance_criteria_count": len(
            acceptance_ids
        ),
        "problems": problems
    }


# ============================================================
# TOOL 1 — GET JIRA ISSUE
# ============================================================

@mcp.tool()
def get_jira_issue(
    issue_key: str
) -> str:
    """
    Read the source Jira requirement.
    """

    data = jira.get_issue(
        issue_key
    )

    fields = data.get(
        "fields",
        {}
    )

    summary = fields.get(
        "summary",
        ""
    )

    description = fields.get(
        "description"
    )

    description_text = ""

    if description:

        description_text = (
            extract_adf_text(
                description
            ).strip()
        )

    if not description_text:

        description_text = (
            "No Jira description provided."
        )

    return (
        f"Source Jira Issue: "
        f"{issue_key}\n\n"
        f"Business Domain: "
        f"{BUSINESS_DOMAIN}\n\n"
        f"Summary:\n"
        f"{summary}\n\n"
        f"Description:\n"
        f"{description_text}"
    )


# ============================================================
# TOOL 2 — CREATE BRD
# ============================================================

@mcp.tool()
def create_brd(
    business_requirement: str
) -> str:
    """
    Pass the business requirement to the AI.

    BRD instructions are maintained in prompts.yaml.
    """

    if not business_requirement.strip():

        return (
            "Business requirement is empty."
        )

    return (
        business_requirement.strip()
    )


# ============================================================
# TOOL 3 — VALIDATE BRD
# ============================================================

@mcp.tool()
def validate_brd(
    brd_content: str
) -> str:
    """
    Validate the generated Insurance BRD.
    """

    result = validate_brd_content(
        brd_content
    )

    return json.dumps(
        result,
        indent=2
    )


# ============================================================
# TOOL 4 — PUBLISH BRD
#
# Jira structure:
#
# Epic
#   ├── Feature
#   │     ├── Subtask
#   │     ├── Subtask
#   │     └── Subtask
#   │
#   ├── Feature
#   │     ├── Subtask
#   │     └── Subtask
#
# ============================================================

@mcp.tool()
def publish_brd_hierarchy(
    source_issue_key: str,
    brd_content: str,
    backlog_json: str
) -> str:
    """
    Publish the Insurance BRD into Jira as:

    Epic
      └── Feature
            └── Subtask

    The BRD PDF is attached to the Epic.
    """

    try:

        # ====================================================
        # CHECK OUTPUT PROJECT
        # ====================================================

        if not JIRA_OUTPUT_PROJECT_KEY:

            return json.dumps(
                {
                    "success": False,
                    "error":
                        "JIRA_OUTPUT_PROJECT_KEY "
                        "is missing from .env"
                },
                indent=2
            )

        # ====================================================
        # VALIDATE JIRA HIERARCHY
        # ====================================================

        hierarchy_validation = (
            jira.validate_brd_hierarchy()
        )

        if isinstance(
            hierarchy_validation,
            dict
        ):

            if not hierarchy_validation.get(
                "valid",
                True
            ):

                return json.dumps(
                    {
                        "success": False,
                        "stage":
                            "jira_hierarchy_validation",
                        "details":
                            hierarchy_validation
                    },
                    indent=2
                )

        # ====================================================
        # GET PROJECT ISSUE TYPES
        # ====================================================

        issue_types = (
            jira.get_issue_types(
                JIRA_OUTPUT_PROJECT_KEY
            )
        )

        epic_type = issue_types.get(
            "epic"
        )

        feature_type = issue_types.get(
            "feature"
        )

        subtask_type = (
            issue_types.get(
                "sub-task"
            )
            or issue_types.get(
                "subtask"
            )
        )

        missing = []

        if not epic_type:

            missing.append(
                "Epic"
            )

        if not feature_type:

            missing.append(
                "Feature"
            )

        if not subtask_type:

            missing.append(
                "Subtask"
            )

        if missing:

            return json.dumps(
                {
                    "success": False,
                    "error":
                        "Missing Jira work types: "
                        + ", ".join(
                            missing
                        )
                },
                indent=2
            )

        # ====================================================
        # VALIDATE BRD
        # ====================================================

        brd_validation = (
            validate_brd_content(
                brd_content
            )
        )

        if not brd_validation.get(
            "valid",
            False
        ):

            return json.dumps(
                {
                    "success": False,
                    "stage":
                        "brd_validation",
                    "details":
                        brd_validation
                },
                indent=2
            )

        # ====================================================
        # PARSE BACKLOG
        # ====================================================

        try:

            backlog = json.loads(
                backlog_json
            )

        except json.JSONDecodeError:

            return json.dumps(
                {
                    "success": False,
                    "stage":
                        "backlog_parsing",
                    "error":
                        "The AI backlog JSON is invalid."
                },
                indent=2
            )

        # ====================================================
        # VALIDATE BACKLOG STRUCTURE
        # ====================================================

        if not isinstance(
            backlog,
            dict
        ):

            return json.dumps(
                {
                    "success": False,
                    "stage":
                        "backlog_validation",
                    "error":
                        "Backlog must be a JSON object."
                },
                indent=2
            )

        if not isinstance(
            backlog.get(
                "epic"
            ),
            dict
        ):

            return json.dumps(
                {
                    "success": False,
                    "stage":
                        "backlog_validation",
                    "error":
                        "Epic is missing."
                },
                indent=2
            )

        features = backlog.get(
            "features"
        )

        if not isinstance(
            features,
            list
        ):

            return json.dumps(
                {
                    "success": False,
                    "stage":
                        "backlog_validation",
                    "error":
                        "Features must be a list."
                },
                indent=2
            )

        if not features:

            return json.dumps(
                {
                    "success": False,
                    "stage":
                        "backlog_validation",
                    "error":
                        "At least one Feature is required."
                },
                indent=2
            )

        # ----------------------------------------------------
        # HARD CHECK:
        # Stories and Tasks are NOT allowed.
        # ----------------------------------------------------

        if backlog.get(
            "stories"
        ):

            return json.dumps(
                {
                    "success": False,
                    "stage":
                        "backlog_validation",
                    "error":
                        "Stories are not allowed. "
                        "Expected hierarchy: "
                        "Epic -> Feature -> Subtask."
                },
                indent=2
            )

        if backlog.get(
            "tasks"
        ):

            return json.dumps(
                {
                    "success": False,
                    "stage":
                        "backlog_validation",
                    "error":
                        "Tasks are not allowed. "
                        "Expected hierarchy: "
                        "Epic -> Feature -> Subtask."
                },
                indent=2
            )

        # ====================================================
        # LABELS
        # ====================================================

        source_label = clean_label(
            f"brd-source-{source_issue_key}"
        )

        base_labels = [
            "insurance",
            "brd-generated",
            source_label
        ]

        # ====================================================
        # CREATE EPIC
        # ====================================================

        epic_data = backlog.get(
            "epic",
            {}
        )

        epic_summary = epic_data.get(
            "summary",
            f"Insurance BRD - "
            f"{source_issue_key}"
        )

        epic_description = (
            epic_data.get(
                "description",
                ""
            )
        )

        epic_description += (
            "\n\nSource Jira Requirement: "
            + source_issue_key
        )

        epic_key = jira.create_issue(
            issue_type_id=epic_type,
            summary=epic_summary,
            description=epic_description,
            labels=base_labels + [
                "brd-epic"
            ]
        )

        created = {
            "success": True,
            "source_issue":
                source_issue_key,
            "epic":
                epic_key,
            "features": [],
            "subtasks": [],
            "stories": [],
            "tasks": [],
            "pdf": None,
            "epic_url":
                f"{JIRA_URL}/browse/{epic_key}"
        }

        # ====================================================
        # CREATE FEATURES UNDER EPIC
        # ====================================================

        for feature in features:

            if not isinstance(
                feature,
                dict
            ):

                return json.dumps(
                    {
                        "success": False,
                        "stage":
                            "feature_validation",
                        "error":
                            "Feature must be an object."
                    },
                    indent=2
                )

            feature_summary = (
                feature.get(
                    "summary",
                    ""
                ).strip()
            )

            if not feature_summary:

                return json.dumps(
                    {
                        "success": False,
                        "stage":
                            "feature_validation",
                        "error":
                            "Feature summary is missing."
                    },
                    indent=2
                )

            feature_description = (
                feature.get(
                    "description",
                    ""
                )
            )

            requirement_ids = (
                feature.get(
                    "brd_requirement_ids",
                    []
                )
            )

            if not isinstance(
                requirement_ids,
                list
            ):

                requirement_ids = []

            if requirement_ids:

                feature_description += (
                    "\n\nBRD Requirement IDs:\n"
                    + ", ".join(
                        str(item)
                        for item
                        in requirement_ids
                    )
                )

            feature_description += (
                "\n\nParent Epic: "
                + epic_key
            )

            feature_key = jira.create_issue(
                issue_type_id=feature_type,
                summary=feature_summary,
                description=feature_description,
                parent_key=epic_key,
                labels=base_labels + [
                    "brd-feature"
                ]
            )

            created[
                "features"
            ].append(
                feature_key
            )

            # =================================================
            # CREATE FEATURE SUBTASKS
            # =================================================

            subtasks = feature.get(
                "subtasks",
                []
            )

            if not isinstance(
                subtasks,
                list
            ):

                subtasks = []

            for subtask in subtasks:

                if not isinstance(
                    subtask,
                    dict
                ):

                    continue

                subtask_summary = (
                    subtask.get(
                        "summary",
                        "Feature Subtask"
                    ).strip()
                )

                subtask_description = (
                    subtask.get(
                        "description",
                        ""
                    )
                )

                subtask_description += (
                    "\n\nParent Feature: "
                    + feature_key
                )

                subtask_key = jira.create_issue(
                    issue_type_id=subtask_type,
                    summary=subtask_summary,
                    description=subtask_description,
                    parent_key=feature_key,
                    labels=base_labels + [
                        "brd-subtask"
                    ]
                )

                created[
                    "subtasks"
                ].append(
                    subtask_key
                )

        # ====================================================
        # SAVE LOCAL BRD
        # ====================================================

        project_dir = Path(
            os.path.dirname(
                os.path.abspath(
                    __file__
                )
            )
        )

        markdown_path = (
            project_dir
            / (
                f"Insurance_BRD_"
                f"{source_issue_key}.md"
            )
        )

        pdf_path = (
            project_dir
            / (
                f"Insurance_BRD_"
                f"{source_issue_key}.pdf"
            )
        )

        markdown_path.write_text(
            brd_content,
            encoding="utf-8"
        )

        # ====================================================
        # CREATE PDF
        # ====================================================

        create_brd_pdf(
            brd_content,
            str(pdf_path)
        )

        # ====================================================
        # UPLOAD PDF TO EPIC
        # ====================================================

        jira.upload_attachment(
            epic_key,
            str(pdf_path)
        )

        created[
            "pdf"
        ] = pdf_path.name

        # ====================================================
        # COMMENT ON SOURCE ISSUE
        # ====================================================

        jira.add_comment(
            source_issue_key,
            (
                "Insurance BRD generated successfully.\n"
                f"Generated Epic: {epic_key}\n"
                f"Epic URL: {created['epic_url']}\n"
                f"Features created: "
                f"{len(created['features'])}\n"
                f"Subtasks created: "
                f"{len(created['subtasks'])}\n"
                f"BRD PDF: {pdf_path.name}"
            )
        )

        return json.dumps(
            created,
            indent=2
        )

    except Exception as exc:

        return json.dumps(
            {
                "success": False,
                "error": str(exc)
            },
            indent=2
        )


# ============================================================
# TOOL 5 — SAVE BRD LOCALLY
# ============================================================

@mcp.tool()
def save_brd_file(
    file_name: str,
    markdown_content: str
) -> str:
    """
    Save the final Insurance BRD locally.
    """

    project_dir = Path(
        os.path.dirname(
            os.path.abspath(
                __file__
            )
        )
    )

    safe_name = os.path.basename(
        file_name
    )

    file_path = (
        project_dir
        / safe_name
    )

    file_path.write_text(
        markdown_content,
        encoding="utf-8"
    )

    return (
        f"BRD saved locally: "
        f"{file_path}"
    )


# ============================================================
# START MCP SERVER
# ============================================================

if __name__ == "__main__":

    mcp.run(
        transport="stdio"
    )