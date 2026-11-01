from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, DecimalField, DateField, PasswordField
from wtforms.validators import DataRequired, Email, Optional, Length, NumberRange


class ClientForm(FlaskForm):
    name = StringField("Client name", validators=[DataRequired(), Length(max=120)])
    email = StringField("Billing email", validators=[Optional(), Email(), Length(max=120)])
    phone = StringField("Phone", validators=[Optional(), Length(max=40)])
    address = StringField("Address", validators=[Optional(), Length(max=255)])


class InvoiceForm(FlaskForm):
    client_id = SelectField("Client", coerce=int, validators=[DataRequired()])
    tax_rate = DecimalField("Tax %", places=2, validators=[Optional(), NumberRange(min=0, max=100)])
    issue_date = DateField("Issue date", validators=[DataRequired()])
    due_date = DateField("Due date", validators=[DataRequired()])
    notes = TextAreaField("Notes", validators=[Optional(), Length(max=1000)])


class PaymentForm(FlaskForm):
    amount = DecimalField("Amount", places=2, validators=[DataRequired(), NumberRange(min=0.01)])
    method = SelectField("Method", choices=[("bank_transfer", "Bank transfer"), ("cash", "Cash"),
                                            ("stripe", "Stripe"), ("paymob", "Paymob")])
    paid_on = DateField("Date", validators=[DataRequired()])
    reference = StringField("Reference", validators=[Optional(), Length(max=120)])    


class TeamForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=120)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    role = SelectField("Role", choices=[("accountant", "Accountant"), ("admin", "Admin"), ("client", "Client")])
    client_id = SelectField("Linked client (only for the Client role)", coerce=int)
    password = PasswordField("Temporary password", validators=[DataRequired(), Length(min=8, message="Use at least 8 characters.")])   

class RecurringForm(FlaskForm):
    client_id = SelectField("Client", coerce=int, validators=[DataRequired()])
    description = StringField("Description", validators=[DataRequired(), Length(max=255)])
    amount = DecimalField("Amount", places=2, validators=[DataRequired(), NumberRange(min=0.01)])
    frequency = SelectField("Repeats", choices=[("monthly", "Monthly"), ("yearly", "Yearly")])
    next_run = DateField("First invoice date", validators=[DataRequired()])     