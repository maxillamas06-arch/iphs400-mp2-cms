"""Shared web plumbing: templates, a database connection per request, the session."""
from __future__ import annotations

import secrets
import sqlite3
from collections.abc import Iterator

from fastapi import Depends, Request
from fastapi.templating import Jinja2Templates

from app import accounts, content, db, policy, settings
from app.accounts import User
from app.content import Page, PageFields, Post, PostFields
from app.dates import monterrey_time

templates = Jinja2Templates(directory=str(settings.TEMPLATES))
templates.env.filters["monterrey_time"] = monterrey_time
templates.env.tests["page"] = lambda item: isinstance(item, content.Page)  # {% if item is page %}


class LoginRequired(Exception):
    """Raised for an anonymous request to an admin route; answered with /login."""


class NicknameRequired(Exception):
    """Raised for a signed-in user who has not chosen a nickname yet; answered with
    the first-login nickname screen."""


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
    """Raised for an unknown id; answered with a Spanish 404 page naming what was
    not found."""

    def __init__(self, user: User, missing: str = "esa publicación") -> None:
        self.user = user
        self.missing = missing


def csrf_token(request: Request) -> str:
    """The session's CSRF token, created on first use."""
    token = request.session.get("csrf")
    if not token:
        token = request.session["csrf"] = secrets.token_urlsafe(32)
    return token


templates.env.globals["csrf_token"] = csrf_token
templates.env.globals["role_names"] = accounts.ROLE_NAMES
# Templates ask Policy only to hide buttons; every route checks again.
templates.env.globals["may_manage_accounts"] = policy.may_manage_accounts
templates.env.globals["may_publish"] = policy.may_publish
templates.env.globals["may_submit_or_withdraw"] = policy.may_submit_or_withdraw
templates.env.globals["may_change_post"] = policy.may_change_post
templates.env.globals["may_propose_edit"] = policy.may_propose_edit
templates.env.globals["may_manage_pages"] = policy.may_manage_pages
templates.env.globals["may_update_site"] = policy.may_update_site


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
    route_name = getattr(request.scope.get("route"), "name", None)
    if policy.must_choose_nickname(user, route_name):
        raise NicknameRequired
    if not policy.may_use_route(user, route_name):
        raise Forbidden(user)
    return user


def flash(request: Request, message: str, *, failed: bool = False) -> None:
    """Show this message on the next page rendered for this session, once; as an
    error when what the button did `failed`."""
    request.session["flash"] = message
    request.session["flash_failed"] = failed


def saved_message(message: str, fields: PostFields | PageFields, saved: Post | Page,
                  taken_by: str) -> str:
    """The save message, saying so when the typed slug was already `taken_by` someone
    else ("otra publicación", "otra página") and got a number."""
    if fields.typed_slug and fields.typed_slug != saved.slug:
        return (f"{message} El enlace «{fields.typed_slug}» ya era de {taken_by}:"
                f" quedó «{saved.slug}».")
    return message


def render(request: Request, name: str, user: User | None = None,
           status_code: int = 200, **context):
    return templates.TemplateResponse(
        request, name, {"site_title": settings.SITE_TITLE, "user": user,
                        "message": request.session.pop("flash", None),
                        "message_failed": request.session.pop("flash_failed", False),
                        **context},
        status_code=status_code,
    )
