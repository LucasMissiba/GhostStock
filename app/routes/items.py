from __future__ import annotations

from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_file
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from sqlalchemy import and_
import os
from flask import jsonify
from io import BytesIO
import csv
import json
import re

from .. import db
from ..models import Item, ItemMovement
from ..utils import allowed_file, validate_image_file

items_bp = Blueprint("items", __name__, url_prefix="/items")


@items_bp.route("/new", methods=["GET", "POST"])
@login_required
def create_item():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        item_type = (request.form.get("item_type") or "").strip() or None
        description = request.form.get("description")
        origin_stock = request.form.get("origin_stock")                  
                                                                             
        status = "disponivel"
        location = request.form.get("location")
                                                          
        patient_name = None
        movement_date = request.form.get("movement_date")
                                                                            
        lat = None
        lng = None
        entry_date = request.form.get("entry_date")
        expiry_date = request.form.get("expiry_date")
        quantity = 1
        min_threshold = 1

        if not name:
            flash("Nome é obrigatório.", "danger")
            return render_template("item_form.html")

        photo_path = None
        file = request.files.get("photo")
        if file and allowed_file(file.filename, current_app.config.get("ALLOWED_EXTENSIONS")) and validate_image_file(file):
                               
            from PIL import Image
            filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{secure_filename(file.filename)}"
            upload_dir = current_app.config["UPLOAD_FOLDER"]
            os.makedirs(upload_dir, exist_ok=True)
            path = os.path.join(upload_dir, filename)
            img = Image.open(file)
            img.save(path, optimize=True, quality=80)
            photo_path = f"static/uploads/{filename}"

                                                             
        next_seq = Item.query.count() + 1
        code = str(next_seq).zfill(6)

        item = Item(
            code=code,
            name=name,
            item_type=item_type,
            description=description,
            status=status,
            origin_stock=origin_stock,
            location=location,
            patient_name=patient_name,
            movement_date=datetime.strptime(movement_date, "%Y-%m-%d") if movement_date else datetime.utcnow(),
            lat=None,
            lng=None,
            photo_path=photo_path,
            entry_date=datetime.strptime(entry_date, "%Y-%m-%d") if entry_date else datetime.utcnow(),
            expiry_date=datetime.strptime(expiry_date, "%Y-%m-%d") if expiry_date else None,
            quantity=quantity,
            min_threshold=min_threshold,
            owner_id=current_user.id,
        )
        db.session.add(item)
        db.session.commit()

        _add_movement(item.id, "created", None, None)
        flash("Item criado com sucesso!", "success")
        return redirect(url_for("items.list_items"))

    return render_template("item_form.html")


