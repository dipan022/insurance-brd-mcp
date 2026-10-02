import re
from pathlib import Path

import yaml


PROMPTS_FILE = Path(
    __file__
).with_name(
    "prompts.yaml"
)


def load_config():

    with PROMPTS_FILE.open(
        "r",
        encoding="utf-8"
    ) as file:

        return yaml.safe_load(
            file
        )


def validate_brd_text(
    brd_text: str
):

    config = load_config()

    required_sections = config.get(
        "brd_sections",
        []
    )

    insurance_keywords = config.get(
        "insurance_keywords",
        []
    )

    text_lower = brd_text.lower()

    missing_sections = []

    for section in required_sections:

        if section.lower() not in text_lower:

            missing_sections.append(
                section
            )

    found_keywords = [
        keyword
        for keyword in insurance_keywords
        if keyword.lower() in text_lower
    ]

    fr_ids = set(
        re.findall(
            r"\bFR-\d+\b",
            brd_text.upper()
        )
    )

    ac_ids = set(
        re.findall(
            r"\bAC-\d+\b",
            brd_text.upper()
        )
    )

    problems = []

    if missing_sections:

        problems.append(
            "Missing sections: "
            + ", ".join(
                missing_sections
            )
        )

    if len(found_keywords) < 3:

        problems.append(
            "Insufficient insurance-domain content."
        )

    if not fr_ids:

        problems.append(
            "No FR requirement IDs found."
        )

    if not ac_ids:

        problems.append(
            "No AC acceptance-criteria IDs found."
        )

    if len(brd_text.strip()) < 1800:

        problems.append(
            "BRD content is too short."
        )

    return {
        "valid": not problems,
        "missing_sections": missing_sections,
        "insurance_keywords_found":
            found_keywords,
        "functional_requirement_count":
            len(fr_ids),
        "acceptance_criteria_count":
            len(ac_ids),
        "problems": problems
    }