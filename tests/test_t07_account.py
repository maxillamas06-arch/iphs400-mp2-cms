"""T07 (#8): on Mi cuenta, anyone changes their own password.

Each test name says which acceptance criterion of #8 it covers.
"""
from __future__ import annotations

import sqlite3
from contextlib import closing

import pytest


@pytest.fixture
def change_password(csrf_token):
    """Return a function: change_password(client, current, new) -> the (unfollowed)
    response to the password form on Mi cuenta."""

    def _change(c, current: str, new: str):
        return c.post("/admin/account/password", follow_redirects=False,
                      data={"csrf_token": csrf_token(c, "/admin/account"),
                            "current_password": current, "new_password": new})

    return _change


@pytest.mark.parametrize("role", ["admin", "editor"])
def test_any_user_changes_their_own_password_on_mi_cuenta_by_giving_the_current_one(
        client_as, client, login, demo_users, change_password, role):
    user, c = demo_users[role], client_as(role)
    assert ">Mi cuenta</a>" in c.get("/admin").text
    page = c.get("/admin/account").text
    assert user["email"] in page and user["nickname"] in page

    response = change_password(c, user["password"], "albiazul")  # exactly 8 characters

    assert response.status_code == 303
    assert "Contraseña cambiada" in c.get(response.headers["location"]).text
    assert login(client, user["email"], user["password"]).status_code == 400
    assert login(client, user["email"], "albiazul").status_code == 303


@pytest.mark.parametrize("current, new, error", [
    ("no-es-la-mia", "nueva-clave-segura", "La contraseña actual no es correcta"),
    ("test-editor-pw", "rayado7", "al menos 8 caracteres"),
])
def test_password_change_is_refused_without_the_right_current_password_or_with_a_short_new_one(
        client_as, client, login, demo_users, change_password, current, new, error):
    ana = demo_users["editor"]

    response = change_password(client_as("editor"), current, new)

    assert response.status_code == 400
    assert error in response.text
    assert login(client, ana["email"], new).status_code == 400
    assert login(client, ana["email"], ana["password"]).status_code == 303


def test_changed_password_is_stored_as_an_argon2_hash_and_never_in_plain(
        client_as, demo_users, change_password, database_path):
    ana = demo_users["editor"]

    change_password(client_as("editor"), ana["password"], "nueva-clave-segura")

    with closing(sqlite3.connect(database_path)) as conn:
        [stored] = conn.execute("SELECT password_hash FROM users WHERE email = ?",
                                (ana["email"],)).fetchone()
    assert stored.startswith("$argon2")
    assert b"nueva-clave-segura" not in database_path.read_bytes()


def test_mi_cuenta_shows_a_member_their_nickname_and_says_only_the_leader_can_change_it(
        client_as):
    page = client_as("editor").get("/admin/account").text

    assert "Rayada de Corazón" in page
    assert "Solo el líder puede cambiar tu apodo" in page


def test_mi_cuenta_shows_the_leader_their_nickname_and_where_they_change_it(
        client_as, account_url, demo_users):
    leader = client_as("admin")

    page = leader.get("/admin/account").text

    assert "El Capi" in page
    assert "Solo el líder puede cambiar tu apodo" not in page
    assert f'href="{account_url(leader, demo_users["admin"]["email"])}"' in page
