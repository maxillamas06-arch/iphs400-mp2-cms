"""T03 (#4): the leader publishes and unpublishes posts; members cannot.

Each test name says which acceptance criterion of #4 it covers.
"""
from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from app.main import create_app

SLUG_LOCKED = "El enlace ya no se puede cambiar"
NOT_SUBMITTED = "El borrador de un miembro se publica cuando quien lo escribió lo envía"


def status_in_content_list(client, title: str, cells) -> str:
    [row] = [row for row in cells(client.get("/admin/content").text) if row and row[0] == title]
    return row[3]


def slug_input(html: str) -> str:
    """The editor's slug <input> tag."""
    match = re.search(r'<input[^>]*name="slug"[^>]*>', html)
    assert match, "no slug field"
    return match.group(0)


def button_form_action(html: str, label: str) -> str | None:
    """Where the POST form holding the button with this label sends, if there is one."""
    for action, form in re.findall(r'<form[^>]*method="post"[^>]*action="([^"]+)"[^>]*>(.*?)</form>',
                                   html, re.S):
        if re.search(rf"<button[^>]*>{label}</button>", form):
            return action
    return None


def test_leader_publishes_own_draft_directly_and_it_becomes_published(
        client_as, write_post, take_action, cells):
    leader = client_as("admin")
    url = write_post(leader, title="Watch party del Clásico", topic="fan-club-news").headers["location"]

    response = take_action(leader, url, "publish")

    assert response.status_code == 303
    assert status_in_content_list(leader, "Watch party del Clásico", cells) == "Publicada"


def test_leader_publishes_a_members_post_once_submitted_but_not_while_it_is_their_draft(
        client_as, write_post, take_action, mark_submitted, cells):
    ana, leader = client_as("editor"), client_as("admin")
    url = write_post(ana, title="Crónica del Clásico Regio").headers["location"]

    assert button_form_action(leader.get(url).text, "Publicar") is None
    refused = take_action(leader, url, "publish")
    assert refused.status_code == 403
    assert "No tienes permiso" in refused.text and NOT_SUBMITTED in refused.text
    assert status_in_content_list(leader, "Crónica del Clásico Regio", cells) == "Borrador"

    mark_submitted(url)

    assert (button_form_action(leader.get(url).text, "Publicar") or "").endswith(f"{url}/publish")
    assert take_action(leader, url, "publish").status_code == 303
    assert status_in_content_list(leader, "Crónica del Clásico Regio", cells) == "Publicada"


def test_publishing_sets_first_published_and_locks_the_slug(
        client_as, write_post, take_action, csrf_token, clock):
    leader = client_as("admin")
    url = write_post(leader, title="Crónica del Clásico Regio").headers["location"]
    clock.time = "2026-10-05T01:15:00+00:00"  # 19:15 on the 4th in Monterrey

    assert take_action(leader, url, "publish").status_code == 303

    page = leader.get(url).text
    assert "Publicada por primera vez: 04/10/2026 19:15" in page
    assert 'value="crónica-del-clásico-regio"' in slug_input(page)
    assert "readonly" in slug_input(page)
    refused = leader.post(url, data={"csrf_token": csrf_token(leader, url), "title": "Crónica",
                                     "topic": "match", "body": "Texto", "slug": "otro-enlace"})
    assert refused.status_code == 400
    assert SLUG_LOCKED in refused.text
    assert 'value="crónica-del-clásico-regio"' in slug_input(leader.get(url).text)


def test_leader_renaming_a_published_post_keeps_its_locked_slug(
        client_as, write_post, take_action, csrf_token):
    leader = client_as("admin")
    url = write_post(leader, title="Crónica del Clásico Regio").headers["location"]
    take_action(leader, url, "publish")

    for typed in ("", "crónica-del-clásico-regio"):  # left empty, or sent back unchanged
        saved = leader.post(url, data={"csrf_token": csrf_token(leader, url), "slug": typed,
                                       "title": "Un título nuevo", "topic": "match", "body": ""})
        assert "Cambios guardados." in saved.text
        assert 'value="crónica-del-clásico-regio"' in slug_input(saved.text)


