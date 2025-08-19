from __future__ import annotations

from datetime import datetime, timedelta
from flask import current_app
from apscheduler.schedulers.background import BackgroundScheduler

from .models import Item, User
from .email_utils import send_email


def schedule_jobs(app):
    interval = app.config.get("SCHEDULER_INTERVAL_MINUTES", 60)
    scheduler = BackgroundScheduler(daemon=True)

    def job():
        with app.app_context():
            _check_and_send_alerts()

    scheduler.add_job(job, "interval", minutes=interval, id="alerts_job", replace_existing=True)
    scheduler.start()


def _check_and_send_alerts() -> None:
                   
    low_stock_items = Item.query.filter(Item.quantity <= Item.min_threshold).all()
    expiring_items = Item.query.filter(Item.expiry_date.isnot(None)).filter(
        Item.expiry_date <= (datetime.utcnow() + timedelta(days=current_app.config.get("EXPIRY_ALERT_DAYS", 7)))
    ).all()

    if not low_stock_items and not expiring_items:
        return

    admins = User.query.filter_by(role="admin").all()
    recipients = [a.email for a in admins]
    lines = []
    if low_stock_items:
        lines.append("Itens com baixo estoque:")
        for it in low_stock_items:
            lines.append(f"- {it.name} (Qtd: {it.quantity} | Min: {it.min_threshold})")
    if expiring_items:
        lines.append("\nItens vencendo:")
        for it in expiring_items:
            dt = it.expiry_date.strftime("%Y-%m-%d") if it.expiry_date else "-"
            lines.append(f"- {it.name} (Vencimento: {dt})")
    body = "\n".join(lines)
    send_email("[GhostStock] Alertas de estoque", recipients, body)










