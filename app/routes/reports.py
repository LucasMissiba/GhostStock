from __future__ import annotations

from io import BytesIO
from flask import Blueprint, render_template, send_file, abort
from flask_login import login_required

from ..models import Item

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")


@reports_bp.route("/")
@login_required
def reports_home():
    return render_template("reports.html")


@reports_bp.route("/pdf/summary")
@login_required
def reports_pdf_summary():
    items_total = Item.query.count()
    disponiveis = Item.query.filter_by(status="disponivel").count()
    locados = Item.query.filter_by(status="locado").count()
    try:
                                                      
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas

        buff = BytesIO()
        c = canvas.Canvas(buff, pagesize=A4)
        text = c.beginText(40, 800)
        text.textLine("Relatório GhostStock - Resumo de Estoque")
        text.textLine("")
        text.textLine(f"Total de itens: {items_total}")
        text.textLine(f"Disponíveis: {disponiveis}")
        text.textLine(f"Locados: {locados}")
        c.drawText(text)
        c.showPage()
        c.save()
        buff.seek(0)
        return send_file(buff, mimetype="application/pdf", as_attachment=True, download_name="relatorio_resumo.pdf")
    except Exception:
                                                        
        html = f"""
        <html><body>
        <h1>Relatório GhostStock</h1>
        <p>Total: {items_total} | Disponíveis: {disponiveis} | Locados: {locados}</p>
        </body></html>
        """.encode("utf-8")
        return send_file(BytesIO(html), mimetype="text/html", as_attachment=True, download_name="relatorio_resumo.pdf")


