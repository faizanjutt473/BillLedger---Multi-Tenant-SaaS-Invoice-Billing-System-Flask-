from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user

from . import bp
from .forms import RegisterForm, LoginForm
from ..extensions import db
from ..models import Tenant, User


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        tenant = Tenant(name=form.company.data.strip(), email=email)
        user = User(tenant=tenant, name=form.name.data.strip(), email=email, role="admin")
        user.set_password(form.password.data)
        db.session.add_all([tenant, user])
        db.session.commit()
        login_user(user)
        flash("Welcome! Your company workspace is ready.", "ok")
        return redirect(url_for("main.home"))
    return render_template("auth/register.html", form=form)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            nxt = request.args.get("next", "")
            if nxt.startswith("/") and not nxt.startswith("//"):
                return redirect(nxt)
            return redirect(url_for("main.home"))
        flash("Wrong email or password.", "error")
    return render_template("auth/login.html", form=form)


@bp.route("/logout", methods=["POST"])
def logout():
    logout_user()
    flash("You have been logged out.", "ok")
    return redirect(url_for("auth.login"))