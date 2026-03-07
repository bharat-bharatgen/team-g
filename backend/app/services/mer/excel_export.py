"""
MER Excel Export Service

Generates an .xlsx from a MERResultModel snapshot.
Coloring matches frontend UI:

| Condition                               | Color       |
|-----------------------------------------|-------------|
| Flag (non-ideal answer)                 | Red         |
| source == "user"                        | Light Green |
| confidence >= 0.9                       | Light Green |
| confidence >= 0.8                       | Yellow      |
| confidence < 0.8                        | Red         |
| confidence is None                      | White       |
"""

from typing import List

from openpyxl import Workbook

from app.models.mer_result import MERField
from app.services.excel_utils import (
    FILL_GREEN,
    FILL_RED,
    FILL_WHITE,
    FILL_YELLOW,
    ColSpec,
    RowStyle,
    workbook_to_bytes,
    write_data_sheet,
    write_meta_row,
)

COLUMNS = [
    ColSpec("Page", width=8, align="center"),
    ColSpec("Section", width=20),
    ColSpec("Field", width=35),
    ColSpec("Answer", width=20),
    ColSpec("Details", width=35),
    ColSpec("Confidence", width=12, align="center"),
    ColSpec("Source", width=10),
]


# Questions where "Yes" is the IDEAL answer (not a flag)
# These are positive questions where "No" would be concerning
POSITIVE_QUESTIONS = {
    "5) Does applicant appear medically fit?",
    "7) Is your vision and hearing normal?",
}


def _is_flag(field: MERField) -> bool:
    """Check if field represents a non-ideal/flagged answer (matches frontend isNonIdealAnswer)."""
    answer = (field.answer or "").lower()
    key = field.key or ""
    
    # "Yes" on negative questions (indicates medical conditions) is a flag
    if answer == "yes" and key not in POSITIVE_QUESTIONS:
        return True
    # "No" on positive questions (not fit, not normal) is a flag
    if answer == "no" and key in POSITIVE_QUESTIONS:
        return True
    return False


def _get_row_style(field: MERField) -> RowStyle:
    """Determine row styling for a field (matches frontend UI)."""
    if _is_flag(field):
        return RowStyle(fill=FILL_RED)
    if field.source == "user":
        return RowStyle(fill=FILL_GREEN)
    if field.confidence is None:
        return RowStyle()
    if field.confidence >= 0.9:
        return RowStyle(fill=FILL_GREEN)
    if field.confidence >= 0.8:
        return RowStyle(fill=FILL_YELLOW)
    return RowStyle(fill=FILL_RED)


def _field_to_row(field: MERField) -> list:
    """Convert a MERField to an Excel row (without internal id)."""
    return [
        field.page,
        field.section,
        field.key,
        field.answer or "",
        field.details or "",
        round(field.confidence, 2) if field.confidence is not None else "",
        field.source,
    ]


def generate_excel(fields: List[MERField], case_id: str, version: int) -> bytes:
    """
    Generate an Excel workbook from MER fields.

    The id column is stored in a hidden column (column A) so that
    re-import can match fields back to their IDs.
    """
    wb = Workbook()
    ws = wb.active
    ws.title = f"MER v{version}"

    rows = [_field_to_row(f) for f in fields]
    styles = [_get_row_style(f) for f in fields]
    ids = [f.id for f in fields]

    write_data_sheet(
        ws, COLUMNS, rows,
        row_styles=styles,
        include_hidden_id=True,
        ids=ids,
    )

    write_meta_row(ws, len(fields), case_id, version, extra={"fields_count": str(len(fields))})

    return workbook_to_bytes(wb)
