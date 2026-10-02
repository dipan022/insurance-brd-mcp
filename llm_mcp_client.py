import asyncio
import json
import os
import re
from pathlib import Path

import yaml

from dotenv import load_dotenv
from openai import OpenAI
from mcp import Client

from server import mcp


# ============================================================
# LOAD ENVIRONMENT
# ============================================================

ENV_FILE = Path(
    __file__
).with_name(
    ".env"
)

load_dotenv(
    dotenv_path=ENV_FILE,
    override=True
)


# ============================================================
# OPENROUTER
# ============================================================

OPENROUTER_API_KEY = os.getenv(
    "OPENROUTER_API_KEY"
)

OPENROUTER_MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "openrouter/free"
)

if not OPENROUTER_API_KEY:

    raise ValueError(
        "OPENROUTER_API_KEY is missing from .env"
    )


ai = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1"
)


# ============================================================
# LOAD PROMPTS
# ============================================================

PROMPTS_PATH = Path(
    __file__
).with_name(
    "prompts.yaml"
)

with PROMPTS_PATH.open(
    "r",
    encoding="utf-8"
) as file:

    prompts = yaml.safe_load(
        file
    )


BRD_PROMPT = prompts[
    "brd_system_prompt"
]

BRD_REVISION_PROMPT = prompts[
    "brd_revision_prompt"
]

BACKLOG_PROMPT = prompts[
    "backlog_system_prompt"
]

BACKLOG_REPAIR_PROMPT = prompts[
    "backlog_repair_prompt"
]


# ============================================================
# HELPERS
# ============================================================

def extract_issue_key(
    text: str
):

    match = re.search(
        r"\b[A-Z][A-Z0-9]+-\d+\b",
        text.upper()
    )

    if match:

        return match.group(
            0
        )

    return None


def get_tool_text(
    result
):

    parts = []

    for content in result.content:

        if (
            hasattr(
                content,
                "text"
            )
            and content.text
        ):

            parts.append(
                content.text
            )

    return "\n".join(
        parts
    )


def clean_json(
    text: str
):

    text = (
        text
        .replace(
            "```json",
            ""
        )
        .replace(
            "```",
            ""
        )
        .strip()
    )

    # Handle accidental text before JSON
    first_brace = text.find(
        "{"
    )

    last_brace = text.rfind(
        "}"
    )

    if (
        first_brace >= 0
        and last_brace > first_brace
    ):

        text = text[
            first_brace:last_brace + 1
        ]

    return text.strip()


# ============================================================
# NORMALIZE SUBTASK
# ============================================================

def normalize_subtask(
    subtask
):

    if isinstance(
        subtask,
        str
    ):

        return {
            "summary": subtask.strip(),
            "description": ""
        }

    if not isinstance(
        subtask,
        dict
    ):

        return {
            "summary": "",
            "description": ""
        }

    summary = (
        subtask.get(
            "summary"
        )
        or subtask.get(
            "title"
        )
        or subtask.get(
            "name"
        )
        or ""
    )

    description = (
        subtask.get(
            "description"
        )
        or ""
    )

    return {
        "summary":
            str(summary).strip(),
        "description":
            str(description).strip()
    }


# ============================================================
# NORMALIZE BACKLOG
#
# ONLY:
#
# Epic
#   └── Feature
#         └── Subtask
#
# ============================================================

