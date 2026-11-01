from flask import current_app
from flask_mail import Message

from .extensions import mail
from .pdf import invoice_pdf


def send_invoice_email(inv):
    """Returns (state, message). state: 'sent' / 'test' / 'error'."""
    if not inv.client.email:
        return "error", "This client has no email address. Add one on the Clients page."
    pdf = invoice_pdf(inv)
    if pdf is None:
        return "error", "Could not build the PDF."

    msg = Message(subject=f"Invoice {inv.number} from {inv.tenant.name}", recipients=[inv.client.email])
    msg.body = (f"Hello {inv.client.name},\n\n"
                f"Please find invoice {inv.number} attached.\n"
                f"Amount due: Rs {inv.balance:,.0f}\nDue date: {inv.due_date}\n\n"
                f"Thank you,\n{inv.tenant.name}")
    msg.attach(f"{inv.number}.pdf", "application/pdf", pdf)

    if current_app.config.get("MAIL_SUPPRESS_SEND"):
        return "test", "Test mode: email is not configured, so nothing was actually sent."
    try:
        mail.send(msg)
    except Exception:
        current_app.logger.exception("Invoice email failed")
        return "error", "Email could not be sent. Check the mail settings in .env."
    return "sent", f"Invoice emailed to {inv.client.email}."

def send_reminder_email(inv, days_left):
    """Returns (state, message). state: 'sent' / 'test' / 'skip' / 'error'."""
    if not inv.client.email:
        return "skip", "Client has no email address."
    if days_left > 0:
        when = f"is due in {days_left} days"
    elif days_left == 0:
        when = "is due today"
    else:
        when = f"is {-days_left} days overdue"
    msg = Message(subject=f"Payment reminder: invoice {inv.number}", recipients=[inv.client.email])
    msg.body = (f"Hello {inv.client.name},\n\n"
                f"This is a friendly reminder that invoice {inv.number} {when}.\n"
                f"Balance due: Rs {inv.balance:,.0f}\nDue date: {inv.due_date}\n\n"
                f"If you have already paid, please ignore this message.\n\n{inv.tenant.name}")
    pdf = invoice_pdf(inv)
    if pdf:
        msg.attach(f"{inv.number}.pdf", "application/pdf", pdf)
    if current_app.config.get("MAIL_SUPPRESS_SEND"):
        return "test", "Test mode: reminder not actually sent."
    try:
        mail.send(msg)
    except Exception:
        current_app.logger.exception("Reminder email failed")
        return "error", "Reminder could not be sent."
    return "sent", "Reminder sent."