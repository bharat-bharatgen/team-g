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

import io
from typing import List

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from app.models.mer_result import MERField


# ─── Color definitions ──────────────────────────────────────────────────────
FILL_WHITE = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
FILL_YELLOW = PatternFill(start_color="FFFF99", end_color="FFFF99", fill_type="solid")
FILL_RED = PatternFill(start_color="FF9999", end_color="FF9999", fill_type="solid")
FILL_GREEN = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
FILL_HEADER = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")

FONT_HEADER = Font(name="Calibri", bold=True, size=11, color="FFFFFF")
FONT_DEFAULT = Font(name="Calibri", size=11)

ALIGN_CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
ALIGN_LEFT = Alignment(horizontal="left", vertical="center", wrap_text=True)

THIN_BORDER = Border(
    left=Side(style="thin"),
    right=Side(style="thin"),
    top=Side(style="thin"),
    bottom=Side(style="thin"),
)

# Columns that appear in the Excel (id is hidden)
COLUMNS = ["Page", "Section", "Field", "Answer", "Details", "Confidence", "Source"]


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


def _get_fill(field: MERField) -> PatternFill:
    """Determine the cell background color for a field (matches frontend UI)."""
    # Flag (non-ideal answer) takes priority
    if _is_flag(field):
        return FILL_RED
    # User edited
    if field.source == "user":
        return FILL_GREEN
    # Null confidence → no highlighting
    if field.confidence is None:
        return FILL_WHITE
    # Confidence-based coloring (90%/80% thresholds like frontend)
    if field.confidence >= 0.9:
        return FILL_GREEN
    if field.confidence >= 0.8:
        return FILL_YELLOW
    return FILL_RED


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

    Args:
        fields: List of MERField from the MERResultModel
        case_id: For the sheet title
        version: For the sheet title

    Returns:
        Excel file as bytes
    """
    wb = Workbook()
    ws = wb.active
    ws.title = f"MER v{version}"

    # ── Hidden ID column (column A) ──────────────────────────────
    ws.column_dimensions["A"].hidden = True
    ws.cell(row=1, column=1, value="__field_id__")

    # ── Visible header row (columns B onward) ────────────────────
    for col_idx, col_name in enumerate(COLUMNS, start=2):
        cell = ws.cell(row=1, column=col_idx, value=col_name)
        cell.font = FONT_HEADER
        cell.fill = FILL_HEADER
        cell.alignment = ALIGN_CENTER
        cell.border = THIN_BORDER

    # ── Data rows ────────────────────────────────────────────────
    for row_idx, field in enumerate(fields, start=2):
        # Hidden id
        id_cell = ws.cell(row=row_idx, column=1, value=field.id)
        id_cell.font = Font(size=1)

        fill = _get_fill(field)
        row_data = _field_to_row(field)

        for col_idx, value in enumerate(row_data, start=2):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.font = FONT_DEFAULT
            cell.fill = fill
            cell.alignment = ALIGN_LEFT if col_idx > 2 else ALIGN_CENTER
            cell.border = THIN_BORDER

    # ── Auto-fit column widths (approximate) ─────────────────────
    col_widths = {
        "B": 8,    # Page
        "C": 20,   # Section
        "D": 35,   # Field
        "E": 20,   # Answer
        "F": 35,   # Details
        "G": 12,   # Confidence
        "H": 10,   # Source
    }
    for col_letter, width in col_widths.items():
        ws.column_dimensions[col_letter].width = width

    # ── Metadata row at bottom (for import validation) ───────────
    meta_row = len(fields) + 3
    ws.cell(row=meta_row, column=1, value="__meta__")
    ws.cell(row=meta_row, column=2, value=f"case_id={case_id}")
    ws.cell(row=meta_row, column=3, value=f"version={version}")
    ws.cell(row=meta_row, column=4, value=f"fields_count={len(fields)}")

    # Hide the metadata row
    ws.row_dimensions[meta_row].hidden = True

    # Freeze top row
    ws.freeze_panes = "B2"

    # Write to bytes
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()