@items_bp.route("/", methods=["GET"])
@login_required
def list_items():
             
    status = request.args.get("status")
    maint = request.args.get("maint")                        
    location = None
    origin_stock = request.args.get("origin_stock")
    item_type = request.args.get("item_type")
    q = request.args.get("q", "").strip()
    page = max(int(request.args.get("page", 1) or 1), 1)
    per_page = min(int(request.args.get("per_page", 20) or 20), 100)
    entry_from = request.args.get('entry_from')
    entry_to = request.args.get('entry_to')

    query = Item.query
    if status:
                                                               
        status_norm = status.lower().strip()
        if status_norm in ("em_uso", "em uso"):
            query = query.filter(Item.status == "locado")
        elif status_norm in ("em_manutencao", "maint_due", "manutencao", "em-manutencao"):
            from datetime import datetime as _dt, timedelta as _td
            cutoff = _dt.utcnow() - _td(days=60)
            query = query.filter(
                Item.last_maintenance_date.isnot(None),
                Item.last_maintenance_date <= cutoff,
            )
        elif status_norm in ("aguardando_manutencao", "maint_soon", "aguardando-manutencao"):
            from datetime import datetime as _dt, timedelta as _td
            now_ = _dt.utcnow()
            query = query.filter(
                Item.last_maintenance_date.isnot(None),
                Item.last_maintenance_date > (now_ - _td(days=60)),
                Item.last_maintenance_date <= (now_ - _td(days=45)),
            )
        else:
            query = query.filter(Item.status == status)
                                          
    if origin_stock:
        query = query.filter(Item.origin_stock == origin_stock)
    if item_type:
        query = query.filter(Item.item_type == item_type)
    if maint == "due":
        cutoff = datetime.utcnow() - timedelta(days=60)
        query = query.filter(
            Item.last_maintenance_date.isnot(None),
            Item.last_maintenance_date <= cutoff,
        )
                                                                                                 
    if status == "aguardando_manutencao":
        now = datetime.utcnow()
        query = query.filter(
            Item.last_maintenance_date.isnot(None),
            Item.last_maintenance_date > (now - timedelta(days=60)),
            Item.last_maintenance_date <= (now - timedelta(days=45)),
        )
        status = None                                                 

    if q:
        like = f"%{q}%"
        query = query.filter(
            (Item.name.ilike(like)) | (Item.description.ilike(like)) | (Item.location.ilike(like)) | (Item.patient_name.ilike(like))
        )
    if entry_from:
        try:
            from datetime import datetime as _dt
            query = query.filter(Item.entry_date >= _dt.strptime(entry_from, '%Y-%m-%d'))
        except Exception:
            pass
    if entry_to:
        try:
            from datetime import datetime as _dt
            query = query.filter(Item.entry_date <= _dt.strptime(entry_to, '%Y-%m-%d'))
        except Exception:
            pass

    pagination = query.order_by(Item.entry_date.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return render_template("items_list.html", items=pagination.items, mine_only=False, pagination=pagination)


@items_bp.route("/api/autocomplete")
@login_required
def autocomplete():
    q = (request.args.get("q") or "").strip()
    if not q:
        return jsonify([])
    like = f"%{q}%"
    results = (
        Item.query.with_entities(Item.id, Item.name)
        .filter(Item.name.ilike(like))
        .order_by(Item.name.asc())
        .limit(10)
        .all()
    )
    return jsonify([{"id": r.id, "name": r.name} for r in results])


@items_bp.route("/api/history/<int:item_id>")
@login_required
def item_history_api(item_id: int):
    item = Item.query.get_or_404(item_id)
    if current_user.role != "admin" and item.owner_id != current_user.id:
        return jsonify({"error": "forbidden"}), 403
    movements = ItemMovement.query.filter_by(item_id=item.id).order_by(ItemMovement.timestamp.asc()).all()
    return jsonify({
        "item": item.to_dict_summary(),
        "movements": [m.to_dict() for m in movements]
    })


@items_bp.route('/import', methods=['POST'])
@login_required
def import_items():
    if current_user.role != 'admin':
        return jsonify({"error": "forbidden"}), 403
    file = request.files.get('file')
    if not file:
        return jsonify({"error": "no_file"}), 400
    filename = (file.filename or '').lower()
    created = 0
    if filename.endswith('.csv'):
        data = file.read().decode('utf-8', errors='ignore').splitlines()
        reader = csv.DictReader(data)
        for row in reader:
            item = Item(
                name=row.get('name') or 'Sem nome',
                description=row.get('description'),
                status=row.get('status') or 'disponivel',
                origin_stock=row.get('origin_stock'),
                location=row.get('location'),
                patient_name=row.get('patient_name'),
                owner_id=current_user.id
            )
            db.session.add(item)
            created += 1
        db.session.commit()
    elif filename.endswith('.json'):
        payload = json.load(file)
        for obj in payload:
            item = Item(
                name=obj.get('name') or 'Sem nome',
                description=obj.get('description'),
                status=obj.get('status') or 'disponivel',
                origin_stock=obj.get('origin_stock'),
                location=obj.get('location'),
                patient_name=obj.get('patient_name'),
                owner_id=current_user.id
            )
            db.session.add(item)
            created += 1
        db.session.commit()
    else:
        return jsonify({"error": "unsupported_format"}), 400
    return jsonify({"created": created})


@items_bp.route('/export', methods=['GET'])
@login_required
def export_items():
    if current_user.role != 'admin':
        return jsonify({"error": "forbidden"}), 403
    fmt = (request.args.get('format') or 'csv').lower()
    rows = [i.to_dict_summary() for i in Item.query.order_by(Item.id).all()]
    if fmt == 'csv':
        from flask import make_response
        import io as _io
        output = _io.StringIO()
        writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()) if rows else ['id','name'])
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
        resp = make_response(output.getvalue())
        resp.headers['Content-Disposition'] = 'attachment; filename=items.csv'
        resp.headers['Content-Type'] = 'text/csv'
        return resp
    elif fmt == 'json':
        return jsonify(rows)
    else:
        return jsonify({"error": "unsupported_format"}), 400


