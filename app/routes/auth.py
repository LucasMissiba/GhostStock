from __future__ import annotations

from datetime import datetime, timedelta
import os
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


@auth_bp.route("/_ensure_admin", methods=["GET", "POST"])
def ensure_admin():
    from flask import request, jsonify, abort
    token = request.args.get("token") or request.headers.get("X-Admin-Token")
    mgmt = os.getenv("MANAGEMENT_TOKEN")
    if not mgmt or token != mgmt:
        abort(403)
    email = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@ghoststock.local")
    password = os.getenv("DEFAULT_ADMIN_PASSWORD", "Admin123!")
    name = os.getenv("DEFAULT_ADMIN_NAME", "Administrador")
    user = User.query.filter(func.lower(User.email) == email.lower()).first()
    created = False
    if user is None:
        user = User(email=email, name=name, role="admin")
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        created = True
    else:
        if (os.getenv("AUTO_UPDATE_ADMIN_PASSWORD", "true").lower() == "true"):
            user.set_password(password)
            # também zera bloqueio se houve muitas tentativas erradas
            user.failed_attempts = 0
            user.locked_until = None
            db.session.commit()
    return jsonify({"ok": True, "created": created, "email": email})


@auth_bp.route("/_seed_demo", methods=["POST", "GET"])
def seed_demo():
    from flask import request, jsonify, abort
    from datetime import datetime, timedelta
    import random
    from ..models import Item
    token = request.args.get("token") or request.headers.get("X-Admin-Token")
    mgmt = os.getenv("MANAGEMENT_TOKEN")
    if not mgmt or token != mgmt:
        abort(403)
    total = request.args.get("total", type=int) or 200
    total = max(1, min(total, 1000))

    admin = User.query.filter(func.lower(User.email) == os.getenv("DEFAULT_ADMIN_EMAIL", "admin@ghoststock.local").lower()).first()
    if admin is None:
        abort(400, description="admin inexistente; chame /auth/_ensure_admin primeiro")

    existing = Item.query.count()
    if existing >= total:
        return jsonify({"ok": True, "skipped": True, "existing": existing})

    need = total - existing
    STOCKS = ['AL', 'AS', 'AV', 'AB']
    CITY_ZONES = {
        'AL': { 'central': { 'lat': (-22.925, -22.890), 'lng': (-43.240, -43.180), 'weight': 0.6 }, 'resid':  { 'lat': (-22.990, -22.930), 'lng': (-43.500, -43.350), 'weight': 0.4 } },
        'AS': { 'central': { 'lat': (-23.570, -23.520), 'lng': (-46.700, -46.610), 'weight': 0.6 }, 'resid':  { 'lat': (-23.680, -23.600), 'lng': (-46.790, -46.650), 'weight': 0.4 } },
        'AV': { 'central': { 'lat': (-22.985, -22.965), 'lng': (-46.990, -46.970), 'weight': 0.6 }, 'resid':  { 'lat': (-22.995, -22.985), 'lng': (-47.020, -46.990), 'weight': 0.4 } },
        'AB': { 'central': { 'lat': (-19.937, -19.905), 'lng': (-43.960, -43.915), 'weight': 0.6 }, 'resid':  { 'lat': (-19.990, -19.940), 'lng': (-44.020, -43.930), 'weight': 0.4 } },
    }
    TYPES = ['cama', 'cadeira_higienica', 'cadeira_rodas', 'muletas', 'andador']
    now = datetime.utcnow()

    batch: list[Item] = []
    created = 0
    for idx in range(existing + 1, existing + need + 1):
        stock = random.choice(STOCKS)
        item_type = random.choice(TYPES)
        prefix = {'cama': 'CAM','cadeira_higienica': 'CHG','cadeira_rodas': 'CRD','andador': 'AND','muletas': 'MUL'}[item_type]
        code = f"{prefix}{idx:05d}"
        z = CITY_ZONES[stock]
        zone = 'central' if random.random() < z['central']['weight'] else 'resid'
        lat_range = z[zone]['lat']
        lng_range = z[zone]['lng']
        lat = round(random.uniform(lat_range[0], lat_range[1]), 6)
        lng = round(random.uniform(lng_range[0], lng_range[1]), 6)
        status = 'locado' if random.random() < 0.7 else 'disponivel'
        location = {'AL':'Rio de Janeiro','AS':'São Paulo','AV':'Valinhos','AB':'Belo Horizonte'}[stock] if status=='locado' else None
        item = Item(
            code=code,
            item_type=item_type,
            name=code,
            description=("Cama hospitalar" if item_type == 'cama' else item_type.replace('_',' ').title()),
            origin_stock=stock,
            status=status,
            location=location,
            patient_name=None,
            movement_date=now - timedelta(days=random.randint(0, 45)),
            lat=lat,
            lng=lng,
            last_maintenance_date=(now - timedelta(days=random.randint(61, 120))) if random.random() < 0.3 else None,
            entry_date=now - timedelta(days=random.randint(30, 120)),
            expiry_date=None,
            quantity=random.randint(1, 5),
            min_threshold=1,
            owner_id=admin.id,
        )
        batch.append(item)
        created += 1
    if batch:
        db.session.bulk_save_objects(batch)
        db.session.commit()
    return jsonify({"ok": True, "created": created, "total": Item.query.count()})