def normalize_backlog(
    backlog
):

    if not isinstance(
        backlog,
        dict
    ):

        raise ValueError(
            "Backlog must be a JSON object."
        )

    # --------------------------------------------------------
    # EPIC
    # --------------------------------------------------------

    epic = backlog.get(
        "epic"
    )

    if not isinstance(
        epic,
        dict
    ):

        raise ValueError(
            "Epic is missing."
        )

    epic_summary = (
        epic.get(
            "summary"
        )
        or epic.get(
            "title"
        )
        or ""
    )

    epic_description = (
        epic.get(
            "description"
        )
        or ""
    )

    normalized = {
        "epic": {
            "summary":
                str(epic_summary).strip(),
            "description":
                str(epic_description).strip()
        },
        "features": []
    }

    # --------------------------------------------------------
    # FEATURES
    # --------------------------------------------------------

    raw_features = backlog.get(
        "features",
        []
    )

    if not isinstance(
        raw_features,
        list
    ):

        raise ValueError(
            "Features must be a list."
        )

    for feature in raw_features:

        if isinstance(
            feature,
            str
        ):

            feature = {
                "summary": feature
            }

        if not isinstance(
            feature,
            dict
        ):

            continue

        feature_summary = (
            feature.get(
                "summary"
            )
            or feature.get(
                "title"
            )
            or feature.get(
                "name"
            )
            or ""
        )

        feature_description = (
            feature.get(
                "description"
            )
            or ""
        )

        requirement_ids = (
            feature.get(
                "brd_requirement_ids"
            )
            or feature.get(
                "brdRequirementIds"
            )
            or []
        )

        if not isinstance(
            requirement_ids,
            list
        ):

            requirement_ids = [
                str(requirement_ids)
            ]

        raw_subtasks = (
            feature.get(
                "subtasks"
            )
            or feature.get(
                "subTasks"
            )
            or []
        )

        if not isinstance(
            raw_subtasks,
            list
        ):

            raw_subtasks = []

        subtasks = []

        for raw_subtask in raw_subtasks:

            normalized_subtask = (
                normalize_subtask(
                    raw_subtask
                )
            )

            if normalized_subtask[
                "summary"
            ]:

                subtasks.append(
                    normalized_subtask
                )

        normalized[
            "features"
        ].append(
            {
                "summary":
                    str(
                        feature_summary
                    ).strip(),

                "description":
                    str(
                        feature_description
                    ).strip(),

                "brd_requirement_ids":
                    [
                        str(item)
                        for item
                        in requirement_ids
                    ],

                "subtasks":
                    subtasks
            }
        )

    # --------------------------------------------------------
    # HARD REMOVE OLD HIERARCHY
    #
    # Stories and Tasks are deliberately not carried forward.
    # --------------------------------------------------------

    if backlog.get(
        "stories"
    ):

        raise ValueError(
            "AI generated Stories. "
            "Only Epic -> Feature -> Subtask is allowed."
        )

    if backlog.get(
        "tasks"
    ):

        raise ValueError(
            "AI generated Tasks. "
            "Only Epic -> Feature -> Subtask is allowed."
        )

    return normalized


# ============================================================
# VALIDATE BACKLOG
# ============================================================

def validate_backlog(
    backlog
):

    if not isinstance(
        backlog,
        dict
    ):

        raise ValueError(
            "Backlog is not an object."
        )

    # --------------------------------------------------------
    # EPIC
    # --------------------------------------------------------

    epic = backlog.get(
        "epic"
    )

    if not isinstance(
        epic,
        dict
    ):

        raise ValueError(
            "Epic is missing."
        )

    if not epic.get(
        "summary"
    ):

        raise ValueError(
            "Epic summary is missing."
        )

    # --------------------------------------------------------
    # FEATURES
    # --------------------------------------------------------

    features = backlog.get(
        "features"
    )

    if not isinstance(
        features,
        list
    ):

        raise ValueError(
            "Features must be a list."
        )

    if not features:

        raise ValueError(
            "At least one Feature is required."
        )

    # --------------------------------------------------------
    # STORIES / TASKS MUST NOT EXIST
    # --------------------------------------------------------

    if backlog.get(
        "stories"
    ):

        raise ValueError(
            "Stories are not allowed."
        )

    if backlog.get(
        "tasks"
    ):

        raise ValueError(
            "Tasks are not allowed."
        )

    # --------------------------------------------------------
    # FEATURES
    # --------------------------------------------------------

    for feature in features:

        if not isinstance(
            feature,
            dict
        ):

            raise ValueError(
                "Feature must be an object."
            )

        if not feature.get(
            "summary"
        ):

            raise ValueError(
                "Feature summary missing."
            )

        if not isinstance(
            feature.get(
                "subtasks",
                []
            ),
            list
        ):

            raise ValueError(
                "Feature subtasks must be a list."
            )

        for subtask in feature.get(
            "subtasks",
            []
        ):

            if not isinstance(
                subtask,
                dict
            ):

                raise ValueError(
                    "Subtask must be an object."
                )

            if not subtask.get(
                "summary"
            ):

                raise ValueError(
                    "Subtask summary missing."
                )


# ============================================================
# OPENROUTER CALL
# ============================================================

def call_openrouter(
    messages,
    max_tokens=6000,
    tools=None
):

    kwargs = {
        "model":
            OPENROUTER_MODEL,

        "messages":
            messages,

        "max_tokens":
            max_tokens,

        "timeout":
            90
    }

    if tools:

        kwargs[
            "tools"
        ] = tools

        kwargs[
            "tool_choice"
        ] = "auto"

    return (
        ai.chat.completions.create(
            **kwargs
        )
    )


# ============================================================
# MAIN
# ============================================================

