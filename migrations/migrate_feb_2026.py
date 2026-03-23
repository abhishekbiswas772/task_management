"""
Seed script — Internal Fuso Projects FEB 2026
Migrates all tasks visible in the OpenProject board screenshots into the
local SQLite database (month=2, year=2026).

Run:  python3 migrate_feb_2026.py
"""

import os
import sqlite3
import uuid
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "tasks.db")

# ── Task data extracted from screenshots ─────────────────────────────
# (title, column_name, priority)
# Priority mapping from OpenProject status:
#   In progress  → High
#   New          → Medium
#   On hold      → Medium
#   Closed       → Low   (completed)
#   Rejected     → Low

TASKS = [
    # ── TODO ──────────────────────────────────────────────────────────
    (
        "QMPQR Chatbot Full Scale",
        "TODO",
        "High",
    ),

    # ── In Progress ───────────────────────────────────────────────────
    (
        "Fine Tune Model using local LLM using collab or something vast.ai",
        "In Progress",
        "High",
    ),
    (
        "DTC image issue when streaming enabled fixes",
        "In Progress",
        "Medium",
    ),

    # ── Internal Testing ──────────────────────────────────────────────
    (
        "find alter (backup) japanese delegate for handle DTC chatbot",
        "Internal Testing",
        "High",
    ),
    (
        "QMPQR Chatbot refinements",
        "Internal Testing",
        "Low",
    ),
    (
        "TIC Bug Fixes",
        "Internal Testing",
        "Low",
    ),
    (
        "TIC Blob related problem and fixes using FileShare",
        "Internal Testing",
        "Low",
    ),

    # ── Client Deployment UAT ─────────────────────────────────────────
    (
        "DTC Contextual Challenge and cross validation",
        "Client Deployment UAT",
        "Low",
    ),
    (
        "DTC on demand image showing in dev",
        "Client Deployment UAT",
        "Low",
    ),
    (
        "DTC Topic change fixes",
        "Client Deployment UAT",
        "Low",
    ),
    (
        "DTC 6R10, 6R20, 6R30 manuals of super great in dev",
        "Client Deployment UAT",
        "Low",
    ),
    (
        "DTC Canter 4P10 in dev",
        "Client Deployment UAT",
        "Low",
    ),
    (
        "DTC halluications Fix",
        "Client Deployment UAT",
        "Low",
    ),

    # ── Client Production ─────────────────────────────────────────────
    (
        "DTC eCanter manuals ingestions",
        "Client Production",
        "Low",
    ),

    # ── Dependency List ───────────────────────────────────────────────
    (
        "Verify the Azure Translation part removal",
        "Dependency List",
        "High",
    ),
    (
        "Veriify the full pipeline for Quick and Deep in DTC Chatbot",
        "Dependency List",
        "High",
    ),
    (
        "Fix Output length of Fine Tune LLM",
        "Dependency List",
        "High",
    ),
    (
        "Don't Download the image while retriving the metadata",
        "Dependency List",
        "High",
    ),
    (
        "Avoid any image refernece in fine tuned llm",
        "Dependency List",
        "High",
    ),
    (
        "IAM Team Coordination",
        "Dependency List",
        "Medium",
    ),
    (
        "DTC User Email for Followup the IAM Team",
        "Dependency List",
        "Medium",
    ),
    (
        "Find a way to directly connect to azure and reload it automatically via data change",
        "Dependency List",
        "High",
    ),
    (
        "Konno San followup for access issue",
        "Dependency List",
        "Medium",
    ),
    (
        "Verify the account access issue in UAT by doing interal discussion",
        "Dependency List",
        "Medium",
    ),
    (
        "Find online secure blob or script to save and upload from there and reload techniques",
        "Dependency List",
        "Medium",
    ),
    (
        "TIC ROSA to vector database and validations",
        "Dependency List",
        "High",
    ),
    (
        "Follow up the Konno San for UAT fixes",
        "Dependency List",
        "Medium",
    ),
    (
        "DTC UAT Access Issue",
        "Dependency List",
        "Medium",
    ),
    (
        "DTC UAT ACCESS TO all TBDIR Account",
        "Dependency List",
        "Medium",
    ),

    # ── Done Internally ───────────────────────────────────────────────
    (
        "Coordinating Abhyang for Azure Function",
        "Done Internally",
        "High",
    ),
    (
        "Discovering AI For PPT with using Existing Template",
        "Done Internally",
        "Low",
    ),
    (
        "Office Tough situation in STAR Format",
        "Done Internally",
        "Low",
    ),
    (
        "UI refinements in Thinking and response part",
        "Done Internally",
        "High",
    ),
    (
        "Fine Tune model using OpenAI",
        "Done Internally",
        "High",
    ),
    (
        "UI refinements in quick and deep thinking",
        "Done Internally",
        "Low",
    ),
    (
        "onboarding api fixes",
        "Done Internally",
        "High",
    ),
    (
        "DTC workspace and publish and reload",
        "Done Internally",
        "Low",
    ),
    (
        "power Bi finalization",
        "Done Internally",
        "Low",
    ),
    (
        "install power bi and setup",
        "Done Internally",
        "Low",
    ),
    (
        "TIC env fixes in UAT",
        "Done Internally",
        "Low",
    ),
    (
        "Power BI Dashboard Publish and Transform",
        "Done Internally",
        "Low",
    ),
    (
        "finishing up the Production Process",
        "Done Internally",
        "Low",
    ),
    (
        "Make A Good Amount of DAX to Help Alisa and myself to Complete this activity fast as possible",
        "Done Internally",
        "Low",
    ),
    (
        "delete parallels and its files",
        "Done Internally",
        "Low",
    ),
    (
        "Making PPT Document for the Japanese Delegate - sent Document to Akshay sir following the given template",
        "Done Internally",
        "Low",
    ),
    (
        "download vm and install windows 10 lite",
        "Done Internally",
        "Low",
    ),
    (
        "finishing up the UAT process",
        "Done Internally",
        "Low",
    ),
    (
        "Make STAR format document for Danish delegate",
        "Done Internally",
        "Low",
    ),
]


# ── Helpers ───────────────────────────────────────────────────────────

def init_db(conn: sqlite3.Connection):
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


def already_seeded(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE month=2 AND year=2026"
    ).fetchone()
    return row[0] > 0


def seed(conn: sqlite3.Connection):
    # Spread created_at timestamps across Feb 1–28 2026
    base   = datetime(2026, 2, 1, 9, 0, 0)
    step   = timedelta(hours=6)          # one task every ~6 hours
    rows   = []

    for i, (title, column, priority) in enumerate(TASKS):
        task_id    = str(uuid.uuid4())
        created_at = (base + step * i).isoformat()
        rows.append((task_id, title, "", column, 2, 2026, priority, None, created_at))

    conn.executemany(
        """INSERT INTO tasks
           (id, title, description, column_name, month, year, priority, due_date, created_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        rows,
    )
    conn.commit()
    return len(rows)


# ── Main ──────────────────────────────────────────────────────────────

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    init_db(conn)

    if already_seeded(conn):
        existing = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE month=2 AND year=2026"
        ).fetchone()[0]
        print(f"⚠  February 2026 already has {existing} tasks in the DB.")
        ans = input("   Re-seed anyway? This will ADD on top (y/N): ").strip().lower()
        if ans != "y":
            print("Aborted.")
            conn.close()
            return

    count = seed(conn)
    conn.close()
    print(f"✅  Inserted {count} tasks for February 2026.")
    print("   Open http://localhost:5000 and navigate to Feb 2026 to see them.")


if __name__ == "__main__":
    main()
