from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from flask import render_template, redirect, url_for, flash, request, make_response, abort
from flask_login import current_user, login_required

from . import bp
from .forms import ClientForm, InvoiceForm, PaymentForm, TeamForm, RecurringForm
from ..extensions import db
from ..models import Client, Invoice, InvoiceItem, Payment, User, RecurringPlan
from ..utils import roles_required
from ..pdf import invoice_pdf as build_pdf
from ..emailer import send_invoice_email
from ..jobs import run_daily

STAFF = ("admin", "accountant")


# ---------- helpers (sab tenant se filter hote hain) ----------
def tenant_client_or_404(client_id):
    return Client.query.filter_by(id=client_id, tenant_id=current_user.tenant_id).first_or_404()


def tenant_invoice_or_404(invoice_id):
    return Invoice.query.filter_by(id=invoice_id, tenant_id=current_user.tenant_id).first_or_404()


def next_invoice_number():
    n = 1001 + Invoice.query.filter_by(tenant_id=current_user.tenant_id).count()
    while Invoice.query.filter_by(tenant_id=current_user.tenant_id, number=f"INV-{n}").first():
        n += 1
    return f"INV-{n}"


def parse_items():
    items = []
    for d, q, p in zip(request.form.getlist("description"),
                       request.form.getlist("quantity"),
                       request.form.getlist("unit_price")):
        d = d.strip()
        if not d:
            continue
        try:
            qty, price = Decimal(q or "0"), Decimal(p or "0")
        except InvalidOperation:
            return None
        if qty <= 0 or price < 0:
            return None
        items.append(InvoiceItem(description=d[:255], quantity=qty, unit_price=price))
    return items


def balance_of(inv):
    return inv.balance.quantize(Decimal("0.01"))


def update_status(inv):
    if inv.status == "draft":
        return
    if balance_of(inv) <= 0:
        inv.status = "paid"
    elif inv.due_date < date.today():
        inv.status = "overdue"
    else:
        inv.status = "sent"


def sync_overdue():
    """Due date guzar chuki 'sent' invoices ko overdue kar do."""
    changed = False
    for inv in Invoice.query.filter_by(tenant_id=current_user.tenant_id, status="sent"):
        if inv.due_date < date.today():
            inv.status = "overdue"
            changed = True
    if changed:
        db.session.commit()


# ---------- home aur dashboard ----------
@bp.route("/")
def index():
    return render_template("index.html")


@bp.route("/dashboard")
@roles_required(*STAFF)
def dashboard():
    sync_overdue()
    invoices = (Invoice.query.filter_by(tenant_id=current_user.tenant_id)
                .order_by(Invoice.created_at.desc()).all())
    live = [i for i in invoices if i.status != "draft"]
    zero = Decimal("0")
    stats = [
        ("Billed", sum((i.total for i in live), zero)),
        ("Paid", sum((p.amount for i in live for p in i.payments), zero)),
        ("Awaiting payment", sum((balance_of(i) for i in live if i.status == "sent"), zero)),
        ("Overdue", sum((balance_of(i) for i in live if i.status == "overdue"), zero)),
    ]
    return render_template("dashboard.html", stats=stats, recent=invoices[:5], active="dashboard")


# ---------- clients ----------
@bp.route("/clients", methods=["GET", "POST"])
@roles_required(*STAFF)
def clients():
    form = ClientForm()
    if form.validate_on_submit():
        db.session.add(Client(
            tenant_id=current_user.tenant_id,
            name=form.name.data.strip(),
            email=(form.email.data or "").strip().lower() or None,
            phone=(form.phone.data or "").strip() or None,
            address=(form.address.data or "").strip() or None))
        db.session.commit()
        flash("Client added.", "ok")
        return redirect(url_for("main.clients"))
    rows = Client.query.filter_by(tenant_id=current_user.tenant_id).order_by(Client.name).all()
    for c in rows:
        c.outstanding = sum((i.balance for i in c.invoices if i.status in ("sent", "overdue")), Decimal("0"))
    return render_template("clients.html", form=form, clients=rows, active="clients")


