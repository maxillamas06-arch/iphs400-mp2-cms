"""Logging in and out."""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app import accounts
from app.web import get_db, render

router = APIRouter()


@router.get("/login", name="login")
def login_form(request: Request):
    return render(request, "admin/login.html")


@router.post("/login", name="login_submit")
def login(request: Request, email: str = Form(""), password: str = Form(""),
          conn: sqlite3.Connection = Depends(get_db)):
    user = accounts.authenticate(conn, email, password)
    if user is None:
        return render(request, "admin/login.html", status_code=400, email=email,
                      error="Correo o contraseña incorrectos.")
    request.session.clear()
    request.session["user_id"] = user.id
    return RedirectResponse(request.app.url_path_for("dashboard"), status_code=303)


@router.post("/logout", name="logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(request.app.url_path_for("login"), status_code=303)
