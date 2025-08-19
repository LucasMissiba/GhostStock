from __future__ import annotations

from datetime import datetime, timedelta
from flask import Blueprint, render_template
from flask_login import login_required

from ..models import Item

maintenance_bp = Blueprint("maintenance", __name__, url_prefix="/maintenance")


def _classify_maintenance(item: Item) -> str | None:
    if item.item_type != "cama":
        return None
    if not item.last_maintenance_date:
        return "due"
    days = (datetime.utcnow() - item.last_maintenance_date).days
    if days >= 120:
        return "due"
    if days >= 90:
        return "soon"
    return None


@maintenance_bp.route("/")
@login_required
def maintenance_home():
    items = Item.query.all()
    due = [i for i in items if _classify_maintenance(i) == "due"]
    soon = [i for i in items if _classify_maintenance(i) == "soon"]
    return render_template("maintenance.html", due=due, soon=soon)


