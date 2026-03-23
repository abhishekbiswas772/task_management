"""
User lookup endpoints for mentions.
"""
from __future__ import annotations

from flask.views import MethodView
from flask_login import current_user
from flask_smorest import Blueprint, abort
from sqlalchemy import select

from src.api.schemas import MentionUserSchema
from src.database import get_session
from src.models.user import User

blp = Blueprint(
    "users",
    __name__,
    url_prefix="/api/users",
    description="User lookup operations",
)


def _require_auth():
    if not current_user.is_authenticated:
        abort(401, message="Authentication required.")


@blp.route("/mentions")
class MentionUsers(MethodView):
    @blp.response(200, MentionUserSchema(many=True))
    async def get(self):
        _require_auth()
        from flask import request

        query = request.args.get("q", "").strip()
        async with get_session() as session:
            stmt = select(User).order_by(User.username.asc()).limit(8)
            if query:
                stmt = stmt.where(User.username.ilike(f"{query}%"))
            result = await session.execute(stmt)
            users = result.scalars().all()
        return [{"id": user.id, "username": user.username} for user in users]
