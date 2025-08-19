from __future__ import annotations

import os
from flask import Blueprint, render_template
from flask_login import login_required

audit_bp = Blueprint("audit", __name__, url_prefix="/audit")


@audit_bp.route("/")
@login_required
def audit_home():
    log_path = os.path.join(os.getcwd(), "logs", "audit.log")
    entries: list[str] = []
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            entries = f.readlines()[-500:]
    entries = [e.strip() for e in entries if e.strip()]
    entries.reverse()
    return render_template("audit.html", entries=entries)


