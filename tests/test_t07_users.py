"""T07 (#8): the leader manages accounts.

Each test name says which acceptance criterion of #8 it covers.
"""
from __future__ import annotations

import pytest


def test_leader_creates_an_account_with_email_role_and_temporary_password_and_it_has_no_nickname_yet(
        client_as, client, login, create_account, cells):
    leader = client_as("admin")

    response = create_account(leader, email="carla@albiazul.example", role="editor",
                              password="albiazul")  # exactly 8 characters

    assert response.status_code == 303
    assert "Cuenta creada" in leader.get(response.headers["location"]).text
    assert ["carla@albiazul.example", "—", "Miembro", "Sí"] in cells(leader.get("/admin/users").text)
    assert login(client, "carla@albiazul.example", "albiazul").status_code == 303


@pytest.mark.parametrize("email, role, password, error", [
    ("ANA@albiazul.example", "editor", "albiazul", "Ya hay una cuenta con el correo"),
    ("carla@albiazul.example", "editor", "rayado7", "al menos 8 caracteres"),
    ("carla@albiazul.example", "jefe", "albiazul", "Elige un rol"),
    ("carla", "editor", "albiazul", "correo válido"),
])
def test_leader_is_refused_an_account_with_a_taken_email_a_short_password_or_no_valid_role(
        client_as, client, login, create_account, cells, email, role, password, error):
    leader = client_as("admin")
    before = cells(leader.get("/admin/users").text)

    response = create_account(leader, email=email, role=role, password=password)

    assert response.status_code == 400
    assert error in response.text
    assert cells(leader.get("/admin/users").text) == before
    assert login(client, email, password).status_code == 400


ANA = "ana@albiazul.example"


def test_leader_changes_a_members_role_and_it_takes_effect_on_their_next_request(
        client_as, account_url, account_action, cells):
    leader, ana = client_as("admin"), client_as("editor")
    url = account_url(leader, ANA)
    assert ana.get("/admin/users").status_code == 403

    response = account_action(leader, url, "role", role="admin")

    assert response.status_code == 303
    assert "Rol cambiado" in leader.get(response.headers["location"]).text
    assert [ANA, "Rayada de Corazón", "Líder", "Sí"] in cells(leader.get("/admin/users").text)
    assert ana.get("/admin/users").status_code == 200

    account_action(leader, url, "role", role="editor")
    assert ana.get("/admin/users").status_code == 403


def test_leader_sets_any_users_nickname_and_it_stays_unique_ignoring_case(
        client_as, account_url, account_action, cells):
    leader, ana = client_as("admin"), client_as("editor")
    url = account_url(leader, ANA)

    taken = account_action(leader, url, "nickname", nickname="FURIA DEL CERRO")
    assert taken.status_code == 400
    assert "ya lo usa otra persona" in taken.text

    response = account_action(leader, url, "nickname", nickname="La Rayada")
    assert response.status_code == 303
    assert "Apodo cambiado" in leader.get(response.headers["location"]).text
    assert [ANA, "La Rayada", "Miembro", "Sí"] in cells(leader.get("/admin/users").text)
    assert "Hola, La Rayada<" in ana.get("/admin").text


def test_leader_sets_a_new_temporary_password_and_the_member_logs_in_only_with_it(
        client_as, client, login, demo_users, account_url, account_action):
    leader = client_as("admin")
    url = account_url(leader, ANA)

    short = account_action(leader, url, "password", password="rayado7")
    assert short.status_code == 400
    assert "al menos 8 caracteres" in short.text
    assert login(client, ANA, demo_users["editor"]["password"]).status_code == 303

    response = account_action(leader, url, "password", password="nueva-temporal")
    assert response.status_code == 303
    assert "Contraseña temporal guardada" in leader.get(response.headers["location"]).text
    assert login(client, ANA, demo_users["editor"]["password"]).status_code == 400
    assert login(client, ANA, "nueva-temporal").status_code == 303


def test_deactivated_member_cannot_log_in_and_their_open_session_is_rejected_until_reactivated(
        client_as, client, login, demo_users, account_url, account_action, cells,
        redirects_to_login):
    leader, ana = client_as("admin"), client_as("editor")
    url = account_url(leader, ANA)

    response = account_action(leader, url, "deactivate")

    assert response.status_code == 303
    assert "Cuenta desactivada" in leader.get(response.headers["location"]).text
    assert redirects_to_login(ana.get("/admin", follow_redirects=False))
    refused = login(client, ANA, demo_users["editor"]["password"])
    assert refused.status_code == 400 and "Correo o contraseña incorrectos." in refused.text
    assert [ANA, "Rayada de Corazón", "Miembro", "No"] in cells(leader.get("/admin/users").text)

    response = account_action(leader, url, "reactivate")

    assert response.status_code == 303
    assert "Cuenta reactivada" in leader.get(response.headers["location"]).text
    assert login(client, ANA, demo_users["editor"]["password"]).status_code == 303
    assert [ANA, "Rayada de Corazón", "Miembro", "Sí"] in cells(leader.get("/admin/users").text)


@pytest.mark.parametrize("action, fields, message", [
    ("role", {"role": "editor"}, "No puedes cambiar tu propio rol"),
    ("deactivate", {}, "No puedes desactivar tu propia cuenta"),
])
def test_leader_cannot_change_their_own_role_or_deactivate_themselves_and_is_told_why(
        client_as, demo_users, account_url, account_action, cells, action, fields, message):
    leader = client_as("admin")
    me = demo_users["admin"]

    response = account_action(leader, account_url(leader, me["email"]), action, **fields)

    assert response.status_code == 400
    assert message in response.text
    users = leader.get("/admin/users")
    assert users.status_code == 200
    assert [me["email"], me["nickname"], "Líder", "Sí"] in cells(users.text)


def test_accounts_are_never_deleted_so_a_deactivated_members_posts_stay_in_export_and_queue(
        client_as, published_post, write_post, take_action, propose_edit, account_url,
        account_action, export, cells, routes):
    leader, beto = client_as("admin"), client_as("editor2")
    published_post(by="editor2", title="Tigres, traigan pañuelos")
    with_edit = published_post(by="editor2", title="Lo que nos falta")
    propose_edit(beto, with_edit, title="Lo que nos falta, corregido")
    submitted = write_post(beto, title="Tres cambios al medio tiempo").headers["location"]
    take_action(beto, submitted, "submit")

    account_action(leader, account_url(leader, "beto@albiazul.example"), "deactivate")

    assert "Furia del Cerro" in (export() / "posts" / "tigres-traigan-pañuelos.html").read_text()

    def titles(query: str) -> list[str]:
        return [row[0] for row in cells(leader.get(f"/admin/content{query}").text) if row]

    assert titles("?status=submitted") == ["Tres cambios al medio tiempo"]
    assert titles("?pending=1") == ["Lo que nos falta"]
    assert ["beto@albiazul.example", "Furia del Cerro", "Miembro", "No"] in cells(
        leader.get("/admin/users").text)
    assert take_action(leader, submitted, "publish").status_code == 303, "the leader still decides"
    assert not [name for method in ("GET", "POST") for name, path in routes(leader, method)
                if path.startswith("/admin/users") and "delete" in name], "no way to delete one"
