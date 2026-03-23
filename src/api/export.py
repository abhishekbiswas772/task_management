"""
Export endpoints: CSV and Excel (.xls XML format).
"""
from __future__ import annotations

import csv
import io

from flask import Blueprint, request, send_file
from flask_login import login_required
from sqlalchemy import select

from src.database import get_session
from src.models.task import Task

export_bp = Blueprint("export", __name__, url_prefix="/api/export")


def _xe(s: str) -> str:
    """XML-escape a value for the Excel export."""
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


@export_bp.route("/csv")
@login_required
async def export_csv():
    month = request.args.get("month", type=int, default=1)
    year  = request.args.get("year",  type=int, default=2026)
    label = request.args.get("label", "Tasks")

    async with get_session() as session:
        result = await session.execute(
            select(Task)
            .where(Task.month == month, Task.year == year)
            .order_by(Task.created_at.asc())
        )
        tasks = result.scalars().all()

    out = io.StringIO()
    w   = csv.writer(out)
    w.writerow(["Title", "Description", "Column", "Priority", "Tags",
                "Comments Count", "Comment Text", "Creator", "Created Date", "Due Date"])

    for t in tasks:
        comments = t.comments
        cmt_text = " | ".join(c.text for c in comments)
        tags_str = t.tags or ""
        creator  = t.creator.username if t.creator else ""
        w.writerow([
            t.title, t.description, t.column_name, t.priority, tags_str,
            len(comments), cmt_text, creator, t.created_at[:10], t.due_date or "",
        ])

    out.seek(0)
    return send_file(
        io.BytesIO(out.getvalue().encode("utf-8-sig")),
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"Tasks-{label}.csv",
    )


@export_bp.route("/excel")
@login_required
async def export_excel():
    month = request.args.get("month", type=int, default=1)
    year  = request.args.get("year",  type=int, default=2026)
    label = request.args.get("label", "Tasks")

    async with get_session() as session:
        result = await session.execute(
            select(Task)
            .where(Task.month == month, Task.year == year)
            .order_by(Task.created_at.asc())
        )
        tasks = result.scalars().all()

    safe = _xe(label[:31])
    xml  = f"""<?xml version="1.0" encoding="UTF-8"?>
<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"
          xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">
  <Styles>
    <Style ss:ID="H">
      <Font ss:Bold="1" ss:Color="#FFFFFF"/>
      <Interior ss:Color="#4F46E5" ss:Pattern="Solid"/>
    </Style>
    <Style ss:ID="Hi"><Font ss:Bold="1" ss:Color="#EF4444"/></Style>
    <Style ss:ID="Hm"><Font ss:Bold="1" ss:Color="#F97316"/></Style>
    <Style ss:ID="Hl"><Font ss:Bold="1" ss:Color="#22C55E"/></Style>
  </Styles>
  <Worksheet ss:Name="{safe}">
    <Table>
      <Row>
        <Cell ss:StyleID="H"><Data ss:Type="String">Title</Data></Cell>
        <Cell ss:StyleID="H"><Data ss:Type="String">Description</Data></Cell>
        <Cell ss:StyleID="H"><Data ss:Type="String">Column</Data></Cell>
        <Cell ss:StyleID="H"><Data ss:Type="String">Priority</Data></Cell>
        <Cell ss:StyleID="H"><Data ss:Type="String">Tags</Data></Cell>
        <Cell ss:StyleID="H"><Data ss:Type="String">Comments</Data></Cell>
        <Cell ss:StyleID="H"><Data ss:Type="String">Comment Text</Data></Cell>
        <Cell ss:StyleID="H"><Data ss:Type="String">Creator</Data></Cell>
        <Cell ss:StyleID="H"><Data ss:Type="String">Created Date</Data></Cell>
        <Cell ss:StyleID="H"><Data ss:Type="String">Due Date</Data></Cell>
      </Row>"""

    for t in tasks:
        comments = t.comments
        ct       = " | ".join(c.text for c in comments)
        priority_style = "Hi" if t.priority == "High" else ("Hl" if t.priority == "Low" else "Hm")
        creator  = _xe(t.creator.username if t.creator else "")
        xml += f"""
      <Row>
        <Cell><Data ss:Type="String">{_xe(t.title)}</Data></Cell>
        <Cell><Data ss:Type="String">{_xe(t.description)}</Data></Cell>
        <Cell><Data ss:Type="String">{_xe(t.column_name)}</Data></Cell>
        <Cell ss:StyleID="{priority_style}"><Data ss:Type="String">{_xe(t.priority)}</Data></Cell>
        <Cell><Data ss:Type="String">{_xe(t.tags or '')}</Data></Cell>
        <Cell><Data ss:Type="Number">{len(comments)}</Data></Cell>
        <Cell><Data ss:Type="String">{_xe(ct)}</Data></Cell>
        <Cell><Data ss:Type="String">{creator}</Data></Cell>
        <Cell><Data ss:Type="String">{_xe(t.created_at[:10])}</Data></Cell>
        <Cell><Data ss:Type="String">{_xe(t.due_date or '')}</Data></Cell>
      </Row>"""

    xml += "\n    </Table>\n  </Worksheet>\n</Workbook>"

    return send_file(
        io.BytesIO(xml.encode("utf-8")),
        mimetype="application/vnd.ms-excel",
        as_attachment=True,
        download_name=f"Tasks-{label}.xls",
    )
