"""
Marshmallow schemas for Flask-Smorest request validation and response serialization.
"""
from marshmallow import EXCLUDE, Schema, fields, validate


# ── Comment ───────────────────────────────────────────────────────────

class CommentSchema(Schema):
    id         = fields.Str(dump_only=True)
    task_id    = fields.Str(dump_only=True)
    text       = fields.Str(required=True, validate=validate.Length(min=1, max=2000))
    mentions   = fields.List(fields.Str(), dump_only=True)
    created_at = fields.Str(dump_only=True)
    user_id    = fields.Int(dump_only=True, allow_none=True)
    username   = fields.Str(dump_only=True)


class CommentCreateSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    text = fields.Str(required=True, validate=validate.Length(min=1, max=2000))


# ── Task ──────────────────────────────────────────────────────────────

class TaskSchema(Schema):
    id           = fields.Str(dump_only=True)
    title        = fields.Str(required=True)
    description  = fields.Str(load_default="")
    mentions     = fields.List(fields.Str(), dump_only=True)
    column_name  = fields.Str(dump_only=True)
    month        = fields.Int(dump_only=True)
    year         = fields.Int(dump_only=True)
    priority     = fields.Str(dump_only=True)
    due_date     = fields.Str(dump_only=True, allow_none=True)
    tags         = fields.List(fields.Str(), dump_only=True)
    created_at   = fields.Str(dump_only=True)
    created_by   = fields.Int(dump_only=True, allow_none=True)
    creator_name = fields.Str(dump_only=True, allow_none=True)
    comments     = fields.List(fields.Nested(CommentSchema), dump_only=True)


class TaskQuerySchema(Schema):
    class Meta:
        unknown = EXCLUDE

    month = fields.Int(required=True, validate=validate.Range(min=1, max=12))
    year  = fields.Int(required=True, validate=validate.Range(min=2020, max=2100))


class TaskCreateSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    title       = fields.Str(required=True, validate=validate.Length(min=1, max=255))
    description = fields.Str(load_default="")
    column      = fields.Str(load_default="TODO")
    month       = fields.Int(required=True, validate=validate.Range(min=1, max=12))
    year        = fields.Int(required=True, validate=validate.Range(min=2020, max=2100))
    priority    = fields.Str(
        load_default="Medium",
        validate=validate.OneOf(["High", "Medium", "Low"]),
    )
    due_date    = fields.Str(load_default=None, allow_none=True)
    tags        = fields.List(fields.Str(), load_default=[])


class TaskUpdateSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    title       = fields.Str(validate=validate.Length(min=1, max=255))
    description = fields.Str()
    column_name = fields.Str()
    priority    = fields.Str(validate=validate.OneOf(["High", "Medium", "Low"]))
    due_date    = fields.Str(allow_none=True)
    tags        = fields.List(fields.Str())


# ── Export ────────────────────────────────────────────────────────────

class ExportQuerySchema(Schema):
    class Meta:
        unknown = EXCLUDE

    month = fields.Int(required=True, validate=validate.Range(min=1, max=12))
    year  = fields.Int(required=True, validate=validate.Range(min=2020, max=2100))
    label = fields.Str(load_default="Tasks")


# ── Board columns ─────────────────────────────────────────────────────

class BoardColumnSchema(Schema):
    id       = fields.Int(dump_only=True)
    name     = fields.Str(required=True)
    position = fields.Int(required=True)
    color    = fields.Str(required=True)


class BoardColumnCreateSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    name  = fields.Str(required=True, validate=validate.Length(min=1, max=80))
    color = fields.Str(load_default="#6B7280", validate=validate.Length(min=4, max=16))


class BoardColumnUpdateSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    name     = fields.Str(validate=validate.Length(min=1, max=80))
    color    = fields.Str(validate=validate.Length(min=4, max=16))
    position = fields.Int(validate=validate.Range(min=0))


class BoardColumnDeleteSchema(Schema):
    deleted_column = fields.Str(required=True)
    moved_to       = fields.Str(required=True)


# ── Auth ──────────────────────────────────────────────────────────────

class UserSchema(Schema):
    id         = fields.Int(dump_only=True)
    username   = fields.Str(dump_only=True)
    email      = fields.Str(dump_only=True)
    created_at = fields.Str(dump_only=True)


class MentionUserSchema(Schema):
    id       = fields.Int(dump_only=True)
    username = fields.Str(dump_only=True)
