"""
Task model — mirrors existing SQLite schema and adds new fields.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class Task(Base):
    __tablename__ = "tasks"

    id:          Mapped[str]             = mapped_column(String(36), primary_key=True)
    title:       Mapped[str]             = mapped_column(String(255), nullable=False)
    description: Mapped[str]             = mapped_column(Text, default="")
    column_name: Mapped[str]             = mapped_column(String(80), default="TODO")
    month:       Mapped[int]             = mapped_column(Integer, nullable=False)
    year:        Mapped[int]             = mapped_column(Integer, nullable=False)
    priority:    Mapped[str]             = mapped_column(String(10), default="Medium")
    due_date:    Mapped[str | None]      = mapped_column(String(32), nullable=True)
    tags:        Mapped[str]             = mapped_column(Text, default="")
    created_at:  Mapped[str]             = mapped_column(String(32), nullable=False)
    created_by:  Mapped[int | None]      = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    comments: Mapped[list["Comment"]] = relationship(
        "Comment",
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="Comment.created_at",
        lazy="raise",
    )
    creator: Mapped[object] = relationship("User", foreign_keys=[created_by], lazy="raise")

    def to_dict(self) -> dict:
        return {
            "id":          self.id,
            "title":       self.title,
            "description": self.description,
            "column_name": self.column_name,
            "month":       self.month,
            "year":        self.year,
            "priority":    self.priority,
            "due_date":    self.due_date,
            "tags":        [t.strip() for t in self.tags.split(",") if t.strip()] if self.tags else [],
            "created_at":  self.created_at,
            "created_by":  self.created_by,
            "creator_name": self.creator.username if self.creator else None,
            "comments":    [c.to_dict() for c in self.comments],
        }
