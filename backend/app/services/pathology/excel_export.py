"""
Pathology Excel Export Service

Generates an .xlsx from a PathologyResultModel snapshot.

Coloring and formatting (matches frontend UI):
| Condition                | Style                              |
|--------------------------|------------------------------------|
| source == "user"         | Light Green background             |
| range_status == abnormal | Gray background + Bold red text    |
| Otherwise                | White background                   |
"""

import io
from typing import List

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from app.models.pathology_result import PathologyField


# ─── Color definitions ──────────────────────────────────────────────────────
FILL_WHITE = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
FILL_GREEN = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
FILL_GRAY = PatternFill(start_color="E5E5E5", end_color="E5E5E5", fill_type="solid")  # gray-100 equivalent
FILL_HEADER = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")

FONT_HEADER = Font(name="Calibri", bold=True, size=11, color="FFFFFF")
FONT_DEFAULT = Font(name="Calibri", size=11)
FONT_BOLD = Font(name="Calibri", size=11, bold=True)
FONT_RED_BOLD = Font(name="Calibri", size=11, bold=True, color="DC2626")  # red-600 equivalent

ALIGN_CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
ALIGN_LEFT = Alignment(horizontal="left", vertical="center", wrap_text=True)

THIN_BORDER = Border(
    left=Side(style="thin"),
    right=Side(style="thin"),
    top=Side(style="thin"),
    bottom=Side(style="thin"),
)

# Columns that appear in the Excel (id is hidden)
# Added "Standard Range" column for config range
COLUMNS = ["Parameter", "Value", "Unit", "Report Range", "Standard Range", "Status", "Method", "Is Standard", "Source"]

# Column indices (1-based, after hidden column A)
COL_PARAMETER = 2
COL_VALUE = 3
COL_UNIT = 4
COL_REPORT_RANGE = 5
COL_STANDARD_RANGE = 6
COL_STATUS = 7
COL_METHOD = 8
COL_IS_STANDARD = 9
COL_SOURCE = 10


def _get_fill(field: PathologyField) -> PatternFill:
    """Determine the cell background color for a field (matches frontend UI)."""
    if field.source == "user":
        return FILL_GREEN
    if field.range_status == "abnormal":
        return FILL_GRAY
    return FILL_WHITE


def _field_to_row(field: PathologyField) -> list:
    """Convert a PathologyField to an Excel row (without internal id)."""
    return [
        field.key,
        field.value or "",
        field.unit or "",
        field.reference_range or "",
        field.config_range or "",
        field.range_status or "",
        field.method or "",
        "Yes" if field.is_standard else "No",
        field.source,
    ]


def generate_excel(fields: List[PathologyField], case_id: str, version: int) -> bytes:
    """
    Generate an Excel workbook from pathology fields.

    The id column is stored in a hidden column (column A) so that
    re-import can match fields back to their IDs.

    Args:
        fields: List of PathologyField from the PathologyResultModel
        case_id: For the sheet title
        version: For the sheet title

    Returns:
        Excel file as bytes
    """
    wb = Workbook()
    ws = wb.active
    ws.title = f"Pathology v{version}"

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

            # Use red bold font for Value column if abnormal (matches frontend)
            if col_idx == COL_VALUE and field.range_status == "abnormal":
                cell.font = FONT_RED_BOLD
            else:
                cell.font = FONT_DEFAULT

            cell.fill = fill
            cell.alignment = ALIGN_LEFT if col_idx > 2 else ALIGN_CENTER
            cell.border = THIN_BORDER

    # ── Auto-fit column widths (approximate) ─────────────────────
    col_widths = {
        "B": 25,   # Parameter
        "C": 15,   # Value
        "D": 12,   # Unit
        "E": 18,   # Report Range
        "F": 18,   # Standard Range
        "G": 10,   # Status
        "H": 20,   # Method
        "I": 12,   # Is Standard
        "J": 10,   # Source
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
