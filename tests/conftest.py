"""Shared test fixtures.

Every test gets its own fresh SQLite database in a temporary folder, holding the
demo users below. `client` gives you the app, signed out. `client_as(role)`
gives you a client signed in as a demo user, so access-control tests stay one
line:

    def test_editor_cannot_manage_users(client_as):
        assert client_as("editor").get("/admin/users").status_code == 403

Every POST needs a CSRF token; `csrf_token(client)` reads it from an admin page
the way a browser would.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.routing import APIRoute, iter_route_contexts
from fastapi.testclient import TestClient

from app import accounts, db
from app.main import create_app

# Same emails, nicknames and roles as scripts/seed_demo.py. Passwords come from
# the environment there; in tests they are fixed and meaningless.
DEMO_USERS = {
    "admin": {"email": "lider@albiazul.example", "password": "test-admin-pw",
              "nickname": "El Capi", "role": "admin"},
    "editor": {"email": "ana@albiazul.example", "password": "test-editor-pw",
               "nickname": "Rayada de Corazón", "role": "editor"},
    "editor2": {"email": "beto@albiazul.example", "password": "test-editor2-pw",
                "nickname": "Furia del Cerro", "role": "editor"},
}

ROOT = Path(__file__).resolve().parents[1]
CSRF_FIELD = re.compile(r'name="csrf_token" value="([^"]+)"')
PATH_PARAM = re.compile(r"\{[^}]+\}")


@pytest.fixture
def demo_users() -> dict[str, dict[str, str]]:
    return DEMO_USERS


@pytest.fixture
def database_path(tmp_path: Path) -> Path:
    path = tmp_path / "cms.db"
    db.init(path)
    conn = db.connect(path)
    try:
        for user in DEMO_USERS.values():
            accounts.create_user(conn, email=user["email"], password=user["password"],
                                 role=user["role"], nickname=user["nickname"])
    finally:
        conn.close()
    return path


@pytest.fixture
def inactive_user(database_path: Path) -> dict[str, str]:
    """An extra member whose account is inactive."""
    user = {"email": "baja@albiazul.example", "password": "inactive-pw",
            "nickname": "Dado de Baja", "role": "editor"}
    conn = db.connect(database_path)
    try:
        accounts.create_user(conn, email=user["email"], password=user["password"],
                             role=user["role"], nickname=user["nickname"], active=False)
    finally:
        conn.close()
    return user


@pytest.fixture
def client(database_path: Path) -> TestClient:
    return TestClient(create_app(database_path))


@pytest.fixture
def csrf_token():
    """Return a function: csrf_token(client, path) -> the token in that page's form."""

    def _read(c: TestClient, path: str = "/admin") -> str:
        match = CSRF_FIELD.search(c.get(path).text)
        assert match, f"No CSRF token in the form on {path}"
        return match.group(1)

    return _read


@pytest.fixture
def login(csrf_token):
    """Return a function: login(client, email, password) -> the login response."""

    def _login(c: TestClient, email: str, password: str):
        token = csrf_token(c, "/login")
        return c.post("/login", data={"email": email, "password": password,
                                      "csrf_token": token},
                      follow_redirects=False)

    return _login


@pytest.fixture
def client_as(database_path: Path, login):
    """Return a factory: client_as("editor") -> a signed-in TestClient."""

    def _client_as(role: str) -> TestClient:
        user = DEMO_USERS[role]
        c = TestClient(create_app(database_path))
        response = login(c, user["email"], user["password"])
        assert response.status_code == 303, (
            f"Login as {role} failed with {response.status_code}")
        return c

    return _client_as


@pytest.fixture
def clock(monkeypatch):
    """The time the app records, fixed until a test moves it:
    clock.time = "2026-10-05T01:00:00+00:00"."""

    class Clock:
        time = "2026-10-04T18:30:00+00:00"  # 12:30 in Monterrey

    fixed = Clock()
    monkeypatch.setattr(db, "now", lambda: fixed.time)
    return fixed


@pytest.fixture
def write_post(csrf_token):
    """Return a function: write_post(client, title=..., topic=..., body=..., slug=...)
    -> the (unfollowed) response to creating that post with the editor's form."""

    def _write(c: TestClient, title: str = "Crónica del Clásico Regio", topic: str = "match",
               body: str = "Ganamos **3-1** en casa.", slug: str = ""):
        return c.post("/admin/posts/new",
                      data={"csrf_token": csrf_token(c), "title": title, "topic": topic,
                            "body": body, "slug": slug},
                      follow_redirects=False)

    return _write


@pytest.fixture
def routes():
    """Return a function: routes(client, method) -> [(name, path), ...] for every
    app route answering that method, with path parameters filled in as 1.
    `with_params=False` leaves out routes that take path parameters."""

    def _routes(c: TestClient, method: str,
                with_params: bool = True) -> list[tuple[str, str]]:
        return [(r.name, PATH_PARAM.sub("1", r.path))
                for r in iter_route_contexts(c.app.routes)
                if isinstance(r.original_route, APIRoute) and method in r.methods
                and (with_params or not PATH_PARAM.search(r.path))]

    return _routes


@pytest.fixture
def redirects_to_login():
    """Return a predicate: was this (unfollowed) response sent to /login?"""

    def _check(response) -> bool:
        return (response.status_code == 303
                and response.headers["location"].endswith("/login"))

    return _check


@pytest.fixture
def cells():
    """Return a function: cells(html) -> the text of each table row's cells, as a
    reader sees them (a header row gives [])."""

    def _cells(html: str) -> list[list[str]]:
        rows = re.findall(r"<tr>(.*?)</tr>", html, re.S)
        return [[re.sub(r"<[^>]+>|\s+", " ", c).strip()
                 for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)] for row in rows]

    return _cells


@pytest.fixture
def env_example() -> dict[str, str]:
    """The values in .env.example, read here rather than through app.settings so
    the expected values do not come from the code under test."""
    pairs = (line.split("=", 1) for line in (ROOT / ".env.example").read_text().splitlines()
             if line.strip() and not line.startswith("#"))
    return {key.strip(): value.strip() for key, value in pairs}


@pytest.fixture
def run_seed(env_example):
    """Return a function: run_seed(database) -> the finished seed process, run with
    the .env.example values against that database file."""

    def _run(database: Path) -> subprocess.CompletedProcess:
        env = {k: v for k, v in os.environ.items() if not k.startswith("CMS_")}
        env |= env_example | {"CMS_DATABASE": str(database)}
        return subprocess.run([sys.executable, "scripts/seed_demo.py"], cwd=ROOT, env=env,
                              capture_output=True, text=True)

    return _run
