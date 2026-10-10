#!/usr/bin/env python3
"""Rebuild the demo database from scratch, with fictional data only.

    uv run python scripts/seed_demo.py

Wipes the database at CMS_DATABASE and creates the leader, two members, and a
member's draft post.
Passwords come from CMS_ADMIN_PASSWORD and CMS_EDITOR_PASSWORD (read from .env,
or from .env.example on a fresh clone); they are never printed.
"""
from __future__ import annotations

import os
import sys
from contextlib import closing

from app import accounts, content, db, settings
from app.content import PostFields

# (email, nickname, role, environment variable holding the password).
# tests/conftest.py uses the same emails and nicknames.
DEMO_USERS = [
    ("lider@albiazul.example", "El Capi", "admin", "CMS_ADMIN_PASSWORD"),
    ("ana@albiazul.example", "Rayada de Corazón", "editor", "CMS_EDITOR_PASSWORD"),
    ("beto@albiazul.example", "Furia del Cerro", "editor", "CMS_EDITOR_PASSWORD"),
]

# A post its member is still writing (written by ana@).
DRAFT = PostFields(
    title="Lo que se vio desde la cabecera norte",
    topic="match",
    body=(
        "Todavía lo estoy escribiendo, pero va la idea:\n\n"
        "- El primer tiempo fue **puro Rayados**.\n"
        "- En el segundo nos faltó *cerrar el partido*.\n\n"
        "> Aquí se viene a alentar, no a sufrir. (Mi tío, cada sábado.)\n\n"
        "Mañana le agrego lo del gol del triunfo.\n"
    ),
)


def main() -> int:
    missing = sorted({var for *_, var in DEMO_USERS if not os.environ.get(var)})
    if missing:
        print(f"Set {', '.join(missing)} in .env (copy .env.example).")
        return 1

    path = settings.DATABASE_PATH
    path.unlink(missing_ok=True)
    db.init(path)
    with closing(db.connect(path)) as conn:
        users = {email: accounts.create_user(conn, email=email, password=os.environ[var],
                                             role=role, nickname=nickname)
                 for email, nickname, role, var in DEMO_USERS}
        content.create_post(conn, users["ana@albiazul.example"], DRAFT)

    print(f"Rebuilt {path} with these demo accounts:")
    for email, nickname, role, var in DEMO_USERS:
        print(f"  {email:<26} {role:<7} {nickname}  (password: ${var})")
    print(f"and one draft post: {DRAFT.title}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