@bp.route("/clients/<int:client_id>/edit", methods=["GET", "POST"])
@roles_required(*STAFF)
def client_edit(client_id):
    c = tenant_client_or_404(client_id)
    form = ClientForm(obj=c)
    if form.validate_on_submit():
        c.name = form.name.data.strip()
        c.email = (form.email.data or "").strip().lower() or None
        c.phone = (form.phone.data or "").strip() or None
        c.address = (form.address.data or "").strip() or None
        db.session.commit()
        flash("Client updated.", "ok")
        return redirect(url_for("main.clients"))
    return render_template("client_edit.html", form=form, client=c, active="clients")


@bp.route("/clients/<int:client_id>/delete", methods=["POST"])
@roles_required(*STAFF)
def client_delete(client_id):
    c = tenant_client_or_404(client_id)
    if c.invoices:
        flash("This client has invoices, so it cannot be deleted.", "error")
        return redirect(url_for("main.client_edit", client_id=c.id))
    db.session.delete(c)
    db.session.commit()
    flash("Client deleted.", "ok")
    return redirect(url_for("main.clients"))


# ---------- invoices ----------
@bp.route("/invoices")
@roles_required(*STAFF)
def invoices():
    sync_overdue()
    status = request.args.get("status", "all")
    q = request.args.get("q", "").strip()
    query = Invoice.query.filter_by(tenant_id=current_user.tenant_id).join(Client)
    if status in ("draft", "sent", "paid", "overdue"):
        query = query.filter(Invoice.status == status)
    if q:
        query = query.filter(db.or_(Invoice.number.ilike(f"%{q}%"), Client.name.ilike(f"%{q}%")))
    rows = query.order_by(Invoice.created_at.desc()).all()
    return render_template("invoices.html", invoices=rows, status=status, q=q, active="invoices")


@bp.route("/invoices/new", methods=["GET", "POST"])
@roles_required(*STAFF)
def invoice_new():
    form = InvoiceForm()
    form.client_id.choices = [(c.id, c.name) for c in
                              Client.query.filter_by(tenant_id=current_user.tenant_id).order_by(Client.name)]
    lines = [("", "1", "0")]
    if request.method == "GET":
        form.issue_date.data = date.today()
        form.due_date.data = date.today() + timedelta(days=14)
        form.tax_rate.data = current_user.tenant.default_tax_rate or 0
    else:
        lines = list(zip(request.form.getlist("description"),
                         request.form.getlist("quantity"),
                         request.form.getlist("unit_price"))) or lines
        if form.validate_on_submit():
            items = parse_items()
            if form.due_date.data < form.issue_date.data:
                flash("Due date cannot be before the issue date.", "error")
            elif not items:
                flash("Add at least one line with a description, quantity and price.", "error")
            else:
                inv = Invoice(
                    tenant_id=current_user.tenant_id, client_id=form.client_id.data,
                    number=next_invoice_number(), issue_date=form.issue_date.data,
                    due_date=form.due_date.data, tax_rate=form.tax_rate.data or 0,
                    notes=(form.notes.data or "").strip() or None, status="draft", items=items)
                db.session.add(inv)
                db.session.commit()
                flash(f"Invoice {inv.number} saved as draft.", "ok")
                return redirect(url_for("main.invoice_view", invoice_id=inv.id))
    return render_template("invoice_form.html", form=form, lines=lines, active="new")


@bp.route("/invoices/<int:invoice_id>")
@roles_required(*STAFF)
def invoice_view(invoice_id):
    inv = tenant_invoice_or_404(invoice_id)
    sync_overdue()
    pform = PaymentForm()
    pform.paid_on.data = date.today()
    pform.amount.data = max(balance_of(inv), Decimal("0"))
    return render_template("invoice_view.html", inv=inv, pform=pform,
                           balance=balance_of(inv), active="invoices")

@bp.route("/invoices/<int:invoice_id>/send", methods=["POST"])
@roles_required(*STAFF)
def invoice_send(invoice_id):
    inv = tenant_invoice_or_404(invoice_id)
    if inv.status == "draft":
        inv.status = "sent"
        update_status(inv)
        db.session.commit()
        flash(f"Invoice {inv.number} marked as sent.", "ok")
    return redirect(url_for("main.invoice_view", invoice_id=inv.id))


@bp.route("/invoices/<int:invoice_id>/delete", methods=["POST"])
@roles_required(*STAFF)
def invoice_delete(invoice_id):
    inv = tenant_invoice_or_404(invoice_id)
    if inv.status != "draft":
        flash("Only draft invoices can be deleted.", "error")
        return redirect(url_for("main.invoice_view", invoice_id=inv.id))
    db.session.delete(inv)
    db.session.commit()
    flash("Draft invoice deleted.", "ok")
    return redirect(url_for("main.invoices"))


