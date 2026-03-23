"""
Application factory.
"""
from __future__ import annotations

import os
import sqlite3

import redis
from flask import Flask, redirect, render_template, url_for
from flask_login import login_required

from config import DB_PATH, config_map
from src.backup.scheduler import start_scheduler
from src.database import create_tables, init_engine
from src.extensions import bcrypt, csrf, login_manager, sess, smorest_api
from src.models.user import User


def create_app(config_name: str | None = None) -> Flask:
    config_name = config_name or os.environ.get("FLASK_ENV", "default")
    cfg = config_map[config_name]

    app = Flask(
        __name__,
        template_folder="src/templates",
        static_folder="src/static",
    )
    app.config.from_object(cfg)

    # ── Redis for Flask-Session ───────────────────────────────────────
    try:
        r = redis.from_url(app.config["REDIS_URL"], decode_responses=False)
        r.ping()
        app.config["SESSION_REDIS"] = r
    except Exception:
        app.logger.warning(
            "Redis unavailable — falling back to filesystem sessions. "
            "Set REDIS_URL env var for production."
        )
        app.config["SESSION_TYPE"] = "filesystem"

    # ── Extensions ────────────────────────────────────────────────────
    bcrypt.init_app(app)
    sess.init_app(app)
    csrf.init_app(app)
    smorest_api.init_app(app)

    # ── Flask-Login ───────────────────────────────────────────────────
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id: str) -> User | None:
        """Sync user loader — uses a direct SQLite connection to avoid event-loop conflicts."""
        try:
            conn = sqlite3.connect(DB_PATH)
            row  = conn.execute(
                "SELECT id, username, email, is_active FROM users WHERE id=?",
                (int(user_id),),
            ).fetchone()
            conn.close()
            if not row:
                return None

            class _User:
                is_anonymous = False
                def get_id(self):
                    return str(self.id)
                @property
                def is_authenticated(self):
                    return self.is_active

            u           = _User()
            u.id        = row[0]
            u.username  = row[1]
            u.email     = row[2]
            u.is_active = bool(row[3])
            return u
        except Exception:
            return None

    # ── Async DB engine ───────────────────────────────────────────────
    init_engine(app.config["SQLALCHEMY_DATABASE_URI"], echo=app.config.get("DEBUG", False))

    # ── Create tables + migrate existing DB ──────────────────────────
    import asyncio
    asyncio.run(create_tables())

    # ── Register blueprints ───────────────────────────────────────────
    from src.auth import auth_bp
    app.register_blueprint(auth_bp)

    from src.api.tasks    import blp as tasks_blp
    from src.api.comments import blp as comments_blp
    smorest_api.register_blueprint(tasks_blp)
    smorest_api.register_blueprint(comments_blp)

    from src.api.export import export_bp
    app.register_blueprint(export_bp)

    # Exempt JSON API and export endpoints from CSRF
    # (API routes use session-cookie auth; CSRF token is passed via X-CSRFToken header in JS)
    csrf.exempt(tasks_blp)
    csrf.exempt(comments_blp)
    csrf.exempt(export_bp)

    # ── Main route ────────────────────────────────────────────────────
    @app.route("/")
    @login_required
    def index():
        return render_template("index.html")

    @app.route("/favicon.ico")
    def favicon():
        return "", 204

    # ── Error handlers ────────────────────────────────────────────────
    @app.errorhandler(401)
    def unauthorized(e):
        from flask import request
        if request.path.startswith("/api/"):
            from flask import jsonify
            return jsonify({"error": "Authentication required"}), 401
        return redirect(url_for("auth.login"))

    @app.errorhandler(404)
    def not_found(e):
        from flask import request, jsonify
        if request.path.startswith("/api/"):
            return jsonify({"error": "Not found"}), 404
        return render_template("404.html"), 404

    # ── Backup scheduler ─────────────────────────────────────────────
    if not app.config.get("TESTING"):
        start_scheduler(app)

    return app
