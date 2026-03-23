"""
Comment model.
"""
from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class Comment(Base):
    __tablename__ = "comments"

    id:         Mapped[str]        = mapped_column(String(36), primary_key=True)
    task_id:    Mapped[str]        = mapped_column(
        String(36), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    text:       Mapped[str]        = mapped_column(Text, nullable=False)
    created_at: Mapped[str]        = mapped_column(String(32), nullable=False)
    user_id:    Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    username:   Mapped[str]        = mapped_column(String(80), default="")

    task:   Mapped[object] = relationship("Task", back_populates="comments")
    author: Mapped[object] = relationship("User", foreign_keys=[user_id], lazy="selectin")

    def to_dict(self) -> dict:
        return {
            "id":         self.id,
            "task_id":    self.task_id,
            "text":       self.text,
            "created_at": self.created_at,
            "user_id":    self.user_id,
            "username":   self.username or (self.author.username if self.author else ""),
        }
