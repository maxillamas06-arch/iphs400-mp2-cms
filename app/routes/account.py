"""Your own account: the nickname chosen at the first login, and Mi cuenta."""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app import accounts
from app.accounts import User
from app.web import flash, get_db, render, signed_in_user

router = APIRouter(prefix="/admin", dependencies=[Depends(signed_in_user)])


@router.get("/nickname", name="nickname")
def nickname_form(request: Request, user: User = Depends(signed_in_user)):
    if user.nickname is not None:
        return RedirectResponse(request.app.url_path_for("dashboard"), status_code=303)
    return render(request, "admin/nickname.html", user, nickname="")


@router.post("/nickname", name="choose_nickname")
def choose_nickname(request: Request, nickname: str = Form(""),
                    user: User = Depends(signed_in_user),
                    conn: sqlite3.Connection = Depends(get_db)):
    try:
        chosen = accounts.choose_nickname(conn, user, nickname)
    except accounts.AccountError as refused:
        return render(request, "admin/nickname.html", user, status_code=400,
                      nickname=nickname, error=str(refused))
    flash(request, f"¡Listo! Tus publicaciones aparecerán con el apodo «{chosen.nickname}».")
    return RedirectResponse(request.app.url_path_for("dashboard"), status_code=303)


@router.get("/account", name="account")
def account(request: Request, user: User = Depends(signed_in_user)):
    return render(request, "admin/account.html", user)


@router.post("/account/password", name="change_password")
def change_password(request: Request, current_password: str = Form(""),
                    new_password: str = Form(""), user: User = Depends(signed_in_user),
                    conn: sqlite3.Connection = Depends(get_db)):
    try:
        accounts.change_password(conn, user, current_password, new_password)
    except accounts.AccountError as refused:
        return render(request, "admin/account.html", user, status_code=400,
                      error=str(refused))
    flash(request, "Contraseña cambiada. Úsala la próxima vez que entres.")
    return RedirectResponse(request.app.url_path_for("account"), status_code=303)
