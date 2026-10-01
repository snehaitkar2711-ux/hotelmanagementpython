"""Flask web interface for the hotel management system."""

import hmac
import os
import secrets
import sqlite3
from functools import wraps
from typing import Callable, TypeVar

from flask import (
    Flask,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from customer import add_customer, list_customers
from database import authenticate, connect, create_user, initialize_database, list_users


app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("HOTEL_SECRET_KEY") or secrets.token_hex(32),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)
initialize_database()

F = TypeVar("F", bound=Callable)


def csrf_token() -> str:
    token = session.get("_csrf_token")
    if token is None:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token


app.jinja_env.globals["csrf_token"] = csrf_token


@app.before_request
def protect_forms() -> None:
    if request.method == "POST":
        submitted = request.form.get("_csrf_token", "")
        expected = session.get("_csrf_token", "")
        if not expected or not hmac.compare_digest(submitted, expected):
            abort(400, description="The form expired. Please reload and try again.")


@app.before_request
def load_logged_in_user() -> None:
    user_id = session.get("user_id")
    g.user = None
    if user_id is not None:
        with connect() as connection:
            g.user = connection.execute(
                "SELECT id, username, role FROM users WHERE id = ?", (user_id,)
            ).fetchone()
        if g.user is None:
            session.clear()


def login_required(view: F) -> F:
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped  # type: ignore[return-value]


def role_required(*roles: str):
    def decorate(view: F) -> F:
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if g.user["role"] not in roles:
                abort(403)
            return view(*args, **kwargs)

        return wrapped  # type: ignore[return-value]

    return decorate


def platform_admin_exists() -> bool:
    with connect() as connection:
        return (
            connection.execute(
                "SELECT 1 FROM users WHERE role = 'platformadmin' LIMIT 1"
            ).fetchone()
            is not None
        )


@app.route("/")
def index():
    if g.user is not None:
        return redirect(url_for("dashboard"))
    if not platform_admin_exists():
        return redirect(url_for("setup"))
    return redirect(url_for("login"))


@app.route("/setup", methods=["GET", "POST"])
def setup():
    if platform_admin_exists():
        return redirect(url_for("dashboard" if g.user else "login"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        try:
            create_user(username, password, "platformadmin")
        except ValueError as error:
            flash(str(error), "error")
        except sqlite3.IntegrityError:
            flash("That username is already in use.", "error")
        else:
            flash("Platform admin account created. You can now log in.", "success")
            return redirect(url_for("login"))
    return render_template("setup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if not platform_admin_exists():
        return redirect(url_for("setup"))
    if g.user is not None:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        user = authenticate(
            request.form.get("username", ""), request.form.get("password", "")
        )
        if user is None:
            flash("Username or password was not correct.", "error")
        else:
            session.clear()
            session["user_id"] = user["id"]
            flash(f"Welcome back, {user['username']}.", "success")
            return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.post("/logout")
@login_required
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    role = g.user["role"]
    users = []
    customers = []
    all_customers = []
    customer_count = 0
    if role == "platformadmin":
        users = list_users()
        all_customers = list_customers()
        customer_count = len(all_customers)
    elif role == "manager":
        users = list_users("waiter", created_by=g.user["id"])
        with connect() as connection:
            customer_count = connection.execute(
                """
                SELECT COUNT(*) FROM customers
                JOIN users AS waiter ON waiter.id = customers.created_by
                WHERE waiter.created_by = ?
                """,
                (g.user["id"],),
            ).fetchone()[0]
    else:
        customers = list_customers(g.user["id"])
        customer_count = len(customers)
    return render_template(
        "dashboard.html",
        users=users,
        customers=customers,
        all_customers=all_customers,
        customer_count=customer_count,
    )


@app.post("/users")
@role_required("platformadmin", "manager")
def add_user():
    role = "manager" if g.user["role"] == "platformadmin" else "waiter"
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    try:
        create_user(username, password, role, g.user["id"])
    except ValueError as error:
        flash(str(error), "error")
    except sqlite3.IntegrityError:
        flash("That username is already in use.", "error")
    else:
        flash(f"{role.title()} account '{username}' created.", "success")
    return redirect(url_for("dashboard"))


@app.post("/customers")
@role_required("waiter")
def add_customer_record():
    try:
        add_customer(
            g.user["id"],
            request.form.get("name", ""),
            request.form.get("phone", ""),
            request.form.get("email", ""),
            request.form.get("notes", ""),
        )
    except ValueError as error:
        flash(str(error), "error")
    else:
        flash("Customer saved successfully.", "success")
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
