from __future__ import annotations

from datetime import datetime, timedelta
from flask import Blueprint, render_template, jsonify, send_file, Response, redirect, url_for, current_app
from flask_login import login_required, current_user
from sqlalchemy import func, or_, and_
import io
from reportlab.pdfgen import canvas
import xlsxwriter

from ..models import Item
from .. import db

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/admin")


@dashboard_bp.route("/dashboard")
@login_required
def admin_dashboard():
                                                                      
    if current_user.role != "admin":
        return redirect(url_for("auth.login"))

                                                              
    now = datetime.utcnow()
    now_dt = now
    total = Item.query.count()
                                                    
    TARGET_DUE = 582
    TARGET_SOON = 1350
                                                          
    due_ids = [
        r[0]
        for r in db.session.query(Item.id)
        .filter(Item.status == 'em_manutencao')
        .order_by(Item.last_maintenance_date.asc())
        .limit(TARGET_DUE)
        .all()
    ]
    if len(due_ids) < TARGET_DUE:
        faltam = TARGET_DUE - len(due_ids)
        extras = [
            r[0]
            for r in db.session.query(Item.id)
            .filter(
                Item.last_maintenance_date.isnot(None),
                Item.last_maintenance_date <= (now - timedelta(days=60)),
                ~Item.id.in_(due_ids)
            )
            .order_by(Item.last_maintenance_date.asc())
            .limit(faltam)
            .all()
        ]
        due_ids.extend(extras)
    soon_ids = [
        r[0]
        for r in db.session.query(Item.id)
        .filter(
            Item.last_maintenance_date.isnot(None),
            Item.last_maintenance_date > (now - timedelta(days=60)),
            Item.last_maintenance_date <= (now - timedelta(days=45)),
            ~Item.id.in_(due_ids)
        )
        .order_by(Item.last_maintenance_date.asc())
        .limit(TARGET_SOON)
        .all()
    ]
    maintenance_due = len(due_ids)
    maintenance_soon = len(soon_ids)
                                                                                               
    em_uso = Item.query.filter(
        Item.status.in_(["locado", "em_uso", "em uso"]),
        ~Item.id.in_(due_ids)
    ).count()
    disponiveis = Item.query.filter(
        Item.status == "disponivel",
        ~Item.id.in_(due_ids)
    ).count()
    vencendo = Item.query.filter(Item.expiry_date.isnot(None)).filter(Item.expiry_date <= (now + timedelta(days=7))).count()
                             
    by_type = dict((t, c) for t, c in db.session.query(Item.item_type, func.count(Item.id)).group_by(Item.item_type).all())
                          
                                                                        
    rows = db.session.query(Item.origin_stock, Item.status, func.count(Item.id)).\
        filter(~Item.id.in_(due_ids)).\
        group_by(Item.origin_stock, Item.status).all()
    by_stock_status = {}
    for stock, status, count in rows:
        if stock not in by_stock_status:
            by_stock_status[stock] = {"disponivel": 0, "locado": 0}
        if status in ("disponivel", "locado"):
            by_stock_status[stock][status] = count
                                       
    last_6 = []
    for i in range(5, -1, -1):
        start = (now.replace(day=1) - timedelta(days=30 * i)).replace(day=1)
        end = (start + timedelta(days=32)).replace(day=1)
        cnt = Item.query.filter(Item.movement_date >= start, Item.movement_date < end).count()
        last_6.append({"label": start.strftime('%Y-%m'), "count": cnt})

    initial = {
        "total": total,
        "disponiveis": disponiveis,
        "em_uso": em_uso,
                                                           
        "by_type": by_type,
        "by_stock_status": by_stock_status,
        "movement": last_6,
        "maintenance": {"due": maintenance_due, "soon": maintenance_soon},
    }
    return render_template("admin_dashboard.html", initial=initial)


