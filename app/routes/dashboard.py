"""The admin console's home: the dashboard."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.accounts import User
from app.web import render, signed_in_user

router = APIRouter(prefix="/admin", dependencies=[Depends(signed_in_user)])


@router.get("", name="dashboard")
def dashboard(request: Request, user: User = Depends(signed_in_user)):
    return render(request, "admin/dashboard.html", user)
