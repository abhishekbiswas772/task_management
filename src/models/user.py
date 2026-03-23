"""
User model — Flask-Login compatible, SQLAlchemy 2.0 declarative style.
"""
from __future__ import annotations

from datetime import datetime, timezone

from flask_login import UserMixin
from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class User(UserMixin, Base):
    __tablename__ = "users"

    id:            Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    username:      Mapped[str]      = mapped_column(String(80),  unique=True,  nullable=False, index=True)
    email:         Mapped[str]      = mapped_column(String(120), unique=True,  nullable=False, index=True)
    password_hash: Mapped[str]      = mapped_column(String(255), nullable=False)
    is_active:     Mapped[bool]     = mapped_column(Boolean, default=True)
    created_at:    Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # Flask-Login
    def get_id(self) -> str:
        return str(self.id)

    def __repr__(self) -> str:
        return f"<User {self.username!r}>"

    def to_dict(self) -> dict:
        return {
            "id":         self.id,
            "username":   self.username,
            "email":      self.email,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
