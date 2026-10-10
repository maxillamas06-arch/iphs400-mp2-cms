"""User management (leader only): the list of accounts."""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Request

from app import accounts
from app.accounts import User
from app.web import get_db, render, signed_in_user

router = APIRouter(prefix="/admin/users", dependencies=[Depends(signed_in_user)])


@router.get("", name="users")
def users_list(request: Request, user: User = Depends(signed_in_user),
               conn: sqlite3.Connection = Depends(get_db)):
    return render(request, "admin/users.html", user, users=accounts.list_users(conn))
