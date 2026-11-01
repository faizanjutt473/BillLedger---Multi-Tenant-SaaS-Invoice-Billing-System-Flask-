from io import BytesIO
from flask import render_template
from xhtml2pdf import pisa


def invoice_pdf(inv):
    """Invoice ka PDF bytes mein. Fail ho to None."""
    html = render_template("invoice_pdf.html", inv=inv, balance=inv.balance)
    buf = BytesIO()
    result = pisa.CreatePDF(html, dest=buf, encoding="utf-8")
    return None if result.err else buf.getvalue()