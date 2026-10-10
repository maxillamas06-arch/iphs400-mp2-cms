"""The FastAPI application.

`create_app()` builds the admin console against one SQLite file. Routes live in
their own modules under app/routes/; this file only wires them together.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from app import db, settings
from app.routes import auth, dashboard, users
from app.web import (CsrfRejected, Forbidden, LoginRequired, render, require_csrf,
                     templates)


def create_app(database_path: Path | None = None) -> FastAPI:
    # Every route checks the CSRF token first, so no POST can forget it.
    app = FastAPI(title=settings.SITE_TITLE, dependencies=[Depends(require_csrf)])
    app.state.database_path = database_path or settings.DATABASE_PATH
    db.init(app.state.database_path)

    # Signed, HTTP-only, same-site cookie holding the user id and CSRF token.
    app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY,
                       session_cookie="cms_session", same_site="lax")

    @app.exception_handler(LoginRequired)
    def to_login(request: Request, exc: LoginRequired):
        return RedirectResponse(app.url_path_for("login"), status_code=303)

    @app.exception_handler(CsrfRejected)
    def reject_form(request: Request, exc: CsrfRejected):
        return render(request, "admin/csrf_rejected.html", status_code=403)

    @app.exception_handler(Forbidden)
    def refuse(request: Request, exc: Forbidden):
        return render(request, "admin/forbidden.html", exc.user, status_code=403)

    app.include_router(auth.router)
    app.include_router(dashboard.router)
    app.include_router(users.router)

    @app.get("/")
    def public_home(request: Request):
        return templates.TemplateResponse(
            request, "public/home.html",
            {"title": settings.SITE_TITLE, "items": []},
        )

    return app
