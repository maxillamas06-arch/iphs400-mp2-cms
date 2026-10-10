"""T01 (#2): the leader and members log in and log out.

Each test name says which acceptance criterion of #2 it covers.
"""
from __future__ import annotations

import sqlite3
from contextlib import closing

import pytest


@pytest.mark.parametrize("role", ["admin", "editor"])
def test_seeded_user_logs_in_and_dashboard_greets_them_by_nickname(client, login, demo_users, role):
    user = demo_users[role]

    response = login(client, user["email"], user["password"])

    assert response.status_code == 303
    assert response.headers["location"].endswith("/admin")
    dashboard = client.get("/admin")
    assert dashboard.status_code == 200
    assert user["nickname"] in dashboard.text


@pytest.mark.parametrize("role", ["admin", "editor"])
def test_seeded_user_logs_out_with_salir(client_as, csrf_token, redirects_to_login, role):
    c = client_as(role)
    dashboard = c.get("/admin").text
    assert ">Salir</button>" in dashboard

    response = c.post("/logout", data={"csrf_token": csrf_token(c)},
                      follow_redirects=False)

    assert redirects_to_login(response)
    assert redirects_to_login(c.get("/admin", follow_redirects=False))


@pytest.mark.parametrize("email, password", [
    ("lider@albiazul.example", "wrong-password"),      # wrong password
    ("nadie@albiazul.example", "test-admin-pw"),       # unknown email
])
def test_wrong_password_and_unknown_email_show_same_message_and_no_session(
        client, login, redirects_to_login, email, password):
    response = login(client, email, password)

    assert response.status_code == 400
    assert "Correo o contraseña incorrectos." in response.text
    assert redirects_to_login(client.get("/admin", follow_redirects=False))


def test_stored_passwords_are_argon2_hashes_and_never_plain(
        client, login, demo_users, database_path, caplog, capsys):
    for user in demo_users.values():
        login(client, user["email"], user["password"])

    with sqlite3.connect(database_path) as conn:
        hashes = [row[0] for row in conn.execute("SELECT password_hash FROM users")]
    assert len(hashes) == len(demo_users)
    assert all(h.startswith("$argon2") for h in hashes)
    stored = database_path.read_bytes()
    printed = caplog.text + "".join(capsys.readouterr())
    for user in demo_users.values():
        assert user["password"].encode() not in stored
        assert user["password"] not in printed


def test_inactive_user_cannot_log_in(client, login, inactive_user, redirects_to_login):
    response = login(client, inactive_user["email"], inactive_user["password"])

    assert response.status_code == 400
    assert "Correo o contraseña incorrectos." in response.text
    assert redirects_to_login(client.get("/admin", follow_redirects=False))


def test_open_session_of_a_deactivated_user_stops_working_on_next_request(
        client_as, database_path, redirects_to_login):
    member = client_as("editor")
    # T07 gives the leader a deactivate button; until then, deactivate in storage.
    with closing(sqlite3.connect(database_path)) as conn, conn:
        conn.execute("UPDATE users SET active = 0 WHERE email = 'ana@albiazul.example'")

    assert redirects_to_login(member.get("/admin", follow_redirects=False))