@bp.route("/invoices/<int:invoice_id>/pay", methods=["POST"])
@roles_required(*STAFF)
def payment_add(invoice_id):
    inv = tenant_invoice_or_404(invoice_id)
    form = PaymentForm()
    if inv.status == "draft":
        flash("Mark the invoice as sent before recording a payment.", "error")
    elif not form.validate_on_submit():
        flash("Enter a valid payment amount and date.", "error")
    elif form.amount.data > balance_of(inv):
        flash("Amount is more than the balance due (Rs {:,.0f}).".format(balance_of(inv)), "error")
    else:
        db.session.add(Payment(
            tenant_id=current_user.tenant_id, invoice=inv, amount=form.amount.data,
            method=form.method.data, paid_on=form.paid_on.data,
            reference=(form.reference.data or "").strip() or None))
        db.session.commit()
        update_status(inv)
        db.session.commit()
        flash("Payment recorded.", "ok")
    return redirect(url_for("main.invoice_view", invoice_id=inv.id))


@bp.route("/payments/<int:payment_id>/delete", methods=["POST"])
@roles_required(*STAFF)
def payment_delete(payment_id):
    p = Payment.query.filter_by(id=payment_id, tenant_id=current_user.tenant_id).first_or_404()
    inv = p.invoice
    db.session.delete(p)
    db.session.commit()
    update_status(inv)
    db.session.commit()
    flash("Payment removed.", "ok")
    return redirect(url_for("main.invoice_view", invoice_id=inv.id))


@bp.route("/payments")
@roles_required(*STAFF)
def payments():
    rows = (Payment.query.filter_by(tenant_id=current_user.tenant_id)
            .order_by(Payment.paid_on.desc(), Payment.id.desc()).all())
    total = sum((p.amount for p in rows), Decimal("0"))
    return render_template("payments.html", payments=rows, total=total, active="payments")


# ---------- role ke hisab se home ----------
@bp.route("/home")
@login_required
def home():
    if current_user.role == "client":
        return redirect(url_for("main.portal"))
    return redirect(url_for("main.dashboard"))


# ---------- team (sirf admin) ----------
@bp.route("/team", methods=["GET", "POST"])
@roles_required("admin")
def team():
    form = TeamForm()
    form.client_id.choices = [(0, "Not a client")] + [
        (c.id, c.name) for c in Client.query.filter_by(tenant_id=current_user.tenant_id).order_by(Client.name)]
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        if User.query.filter_by(email=email).first():
            flash("This email is already registered.", "error")
        elif form.role.data == "client" and not form.client_id.data:
            flash("Choose which client this user belongs to.", "error")
        else:
            u = User(tenant_id=current_user.tenant_id, name=form.name.data.strip(), email=email,
                     role=form.role.data,
                     client_id=form.client_id.data if form.role.data == "client" else None)
            u.set_password(form.password.data)
            db.session.add(u)
            db.session.commit()
            flash(f"{u.name} added. Share the temporary password with them.", "ok")
            return redirect(url_for("main.team"))
    members = User.query.filter_by(tenant_id=current_user.tenant_id).order_by(User.created_at).all()
    names = {c.id: c.name for c in Client.query.filter_by(tenant_id=current_user.tenant_id)}
    return render_template("team.html", form=form, members=members, names=names, active="team")


@bp.route("/team/<int:user_id>/role", methods=["POST"])
@roles_required("admin")
def team_role(user_id):
    u = User.query.filter_by(id=user_id, tenant_id=current_user.tenant_id).first_or_404()
    role = request.form.get("role")
    if u.id == current_user.id:
        flash("You cannot change your own role.", "error")
    elif u.role == "client" or role not in ("admin", "accountant"):
        flash("This role cannot be changed here.", "error")
    else:
        u.role = role
        db.session.commit()
        flash(f"{u.name} is now {role}.", "ok")
    return redirect(url_for("main.team"))


@bp.route("/team/<int:user_id>/remove", methods=["POST"])
@roles_required("admin")
def team_remove(user_id):
    u = User.query.filter_by(id=user_id, tenant_id=current_user.tenant_id).first_or_404()
    if u.id == current_user.id:
        flash("You cannot remove your own account.", "error")
    else:
        db.session.delete(u)
        db.session.commit()
        flash("Team member removed.", "ok")
    return redirect(url_for("main.team"))


