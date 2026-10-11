"""T07 (#8): managing accounts is the leader's alone.

Each test name says which acceptance criterion of #8 it covers.
"""
from __future__ import annotations

from urllib.parse import urlsplit

from app.policy import LEADER_ONLY_ROUTES


def user_routes(c, routes) -> list[tuple[str, str, str]]:
    """(method, name, path) for every user-management route, path parameters filled in as 1."""
    return [(method, name, path) for method in ("GET", "POST")
            for name, path in routes(c, method) if path.startswith("/admin/users")]


def test_every_user_management_route_is_declared_leader_only_so_the_access_control_test_covers_it(
        client, routes):
    found = user_routes(client, routes)

    assert {name for _, name, _ in found} >= {
        "users", "new_user", "create_user", "user", "change_role", "set_nickname",
        "set_temporary_password", "deactivate_user", "reactivate_user"}
    for method, name, path in found:
        assert name in LEADER_ONLY_ROUTES, f"{method} {path} ({name}) is not leader-only"


def test_member_is_refused_every_user_management_route_on_real_accounts_and_nothing_changes(
        client, client_as, routes, csrf_token, account_url, cells, login, demo_users):
    leader, ana = client_as("admin"), client_as("editor")
    before = cells(leader.get("/admin/users").text)
    token = csrf_token(ana)
    # The leader's account, and her own: she may not promote herself either.
    targets = [urlsplit(account_url(leader, demo_users[role]["email"])).path
               for role in ("admin", "editor")]

    for method, name, path in user_routes(ana, routes):
        for target in targets:
            path_on_target = path.replace("/admin/users/1", target)
            response = ana.request(method, path_on_target, follow_redirects=False, data={
                "csrf_token": token, "email": "intrusa@albiazul.example", "role": "admin",
                "nickname": "Hackeada", "password": "hackeada-123",
            } if method == "POST" else None)
            assert response.status_code == 403, f"member reached {method} {path_on_target}"
            assert "No tienes permiso" in response.text

    assert cells(leader.get("/admin/users").text) == before
    assert ana.get("/admin/users").status_code == 403, "she is still a member"
    leader_user = demo_users["admin"]
    assert login(client, leader_user["email"], leader_user["password"]).status_code == 303
