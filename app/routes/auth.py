from __future__ import annotations

from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user
from sqlalchemy import func

from .. import db, limiter
from ..models import User, ActivityLog
from ..config import Config

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit(lambda: Config.LOGIN_RATE_LIMIT)
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter(func.lower(User.email) == email).first()

        if not user:
            flash("E-mail ou senha incorretos.", "danger")
            return render_template("login.html")

                          
        if user.locked_until and user.locked_until > datetime.utcnow():
            minutes = int((user.locked_until - datetime.utcnow()).total_seconds() // 60) + 1
            flash(f"Conta temporariamente bloqueada. Tente novamente em {minutes} minuto(s).", "danger")
            _log_activity(None if not user else user.id, "login_blocked")
            return render_template("login.html")

        if user.check_password(password):
            user.failed_attempts = 0
            user.locked_until = None
            db.session.commit()
            login_user(user, remember=True)
            _log_activity(user.id, "login_success")
            return redirect(url_for("main.index"))
        else:
            user.failed_attempts += 1
            if user.failed_attempts >= Config.MAX_LOGIN_ATTEMPTS:
                user.locked_until = datetime.utcnow() + timedelta(minutes=Config.LOCKOUT_MINUTES)
            db.session.commit()
            flash("E-mail ou senha incorretos.", "danger")
            _log_activity(user.id, "login_failed")

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    if current_user.is_authenticated:
        _log_activity(current_user.id, "logout")
    logout_user()
    return redirect(url_for("auth.login"))


def _log_activity(user_id: int | None, action: str) -> None:
    from flask import request

    log = ActivityLog(user_id=user_id, action=action, ip=request.remote_addr)
    db.session.add(log)
    db.session.commit()