@items_bp.route('/image-search', methods=['POST'])
@login_required
def image_search():
    """Busca por imagem usando OCR (pytesseract). Extrai texto e pesquisa por nome/código.
    Requer Tesseract instalado no sistema. Se indisponível, retorna erro amigável."""
    file = request.files.get('file')
    if not file:
        return jsonify({"error": "no_file"}), 400
    try:
        import pytesseract
        from PIL import Image
        img = Image.open(file.stream)
        text = pytesseract.image_to_string(img) or ''
        text = re.sub(r'[^\w\s-]', ' ', text).strip()
        if not text:
            return jsonify({"matches": [], "text": text})
        like = f"%{text.split()[0]}%"
        matches = Item.query.filter(
            (Item.name.ilike(like)) | (Item.description.ilike(like))
        ).limit(20).all()
        return jsonify({
            "text": text,
            "matches": [i.to_dict_summary() for i in matches]
        })
    except Exception as exc:
        return jsonify({"error": "ocr_failed", "detail": str(exc)}), 500


@items_bp.route('/api/similar')
@login_required
def similar_items():
    """Sugestão de itens parecidos por nome/tipo/estoque."""
    q = (request.args.get('q') or '').strip().lower()
    item_type = request.args.get('item_type')
    origin_stock = request.args.get('origin_stock')
    query = Item.query
    if item_type:
        query = query.filter(Item.item_type == item_type)
    if origin_stock:
        query = query.filter(Item.origin_stock == origin_stock)
    if q:
        like = f"%{q}%"
        query = query.filter((Item.name.ilike(like)) | (Item.description.ilike(like)))
    results = query.order_by(Item.entry_date.desc()).limit(10).all()
    return jsonify([i.to_dict_summary() for i in results])


@items_bp.route("/<int:item_id>")
@login_required
def view_item(item_id: int):
    item = Item.query.get_or_404(item_id)
    if current_user.role != "admin" and item.owner_id != current_user.id:
        flash("Sem permissão para visualizar este item.", "danger")
        return redirect(url_for("items.list_items"))
    return render_template("item_view.html", item=item)


