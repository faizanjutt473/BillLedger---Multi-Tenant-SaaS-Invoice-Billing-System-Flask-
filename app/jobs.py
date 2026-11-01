import calendar
from datetime import date, timedelta

import click

from .extensions import db
from .models import Invoice, InvoiceItem, RecurringPlan
from .emailer import send_invoice_email, send_reminder_email


def add_period(d, frequency):
    if frequency == "yearly":
        try:
            return d.replace(year=d.year + 1)
        except ValueError:  # 29 Feb
            return d.replace(year=d.year + 1, day=28)
    year = d.year + (d.month // 12)
    month = d.month % 12 + 1
    return date(year, month, min(d.day, calendar.monthrange(year, month)[1]))


def next_number(tenant_id):
    n = 1001 + Invoice.query.filter_by(tenant_id=tenant_id).count()
    while Invoice.query.filter_by(tenant_id=tenant_id, number=f"INV-{n}").first():
        n += 1
    return f"INV-{n}"


def run_recurring(today, tenant_id=None):
    q = RecurringPlan.query.filter(RecurringPlan.active.is_(True), RecurringPlan.next_run <= today)
    if tenant_id:
        q = q.filter(RecurringPlan.tenant_id == tenant_id)
    made = 0
    for plan in q.all():
        inv = Invoice(
            tenant_id=plan.tenant_id, client_id=plan.client_id, number=next_number(plan.tenant_id),
            issue_date=today, due_date=today + timedelta(days=14),
            tax_rate=plan.client.tenant.default_tax_rate or 0, status="sent",
            notes="Recurring invoice",
            items=[InvoiceItem(description=plan.description, quantity=1, unit_price=plan.amount)])
        db.session.add(inv)
        while plan.next_run <= today:           # chhooti hui dates ek hi invoice mein cover
            plan.next_run = add_period(plan.next_run, plan.frequency)
        db.session.commit()
        send_invoice_email(inv)
        made += 1
    return made


def run_reminders(today, tenant_id=None):
    q = Invoice.query.filter(Invoice.status.in_(["sent", "overdue"]))
    if tenant_id:
        q = q.filter(Invoice.tenant_id == tenant_id)
    sent = test = 0
    for inv in q.all():
        if inv.status == "sent" and inv.due_date < today:
            inv.status = "overdue"
        if inv.balance <= 0:
            continue
        days_left = (inv.due_date - today).days
        due_now = days_left in (3, 0) or (days_left < 0 and (-days_left) % 7 == 0)
        if not due_now or inv.last_reminded == today:
            continue
        state, _ = send_reminder_email(inv, days_left)
        if state == "sent":
            inv.last_reminded = today
            sent += 1
        elif state == "test":
            test += 1
    db.session.commit()
    return sent, test


def run_daily(tenant_id=None):
    today = date.today()
    made = run_recurring(today, tenant_id)
    sent, test = run_reminders(today, tenant_id)
    return {"made": made, "sent": sent, "test": test}


def register_commands(app):
    @app.cli.command("run-daily")
    def run_daily_cmd():
        """Recurring invoices banao aur payment reminders bhejo."""
        r = run_daily()
        click.echo(f"Recurring invoices created: {r['made']} | "
                   f"reminders sent: {r['sent']} | reminders prepared in test mode: {r['test']}")