import html
import re

from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import (
    ParagraphStyle,
    getSampleStyleSheet,
)
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib import colors


def clean_text(
    text: str
) -> str:

    replacements = {
        "–": "-",
        "—": "-",
        "’": "'",
        "‘": "'",
        "“": '"',
        "”": '"',
        "•": "-",
        "→": "->",
        "≤": "<=",
        "≥": ">=",
    }

    for old, new in replacements.items():

        text = text.replace(
            old,
            new
        )

    return text


def markdown_to_html(
    text: str
) -> str:

    text = clean_text(
        text
    )

    text = html.escape(
        text
    )

    text = re.sub(
        r"\*\*(.*?)\*\*",
        r"<b>\1</b>",
        text
    )

    text = re.sub(
        r"`(.*?)`",
        r"<font name='Courier'>\1</font>",
        text
    )

    return text


def table_separator(
    line: str
) -> bool:

    return bool(
        re.match(
            r"^\s*\|?\s*:?-+:?\s*"
            r"(\|\s*:?-+:?\s*)+\|?\s*$",
            line
        )
    )


def table_cells(
    line: str
):

    return [
        clean_text(
            cell.strip()
        )
        for cell
        in line.strip("|").split("|")
    ]


def footer(
    canvas,
    document
):

    canvas.saveState()

    canvas.setFont(
        "Helvetica",
        8
    )

    canvas.drawString(
        18 * mm,
        10 * mm,
        "Insurance BRD Management"
    )

    canvas.drawRightString(
        A4[0] - 18 * mm,
        10 * mm,
        f"Page {document.page}"
    )

    canvas.restoreState()


def create_brd_pdf(
    markdown_content: str,
    pdf_path: str
):

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "BRDTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=25,
        alignment=TA_CENTER,
        spaceAfter=18,
    )

    h1_style = ParagraphStyle(
        "BRDH1",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=20,
        spaceBefore=14,
        spaceAfter=8,
    )

    h2_style = ParagraphStyle(
        "BRDH2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        spaceBefore=10,
        spaceAfter=6,
    )

    h3_style = ParagraphStyle(
        "BRDH3",
        parent=styles["Heading3"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        spaceBefore=8,
        spaceAfter=4,
    )

    body_style = ParagraphStyle(
        "BRDBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13.5,
        spaceAfter=5,
    )

    bullet_style = ParagraphStyle(
        "BRDBullet",
        parent=body_style,
        leftIndent=14,
        firstLineIndent=-8,
    )

    document = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="Insurance Business Requirement Document",
        author="Insurance BRD Management MCP",
    )

    flowables = []

    lines = markdown_content.splitlines()

    index = 0

    while index < len(lines):

        line = lines[index].strip()

        if not line:

            flowables.append(
                Spacer(1, 4)
            )

            index += 1

            continue

        # ----------------------------------------------------
        # TABLE
        # ----------------------------------------------------

        if (
            "|" in line
            and index + 1 < len(lines)
            and table_separator(
                lines[index + 1].strip()
            )
        ):

            rows = [
                table_cells(
                    line
                )
            ]

            index += 2

            while (
                index < len(lines)
                and "|" in lines[index]
                and lines[index].strip()
            ):

                rows.append(
                    table_cells(
                        lines[index].strip()
                    )
                )

                index += 1

            column_count = max(
                len(row)
                for row in rows
            )

            normalized = []

            for row in rows:

                row += [
                    ""
                ] * (
                    column_count
                    - len(row)
                )

                normalized.append(
                    [
                        Paragraph(
                            markdown_to_html(
                                cell
                            ),
                            body_style
                        )
                        for cell
                        in row
                    ]
                )

            table = Table(
                normalized,
                repeatRows=1,
                hAlign="LEFT",
                colWidths=[
                    (
                        A4[0]
                        - 36 * mm
                    )
                    / column_count
                ] * column_count,
            )

            table.setStyle(
                TableStyle(
                    [
                        (
                            "GRID",
                            (0, 0),
                            (-1, -1),
                            0.5,
                            colors.grey
                        ),
                        (
                            "BACKGROUND",
                            (0, 0),
                            (-1, 0),
                            colors.lightgrey
                        ),
                        (
                            "VALIGN",
                            (0, 0),
                            (-1, -1),
                            "TOP"
                        ),
                        (
                            "LEFTPADDING",
                            (0, 0),
                            (-1, -1),
                            5
                        ),
                        (
                            "RIGHTPADDING",
                            (0, 0),
                            (-1, -1),
                            5
                        ),
                        (
                            "TOPPADDING",
                            (0, 0),
                            (-1, -1),
                            5
                        ),
                        (
                            "BOTTOMPADDING",
                            (0, 0),
                            (-1, -1),
                            5
                        ),
                    ]
                )
            )

            flowables.append(
                table
            )

            flowables.append(
                Spacer(1, 8)
            )

            continue

        # ----------------------------------------------------
        # HEADINGS
        # ----------------------------------------------------

        if line.startswith(
            "# "
        ):

            flowables.append(
                Paragraph(
                    markdown_to_html(
                        line[2:]
                    ),
                    title_style
                )
            )

        elif line.startswith(
            "## "
        ):

            flowables.append(
                Paragraph(
                    markdown_to_html(
                        line[3:]
                    ),
                    h1_style
                )
            )

        elif line.startswith(
            "### "
        ):

            flowables.append(
                Paragraph(
                    markdown_to_html(
                        line[4:]
                    ),
                    h2_style
                )
            )

        elif line.startswith(
            "#### "
        ):

            flowables.append(
                Paragraph(
                    markdown_to_html(
                        line[5:]
                    ),
                    h3_style
                )
            )

        # ----------------------------------------------------
        # BULLETS
        # ----------------------------------------------------

        elif (
            line.startswith(
                "- "
            )
            or line.startswith(
                "* "
            )
        ):

            flowables.append(
                Paragraph(
                    "- "
                    + markdown_to_html(
                        line[2:]
                    ),
                    bullet_style
                )
            )

        # ----------------------------------------------------
        # NUMBERED LIST
        # ----------------------------------------------------

        elif re.match(
            r"^\d+\.\s+",
            line
        ):

            flowables.append(
                Paragraph(
                    markdown_to_html(
                        line
                    ),
                    body_style
                )
            )

        # ----------------------------------------------------
        # NORMAL PARAGRAPH
        # ----------------------------------------------------

        else:

            flowables.append(
                Paragraph(
                    markdown_to_html(
                        line
                    ),
                    body_style
                )
            )

        index += 1

    document.build(
        flowables,
        onFirstPage=footer,
        onLaterPages=footer,
    )