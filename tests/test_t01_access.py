"""T01 (#2): who may reach which admin screen.

Each test name says which acceptance criterion of #2 it covers.
"""
from __future__ import annotations

import pytest

from app.policy import LEADER_ONLY_ROUTES


def test_leader_sees_list_of_accounts_with_email_nickname_role_and_active(
        client_as, demo_users, inactive_user, cells):
    response = client_as("admin").get("/admin/users")

    assert response.status_code == 200
    rows = [r for r in cells(response.text) if r]
    assert ["lider@albiazul.example", "El Capi", "Líder", "Sí"] in rows
    assert ["ana@albiazul.example", "Rayada de Corazón", "Miembro", "Sí"] in rows
    assert ["beto@albiazul.example", "Furia del Cerro", "Miembro", "Sí"] in rows
    assert ["baja@albiazul.example", "Dado de Baja", "Miembro", "No"] in rows
    assert len(rows) == len(demo_users) + 1


def test_member_requesting_accounts_gets_403_refusal_page_with_admin_menu(client_as):
    response = client_as("editor").get("/admin/users")

    assert response.status_code == 403
    assert "No tienes permiso" in response.text
    assert 'aria-label="Menú de administración"' in response.text
    assert ">Salir</button>" in response.text
    assert "ana@albiazul.example" not in response.text


def test_anonymous_request_to_any_admin_route_redirects_to_login(
        client, routes, csrf_token, redirects_to_login):
    token = csrf_token(client, "/login")
    admin_routes = [(method, path) for method in ("GET", "POST")
                    for _, path in routes(client, method) if path.startswith("/admin")]
    assert ("GET", "/admin") in admin_routes and ("GET", "/admin/users") in admin_routes

    for method, path in admin_routes:
        data = {"csrf_token": token} if method == "POST" else None
        response = client.request(method, path, data=data, follow_redirects=False)
        assert redirects_to_login(response), f"anonymous {method} {path} was not sent to /login"


def test_every_leader_only_route_declared_in_policy_refuses_member_403_and_anonymous_to_login(
        client, client_as, routes, csrf_token, redirects_to_login):
    assert "users" in LEADER_ONLY_ROUTES
    member = client_as("editor")
    tokens = {"member": csrf_token(member), "anonymous": csrf_token(client, "/login")}

    found = set()
    for method in ("GET", "POST"):
        for name, path in routes(member, method):
            if name not in LEADER_ONLY_ROUTES:
                continue
            found.add(name)
            as_member = member.request(method, path, follow_redirects=False,
                                       data={"csrf_token": tokens["member"]} if method == "POST" else None)
            as_anonymous = client.request(method, path, follow_redirects=False,
                                          data={"csrf_token": tokens["anonymous"]} if method == "POST" else None)
            assert as_member.status_code == 403, f"member reached leader-only {method} {path}"
            assert "No tienes permiso" in as_member.text
            assert redirects_to_login(as_anonymous), f"anonymous {method} {path} not sent to /login"
    assert found == LEADER_ONLY_ROUTES, "every declared leader-only name is a real route"


@pytest.mark.parametrize("role", ["admin", "editor"])
def test_every_admin_page_shows_the_persistent_spanish_admin_menu(client_as, routes, role):
    c = client_as(role)
    pages = [path for _, path in routes(c, "GET", with_params=False) if path.startswith("/admin")]
    assert "/admin" in pages and "/admin/users" in pages

    for path in pages:
        html = c.get(path).text
        assert 'aria-label="Menú de administración"' in html, f"no admin menu on {path}"
        assert ">Panel</a>" in html and ">Salir</button>" in html, f"menu incomplete on {path}"
