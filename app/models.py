from __future__ import annotations

from datetime import datetime
from typing import Optional
from flask_login import UserMixin
from . import db, bcrypt


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), default="user", index=True)                     
    failed_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    theme = db.Column(db.String(20), default="system")                         

    items = db.relationship("Item", backref="owner", lazy=True)

    def set_password(self, password: str) -> None:
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password: str) -> bool:
        return bcrypt.check_password_hash(self.password_hash, password)


class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
                                        
    code = db.Column(db.String(32), unique=True, nullable=True)
                                                                             
    item_type = db.Column(db.String(40), nullable=True, index=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
                                       
    origin_stock = db.Column(db.String(2), nullable=True)
                                 
    status = db.Column(db.String(20), default="disponivel", index=True)
                                         
    location = db.Column(db.String(120), nullable=True, index=True)
                                 
    patient_name = db.Column(db.String(120), nullable=True)
                          
    movement_date = db.Column(db.DateTime, default=datetime.utcnow, index=True)
                               
    last_maintenance_date = db.Column(db.DateTime, nullable=True, index=True)
                               
    lat = db.Column(db.Float, nullable=True)
    lng = db.Column(db.Float, nullable=True)
    photo_path = db.Column(db.String(255), nullable=True)
    entry_date = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    expiry_date = db.Column(db.DateTime, nullable=True, index=True)
    quantity = db.Column(db.Integer, default=1)
    min_threshold = db.Column(db.Integer, default=1)

    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    movements = db.relationship("ItemMovement", backref="item", lazy=True)

    def to_dict_summary(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "item_type": self.item_type,
            "origin_stock": self.origin_stock,
            "location": self.location,
            "lat": self.lat,
            "lng": self.lng,
            "quantity": self.quantity,
            "min_threshold": self.min_threshold,
        }

    @property
    def is_cama(self) -> bool:
        t = (self.item_type or '').lower()
        return 'cama' in t or (self.name or '').upper().startswith('CAM')

    @property
    def maintenance_due(self) -> bool:
        if not self.last_maintenance_date:
            return False
        from datetime import datetime, timedelta
        return datetime.utcnow() >= self.last_maintenance_date + timedelta(days=60)

    @property
    def maintenance_due_date(self):
        if not self.last_maintenance_date:
            return None
        from datetime import timedelta
        return self.last_maintenance_date + timedelta(days=60)

    @property
    def maintenance_overdue_days(self) -> Optional[int]:
        if not self.is_cama or not self.last_maintenance_date:
            return None
        from datetime import datetime
        due_date = self.maintenance_due_date
        if not due_date:
            return None
        delta_days = (datetime.utcnow() - due_date).days
        return delta_days if delta_days > 0 else 0

    @property
    def days_until_maintenance_due(self) -> Optional[int]:
        if not self.last_maintenance_date:
            return None
        from datetime import datetime
        due_date = self.maintenance_due_date
        if not due_date:
            return None
        return (due_date - datetime.utcnow()).days

    @property
    def maintenance_soon(self) -> bool:
        if not self.last_maintenance_date:
            return False
        from datetime import datetime, timedelta
        due_date = self.last_maintenance_date + timedelta(days=60)
        remaining = (due_date - datetime.utcnow()).days
        return 0 < remaining <= 15


class ItemMovement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey("item.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    action = db.Column(db.String(50), nullable=False)                                               
    from_value = db.Column(db.String(120), nullable=True)
    to_value = db.Column(db.String(120), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "from": self.from_value,
            "to": self.to_value,
            "timestamp": self.timestamp.isoformat()
        }


class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    ip = db.Column(db.String(64), nullable=True)
    action = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


