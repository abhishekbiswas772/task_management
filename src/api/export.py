"""
Export endpoints: CSV and Excel (.xls XML format).
"""
from __future__ import annotations

import csv
import io
from calendar import monthrange
from collections import Counter
from datetime import datetime

from flask import Blueprint, jsonify, request, send_file
from flask_login import current_user, login_required
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.database import get_session
from src.models.task import Task

export_bp = Blueprint("export", __name__, url_prefix="/api/export")

_NO_TASKS = "No tasks"


def _require_auth_api():
    if not current_user.is_authenticated:
        return jsonify({"error": "Authentication required"}), 401
    return None


def _xe(s: str) -> str:
    """XML-escape a value for the Excel export."""
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _parse_iso_date(value: str | None) -> datetime | None:
    """Parse ISO-ish timestamps from the database."""
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is not None:
            return parsed.astimezone().replace(tzinfo=None)
        return parsed
    except ValueError:
        return None


def _fmt_day(value: datetime | None) -> str:
    if not value:
        return "N/A"
    return value.strftime("%b %-d")


async def _load_tasks(month: int, year: int) -> list[Task]:
    async with get_session() as session:
        result = await session.execute(
            select(Task)
            .options(selectinload(Task.comments), selectinload(Task.creator))
            .where(Task.month == month, Task.year == year)
            .order_by(Task.created_at.asc())
        )
        return result.scalars().all()


