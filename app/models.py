from datetime import datetime, date
from decimal import Decimal

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from .extensions import db


class Tenant(db.Model):
    """Ek company / workspace."""
    __tablename__ = "tenants"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120))
    address = db.Column(db.String(255))
    currency = db.Column(db.String(8), default="PKR")
    default_tax_rate = db.Column(db.Numeric(5, 2), default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    users = db.relationship("User", backref="tenant", lazy=True)
    clients = db.relationship("Client", backref="tenant", lazy=True)
    invoices = db.relationship("Invoice", backref="tenant", lazy=True)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id"), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="accountant")  # admin / accountant / client
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"))  # sirf client role ke liye
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Client(db.Model):
    """Company ke customers jinhein invoice bhejte hain."""
    __tablename__ = "clients"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id"), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(40))
    address = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    invoices = db.relationship("Invoice", backref="client", lazy=True)


class Invoice(db.Model):
    __tablename__ = "invoices"
    __table_args__ = (db.UniqueConstraint("tenant_id", "number", name="uq_invoice_number_per_tenant"),)

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id"), nullable=False, index=True)
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=False)
    number = db.Column(db.String(30), nullable=False)          # INV-1001
    issue_date = db.Column(db.Date, default=date.today)
    due_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default="draft")         # draft / sent / paid / overdue
    tax_rate = db.Column(db.Numeric(5, 2), default=0)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_reminded = db.Column(db.Date)

    items = db.relationship("InvoiceItem", backref="invoice", cascade="all, delete-orphan", lazy=True)
    payments = db.relationship("Payment", backref="invoice", cascade="all, delete-orphan", lazy=True)

    @property
    def subtotal(self):
        return sum((i.amount for i in self.items), Decimal("0"))

    @property
    def tax_amount(self):
        return self.subtotal * Decimal(self.tax_rate or 0) / Decimal("100")

    @property
    def total(self):
        return self.subtotal + self.tax_amount

    @property
    def paid_amount(self):
        return sum((p.amount for p in self.payments), Decimal("0"))

    @property
    def balance(self):
        return self.total - self.paid_amount


class InvoiceItem(db.Model):
    __tablename__ = "invoice_items"

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id"), nullable=False, index=True)
    description = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.Numeric(10, 2), default=1)
    unit_price = db.Column(db.Numeric(12, 2), default=0)

    @property
    def amount(self):
        return Decimal(self.quantity or 0) * Decimal(self.unit_price or 0)


class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id"), nullable=False, index=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id"), nullable=False, index=True)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    method = db.Column(db.String(30), default="bank_transfer")  # stripe / paymob / bank_transfer
    paid_on = db.Column(db.Date, default=date.today)
    reference = db.Column(db.String(120))


class RecurringPlan(db.Model):
    __tablename__ = "recurring_plans"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id"), nullable=False, index=True)
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    frequency = db.Column(db.String(20), default="monthly")    # monthly / yearly
    next_run = db.Column(db.Date, nullable=False)
    active = db.Column(db.Boolean, default=True)

    client = db.relationship("Client")