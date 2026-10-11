"""The admin console's home: the dashboard."""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Request

from app import content, policy
from app.accounts import User
from app.web import get_db, render, signed_in_user

router = APIRouter(prefix="/admin", dependencies=[Depends(signed_in_user)])


@router.get("", name="dashboard")
def dashboard(request: Request, user: User = Depends(signed_in_user),
              conn: sqlite3.Connection = Depends(get_db)):
    return render(request, "admin/dashboard.html", user,
                  counts=content.count_by_status(conn),
                  pending_edits=content.count_pending_edits(conn),
                  pages=content.count_pages(conn) if policy.may_manage_pages(user) else None)