# ---------- client portal (sirf client role) ----------
def portal_query():
    return Invoice.query.filter(Invoice.tenant_id == current_user.tenant_id,
                                Invoice.client_id == current_user.client_id,
                                Invoice.status != "draft")


@bp.route("/portal")
@roles_required("client")
def portal():
    sync_overdue()
    rows = portal_query().order_by(Invoice.created_at.desc()).all()
    return render_template("portal.html", invoices=rows, active="portal")


@bp.route("/portal/invoices/<int:invoice_id>")
@roles_required("client")
def portal_invoice(invoice_id):
    inv = portal_query().filter(Invoice.id == invoice_id).first_or_404()
    return render_template("portal_invoice.html", inv=inv, balance=balance_of(inv), active="portal")

# ---------- PDF aur email ----------
def pdf_response(inv):
    data = build_pdf(inv)
    if data is None:
        abort(500)
    resp = make_response(data)
    resp.headers["Content-Type"] = "application/pdf"
    resp.headers["Content-Disposition"] = f'attachment; filename="{inv.number}.pdf"'
    return resp


@bp.route("/invoices/<int:invoice_id>/pdf")
@roles_required(*STAFF)
def invoice_pdf_download(invoice_id):
    return pdf_response(tenant_invoice_or_404(invoice_id))


@bp.route("/invoices/<int:invoice_id>/email", methods=["POST"])
@roles_required(*STAFF)
def invoice_email(invoice_id):
    inv = tenant_invoice_or_404(invoice_id)
    state, message = send_invoice_email(inv)
    if state == "sent" and inv.status == "draft":
        inv.status = "sent"
        update_status(inv)
        db.session.commit()
    flash(message, "error" if state == "error" else "ok")
    return redirect(url_for("main.invoice_view", invoice_id=inv.id))


@bp.route("/portal/invoices/<int:invoice_id>/pdf")
@roles_required("client")
def portal_invoice_pdf(invoice_id):
    return pdf_response(portal_query().filter(Invoice.id == invoice_id).first_or_404())

# ---------- recurring invoices ----------
@bp.route("/recurring", methods=["GET", "POST"])
@roles_required(*STAFF)
def recurring():
    form = RecurringForm()
    form.client_id.choices = [(c.id, c.name) for c in
                              Client.query.filter_by(tenant_id=current_user.tenant_id).order_by(Client.name)]
    if request.method == "GET":
        form.next_run.data = date.today()
    if form.validate_on_submit():
        db.session.add(RecurringPlan(
            tenant_id=current_user.tenant_id, client_id=form.client_id.data,
            description=form.description.data.strip(), amount=form.amount.data,
            frequency=form.frequency.data, next_run=form.next_run.data))
        db.session.commit()
        flash("Recurring plan created.", "ok")
        return redirect(url_for("main.recurring"))
    plans = (RecurringPlan.query.filter_by(tenant_id=current_user.tenant_id)
             .order_by(RecurringPlan.next_run).all())
    return render_template("recurring.html", form=form, plans=plans, active="recurring")


@bp.route("/recurring/<int:plan_id>/toggle", methods=["POST"])
@roles_required(*STAFF)
def recurring_toggle(plan_id):
    p = RecurringPlan.query.filter_by(id=plan_id, tenant_id=current_user.tenant_id).first_or_404()
    p.active = not p.active
    db.session.commit()
    flash("Plan resumed." if p.active else "Plan paused.", "ok")
    return redirect(url_for("main.recurring"))


@bp.route("/recurring/<int:plan_id>/delete", methods=["POST"])
@roles_required(*STAFF)
def recurring_delete(plan_id):
    p = RecurringPlan.query.filter_by(id=plan_id, tenant_id=current_user.tenant_id).first_or_404()
    db.session.delete(p)
    db.session.commit()
    flash("Plan deleted.", "ok")
    return redirect(url_for("main.recurring"))


@bp.route("/recurring/run", methods=["POST"])
@roles_required(*STAFF)
def recurring_run():
    r = run_daily(current_user.tenant_id)   # sirf apni company ke liye
    flash(f"{r['made']} recurring invoice(s) created, {r['sent']} reminder(s) sent, "
          f"{r['test']} reminder(s) prepared in test mode.", "ok")
    return redirect(url_for("main.recurring"))