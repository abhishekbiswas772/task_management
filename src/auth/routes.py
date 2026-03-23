"""
Authentication routes: register, login, logout.
All write routes are async; login_required is enforced per-route.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from flask import flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import select

from src.auth import auth_bp
from src.database import get_session
from src.extensions import bcrypt
from src.models.user import User


# ── Register ──────────────────────────────────────────────────────────

@auth_bp.route("/register", methods=["GET", "POST"])
async def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email    = request.form.get("email",    "").strip().lower()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm",  "")

        if not username or not email or not password:
            error = "All fields are required."
        elif len(username) < 3:
            error = "Username must be at least 3 characters."
        elif len(password) < 8:
            error = "Password must be at least 8 characters."
        elif password != confirm:
            error = "Passwords do not match."
        else:
            async with get_session() as session:
                existing = await session.execute(
                    select(User).where(
                        (User.username == username) | (User.email == email)
                    )
                )
                if existing.scalar_one_or_none():
                    error = "Username or email already taken."
                else:
                    pw_hash = bcrypt.generate_password_hash(password).decode("utf-8")
                    user = User(
                        username=username,
                        email=email,
                        password_hash=pw_hash,
                        created_at=datetime.now(timezone.utc),
                    )
                    session.add(user)

            if not error:
                flash("Account created! Please log in.", "success")
                return redirect(url_for("auth.login"))

    return render_template("auth/register.html", error=error)


# ── Login ─────────────────────────────────────────────────────────────

@auth_bp.route("/login", methods=["GET", "POST"])
async def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    error = None
    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        password   = request.form.get("password",   "")
        remember   = bool(request.form.get("remember"))

        async with get_session() as session:
            result = await session.execute(
                select(User).where(
                    (User.username == identifier) | (User.email == identifier.lower())
                )
            )
            user = result.scalar_one_or_none()

        if user and bcrypt.check_password_hash(user.password_hash, password):
            session.permanent = True          # persist for PERMANENT_SESSION_LIFETIME
            login_user(user, remember=True)   # always set remember cookie (90 days)
            next_page = request.args.get("next")
            return redirect(next_page or url_for("index"))
        else:
            error = "Invalid username/email or password."

    return render_template("auth/login.html", error=error)


# ── Logout ────────────────────────────────────────────────────────────

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
