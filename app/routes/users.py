"""User management (leader only): the accounts. Every route here is named in
`policy.LEADER_ONLY_ROUTES`."""
from __future__ import annotations

import sqlite3
from collections.abc import Callable

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app import accounts
from app.accounts import Role, User
from app.web import NotFound, flash, get_db, render, signed_in_user

router = APIRouter(prefix="/admin/users", dependencies=[Depends(signed_in_user)])


def existing_account(account_id: str, user: User = Depends(signed_in_user),
                     conn: sqlite3.Connection = Depends(get_db)) -> User:
    # An id that is not a number is as unknown as one that is not in the database.
    account = accounts.get_user(conn, int(account_id)) if account_id.isdecimal() else None
    if account is None:
        raise NotFound(user, "esa cuenta")
    return account


def render_account(request: Request, user: User, account: User, status_code: int = 200,
                   **context):
    return render(request, "admin/user.html", user, status_code=status_code,
                  account=account, **context)


def change_account(request: Request, user: User, account: User,
                   change: Callable[[], User], done: str):
    """One form on an account's screen: done with a message, or refused with the
    reason why."""
    try:
        change()
    except accounts.AccountError as refused:
        return render_account(request, user, account, status_code=400, error=str(refused))
    flash(request, done)
    return RedirectResponse(request.app.url_path_for("user", account_id=account.id),
                            status_code=303)


@router.get("", name="users")
def users_list(request: Request, user: User = Depends(signed_in_user),
               conn: sqlite3.Connection = Depends(get_db)):
    return render(request, "admin/users.html", user, users=accounts.list_users(conn))


@router.get("/new", name="new_user")
def new_user(request: Request, user: User = Depends(signed_in_user)):
    return render(request, "admin/user_new.html", user, email="", role=Role.EDITOR)


@router.post("/new", name="create_user")
def create_user(request: Request, email: str = Form(""), role: str = Form(""),
                password: str = Form(""), user: User = Depends(signed_in_user),
                conn: sqlite3.Connection = Depends(get_db)):
    try:
        accounts.create_user(conn, email=email, password=password, role=role)
    except accounts.AccountError as refused:
        return render(request, "admin/user_new.html", user, status_code=400,
                      email=email, role=role, error=str(refused))
    flash(request, "Cuenta creada. Dale la contraseña temporal en persona: elegirá su apodo"
                   " la primera vez que entre.")
    return RedirectResponse(request.app.url_path_for("users"), status_code=303)


@router.get("/{account_id}", name="user")
def user_screen(request: Request, account: User = Depends(existing_account),
                   user: User = Depends(signed_in_user)):
    return render_account(request, user, account)


@router.post("/{account_id}/role", name="change_role")
def change_role(request: Request, role: str = Form(""),
                account: User = Depends(existing_account), user: User = Depends(signed_in_user),
                conn: sqlite3.Connection = Depends(get_db)):
    return change_account(request, user, account,
                          lambda: accounts.change_role(conn, user, account, role),
                          "Rol cambiado.")


@router.post("/{account_id}/nickname", name="set_nickname")
def set_nickname(request: Request, nickname: str = Form(""),
                 account: User = Depends(existing_account), user: User = Depends(signed_in_user),
                 conn: sqlite3.Connection = Depends(get_db)):
    return change_account(request, user, account,
                          lambda: accounts.set_nickname(conn, account, nickname),
                          "Apodo cambiado. Sus publicaciones lo mostrarán después de la próxima"
                          " actualización del sitio.")


@router.post("/{account_id}/password", name="set_temporary_password")
def set_temporary_password(request: Request, password: str = Form(""),
                           account: User = Depends(existing_account),
                           user: User = Depends(signed_in_user),
                           conn: sqlite3.Connection = Depends(get_db)):
    return change_account(request, user, account,
                          lambda: accounts.set_password(conn, account, password),
                          "Contraseña temporal guardada. Dásela en persona: después puede"
                          " cambiarla en Mi cuenta.")


@router.post("/{account_id}/deactivate", name="deactivate_user")
def deactivate_user(request: Request, account: User = Depends(existing_account),
                    user: User = Depends(signed_in_user),
                    conn: sqlite3.Connection = Depends(get_db)):
    return change_account(request, user, account,
                          lambda: accounts.deactivate(conn, user, account),
                          "Cuenta desactivada: ya no puede entrar. Sus publicaciones siguen"
                          " donde estaban.")


@router.post("/{account_id}/reactivate", name="reactivate_user")
def reactivate_user(request: Request, account: User = Depends(existing_account),
                    user: User = Depends(signed_in_user),
                    conn: sqlite3.Connection = Depends(get_db)):
    return change_account(request, user, account, lambda: accounts.reactivate(conn, account),
                          "Cuenta reactivada: ya puede volver a entrar.")