async def run():

    user_request = input(
        "\nWhat do you want to do?\n> "
    ).strip()

    source_issue_key = (
        extract_issue_key(
            user_request
        )
    )

    if not source_issue_key:

        print(
            "\nPlease include a Jira issue key, "
            "for example KAN-1."
        )

        return

    print(
        "\nSource Jira issue:",
        source_issue_key
    )

    # ========================================================
    # CONNECT MCP
    # ========================================================

    async with Client(mcp) as client:

        print(
            "\nConnected to MCP server."
        )

        tools_result = (
            await client.list_tools()
        )

        print(
            "\nMCP tools available:"
        )

        for tool in (
            tools_result.tools
        ):

            print(
                "-",
                tool.name
            )

        # ====================================================
        # AI SELECTABLE MCP TOOLS
        # ====================================================

        ai_tool_names = {
            "get_jira_issue",
            "create_brd"
        }

        ai_tools = []

        for tool in (
            tools_result.tools
        ):

            if tool.name not in (
                ai_tool_names
            ):

                continue

            ai_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name":
                            tool.name,

                        "description":
                            tool.description
                            or "",

                        "parameters":
                            tool.input_schema
                    }
                }
            )

        # ====================================================
        # BRD GENERATION
        # ====================================================

        messages = [
            {
                "role":
                    "system",

                "content":
                    BRD_PROMPT
            },
            {
                "role":
                    "user",

                "content":
                    user_request
            }
        ]

        jira_read = False
        brd_tool_called = False
        final_brd = None

        # ====================================================
        # AI ↔ MCP LOOP
        # ====================================================

        for _ in range(8):

            print(
                "\nSending request to OpenRouter..."
            )

            response = call_openrouter(
                messages=messages,
                max_tokens=7000,
                tools=ai_tools
            )

            if not response.choices:

                print(
                    "\nOpenRouter returned no choices."
                )

                return

            assistant = (
                response
                .choices[0]
                .message
            )

            # ------------------------------------------------
            # FINAL BRD
            # ------------------------------------------------

            if not assistant.tool_calls:

                final_brd = (
                    assistant.content
                    or ""
                ).strip()

                break

            # ------------------------------------------------
            # RECORD TOOL CALLS
            # ------------------------------------------------

            messages.append(
                {
                    "role":
                        "assistant",

                    "content":
                        assistant.content
                        or "",

                    "tool_calls": [
                        {
                            "id":
                                call.id,

                            "type":
                                "function",

                            "function": {
                                "name":
                                    call.function.name,

                                "arguments":
                                    call.function.arguments
                            }
                        }
                        for call
                        in assistant.tool_calls
                    ]
                }
            )

            # ------------------------------------------------
            # EXECUTE MCP TOOLS
            # ------------------------------------------------

            for call in (
                assistant.tool_calls
            ):

                tool_name = (
                    call.function.name
                )

                try:

                    arguments = json.loads(
                        call.function.arguments
                    )

                except json.JSONDecodeError:

                    print(
                        "\nInvalid tool arguments:"
                    )

                    print(
                        call.function.arguments
                    )

                    return

                print(
                    "\nAI automatically selected:",
                    tool_name
                )

                print(
                    "Arguments:",
                    arguments
                )

                if (
                    tool_name
                    == "get_jira_issue"
                ):

                    jira_read = True

                elif (
                    tool_name
                    == "create_brd"
                ):

                    brd_tool_called = True

                result = (
                    await client.call_tool(
                        tool_name,
                        arguments
                    )
                )

                tool_output = (
                    get_tool_text(
                        result
                    )
                )

                print(
                    "\nMCP tool executed successfully."
                )

                messages.append(
                    {
                        "role":
                            "tool",

                        "tool_call_id":
                            call.id,

                        "content":
                            tool_output
                    }
                )

        # ====================================================
        # CHECK BRD GENERATION
        # ====================================================

        if not jira_read:

            print(
                "\nERROR: AI did not read the Jira issue."
            )

            return

        if not brd_tool_called:

            print(
                "\nERROR: AI did not call create_brd."
            )

            return

        if not final_brd:

            print(
                "\nERROR: No final BRD was generated."
            )

            return

        # ====================================================
        # VALIDATE BRD
        # ====================================================

        print(
            "\nValidating Insurance BRD..."
        )

        validation_result = (
            await client.call_tool(
                "validate_brd",
                {
                    "brd_content":
                        final_brd
                }
            )
        )

        validation_text = (
            get_tool_text(
                validation_result
            )
        )

        try:

            validation = json.loads(
                validation_text
            )

        except json.JSONDecodeError:

            print(
                "\nERROR: BRD validation returned invalid JSON."
            )

            print(
                validation_text
            )

            return

        # ====================================================
        # ONE AUTOMATIC BRD REPAIR
        # ====================================================

        if not validation.get(
            "valid",
            False
        ):

            print(
                "\nBRD validation failed."
            )

            print(
                validation_text
            )

            revision_response = (
                call_openrouter(
                    messages=[
                        {
                            "role":
                                "system",

                            "content":
                                BRD_REVISION_PROMPT
                        },
                        {
                            "role":
                                "user",

                            "content":
                                (
                                    "Previous BRD:\n\n"
                                    + final_brd
                                    + "\n\nValidation:\n"
                                    + validation_text
                                )
                        }
                    ],
                    max_tokens=7000
                )
            )

            if not revision_response.choices:

                print(
                    "\nBRD revision failed."
                )

                return

            final_brd = (
                revision_response
                .choices[0]
                .message
                .content
                or ""
            ).strip()

            validation_result = (
                await client.call_tool(
                    "validate_brd",
                    {
                        "brd_content":
                            final_brd
                    }
                )
            )

            validation_text = (
                get_tool_text(
                    validation_result
                )
            )

            try:

                validation = json.loads(
                    validation_text
                )

            except json.JSONDecodeError:

                print(
                    "\nERROR: BRD re-validation returned invalid JSON."
                )

                return

            if not validation.get(
                "valid",
                False
            ):

                print(
                    "\nBRD still failed validation."
                )

                print(
                    validation_text
                )

                return

        print(
            "\nBRD validation passed."
        )

        # ====================================================
        # SHOW FINAL BRD
        # ====================================================

        print("\n")
        print("=" * 70)
        print("FINAL INSURANCE BRD")
        print("=" * 70)

        print(
            final_brd
        )

        # ====================================================
        # GENERATE JIRA BACKLOG
        # ====================================================

        print(
            "\nGenerating Epic / Feature / Subtask structure..."
        )

        backlog_response = (
            call_openrouter(
                messages=[
                    {
                        "role":
                            "system",

                        "content":
                            BACKLOG_PROMPT
                    },
                    {
                        "role":
                            "user",

                        "content":
                            final_brd
                    }
                ],
                max_tokens=6000
            )
        )

        if not backlog_response.choices:

            print(
                "\nNo backlog response returned."
            )

            return

        backlog_text = (
            backlog_response
            .choices[0]
            .message
            .content
            or ""
        )

        backlog_text = clean_json(
            backlog_text
        )

        # ====================================================
        # PARSE + NORMALIZE BACKLOG
        # ====================================================

        try:

            backlog = json.loads(
                backlog_text
            )

            backlog = normalize_backlog(
                backlog
            )

            validate_backlog(
                backlog
            )

        except (
            json.JSONDecodeError,
            ValueError
        ) as first_error:

            print(
                "\nInitial backlog response invalid."
            )

            print(
                "Reason:",
                first_error
            )

            # =================================================
            # AUTOMATIC BACKLOG REPAIR
            # =================================================

            repair_response = (
                call_openrouter(
                    messages=[
                        {
                            "role":
                                "system",

                            "content":
                                BACKLOG_REPAIR_PROMPT
                        },
                        {
                            "role":
                                "user",

                            "content":
                                (
                                    final_brd
                                    + "\n\n"
                                    + "The previous backlog was invalid.\n"
                                    + "Reason: "
                                    + str(first_error)
                                )
                        }
                    ],
                    max_tokens=6000
                )
            )

            if not repair_response.choices:

                print(
                    "\nBacklog repair failed."
                )

                return

            backlog_text = (
                repair_response
                .choices[0]
                .message
                .content
                or ""
            )

            backlog_text = clean_json(
                backlog_text
            )

            try:

                backlog = json.loads(
                    backlog_text
                )

                backlog = normalize_backlog(
                    backlog
                )

                validate_backlog(
                    backlog
                )

            except (
                json.JSONDecodeError,
                ValueError
            ) as exc:

                print(
                    "\nBacklog validation failed:"
                )

                print(
                    exc
                )

                print(
                    "\nReturned backlog:"
                )

                print(
                    backlog_text
                )

                return

        # ====================================================
        # BACKLOG READY
        # ====================================================

        print(
            "\nBacklog validation passed."
        )

        print(
            "Epic:",
            backlog[
                "epic"
            ][
                "summary"
            ]
        )

        print(
            "Features:",
            len(
                backlog.get(
                    "features",
                    []
                )
            )
        )

        total_subtasks = sum(
            len(
                feature.get(
                    "subtasks",
                    []
                )
            )
            for feature
            in backlog.get(
                "features",
                []
            )
        )

        print(
            "Subtasks:",
            total_subtasks
        )

        # ====================================================
        # PUBLISH TO JIRA
        # ====================================================

        print(
            "\nPublishing complete Insurance BRD to Jira..."
        )

        publish_result = (
            await client.call_tool(
                "publish_brd_hierarchy",
                {
                    "source_issue_key":
                        source_issue_key,

                    "brd_content":
                        final_brd,

                    "backlog_json":
                        json.dumps(
                            backlog,
                            ensure_ascii=False
                        )
                }
            )
        )

        publish_output = (
            get_tool_text(
                publish_result
            )
        )

        print("\n")
        print("=" * 70)
        print("JIRA BRD COMPLETED")
        print("=" * 70)

        print(
            publish_output
        )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    asyncio.run(
        run()
    )