def _build_summary_payload(tasks: list[Task], month: int, year: int) -> dict:
    total = len(tasks)
    total_comments = sum(len(task.comments) for task in tasks)
    overdue = 0
    with_due_date = 0
    daily_counter: Counter[int] = Counter()
    tag_counter: Counter[str] = Counter()
    column_counter: Counter[str] = Counter()
    priority_counter: Counter[str] = Counter()
    weekly_buckets: list[dict] = []
    days_in_month = monthrange(year, month)[1]

    for start_day in range(1, days_in_month + 1, 7):
        end_day = min(start_day + 6, days_in_month)
        weekly_buckets.append(
            {
                "label": f"Week {(start_day - 1) // 7 + 1}",
                "range": f"{start_day}-{end_day}",
                "start_day": start_day,
                "end_day": end_day,
                "tasks": [],
            }
        )

    now = datetime.now()
    oldest_created: datetime | None = None
    newest_created: datetime | None = None

    for task in tasks:
        created_dt = _parse_iso_date(task.created_at)
        due_dt = _parse_iso_date(task.due_date)

        if created_dt:
            if oldest_created is None or created_dt < oldest_created:
                oldest_created = created_dt
            if newest_created is None or created_dt > newest_created:
                newest_created = created_dt
            daily_counter[created_dt.day] += 1

        if due_dt:
            with_due_date += 1
            if due_dt < now:
                overdue += 1

        if task.tags:
            for tag in (item.strip() for item in task.tags.split(",")):
                if tag:
                    tag_counter[tag] += 1

        column_counter[task.column_name] += 1
        priority_counter[task.priority] += 1

        bucket_idx = min(max((created_dt.day if created_dt else 1) - 1, 0) // 7, len(weekly_buckets) - 1)
        weekly_buckets[bucket_idx]["tasks"].append(task)

    top_tags = [
        {"name": tag, "count": count}
        for tag, count in tag_counter.most_common(5)
    ]
    daily_activity = [
        {"day": day, "count": daily_counter.get(day, 0)}
        for day in range(1, days_in_month + 1)
    ]

    weekly_summary = []
    for bucket in weekly_buckets:
        bucket_tasks = bucket["tasks"]
        if bucket["start_day"] > days_in_month:
            continue
        top_col_counter = Counter(task.column_name for task in bucket_tasks).most_common(1)
        weekly_summary.append(
            {
                "label": bucket["label"],
                "range": bucket["range"],
                "task_count": len(bucket_tasks),
                "high_priority_count": sum(1 for task in bucket_tasks if task.priority == "High"),
                "comment_count": sum(len(task.comments) for task in bucket_tasks),
                "top_column": top_col_counter[0][0] if top_col_counter else _NO_TASKS,
            }
        )

    top_column = column_counter.most_common(1)[0][0] if column_counter else _NO_TASKS
    top_priority = priority_counter.most_common(1)[0][0] if priority_counter else _NO_TASKS
    date_span = f"{_fmt_day(oldest_created)} - {_fmt_day(newest_created)}" if total else _NO_TASKS

    return {
        "month": month,
        "year": year,
        "month_label": datetime(year, month, 1).strftime("%B %Y"),
        "monthly_summary": {
            "task_count": total,
            "high_priority_count": priority_counter.get("High", 0),
            "with_due_date_count": with_due_date,
            "overdue_count": overdue,
            "comment_count": total_comments,
            "top_column": top_column,
            "top_priority": top_priority,
            "date_span": date_span,
            "top_tags": top_tags,
            "columns": [
                {"name": name, "count": count}
                for name, count in column_counter.most_common()
            ],
            "priorities": [
                {"name": name, "count": count}
                for name, count in priority_counter.most_common()
            ],
            "daily_activity": daily_activity,
        },
        "weekly_summary": weekly_summary,
    }


def _build_summary_export_text(summary: dict) -> str:
    monthly = summary["monthly_summary"]
    weekly = summary["weekly_summary"]
    lines = [
        f"Task Summary Export - {summary['month_label']}",
        "",
        "Monthly Summary",
        f"Total tasks: {monthly['task_count']}",
        f"High priority: {monthly['high_priority_count']}",
        f"With due date: {monthly['with_due_date_count']}",
        f"Overdue: {monthly['overdue_count']}",
        f"Comments: {monthly['comment_count']}",
        f"Top column: {monthly['top_column']}",
        f"Top priority: {monthly['top_priority']}",
        f"Activity span: {monthly['date_span']}",
        "",
        "Column Breakdown",
    ]

    if monthly["columns"]:
        lines.extend(f"- {col['name']}: {col['count']}" for col in monthly["columns"])
    else:
        lines.append("- No tasks")

    lines.extend(["", "Top Tags"])
    if monthly["top_tags"]:
        lines.extend(f"- {tag['name']}: {tag['count']}" for tag in monthly["top_tags"])
    else:
        lines.append("- No tags")

    lines.extend(["", "Weekly Summary"])
    if weekly:
        for item in weekly:
            lines.append(
                f"- {item['label']} ({item['range']}): "
                f"{item['task_count']} tasks, "
                f"{item['high_priority_count']} high priority, "
                f"{item['comment_count']} comments, "
                f"top column: {item['top_column']}"
            )
    else:
        lines.append("- No weekly data")

    return "\n".join(lines)


@export_bp.route("/csv", methods=["GET"])
@login_required
async def export_csv():
    month = request.args.get("month", type=int, default=1)
    year  = request.args.get("year",  type=int, default=2026)
    label = request.args.get("label", "Tasks")

    tasks = await _load_tasks(month, year)

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


@export_bp.route("/excel", methods=["GET"])
@login_required
async def export_excel():
    month = request.args.get("month", type=int, default=1)
    year  = request.args.get("year",  type=int, default=2026)
    label = request.args.get("label", "Tasks")

    tasks = await _load_tasks(month, year)

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
        if t.priority == "High":
            priority_style = "Hi"
        elif t.priority == "Low":
            priority_style = "Hl"
        else:
            priority_style = "Hm"
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


@export_bp.route("/summary", methods=["GET"])
async def export_summary():
    auth_error = _require_auth_api()
    if auth_error:
        return auth_error
    month = request.args.get("month", type=int, default=1)
    year = request.args.get("year", type=int, default=2026)
    tasks = await _load_tasks(month, year)
    return jsonify(_build_summary_payload(tasks, month, year))


@export_bp.route("/summary/txt", methods=["GET"])
@login_required
async def export_summary_text():
    month = request.args.get("month", type=int, default=1)
    year = request.args.get("year", type=int, default=2026)
    label = request.args.get("label", "Summary")
    tasks = await _load_tasks(month, year)
    summary = _build_summary_payload(tasks, month, year)
    text = _build_summary_export_text(summary)

    return send_file(
        io.BytesIO(text.encode("utf-8")),
        mimetype="text/plain",
        as_attachment=True,
        download_name=f"{label}.txt",
    )