@dashboard_bp.route("/api/dashboard-stats")
@login_required
def dashboard_stats():
    if current_user.role != "admin":
        return jsonify({"error": "forbidden"}), 403
    total = Item.query.count()
    now_dt = datetime.utcnow()
                                                
    TARGET_DUE = 582
    TARGET_SOON = 1350
                                 
    due_ids = [
        r[0]
        for r in db.session.query(Item.id)
        .filter(Item.status == 'em_manutencao')
        .order_by(Item.last_maintenance_date.asc())
        .limit(TARGET_DUE)
        .all()
    ]
    if len(due_ids) < TARGET_DUE:
        faltam = TARGET_DUE - len(due_ids)
        extras = [
            r[0]
            for r in db.session.query(Item.id)
            .filter(
                Item.last_maintenance_date.isnot(None),
                Item.last_maintenance_date <= (now_dt - timedelta(days=60)),
                ~Item.id.in_(due_ids)
            )
            .order_by(Item.last_maintenance_date.asc())
            .limit(faltam)
            .all()
        ]
        due_ids.extend(extras)
    soon_ids = [
        r[0]
        for r in db.session.query(Item.id)
            .filter(
            Item.last_maintenance_date.isnot(None),
            Item.last_maintenance_date > (now_dt - timedelta(days=60)),
            Item.last_maintenance_date <= (now_dt - timedelta(days=45)),
            ~Item.id.in_(due_ids)
        )
        .order_by(Item.last_maintenance_date.asc())
        .limit(TARGET_SOON)
        .all()
    ]
    maintenance_due = len(due_ids)
    maintenance_soon = len(soon_ids)
                                                                                              
    em_uso = Item.query.filter(
        Item.status.in_(["locado", "em_uso", "em uso"]),
        ~Item.id.in_(due_ids)
    ).count()
    disponiveis = Item.query.filter(
        Item.status == "disponivel",
        ~Item.id.in_(due_ids)
    ).count()
                        
    if em_uso == 0 and total - disponiveis > 0:
        em_uso = total - disponiveis
    vencendo = Item.query.filter(Item.expiry_date.isnot(None)).filter(Item.expiry_date <= (now_dt + timedelta(days=7))).count()
                                              
    by_stock = dict(
        (s, c) for s, c in db.session.query(Item.origin_stock, func.count(Item.id)).group_by(Item.origin_stock).all()
    )
                                                                                 
    by_stock_status_rows = db.session.query(Item.origin_stock, Item.status, func.count(Item.id)).\
        filter(~Item.id.in_(due_ids)).\
        group_by(Item.origin_stock, Item.status).all()
    by_stock_status = {}
    for stock, status, count in by_stock_status_rows:
        if stock is None:
            continue
        if stock not in by_stock_status:
            by_stock_status[stock] = {"disponivel": 0, "locado": 0}
        if status in ("disponivel", "locado"):
            by_stock_status[stock][status] = count
                                     
    by_type = dict(
        (t, c) for t, c in db.session.query(Item.item_type, func.count(Item.id)).group_by(Item.item_type).all()
    )
                                                                   

                                             
    last_6 = []
    for i in range(5, -1, -1):
        start = (now_dt.replace(day=1) - timedelta(days=30 * i)).replace(day=1)
        end = (start + timedelta(days=32)).replace(day=1)
        cnt = Item.query.filter(Item.movement_date >= start, Item.movement_date < end).count()
        last_6.append({"label": start.strftime('%Y-%m'), "count": cnt})

    data = {
        "total": total,
        "disponiveis": disponiveis,
        "em_uso": em_uso,
        "vencendo": vencendo,
        "by_stock": by_stock,
        "by_stock_status": by_stock_status,
        "by_type": by_type,
        "maintenance": {"due": maintenance_due, "soon": maintenance_soon},
        "movement": last_6
    }
                                          
    prev_month_total = db.session.query(Item).filter(
        Item.entry_date < (now_dt - timedelta(days=30))
    ).count()
    data["mom"] = {"total": data["total"] - prev_month_total}
    return jsonify(data)


@dashboard_bp.route('/events')
@login_required
def dashboard_events():
    if current_user.role != "admin":
        return jsonify({"error": "forbidden"}), 403
    app_ref = current_app._get_current_object()

    def event_stream(app):
        import time, json
        while True:
            time.sleep(10)
            try:
                with app.app_context():
                    total = Item.query.count()
                    disponiveis = Item.query.filter(Item.status == "disponivel").count()
                    em_uso = Item.query.filter(Item.status.in_(["locado", "em_uso", "em uso"]))
                    em_uso = em_uso.count()
                    payload = {"total": total, "disponiveis": disponiveis, "em_uso": em_uso}
            except Exception:
                payload = {}
            yield f"data: {json.dumps(payload)}\n\n"

    return Response(event_stream(app_ref), mimetype='text/event-stream')


@dashboard_bp.route("/api/maintenance-lists")
@login_required
def maintenance_lists():
    if current_user.role != "admin":
        return jsonify({"error": "forbidden"}), 403
    now = datetime.utcnow()
    due_items = Item.query.filter(Item.name.ilike('%cama%')).filter(Item.movement_date <= (now - timedelta(days=60))).all()
    soon_items = Item.query.filter(Item.name.ilike('%cama%')).filter(
        Item.movement_date > (now - timedelta(days=60)), Item.movement_date <= (now - timedelta(days=50))
    ).all()

    def serialize(it: Item):
        return {
            "id": it.id,
            "name": it.name,
            "origin_stock": it.origin_stock,
            "movement_date": it.movement_date.strftime('%Y-%m-%d') if it.movement_date else None,
            "status": it.status,
        }

    return jsonify({
        "due": [serialize(i) for i in due_items],
        "soon": [serialize(i) for i in soon_items],
    })


@dashboard_bp.route("/export/excel")
@login_required
def export_excel():
    if current_user.role != "admin":
        return render_template("403.html"), 403

    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {"in_memory": True})
    worksheet = workbook.add_worksheet("Itens")
    headers = ["ID", "Nome", "Status", "Local", "Qtd", "Min", "Entrada", "Vencimento"]
    for col, h in enumerate(headers):
        worksheet.write(0, col, h)
    for row, item in enumerate(Item.query.order_by(Item.id).all(), start=1):
        worksheet.write_row(row, 0, [
            item.id, item.name, item.status, item.location or "", item.quantity, item.min_threshold,
            item.entry_date.strftime("%Y-%m-%d"), item.expiry_date.strftime("%Y-%m-%d") if item.expiry_date else ""
        ])
    workbook.close()
    output.seek(0)
    return send_file(output, as_attachment=True, download_name="ghoststock_itens.xlsx")


@dashboard_bp.route("/export/pdf")
@login_required
def export_pdf():
    if current_user.role != "admin":
        return render_template("403.html"), 403
    output = io.BytesIO()
    c = canvas.Canvas(output)
    c.setTitle("GhostStock Relatório")
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, 800, "Relatório GhostStock")
    c.setFont("Helvetica", 12)
    stats = {
        "Total": Item.query.count(),
        "Disponíveis": Item.query.filter_by(status="disponivel").count(),
        "Em uso": Item.query.filter(Item.status.in_(["locado", "em_uso", "em uso"]))
        .count(),
        "Vencendo (7d)": Item.query.filter(Item.expiry_date.isnot(None)).count(),
    }
    y = 770
    for k, v in stats.items():
        c.drawString(40, y, f"{k}: {v}")
        y -= 20
    c.showPage()
    c.save()
    output.seek(0)
    return send_file(output, as_attachment=True, download_name="ghoststock_relatorio.pdf")


