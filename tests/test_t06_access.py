"""T06 (#7): pages are the leader's alone.

Each test name says which acceptance criterion of #7 it covers.
"""
from __future__ import annotations

from app.policy import LEADER_ONLY_ROUTES


def page_routes(c, routes) -> list[tuple[str, str, str]]:
    """(method, name, path) for every page route, path parameters filled in as 1."""
    return [(method, name, path) for method in ("GET", "POST")
            for name, path in routes(c, method) if path.startswith("/admin/pages")]


def test_every_page_route_is_declared_leader_only_so_the_access_control_test_covers_it(
        client, routes):
    found = page_routes(client, routes)

    assert {name for _, name, _ in found} >= {
        "new_page", "create_page", "preview_new_page", "page", "save_page", "preview_page",
        "publish_page", "unpublish_page", "confirm_delete_page", "delete_page"}
    for method, name, path in found:
        assert name in LEADER_ONLY_ROUTES, f"{method} {path} ({name}) is not leader-only"


def test_member_is_refused_every_page_route_on_a_real_page_and_it_stays_as_it_was(
        client_as, routes, published_page, csrf_token, export):
    published_page(title="Quiénes somos", body="Somos aficionados.")  # page 1
    member = client_as("editor")
    token = csrf_token(member)

    for method, name, path in page_routes(member, routes):
        response = member.request(method, path, follow_redirects=False, data={
            "csrf_token": token, "title": "Hackeada", "body": "Hackeada", "menu_order": "1",
            "slug": ""} if method == "POST" else None)
        assert response.status_code == 403, f"member reached {method} {path}"
        assert "No tienes permiso" in response.text
        assert "Somos aficionados." not in response.text, f"{method} {path} showed the page"

    html = (export() / "quiénes-somos.html").read_text()
    assert "Somos aficionados." in html and "Hackeada" not in html
