"""
Comment API — Flask-Smorest blueprint, async.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from flask.views import MethodView
from flask_login import current_user
from flask_smorest import Blueprint, abort

from src.api.schemas import CommentCreateSchema, CommentSchema
from src.database import get_session
from src.models.comment import Comment

blp = Blueprint(
    "comments",
    __name__,
    url_prefix="/api",
    description="Comment operations",
)


def _require_auth():
    if not current_user.is_authenticated:
        abort(401, message="Authentication required.")


@blp.route("/tasks/<string:task_id>/comments")
class CommentList(MethodView):

    @blp.arguments(CommentCreateSchema, location="json")
    @blp.response(201, CommentSchema)
    async def post(self, data, task_id):
        """Add a comment to a task."""
        _require_auth()
        cid = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        comment = Comment(
            id=cid,
            task_id=task_id,
            text=data["text"],
            created_at=now,
            user_id=current_user.id,
            username=current_user.username,
        )
        async with get_session() as session:
            session.add(comment)
        return comment.to_dict()


@blp.route("/comments/<string:comment_id>")
class CommentDetail(MethodView):

    @blp.response(204)
    async def delete(self, comment_id):
        """Delete a comment."""
        _require_auth()
        async with get_session() as session:
            comment = await session.get(Comment, comment_id)
            if not comment:
                abort(404, message="Comment not found.")
            await session.delete(comment)
