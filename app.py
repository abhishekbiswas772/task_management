import csv
import io
import os
import uuid
from datetime import datetime

from flask import Flask, jsonify, render_template, request, send_file

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(__file__), "tasks.db")


# ──────────────────────────── DB helpers ─────────────────────────────

def get_db():
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id          TEXT PRIMARY KEY,
            title       TEXT NOT NULL,
            description TEXT DEFAULT '',
            column_name TEXT DEFAULT 'TODO',
            month       INTEGER NOT NULL,
            year        INTEGER NOT NULL,
            priority    TEXT DEFAULT 'Medium',
            due_date    TEXT,
            created_at  TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id         TEXT PRIMARY KEY,
            task_id    TEXT NOT NULL,
            text       TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    conn.close()


def task_with_comments(conn, task_row):
    td = dict(task_row)
    rows = conn.execute(
        "SELECT * FROM comments WHERE task_id=? ORDER BY created_at ASC",
        (td["id"],),
    ).fetchall()
    td["comments"] = [dict(r) for r in rows]
    return td


# ──────────────────────────── Routes ────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


# Tasks

@app.route("/api/tasks")
def get_tasks():
    month = request.args.get("month", type=int)
    year  = request.args.get("year",  type=int)
    conn  = get_db()
    rows  = conn.execute(
        "SELECT * FROM tasks WHERE month=? AND year=? ORDER BY created_at ASC",
        (month, year),
    ).fetchall()
    result = [task_with_comments(conn, r) for r in rows]
    conn.close()
    return jsonify(result)


@app.route("/api/tasks", methods=["POST"])
def create_task():
    data       = request.json
    task_id    = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat()
    conn       = get_db()
    conn.execute(
        """INSERT INTO tasks
           (id,title,description,column_name,month,year,priority,due_date,created_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (
            task_id,
            data["title"],
            data.get("description", ""),
            data.get("column", "TODO"),
            data["month"],
            data["year"],
            data.get("priority", "Medium"),
            data.get("due_date"),
            created_at,
        ),
    )
    conn.commit()
    conn.close()
    return jsonify({"id": task_id, "created_at": created_at}), 201


@app.route("/api/tasks/<task_id>", methods=["PUT"])
def update_task(task_id):
    data = request.json
    if "column" in data:
        data["column_name"] = data.pop("column")
    allowed = {"title", "description", "column_name", "priority", "due_date"}
    fields  = [f for f in data if f in allowed]
    if not fields:
        return jsonify({"error": "nothing to update"}), 400
    sql    = f"UPDATE tasks SET {', '.join(f+'=?' for f in fields)} WHERE id=?"
    values = [data[f] for f in fields] + [task_id]
    conn   = get_db()
    conn.execute(sql, values)
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.route("/api/tasks/<task_id>", methods=["DELETE"])
def delete_task(task_id):
    conn = get_db()
    conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


# Comments

@app.route("/api/tasks/<task_id>/comments", methods=["POST"])
def add_comment(task_id):
    data       = request.json
    cid        = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat()
    conn       = get_db()
    conn.execute(
        "INSERT INTO comments (id,task_id,text,created_at) VALUES (?,?,?,?)",
        (cid, task_id, data["text"], created_at),
    )
    conn.commit()
    conn.close()
    return jsonify({"id": cid, "created_at": created_at}), 201


@app.route("/api/comments/<comment_id>", methods=["DELETE"])
def delete_comment(comment_id):
    conn = get_db()
    conn.execute("DELETE FROM comments WHERE id=?", (comment_id,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


# Export

@app.route("/api/export/csv")
def export_csv():
    month = request.args.get("month", type=int)
    year  = request.args.get("year",  type=int)
    label = request.args.get("label", "Tasks")
    conn  = get_db()
    tasks = conn.execute(
        "SELECT * FROM tasks WHERE month=? AND year=? ORDER BY created_at",
        (month, year),
    ).fetchall()
    out = io.StringIO()
    w   = csv.writer(out)
    w.writerow(["Title", "Description", "Column", "Priority",
                "Comments Count", "Comment Text", "Created Date", "Due Date"])
    for t in tasks:
        crows = conn.execute(
            "SELECT text FROM comments WHERE task_id=? ORDER BY created_at", (t["id"],)
        ).fetchall()
        w.writerow([
            t["title"], t["description"], t["column_name"], t["priority"],
            len(crows), " | ".join(c["text"] for c in crows),
            t["created_at"][:10], t["due_date"] or "",
        ])
    conn.close()
    out.seek(0)
    return send_file(
        io.BytesIO(out.getvalue().encode("utf-8-sig")),
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"Tasks-{label}.csv",
    )


@app.route("/api/export/excel")
def export_excel():
    month = request.args.get("month", type=int)
    year  = request.args.get("year",  type=int)
    label = request.args.get("label", "Tasks")
    conn  = get_db()
    tasks = conn.execute(
        "SELECT * FROM tasks WHERE month=? AND year=? ORDER BY created_at",
        (month, year),
    ).fetchall()

    def xe(s):
        return (str(s)
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;"))

    safe = xe(label[:31])
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
        <Cell ss:StyleID="H"><Data ss:Type="String">Comments</Data></Cell>
        <Cell ss:StyleID="H"><Data ss:Type="String">Comment Text</Data></Cell>
        <Cell ss:StyleID="H"><Data ss:Type="String">Created Date</Data></Cell>
        <Cell ss:StyleID="H"><Data ss:Type="String">Due Date</Data></Cell>
      </Row>"""

    for t in tasks:
        crows = conn.execute(
            "SELECT text FROM comments WHERE task_id=? ORDER BY created_at", (t["id"],)
        ).fetchall()
        ct = " | ".join(c["text"] for c in crows)
        ps = "Hi" if t["priority"] == "High" else ("Hl" if t["priority"] == "Low" else "Hm")
        xml += f"""
      <Row>
        <Cell><Data ss:Type="String">{xe(t['title'])}</Data></Cell>
        <Cell><Data ss:Type="String">{xe(t['description'])}</Data></Cell>
        <Cell><Data ss:Type="String">{xe(t['column_name'])}</Data></Cell>
        <Cell ss:StyleID="{ps}"><Data ss:Type="String">{xe(t['priority'])}</Data></Cell>
        <Cell><Data ss:Type="Number">{len(crows)}</Data></Cell>
        <Cell><Data ss:Type="String">{xe(ct)}</Data></Cell>
        <Cell><Data ss:Type="String">{xe(t['created_at'][:10])}</Data></Cell>
        <Cell><Data ss:Type="String">{xe(t['due_date'] or '')}</Data></Cell>
      </Row>"""

    xml += "\n    </Table>\n  </Worksheet>\n</Workbook>"
    conn.close()
    return send_file(
        io.BytesIO(xml.encode("utf-8")),
        mimetype="application/vnd.ms-excel",
        as_attachment=True,
        download_name=f"Tasks-{label}.xls",
    )


# ──────────────────────────── Entry point ────────────────────────────

if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)
