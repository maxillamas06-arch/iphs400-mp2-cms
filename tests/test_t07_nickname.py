"""T07 (#8): a new member chooses their nickname at their first login.

Each test name says which acceptance criterion of #8 it covers.
"""
from __future__ import annotations

import pytest


@pytest.fixture
def newcomer(client, client_as, create_account, login):
    """A client signed in as a member the leader just let in: no nickname yet."""
    create_account(client_as("admin"), email="carla@albiazul.example", password="albiazul")
    assert login(client, "carla@albiazul.example", "albiazul").status_code == 303
    return client


@pytest.fixture
def choose_nickname(csrf_token):
    """Return a function: choose_nickname(client, nickname) -> the (unfollowed)
    response to sending the first-login nickname form."""

    def _choose(c, nickname: str):
        return c.post("/admin/nickname",
                      data={"csrf_token": csrf_token(c, "/admin/nickname"), "nickname": nickname},
                      follow_redirects=False)

    return _choose


def sent_to_nickname_screen(response) -> bool:
    return (response.status_code == 303
            and response.headers["location"].endswith("/admin/nickname"))


def test_user_without_a_nickname_is_redirected_from_every_admin_route_to_the_nickname_screen(
        newcomer, routes, csrf_token):
    token = csrf_token(newcomer, "/admin/nickname")
    admin_routes = [(method, name, path) for method in ("GET", "POST")
                    for name, path in routes(newcomer, method)
                    if path.startswith("/admin") and path != "/admin/nickname"]
    assert ("GET", "dashboard", "/admin") in admin_routes

    for method, name, path in admin_routes:
        response = newcomer.request(method, path, follow_redirects=False,
                                    data={"csrf_token": token} if method == "POST" else None)
        assert sent_to_nickname_screen(response), f"{method} {path} ({name}) let them through"


def test_nickname_screen_asks_for_a_nickname_and_shows_no_admin_menu_until_one_is_chosen(newcomer):
    html = newcomer.get("/admin/nickname").text

    assert "Elige tu apodo" in html
    assert 'name="nickname"' in html
    assert ">Panel</a>" not in html and ">Salir</button>" in html


@pytest.mark.parametrize("nickname", ["Yo", "La Fiera del Barrio", "z" * 40])
def test_new_member_chooses_a_nickname_of_2_to_40_characters_and_the_dashboard_greets_them(
        newcomer, choose_nickname, nickname):
    response = choose_nickname(newcomer, f"  {nickname} ")

    assert response.status_code == 303
    dashboard = newcomer.get(response.headers["location"], follow_redirects=False)
    assert dashboard.status_code == 200
    assert f"Hola, {nickname}<" in dashboard.text


@pytest.mark.parametrize("nickname, error", [
    ("x", "entre 2 y 40 caracteres"),
    ("z" * 41, "entre 2 y 40 caracteres"),
    ("   ", "entre 2 y 40 caracteres"),
    ("el capi", "ya lo usa otra persona"),            # El Capi, the leader
    ("RAYADA DE CORAZÓN", "ya lo usa otra persona"),  # Rayada de Corazón: case beyond ASCII
])
def test_nickname_too_short_too_long_or_taken_ignoring_case_is_refused_and_they_stay_on_the_screen(
        newcomer, choose_nickname, nickname, error):
    response = choose_nickname(newcomer, nickname)

    assert response.status_code == 400
    assert error in response.text
    assert sent_to_nickname_screen(newcomer.get("/admin", follow_redirects=False))


@pytest.mark.parametrize("who", ["newcomer", "seeded member"])
def test_member_cannot_change_their_nickname_once_chosen(
        newcomer, client_as, choose_nickname, csrf_token, who):
    if who == "newcomer":
        member, nickname = newcomer, "La Fiera del Barrio"
        choose_nickname(member, nickname)
    else:
        member, nickname = client_as("editor"), "Rayada de Corazón"

    response = member.post("/admin/nickname", follow_redirects=False,
                           data={"csrf_token": csrf_token(member), "nickname": "Otro Apodo"})

    assert response.status_code == 400
    assert "Solo el líder puede cambiarlo" in response.text
    dashboard = member.get("/admin").text
    assert f"Hola, {nickname}<" in dashboard and "Otro Apodo" not in dashboard
