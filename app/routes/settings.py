from __future__ import annotations

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from .. import db

settings_bp = Blueprint("settings", __name__, url_prefix="/settings")


@settings_bp.route("/", methods=["GET", "POST"])
@login_required
def settings_home():
    if request.method == "POST":
        theme = request.form.get("theme")
        if theme in {"light", "dark"}:
            current_user.theme = theme
            db.session.commit()
                                                                       
                                         
            flash("Tema salvo.", "success")
            return redirect(url_for("settings.settings_home"))
    return render_template("settings.html")