def test_leader_unpublishes_a_published_post_back_to_draft_and_first_published_is_kept(
        client_as, write_post, take_action, clock, cells):
    leader = client_as("admin")
    url = write_post(leader, title="Crónica del Clásico Regio").headers["location"]
    take_action(leader, url, "publish")
    clock.time = "2026-10-06T18:00:00+00:00"

    response = take_action(leader, url, "unpublish")

    assert response.status_code == 303
    assert status_in_content_list(leader, "Crónica del Clásico Regio", cells) == "Borrador"
    page = leader.get(url).text
    assert "Publicada por primera vez: 04/10/2026 12:30" in page
    assert "readonly" in slug_input(page), "the slug stays locked"
    take_action(leader, url, "publish")
    assert "Publicada por primera vez: 04/10/2026 12:30" in leader.get(url).text


def test_leaders_post_page_offers_publicar_on_own_draft_and_despublicar_once_published(
        client_as, write_post, take_action):
    leader = client_as("admin")
    url = write_post(leader).headers["location"]

    draft = leader.get(url).text
    assert (button_form_action(draft, "Publicar") or "").endswith(f"{url}/publish")
    assert button_form_action(draft, "Despublicar") is None
    take_action(leader, url, "publish")
    published = leader.get(url).text
    assert (button_form_action(published, "Despublicar") or "").endswith(f"{url}/unpublish")
    assert button_form_action(published, "Publicar") is None


def test_members_see_no_publicar_or_despublicar_button(
        client_as, write_post, take_action, mark_submitted):
    ana, leader = client_as("editor"), client_as("admin")
    draft_url = write_post(ana, title="Mi borrador").headers["location"]
    published_url = write_post(ana, title="Ya publicada").headers["location"]
    mark_submitted(published_url)
    take_action(leader, published_url, "publish")

    for page in (ana.get(draft_url).text, ana.get(published_url).text):
        assert button_form_action(page, "Publicar") is None
        assert button_form_action(page, "Despublicar") is None


@pytest.mark.parametrize("publish_first, action, message", [
    (True, "publish", "Esta publicación ya está publicada."),
    (False, "unpublish", "Solo se puede despublicar una publicación publicada."),
])
def test_leader_publishing_a_published_post_or_unpublishing_a_draft_is_refused_with_a_message(
        client_as, write_post, take_action, cells, publish_first, action, message):
    leader = client_as("admin")
    url = write_post(leader, title="Crónica del Clásico Regio").headers["location"]
    if publish_first:
        take_action(leader, url, "publish")
    before = status_in_content_list(leader, "Crónica del Clásico Regio", cells)

    response = take_action(leader, url, action)

    assert response.status_code == 400
    assert message in response.text
    assert status_in_content_list(leader, "Crónica del Clásico Regio", cells) == before


def test_member_direct_post_to_publish_or_unpublish_gets_403_and_nothing_changes(
        client_as, write_post, take_action, mark_submitted, cells):
    ana, leader = client_as("editor"), client_as("admin")
    draft_url = write_post(ana, title="Mi borrador").headers["location"]
    published_url = write_post(ana, title="Ya publicada").headers["location"]
    mark_submitted(published_url)
    take_action(leader, published_url, "publish")

    for url, action in ((draft_url, "publish"), (published_url, "unpublish"),
                        (draft_url, "unpublish"), (published_url, "publish")):
        response = take_action(ana, url, action)
        assert response.status_code == 403, f"member {action} on {url}"
        assert "No tienes permiso" in response.text

    assert status_in_content_list(ana, "Mi borrador", cells) == "Borrador"
    assert status_in_content_list(ana, "Ya publicada", cells) == "Publicada"


def test_a_post_created_through_one_app_instance_is_still_there_through_a_new_instance(
        database_path, login, demo_users, write_post, take_action, cells):
    leader = demo_users["admin"]
    first = TestClient(create_app(database_path))
    login(first, leader["email"], leader["password"])
    take_action(first, write_post(first, title="Crónica del Clásico Regio").headers["location"],
                "publish")
    first.close()

    second = TestClient(create_app(database_path))  # a fresh app on the same database file
    login(second, leader["email"], leader["password"])

    assert status_in_content_list(second, "Crónica del Clásico Regio", cells) == "Publicada"
