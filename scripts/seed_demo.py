#!/usr/bin/env python3
"""Rebuild the demo database from scratch, with fictional data only.

    uv run python scripts/seed_demo.py

Wipes the database at CMS_DATABASE and creates the leader and two members.
Passwords come from CMS_ADMIN_PASSWORD and CMS_EDITOR_PASSWORD (read from .env,
or from .env.example on a fresh clone); they are never printed.
"""
from __future__ import annotations

import os
import sys
from contextlib import closing

from app import accounts, db, settings

# (email, nickname, role, environment variable holding the password).
# tests/conftest.py uses the same emails and nicknames.
DEMO_USERS = [
    ("lider@albiazul.example", "El Capi", "admin", "CMS_ADMIN_PASSWORD"),
    ("ana@albiazul.example", "Rayada de Corazón", "editor", "CMS_EDITOR_PASSWORD"),
    ("beto@albiazul.example", "Furia del Cerro", "editor", "CMS_EDITOR_PASSWORD"),
]


def main() -> int:
    missing = sorted({var for *_, var in DEMO_USERS if not os.environ.get(var)})
    if missing:
        print(f"Set {', '.join(missing)} in .env (copy .env.example).")
        return 1

    path = settings.DATABASE_PATH
    path.unlink(missing_ok=True)
    db.init(path)
    with closing(db.connect(path)) as conn:
        for email, nickname, role, var in DEMO_USERS:
            accounts.create_user(conn, email=email, password=os.environ[var],
                                 role=role, nickname=nickname)

    print(f"Rebuilt {path} with these demo accounts:")
    for email, nickname, role, var in DEMO_USERS:
        print(f"  {email:<26} {role:<7} {nickname}  (password: ${var})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
