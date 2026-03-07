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

from typing import List

from openpyxl import Workbook

from app.models.pathology_result import PathologyField
from app.services.excel_utils import (
    FILL_GRAY,
    FILL_GREEN,
    FILL_WHITE,
    FONT_RED_BOLD,
    ColSpec,
    RowStyle,
    workbook_to_bytes,
    write_data_sheet,
    write_meta_row,
)

COLUMNS = [
    ColSpec("Parameter", width=25),
    ColSpec("Original Name", width=25),
    ColSpec("Value", width=15),
    ColSpec("Unit", width=12),
    ColSpec("Report Range", width=18),
    ColSpec("Standard Range", width=18),
    ColSpec("Status", width=10, align="center"),
    ColSpec("Method", width=20),
    ColSpec("Is Standard", width=12, align="center"),
    ColSpec("Source", width=10),
]

# 1-based index of the Value column within the visible columns
# (used for font override in the hidden-id layout where visible cols start at B=2)
COL_VALUE = 4  # "Value" is the 3rd visible column → col index 4 when offset by hidden col A


def _get_row_style(field: PathologyField) -> RowStyle:
    """Determine row styling for a field (matches frontend UI)."""
    if field.source == "user":
        return RowStyle(fill=FILL_GREEN)
    if field.range_status == "abnormal":
        return RowStyle(fill=FILL_GRAY, font_overrides={COL_VALUE: FONT_RED_BOLD})
    return RowStyle()


def _field_to_row(field: PathologyField) -> list:
    """Convert a PathologyField to an Excel row (without internal id)."""
    return [
        field.key,
        field.reference_name or "",
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
    """
    wb = Workbook()
    ws = wb.active
    ws.title = f"Pathology v{version}"

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
