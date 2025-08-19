from __future__ import annotations

from flask import Blueprint, render_template, jsonify
from flask_login import login_required

from ..models import Item

map_bp = Blueprint("map_view", __name__, url_prefix="")


@map_bp.route("/map")
@login_required
def map_page():
    return render_template("map.html")


@map_bp.route("/items/api/geo")
@login_required
def items_geo():
    rows = (
        Item.query.with_entities(
            Item.id, Item.name, Item.item_type, Item.status, Item.origin_stock, Item.lat, Item.lng
        )
        .filter(Item.lat.isnot(None), Item.lng.isnot(None))
        .all()
    )
    data = [
        {
            "id": r.id,
            "name": r.name,
            "type": r.item_type,
            "status": r.status,
            "stock": r.origin_stock,
            "lat": float(r.lat),
            "lng": float(r.lng),
        }
        for r in rows
    ]
    return jsonify({"items": data})


