"""T01 (#2): every POST form carries a CSRF token; a POST without one gets 403."""
from __future__ import annotations

import re

import pytest

POST_FORM = re.compile(r'<form[^>]*method="post"[^>]*>(.*?)</form>', re.S | re.I)


def test_every_post_form_carries_a_csrf_token_including_login_and_logout(client_as, client, routes):
    leader = client_as("admin")
    pages = {"/login": client.get("/login").text}
    pages |= {path: leader.get(path).text for _, path in routes(leader, "GET")
              if path.startswith("/admin")}

    forms = {path: POST_FORM.findall(html) for path, html in pages.items()}
    assert forms["/login"], "the login page has a POST form"
    assert any("Salir" in f for f in forms["/admin"]), "the admin menu has the logout form"
    for path, page_forms in forms.items():
        for form in page_forms:
            assert 'name="csrf_token"' in form, f"a POST form on {path} has no CSRF token"


def test_login_without_csrf_token_gets_403_and_no_session(client, demo_users):
    user = demo_users["admin"]

    response = client.post("/login", data={"email": user["email"],
                                           "password": user["password"]})

    assert response.status_code == 403
    assert response.headers["content-type"].startswith("text/html")
    assert "Formulario caducado" in response.text
    assert client.get("/admin", follow_redirects=False).status_code == 303


def test_logout_without_csrf_token_gets_403_and_stays_signed_in(client_as):
    leader = client_as("admin")

    assert leader.post("/logout", data={}).status_code == 403
    assert leader.get("/admin", follow_redirects=False).status_code == 200


@pytest.mark.parametrize("token", [None, "forged-token"])
def test_every_post_route_without_a_valid_csrf_token_gets_403(client_as, routes, token):
    leader = client_as("admin")
    data = {} if token is None else {"csrf_token": token}

    post_routes = routes(leader, "POST")
    assert {"login_submit", "logout"} <= {name for name, _ in post_routes}
    for name, path in post_routes:
        response = leader.post(path, data=data, follow_redirects=False)
        assert response.status_code == 403, f"{name} ({path}) accepted a POST without a valid token"
