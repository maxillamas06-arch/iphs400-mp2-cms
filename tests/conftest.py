"""Shared test fixtures.

Every test gets its own fresh SQLite database in a temporary folder, holding the
demo users below. `client` gives you the app, signed out. `client_as(role)`
gives you a client signed in as a demo user, so access-control tests stay one
line:

    def test_editor_cannot_manage_users(client_as):
        assert client_as("editor").get("/admin/users").status_code == 403

Every POST needs a CSRF token; `csrf_token(client)` reads it from an admin page
the way a browser would.

The test app's site update exports to a temporary `public_site` folder and uploads
with a fake (`uploads`), so no test writes site/ or uploads anything to GitHub.
"""
from __future__ import annotations

import html
import os
import re
import subprocess
import sys
from contextlib import closing
from pathlib import Path

import pytest
from fastapi.routing import APIRoute, iter_route_contexts
from fastapi.testclient import TestClient

from app import accounts, db, main, settings
from app.export import export_site
from app.main import create_app
from app.site_update import UploadFailed

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


class FakeUpload:
    """Stands in for the upload to GitHub Pages, so nothing goes online. Records
    the files of each folder it is handed, as they were when the upload ran, and
    fails like a dropped connection while `failing` is set."""

    def __init__(self) -> None:
        self.sent: list[set[str]] = []
        self.failing = False

    def __call__(self, site: Path) -> None:
        if self.failing:
            raise UploadFailed("could not read from remote repository")
        self.sent.append({path.relative_to(site).as_posix()
                          for path in site.rglob("*") if path.is_file()})


@pytest.fixture(autouse=True)
def nothing_goes_online(monkeypatch, tmp_path: Path) -> None:
    """Every test, even one that builds its app without `app_for`: the site update
    exports to a temporary folder instead of site/, and the upload fails before
    anything reaches GitHub. A test that wants the real upload passes it in."""

    def refuse(site: Path) -> None:
        raise UploadFailed("tests never upload to GitHub")

    monkeypatch.setattr(main, "upload_to_github_pages", refuse)
    monkeypatch.setattr(settings, "SITE", tmp_path / "default-site")


@pytest.fixture
def uploads() -> FakeUpload:
    """The fake upload every test app uses: uploads.sent, uploads.failing = True."""
    return FakeUpload()


@pytest.fixture
def public_site(tmp_path: Path) -> Path:
    """Where the test app's site update exports the public site (never site/)."""
    return tmp_path / "public-site"


@pytest.fixture
def app_for(public_site: Path, uploads: FakeUpload):
    """Return a function: app_for(database) -> the admin console on that database,
    exporting to `public_site` and uploading with the fake."""

    def _app(database: Path):
        return create_app(database, site=public_site, upload=uploads)

    return _app


@pytest.fixture
def client(database_path: Path, app_for) -> TestClient:
    return TestClient(app_for(database_path))


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
def client_as(database_path: Path, login, app_for):
    """Return a factory: client_as("editor") -> a signed-in TestClient."""

    def _client_as(role: str) -> TestClient:
        user = DEMO_USERS[role]
        c = TestClient(app_for(database_path))
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
def write_page(csrf_token):
    """Return a function: write_page(client, title=..., body=..., menu_order=..., slug=...)
    -> the (unfollowed) response to creating that page with the page editor's form."""

    def _write(c: TestClient, title: str = "Quiénes somos",
               body: str = "Somos aficionados de **Rayados**.", menu_order: str = "1",
               slug: str = ""):
        return c.post("/admin/pages/new",
                      data={"csrf_token": csrf_token(c), "title": title, "body": body,
                            "menu_order": menu_order, "slug": slug},
                      follow_redirects=False)

    return _write


@pytest.fixture
def propose_edit(csrf_token):
    """Return a function: propose_edit(client, post_url, title=..., topic=..., body=...,
    slug=...) -> the (unfollowed) response to a member saving changes to their
    published post with the editor's Proponer cambios button."""

    def _propose(c: TestClient, url: str, title: str = "Crónica del Clásico Regio",
                 topic: str = "match", body: str = "Ganamos **3-1** en casa.", slug: str = ""):
        return c.post(f"{url}/propose-edit",
                      data={"csrf_token": csrf_token(c, url), "title": title, "topic": topic,
                            "body": body, "slug": slug},
                      follow_redirects=False)

    return _propose


