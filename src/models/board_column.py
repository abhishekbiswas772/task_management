"""
Configurable board columns for the kanban flow.
"""
from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class BoardColumn(Base):
    __tablename__ = "board_columns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    color: Mapped[str] = mapped_column(String(16), nullable=False, default="#6B7280")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "position": self.position,
            "color": self.color,
        }
