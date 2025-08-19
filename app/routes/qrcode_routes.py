from __future__ import annotations

import io
import os
from PIL import Image
from flask import Blueprint, current_app, render_template, send_file, url_for, request, redirect, flash
from flask_login import login_required, current_user
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
import qrcode

from ..models import Item, ItemMovement
from .. import db

qrcode_bp = Blueprint("qrcode", __name__, url_prefix="/qr")


def _signer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="ghoststock-qr")


@qrcode_bp.route("/generate/<int:item_id>")
@login_required
def generate_qr(item_id: int):
    if current_user.role != "admin":
        flash("Apenas administradores podem gerar QR Code.", "danger")
        return redirect(url_for("items.list_items"))
    item = Item.query.get_or_404(item_id)
    token = _signer().dumps({"item_id": item.id})
    item_url = url_for("qrcode.view_item_signed", item_id=item.id, token=token, _external=True)

                              
    qr_img = qrcode.make(item_url)
    qr_img = qr_img.convert("RGB")

    logo_path = os.path.join(os.getcwd(), "app", "static", "img", "logo.png")
    if os.path.exists(logo_path):
        try:
            logo = Image.open(logo_path)
            basewidth = 80
            wpercent = basewidth / float(logo.size[0])
            hsize = int((float(logo.size[1]) * float(wpercent)))
            logo = logo.resize((basewidth, hsize))
            pos = ((qr_img.size[0] - logo.size[0]) // 2, (qr_img.size[1] - logo.size[1]) // 2)
            qr_img.paste(logo, pos)
        except Exception:
                                                       
            pass

    os.makedirs(current_app.config["QR_FOLDER"], exist_ok=True)
    file_path = os.path.join(current_app.config["QR_FOLDER"], f"item_{item.id}.png")
    qr_img.save(file_path)

    return send_file(file_path, as_attachment=True, download_name=f"ghoststock_item_{item.id}.png")


@qrcode_bp.route("/pdf/<int:item_id>")
@login_required
def qr_pdf(item_id: int):
                                                                     
    png_path = os.path.join(current_app.config["QR_FOLDER"], f"item_{item_id}.png")
    if not os.path.exists(png_path):
        return redirect(url_for("qrcode.generate_qr", item_id=item_id))
    image = Image.open(png_path).convert("RGB")
    output = io.BytesIO()
    image.save(output, format="PDF")
    output.seek(0)
    return send_file(output, as_attachment=True, download_name=f"ghoststock_item_{item_id}.pdf")


@qrcode_bp.route("/scan")
@login_required
def scan_page():
    return render_template("scan.html")


@qrcode_bp.route("/item/<int:item_id>")
@login_required
def view_item_signed(item_id: int):
                                         
    token = request.args.get("token")
    if not token:
        flash("QR Code inválido.", "danger")
        return redirect(url_for("auth.login"))
    try:
        data = _signer().loads(token, max_age=current_app.config.get("QR_TOKEN_MAX_AGE", 90 * 24 * 3600))
        if data.get("item_id") != item_id:
            raise BadSignature("mismatch")
    except SignatureExpired:
        flash("QR Code expirado.", "danger")
        return redirect(url_for("auth.login"))
    except BadSignature:
        flash("QR Code inválido.", "danger")
        return redirect(url_for("auth.login"))

    item = Item.query.get_or_404(item_id)
                                                       
    if current_user.role != "admin" and item.owner_id != current_user.id:
        flash("Sem permissão para visualizar este item.", "danger")
        return redirect(url_for("items.list_items"))
                    
    mv = ItemMovement(item_id=item.id, user_id=current_user.id if current_user.is_authenticated else None, action="scan")
    db.session.add(mv)
    db.session.commit()
    return render_template("item_view.html", item=item)


