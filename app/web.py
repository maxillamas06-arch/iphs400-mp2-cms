"""Shared web plumbing: templates, a database connection per request, the session."""
from __future__ import annotations

import secrets
import sqlite3
from collections.abc import Iterator

from fastapi import Depends, Request
from fastapi.templating import Jinja2Templates

from app import accounts, db, policy, settings
from app.accounts import User
from app.dates import monterrey_time

templates = Jinja2Templates(directory=str(settings.TEMPLATES))
templates.env.filters["monterrey_time"] = monterrey_time


class LoginRequired(Exception):
    """Raised for an anonymous request to an admin route; answered with /login."""


class CsrfRejected(Exception):
    """Raised for a POST without this session's CSRF token; answered with 403."""


class Forbidden(Exception):
    """Raised when a signed-in user may not do this; answered with the refusal page,
    which gives the reason."""

    def __init__(self, user: User,
                 reason: str = "Esta pantalla es solo para el líder del club de aficionados.",
                 ) -> None:
        self.user = user
        self.reason = reason


class NotFound(Exception):
    """Raised for an unknown id; answered with a Spanish 404 page."""

    def __init__(self, user: User) -> None:
        self.user = user


def csrf_token(request: Request) -> str:
    """The session's CSRF token, created on first use."""
    token = request.session.get("csrf")
    if not token:
        token = request.session["csrf"] = secrets.token_urlsafe(32)
    return token


templates.env.globals["csrf_token"] = csrf_token
# Templates ask Policy only to hide buttons; every route checks again.
templates.env.globals["may_publish"] = policy.may_publish
templates.env.globals["may_submit_or_withdraw"] = policy.may_submit_or_withdraw
templates.env.globals["may_change_post"] = policy.may_change_post
templates.env.globals["may_propose_edit"] = policy.may_propose_edit


async def require_csrf(request: Request) -> None:
    """Refuse any POST whose form does not carry this session's CSRF token."""
    if request.method != "POST":
        return
    sent = (await request.form()).get("csrf_token")
    expected = request.session.get("csrf")
    if not (isinstance(sent, str) and expected and secrets.compare_digest(sent, expected)):
        raise CsrfRejected


def get_db(request: Request) -> Iterator[sqlite3.Connection]:
    conn = db.connect(request.app.state.database_path)
    try:
        yield conn
    finally:
        conn.close()


def signed_in_user(request: Request, conn: sqlite3.Connection = Depends(get_db)) -> User:
    """The user behind this session, reloaded on every request, if this route
    is one they may use."""
    user = accounts.active_user(conn, request.session.get("user_id"))
    if user is None:
        raise LoginRequired
    route = request.scope.get("route")
    if not policy.may_use_route(user, getattr(route, "name", None)):
        raise Forbidden(user)
    return user


def flash(request: Request, message: str) -> None:
    """Show this message on the next page rendered for this session, once."""
    request.session["flash"] = message


def render(request: Request, name: str, user: User | None = None,
           status_code: int = 200, **context):
    return templates.TemplateResponse(
        request, name, {"site_title": settings.SITE_TITLE, "user": user,
                        "message": request.session.pop("flash", None), **context},
        status_code=status_code,
    )