@items_bp.route("/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
def edit_item(item_id: int):
    item = Item.query.get_or_404(item_id)
    if current_user.role != "admin" and item.owner_id != current_user.id:
        flash("Sem permissão para editar este item.", "danger")
        return redirect(url_for("items.list_items"))

    if request.method == "POST":
        old_status = item.status
        old_location = item.location
        old_patient = item.patient_name

                                                                            
        item.name = request.form.get("name", item.name)
        posted_type = (request.form.get("item_type") or "").strip()
        if posted_type:
            item.item_type = posted_type
        item.description = request.form.get("description", item.description)
        item.origin_stock = request.form.get("origin_stock", item.origin_stock)
        item.status = request.form.get("status", item.status)
        item.location = request.form.get("location", item.location)
                                                                                        
        if item.status != "disponivel":
            item.patient_name = request.form.get("patient_name", item.patient_name)
        movement_date = request.form.get("movement_date")
        item.movement_date = datetime.strptime(movement_date, "%Y-%m-%d") if movement_date else item.movement_date
        lat = request.form.get("lat")
        lng = request.form.get("lng")
        item.lat = float(lat) if lat else item.lat
        item.lng = float(lng) if lng else item.lng
        expiry_date = request.form.get("expiry_date")
        item.expiry_date = (
            datetime.strptime(expiry_date, "%Y-%m-%d") if expiry_date else item.expiry_date
        )
        item.quantity = 1
        item.min_threshold = 1

        file = request.files.get("photo")
        if file and allowed_file(file.filename, current_app.config.get("ALLOWED_EXTENSIONS")) and validate_image_file(file):
            from PIL import Image
            filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{secure_filename(file.filename)}"
            upload_dir = current_app.config["UPLOAD_FOLDER"]
            os.makedirs(upload_dir, exist_ok=True)
            path = os.path.join(upload_dir, filename)
            img = Image.open(file)
            img.save(path, optimize=True, quality=80)
            item.photo_path = f"static/uploads/{filename}"

        db.session.commit()

        if old_status != item.status:
            _add_movement(item.id, "status_change", old_status, item.status)
        if old_location != item.location:
            _add_movement(item.id, "location_change", old_location, item.location)
        if old_patient != item.patient_name:
            _add_movement(item.id, "patient_change", old_patient, item.patient_name)

        flash("Item atualizado com sucesso!", "success")
        return redirect(url_for("items.view_item", item_id=item.id))

    return render_template("item_form.html", item=item)


@items_bp.route("/<int:item_id>/status", methods=["POST"])
@login_required
def update_status(item_id: int):
    item = Item.query.get_or_404(item_id)
    if current_user.role != "admin" and item.owner_id != current_user.id:
        return jsonify({"error": "forbidden"}), 403

    data = request.get_json(silent=True) or {}
    requested = (data.get("status") or "").strip().lower()
    mapping = {
        "aguardando_manutencao": "em_manutencao",
        "em_manutencao": "em_manutencao",
        "locado": "locado",
        "vencido": "vencido",
        "disponivel": "disponivel",
    }
    new_status = mapping.get(requested)
    if not new_status:
        return jsonify({"error": "invalid_status"}), 400

    old_status = item.status
    item.status = new_status
    item.movement_date = datetime.utcnow()
    db.session.commit()
    _add_movement(item.id, "status_change", old_status, item.status)

    return jsonify({"status": item.status})


def _add_movement(item_id: int, action: str, from_value: str | None, to_value: str | None) -> None:
    mv = ItemMovement(item_id=item_id, user_id=current_user.id, action=action, from_value=from_value, to_value=to_value)
    db.session.add(mv)
    db.session.commit()


@items_bp.route("/<int:item_id>/history", methods=["GET"])
@login_required
def item_history(item_id: int):
    item = Item.query.get_or_404(item_id)
    if current_user.role != "admin" and item.owner_id != current_user.id:
        return jsonify({"error": "forbidden"}), 403

                          
    movements = ItemMovement.query.filter_by(item_id=item.id).order_by(ItemMovement.timestamp.asc()).all()

                                                            
    patients = []
    for mv in movements:
        if mv.action == "patient_change" and mv.to_value:
            if mv.to_value not in patients:
                patients.append(mv.to_value)

                                                                               
    maintenance_periods = []
    start = None
    for mv in movements:
        if mv.action == "status_change":
            if (mv.to_value == "em_manutencao") and start is None:
                start = mv.timestamp
            elif start is not None and mv.from_value == "em_manutencao" and mv.to_value != "em_manutencao":
                duration_days = (mv.timestamp - start).days
                maintenance_periods.append({
                    "start": start.strftime('%Y-%m-%d %H:%M'),
                    "end": mv.timestamp.strftime('%Y-%m-%d %H:%M'),
                    "days": duration_days
                })
                start = None

    data = {
        "id": item.id,
        "code": item.name,
        "entry_date": item.entry_date.strftime('%Y-%m-%d') if item.entry_date else None,
        "current_status": item.status,
        "lat": item.lat,
        "lng": item.lng,
        "location": item.location,
        "patients": patients,
        "maintenance_periods": maintenance_periods,
        "movements": [
            {
                "action": mv.action,
                "from": mv.from_value,
                "to": mv.to_value,
                "timestamp": mv.timestamp.strftime('%Y-%m-%d %H:%M')
            } for mv in movements
        ]
    }
    return jsonify(data)


