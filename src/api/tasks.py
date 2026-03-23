"""
Task CRUD API — Flask-Smorest blueprint with full async support.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from flask.views import MethodView
from flask_login import current_user
from flask_smorest import Blueprint, abort
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.api.schemas import TaskCreateSchema, TaskQuerySchema, TaskSchema, TaskUpdateSchema
from src.database import get_session
from src.models.task import Task

blp = Blueprint(
    "tasks",
    __name__,
    url_prefix="/api/tasks",
    description="Task CRUD operations",
)


def _require_auth():
    if not current_user.is_authenticated:
        abort(401, message="Authentication required.")


# ── List / Create ─────────────────────────────────────────────────────

@blp.route("/")
class TaskList(MethodView):

    @blp.arguments(TaskQuerySchema, location="query")
    @blp.response(200, TaskSchema(many=True))
    async def get(self, args):
        """Fetch all tasks for a given month/year."""
        _require_auth()
        async with get_session() as session:
            result = await session.execute(
                select(Task)
                .options(selectinload(Task.comments), selectinload(Task.creator))
                .where(Task.month == args["month"], Task.year == args["year"])
                .order_by(Task.created_at.asc())
            )
            tasks = result.scalars().all()
        return [t.to_dict() for t in tasks]

    @blp.arguments(TaskCreateSchema, location="json")
    @blp.response(201, TaskSchema)
    async def post(self, data):
        """Create a new task."""
        _require_auth()
        task_id   = str(uuid.uuid4())
        now       = datetime.now(timezone.utc).isoformat()
        tags_str  = ",".join(data.get("tags", []))

        task = Task(
            id=task_id,
            title=data["title"],
            description=data.get("description", ""),
            column_name=data.get("column", "TODO"),
            month=data["month"],
            year=data["year"],
            priority=data.get("priority", "Medium"),
            due_date=data.get("due_date"),
            tags=tags_str,
            created_at=now,
            created_by=current_user.id,
        )
        async with get_session() as session:
            session.add(task)
            await session.flush()
            result = await session.execute(
                select(Task)
                .options(selectinload(Task.comments), selectinload(Task.creator))
                .where(Task.id == task_id)
            )
            created = result.scalar_one()
            return created.to_dict()


# ── Single task ───────────────────────────────────────────────────────

@blp.route("/<string:task_id>")
class TaskDetail(MethodView):

    @blp.response(200, TaskSchema)
    async def get(self, task_id):
        """Get a single task."""
        _require_auth()
        async with get_session() as session:
            result = await session.execute(
                select(Task)
                .options(selectinload(Task.comments), selectinload(Task.creator))
                .where(Task.id == task_id)
            )
            task = result.scalar_one_or_none()
        if not task:
            abort(404, message="Task not found.")
        return task.to_dict()

    @blp.arguments(TaskUpdateSchema, location="json")
    @blp.response(200, TaskSchema)
    async def put(self, data, task_id):
        """Update a task."""
        _require_auth()
        async with get_session() as session:
            task = await session.get(Task, task_id)
            if not task:
                abort(404, message="Task not found.")

            for field in ("title", "description", "column_name", "priority", "due_date"):
                if field in data:
                    setattr(task, field, data[field])

            if "tags" in data:
                task.tags = ",".join(data["tags"])

        async with get_session() as session:
            result = await session.execute(
                select(Task)
                .options(selectinload(Task.comments), selectinload(Task.creator))
                .where(Task.id == task_id)
            )
            updated = result.scalar_one()
            return updated.to_dict()

    @blp.response(204)
    async def delete(self, task_id):
        """Delete a task and all its comments."""
        _require_auth()
        async with get_session() as session:
            task = await session.get(Task, task_id)
            if not task:
                abort(404, message="Task not found.")
            await session.delete(task)
