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
from app.routes import account, auth, dashboard, pages, posts, site_update, users
from app.site_update import Upload, upload_to_github_pages
from app.web import (CsrfRejected, Forbidden, LoginRequired, NicknameRequired, NotFound,
                     render, require_csrf)


def create_app(database_path: Path | None = None, site: Path | None = None,
               upload: Upload | None = None) -> FastAPI:
    """The admin console on one SQLite file. Its site update exports to `site` and
    puts it online with `upload`; tests pass a temporary folder and a fake."""
    # Every route checks the CSRF token first, so no POST can forget it.
    app = FastAPI(title=settings.SITE_TITLE, dependencies=[Depends(require_csrf)])
    app.state.database_path = database_path or settings.DATABASE_PATH
    app.state.site = site or settings.SITE
    app.state.upload = upload or upload_to_github_pages
    db.init(app.state.database_path)

    # Signed, HTTP-only, same-site cookie holding the user id and CSRF token.
    app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY,
                       session_cookie="cms_session", same_site="lax")

    @app.exception_handler(LoginRequired)
    def to_login(request: Request, exc: LoginRequired):
        return RedirectResponse(app.url_path_for("login"), status_code=303)

    @app.exception_handler(NicknameRequired)
    def to_nickname(request: Request, exc: NicknameRequired):
        return RedirectResponse(app.url_path_for("nickname"), status_code=303)

    @app.exception_handler(CsrfRejected)
    def reject_form(request: Request, exc: CsrfRejected):
        return render(request, "admin/csrf_rejected.html", status_code=403)

    @app.exception_handler(Forbidden)
    def refuse(request: Request, exc: Forbidden):
        return render(request, "admin/forbidden.html", exc.user, status_code=403,
                      reason=exc.reason)

    @app.exception_handler(NotFound)
    def not_found(request: Request, exc: NotFound):
        return render(request, "admin/not_found.html", exc.user, status_code=404,
                      missing=exc.missing)

    app.include_router(auth.router)
    app.include_router(dashboard.router)
    app.include_router(account.router)
    app.include_router(posts.router)
    app.include_router(pages.router)
    app.include_router(users.router)
    app.include_router(site_update.router)

    # The public site is the static export (ADR-001), not served here, so the
    # server's front door is the admin console.
    @app.get("/")
    def front_door(request: Request):
        return RedirectResponse(app.url_path_for("dashboard"), status_code=303)

    return app
