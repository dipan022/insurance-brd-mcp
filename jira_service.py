import os
from pathlib import Path

import httpx
from dotenv import load_dotenv


# ============================================================
# LOAD .ENV
# ============================================================

ENV_FILE = Path(__file__).with_name(".env")

load_dotenv(
    dotenv_path=ENV_FILE,
    override=True
)


# ============================================================
# JIRA SERVICE
# ============================================================

class JiraService:

    # ========================================================
    # INITIALIZE
    # ========================================================

    def __init__(self):

        self.base_url = os.getenv(
            "JIRA_URL"
        )

        self.email = os.getenv(
            "JIRA_EMAIL"
        )

        self.api_token = os.getenv(
            "JIRA_API_TOKEN"
        )

        self.source_project_key = os.getenv(
            "JIRA_SOURCE_PROJECT_KEY",
            "KAN"
        )

        self.output_project_key = os.getenv(
            "JIRA_OUTPUT_PROJECT_KEY"
        )

        missing = []

        if not self.base_url:
            missing.append("JIRA_URL")

        if not self.email:
            missing.append("JIRA_EMAIL")

        if not self.api_token:
            missing.append("JIRA_API_TOKEN")

        if not self.output_project_key:
            missing.append(
                "JIRA_OUTPUT_PROJECT_KEY"
            )

        if missing:

            raise ValueError(
                "Missing Jira configuration: "
                + ", ".join(missing)
            )

        self.base_url = self.base_url.rstrip(
            "/"
        )

        self.auth = (
            self.email,
            self.api_token
        )

    # ========================================================
    # GET ISSUE
    # ========================================================

    def get_issue(
        self,
        issue_key: str
    ):

        response = httpx.get(
            f"{self.base_url}/rest/api/3/issue/"
            f"{issue_key}",
            auth=self.auth,
            headers={
                "Accept": "application/json"
            },
            timeout=30
        )

        if response.status_code != 200:

            raise RuntimeError(
                f"Unable to retrieve Jira issue "
                f"{issue_key}.\n"
                f"Status: {response.status_code}\n"
                f"{response.text}"
            )

        return response.json()

    # ========================================================
    # GET PROJECT
    # ========================================================

    def get_project(
        self,
        project_key: str = None
    ):

        project_key = (
            project_key
            or self.output_project_key
        )

        response = httpx.get(
            f"{self.base_url}/rest/api/3/project/"
            f"{project_key}",
            auth=self.auth,
            headers={
                "Accept": "application/json"
            },
            timeout=30
        )

        if response.status_code != 200:

            raise RuntimeError(
                f"Unable to retrieve project "
                f"{project_key}.\n"
                f"Status: {response.status_code}\n"
                f"{response.text}"
            )

        return response.json()

    # ========================================================
    # GET ISSUE TYPE DETAILS FOR PROJECT
    # ========================================================

    def get_issue_type_details(
        self,
        project_key: str = None
    ):

        project = self.get_project(
            project_key
        )

        project_id = project["id"]

        response = httpx.get(
            f"{self.base_url}/rest/api/3/issuetype/project",
            auth=self.auth,
            headers={
                "Accept": "application/json"
            },
            params={
                "projectId": project_id
            },
            timeout=30
        )

        if response.status_code != 200:

            raise RuntimeError(
                "Unable to retrieve Jira issue type details.\n"
                f"Status: {response.status_code}\n"
                f"{response.text}"
            )

        return response.json()

    # ========================================================
    # GET ISSUE TYPES FOR PROJECT
    # ========================================================

    def get_issue_types(
        self,
        project_key: str = None
    ):

        issue_types = self.get_issue_type_details(
            project_key
        )

        result = {}

        for item in issue_types:

            name = (
                item.get(
                    "name",
                    ""
                )
                .strip()
                .lower()
            )

            if name:

                result[name] = item.get(
                    "id"
                )

        return result

    # ========================================================
    # GET HIERARCHY
    # ========================================================
    #
    # Simplified project:
    #     Use /project/{id}/hierarchy
    #
    # Non-simplified/company-managed project:
    #     Build hierarchy from issue-type metadata.
    #
    # Jira's project hierarchy endpoint is intended for
    # next-gen/simplified projects.
    # ========================================================

    def get_hierarchy(
        self,
        project_key: str = None
    ):

        project = self.get_project(
            project_key
        )

        project_id = project["id"]

        # ----------------------------------------------------
        # SIMPLIFIED / NEXT-GEN PROJECT
        # ----------------------------------------------------

        if project.get(
            "simplified",
            False
        ):

            response = httpx.get(
                f"{self.base_url}/rest/api/3/project/"
                f"{project_id}/hierarchy",
                auth=self.auth,
                headers={
                    "Accept": "application/json"
                },
                timeout=30
            )

            if response.status_code != 200:

                raise RuntimeError(
                    "Unable to retrieve Jira hierarchy.\n"
                    f"Status: {response.status_code}\n"
                    f"{response.text}"
                )

            return response.json()

        # ----------------------------------------------------
        # NON-SIMPLIFIED / COMPANY-MANAGED PROJECT
        # ----------------------------------------------------

        issue_types = self.get_issue_type_details(
            project_key
        )

        hierarchy_levels = {}

        for item in issue_types:

            name = (
                item.get(
                    "name",
                    ""
                )
                .strip()
            )

            if not name:
                continue

            # Jira issue type details normally provide
            # hierarchyLevel for standard issue types.
            level = item.get(
                "hierarchyLevel"
            )

            # Subtask types are level -1.
            if item.get(
                "subtask",
                False
            ):

                level = -1

            if level is None:
                continue

            hierarchy_levels.setdefault(
                level,
                []
            ).append(
                {
                    "id": item.get(
                        "id"
                    ),
                    "name": name
                }
            )

        hierarchy = []

        for level in sorted(
            hierarchy_levels.keys(),
            reverse=True
        ):

            if level == 1:

                level_name = "Epic"

            elif level == 0:

                level_name = "Base"

            elif level == -1:

                level_name = "Subtask"

            else:

                level_name = (
                    f"Level {level}"
                )

            hierarchy.append(
                {
                    "level": level,
                    "name": level_name,
                    "issueTypes":
                        hierarchy_levels[level]
                }
            )

        return {
            "hierarchy": hierarchy,
            "projectId": project_id,
            "simplified": False
        }

    # ========================================================
    # VALIDATE REQUIRED BRD HIERARCHY
    # ========================================================

    def validate_brd_hierarchy(
    self,
    project_key: str = None):

        hierarchy = self.get_hierarchy(project_key)

        detected = {}

        for level in hierarchy.get(
            "hierarchy",
            []
        ):

            level_number = level.get(
                "level"
            )

            for issue_type in level.get(
                "issueTypes",
                []
            ):

                name = (
                    issue_type.get(
                        "name",
                        ""
                    )
                    .strip()
                    .lower()
                )

                if name:

                    detected[name] = level_number

        # ----------------------------------------------------
        # REQUIRED STRUCTURE
        # ----------------------------------------------------
        #
        # Epic                 -> Level 1
        # Feature / Story/Task -> Level 0
        # Subtask              -> Level -1
        # ----------------------------------------------------

        expected = {
            "epic": 1,
            "feature": 0,
            "story": 0,
            "task": 0
        }

        # ----------------------------------------------------
        # SUBTASK NAME CAN VARY
        # ----------------------------------------------------

        if "sub-task" in detected:

            expected[
                "sub-task"
            ] = -1

        elif "subtask" in detected:

            expected[
                "subtask"
            ] = -1

        else:

            expected[
                "subtask"
            ] = -1

        # ----------------------------------------------------
        # VALIDATE
        # ----------------------------------------------------

        problems = []

        for name, expected_level in expected.items():

            actual_level = detected.get(
                name
            )

            if actual_level != expected_level:

                problems.append(
                    f"{name}: expected level "
                    f"{expected_level}, "
                    f"found {actual_level}"
                )

        if problems:

            raise RuntimeError(
                "Jira output project hierarchy is not "
                "configured as Epic → Feature/Story/Task "
                "→ Subtask.\n"
                + "\n".join(
                    problems
                )
            )

        return detected

    # ========================================================
    # ALIAS FOR SERVER.PY
    # ========================================================

    def validate_hierarchy(self, project_key: str = None):
      return self.validate_brd_hierarchy(project_key)

    # ========================================================
    # MARKDOWN → JIRA ADF
    # ========================================================

    @staticmethod
    def markdown_to_adf(
        markdown_text: str
    ):

        content = []

        for raw_line in markdown_text.splitlines():

            line = raw_line.strip()

            if not line:

                continue

            # ------------------------------------------------
            # H3
            # ------------------------------------------------

            if line.startswith(
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
                                "text": line[4:].strip()
                            }
                        ]
                    }
                )

            # ------------------------------------------------
            # H2
            # ------------------------------------------------

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
                                "text": line[3:].strip()
                            }
                        ]
                    }
                )

            # ------------------------------------------------
            # H1
            # ------------------------------------------------

            elif line.startswith(
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
                                "text": line[2:].strip()
                            }
                        ]
                    }
                )

            # ------------------------------------------------
            # BULLET
            # ------------------------------------------------

            elif line.startswith(
                "- "
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
                                                "text": (
                                                    line[2:].strip()
                                                )
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                )

            # ------------------------------------------------
            # NUMBERED LIST
            # ------------------------------------------------

            elif (
                len(line) > 2
                and line[0].isdigit()
                and ". " in line[:4]
            ):

                text = line.split(
                    ". ",
                    1
                )[1]

                content.append(
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": text
                            }
                        ]
                    }
                )

            # ------------------------------------------------
            # NORMAL PARAGRAPH
            # ------------------------------------------------

            else:

                content.append(
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": line
                            }
                        ]
                    }
                )

        return {
            "type": "doc",
            "version": 1,
            "content": content
        }

    # ========================================================
    # CREATE ISSUE
    # ========================================================

    def create_issue(
        self,
        issue_type_id: str,
        summary: str,
        description: str,
        parent_key: str = None,
        labels=None
    ):

        fields = {
            "project": {
                "key": self.output_project_key
            },
            "summary": summary[:255],
            "issuetype": {
                "id": issue_type_id
            },
            "description": self.markdown_to_adf(
                description
            )
        }

        # ----------------------------------------------------
        # PARENT
        # ----------------------------------------------------

        if parent_key:

            fields["parent"] = {
                "key": parent_key
            }

        # ----------------------------------------------------
        # LABELS
        # ----------------------------------------------------

        if labels:

            fields["labels"] = labels

        # ----------------------------------------------------
        # CREATE ISSUE
        # ----------------------------------------------------

        response = httpx.post(
            f"{self.base_url}/rest/api/3/issue",
            auth=self.auth,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json"
            },
            json={
                "fields": fields
            },
            timeout=60
        )

        if response.status_code not in (
            200,
            201
        ):

            raise RuntimeError(
                "Jira issue creation failed.\n"
                f"Summary: {summary}\n"
                f"Status: {response.status_code}\n"
                f"{response.text}"
            )

        return response.json()["key"]

    # ========================================================
    # ADD COMMENT
    # ========================================================

    def add_comment(
        self,
        issue_key: str,
        message: str
    ):

        response = httpx.post(
            f"{self.base_url}/rest/api/3/issue/"
            f"{issue_key}/comment",
            auth=self.auth,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json"
            },
            json={
                "body": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": message
                                }
                            ]
                        }
                    ]
                }
            },
            timeout=30
        )

        if response.status_code not in (
            200,
            201
        ):

            raise RuntimeError(
                "Unable to add Jira comment.\n"
                f"Issue: {issue_key}\n"
                f"Status: {response.status_code}\n"
                f"{response.text}"
            )

        return True

    # ========================================================
    # GET LINK TYPES
    # ========================================================

    def get_link_types(self):

        response = httpx.get(
            f"{self.base_url}/rest/api/3/issueLinkType",
            auth=self.auth,
            headers={
                "Accept": "application/json"
            },
            timeout=30
        )

        if response.status_code != 200:

            return []

        return response.json().get(
            "issueLinkTypes",
            []
        )

    # ========================================================
    # LINK ISSUES
    # ========================================================

    def link_issues(
        self,
        issue_a: str,
        issue_b: str,
        link_name: str = "Relates",
        link_type: str = None
    ):

        # Supports both parameter names:
        #
        # link_name="Relates"
        #
        # and
        #
        # link_type="Relates"

        if link_type:

            link_name = link_type

        link_types = self.get_link_types()

        selected = None

        for item in link_types:

            if (
                item.get(
                    "name",
                    ""
                )
                .strip()
                .lower()
                == link_name.lower()
            ):

                selected = item
                break

        if not selected:

            return False

        response = httpx.post(
            f"{self.base_url}/rest/api/3/issueLink",
            auth=self.auth,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json"
            },
            json={
                "type": {
                    "name": selected["name"]
                },
                "inwardIssue": {
                    "key": issue_a
                },
                "outwardIssue": {
                    "key": issue_b
                }
            },
            timeout=30
        )

        if response.status_code != 201:

            return False

        return True

    # ========================================================
    # UPLOAD ATTACHMENT
    # ========================================================

    def upload_attachment(
        self,
        issue_key: str,
        file_path: str
    ):

        path = Path(
            file_path
        )

        if not path.exists():

            raise FileNotFoundError(
                f"Attachment file not found: {path}"
            )

        with path.open(
            "rb"
        ) as file:

            response = httpx.post(
                f"{self.base_url}/rest/api/3/issue/"
                f"{issue_key}/attachments",
                auth=self.auth,
                headers={
                    "Accept": "application/json",
                    "X-Atlassian-Token": "no-check"
                },
                files={
                    "file": (
                        path.name,
                        file,
                        "application/pdf"
                    )
                },
                timeout=60
            )

        if response.status_code not in (
            200,
            201
        ):

            raise RuntimeError(
                "Jira attachment upload failed.\n"
                f"Status: {response.status_code}\n"
                f"{response.text}"
            )

        return response.json()