"""
Board column configuration API.
"""
from __future__ import annotations

from flask.views import MethodView
from flask_login import current_user
from flask_smorest import Blueprint, abort
from sqlalchemy import delete, select, update

from src.api.schemas import (
    BoardColumnCreateSchema,
    BoardColumnDeleteSchema,
    BoardColumnSchema,
    BoardColumnUpdateSchema,
)
from src.database import get_session
from src.models.board_column import BoardColumn
from src.models.task import Task

blp = Blueprint(
    "board_columns",
    __name__,
    url_prefix="/api/board-columns",
    description="Configurable kanban columns",
)


def _require_auth():
    if not current_user.is_authenticated:
        abort(401, message="Authentication required.")


@blp.route("/")
class BoardColumnList(MethodView):
    @blp.response(200, BoardColumnSchema(many=True))
    async def get(self):
        _require_auth()
        async with get_session() as session:
            result = await session.execute(
                select(BoardColumn).order_by(BoardColumn.position.asc(), BoardColumn.id.asc())
            )
            columns = result.scalars().all()
        return [column.to_dict() for column in columns]

    @blp.arguments(BoardColumnCreateSchema, location="json")
    @blp.response(201, BoardColumnSchema)
    async def post(self, data):
        _require_auth()
        name = data["name"].strip()
        if not name:
            abort(400, message="Column name is required.")

        async with get_session() as session:
            existing = await session.execute(
                select(BoardColumn).where(BoardColumn.name.ilike(name))
            )
            if existing.scalar_one_or_none():
                abort(409, message="A column with that name already exists.")

            last = await session.execute(select(BoardColumn).order_by(BoardColumn.position.desc()).limit(1))
            last_column = last.scalar_one_or_none()
            column = BoardColumn(
                name=name,
                color=data.get("color", "#6B7280"),
                position=(last_column.position + 1) if last_column else 0,
            )
            session.add(column)
            await session.flush()
            return column.to_dict()


@blp.route("/<int:column_id>")
class BoardColumnDetail(MethodView):
    @blp.arguments(BoardColumnUpdateSchema, location="json")
    @blp.response(200, BoardColumnSchema)
    async def put(self, data, column_id):
        _require_auth()
        async with get_session() as session:
            column = await session.get(BoardColumn, column_id)
            if not column:
                abort(404, message="Column not found.")

            old_name = column.name
            new_name = data.get("name", column.name).strip()
            if not new_name:
                abort(400, message="Column name is required.")

            duplicate = await session.execute(
                select(BoardColumn).where(BoardColumn.id != column_id, BoardColumn.name.ilike(new_name))
            )
            if duplicate.scalar_one_or_none():
                abort(409, message="A column with that name already exists.")

            if "position" in data:
                column.position = data["position"]
            if "color" in data:
                column.color = data["color"]
            column.name = new_name

            if new_name != old_name:
                await session.execute(
                    update(Task)
                    .where(Task.column_name == old_name)
                    .values(column_name=new_name)
                )

            await session.flush()
            return column.to_dict()

    @blp.response(200, BoardColumnDeleteSchema)
    async def delete(self, column_id):
        _require_auth()
        async with get_session() as session:
            column = await session.get(BoardColumn, column_id)
            if not column:
                abort(404, message="Column not found.")

            result = await session.execute(
                select(BoardColumn).order_by(BoardColumn.position.asc(), BoardColumn.id.asc())
            )
            columns = result.scalars().all()
            if len(columns) <= 1:
                abort(400, message="You cannot delete the last kanban column.")

            fallback = next((item for item in columns if item.id != column_id), None)
            if not fallback:
                abort(400, message="No fallback column available.")

            await session.execute(
                update(Task)
                .where(Task.column_name == column.name)
                .values(column_name=fallback.name)
            )
            await session.execute(delete(BoardColumn).where(BoardColumn.id == column_id))
            await session.flush()

            remaining_result = await session.execute(
                select(BoardColumn).order_by(BoardColumn.position.asc(), BoardColumn.id.asc())
            )
            remaining = remaining_result.scalars().all()
            for index, item in enumerate(remaining):
                item.position = index

            await session.flush()
            return {
                "deleted_column": column.name,
                "moved_to": fallback.name,
            }