@pytest.fixture
def create_account(csrf_token):
    """Return a function: create_account(leader, email=..., role=..., password=...) ->
    the (unfollowed) response to the leader creating that account with the form."""

    def _create(c: TestClient, email: str = "carla@albiazul.example", role: str = "editor",
                password: str = "albiazul"):
        return c.post("/admin/users/new",
                      data={"csrf_token": csrf_token(c, "/admin/users/new"), "email": email,
                            "role": role, "password": password},
                      follow_redirects=False)

    return _create


@pytest.fixture
def account_url():
    """Return a function: account_url(leader, email) -> the admin URL of that account,
    found by its email in the list of accounts."""

    def _url(c: TestClient, email: str) -> str:
        match = re.search(rf'<a href="([^"]+)">{re.escape(email)}</a>', c.get("/admin/users").text)
        assert match, f"no link to {email} in the list of accounts"
        return match.group(1)

    return _url


@pytest.fixture
def account_action(csrf_token):
    """Return a function: account_action(leader, account_url, "role", role="admin") ->
    the (unfollowed) response to that form on the account's screen."""

    def _act(c: TestClient, url: str, action: str, **fields: str):
        return c.post(f"{url}/{action}", data={"csrf_token": csrf_token(c, url), **fields},
                      follow_redirects=False)

    return _act


@pytest.fixture
def take_action(csrf_token):
    """Return a function: take_action(client, post_url, "publish") -> the (unfollowed)
    response to that lifecycle action's button on the post's page."""

    def _take(c: TestClient, url: str, action: str):
        return c.post(f"{url}/{action}", data={"csrf_token": csrf_token(c, url)},
                      follow_redirects=False)

    return _take


@pytest.fixture
def published_post(client_as, write_post, take_action, clock):
    """Return a function: published_post(by="editor", day=None, **post) -> the admin
    URL of a post written by that demo user (submitted first, when a member wrote
    it) and published by the leader, at noon Monterrey time on that October day
    if one is given. `post` takes write_post's fields."""
    clients: dict[str, TestClient] = {}

    def _published(by: str = "editor", day: int | None = None, **post: str) -> str:
        for role in (by, "admin"):
            clients.setdefault(role, client_as(role))
        url = write_post(clients[by], **post).headers["location"]
        if by != "admin":
            take_action(clients[by], url, "submit")
        if day is not None:
            clock.time = f"2026-10-{day:02d}T18:00:00+00:00"
        take_action(clients["admin"], url, "publish")
        return url

    return _published


@pytest.fixture
def published_page(client_as, write_page, take_action):
    """Return a function: published_page(**page) -> the admin URL of a page the leader
    wrote and published. `page` takes write_page's fields."""
    clients: dict[str, TestClient] = {}

    def _published(**page: str) -> str:
        leader = clients.setdefault("admin", client_as("admin"))
        url = write_page(leader, **page).headers["location"]
        take_action(leader, url, "publish")
        return url

    return _published


@pytest.fixture
def export(database_path: Path, tmp_path: Path):
    """Return a function: export(database=None) -> the folder the site export wrote,
    from this test's database unless another is given. Every call regenerates it."""

    def _export(database: Path | None = None) -> Path:
        out = tmp_path / "site"
        with closing(db.connect(database or database_path)) as conn:
            export_site(conn, out)
        return out

    return _export


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
def button_action():
    """Return a function: button_action(html, label) -> where the POST form holding
    the button with this label sends, or None when the page has no such button."""

    def _action(html: str, label: str) -> str | None:
        for action, form in re.findall(
                r'<form[^>]*method="post"[^>]*action="([^"]+)"[^>]*>(.*?)</form>', html, re.S):
            if re.search(rf"<button[^>]*>{label}</button>", form):
                return action
        return None

    return _action


@pytest.fixture
def dashboard_counts():
    """Return a function: dashboard_counts(client) -> each dashboard count's label ->
    (its number, where it links), as a reader sees them."""

    def _text(html: str) -> str:
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()

    def _counts(c: TestClient) -> dict[str, tuple[str, str]]:
        found = re.findall(r'<dt>(.*?)</dt>\s*<dd><a href="([^"]+)">(.*?)</a></dd>',
                           c.get("/admin").text, re.S)
        # A browser reads "&amp;" in an href as "&".
        return {_text(label): (_text(number), html.unescape(href))
                for label, href, number in found}

    return _counts


@pytest.fixture
def status_of(cells):
    """Return a function: status_of(client, title) -> that post's status as the
    content list shows it ("Borrador", "Enviada", "Publicada")."""

    def _status(c: TestClient, title: str) -> str:
        [row] = [row for row in cells(c.get("/admin/content").text) if row and row[0] == title]
        return row[3]

    return _status


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
