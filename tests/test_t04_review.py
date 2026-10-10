"""T04 (#5): members submit and withdraw posts; the leader works the review queue.

Each test name says which acceptance criterion of #5 it covers.
"""
from __future__ import annotations

import pytest

NOT_THE_AUTHOR = "Solo el miembro que escribió esta publicación puede enviarla o retirarla."


def test_member_submits_own_draft_and_it_becomes_submitted(
        client_as, write_post, take_action, button_action, status_of):
    ana = client_as("editor")
    url = write_post(ana, title="Crónica del Clásico Regio").headers["location"]
    assert (button_action(ana.get(url).text, "Enviar para revisión") or "").endswith(f"{url}/submit")

    response = take_action(ana, url, "submit")

    assert response.status_code == 303
    assert status_of(ana, "Crónica del Clásico Regio") == "Enviada"


def test_member_withdraws_own_submitted_post_back_to_draft_and_can_edit_it_again(
        client_as, write_post, take_action, button_action, status_of):
    ana = client_as("editor")
    url = write_post(ana, title="Crónica del Clásico Regio").headers["location"]
    take_action(ana, url, "submit")
    assert (button_action(ana.get(url).text, "Retirar") or "").endswith(f"{url}/withdraw")

    response = take_action(ana, url, "withdraw")

    assert response.status_code == 303
    assert status_of(ana, "Crónica del Clásico Regio") == "Borrador"
    page = ana.get(url).text
    assert "<textarea" in page, "the member's editor is back"
    assert button_action(page, "Enviar para revisión"), "and the draft can be submitted again"


def test_member_cannot_edit_own_submitted_post_directly_403_until_they_withdraw_it(
        client_as, write_post, take_action, csrf_token):
    ana = client_as("editor")
    url = write_post(ana, title="Crónica del Clásico Regio", body="Original").headers["location"]
    take_action(ana, url, "submit")
    edit = {"title": "Crónica cambiada", "topic": "match", "body": "Cambiado"}

    assert "<textarea" not in ana.get(url).text
    for path in (url, f"{url}/preview", f"{url}/delete"):
        refused = ana.post(path, data={"csrf_token": csrf_token(ana), **edit})
        assert refused.status_code == 403, path
        assert "No tienes permiso" in refused.text
    assert "<h1>Crónica del Clásico Regio</h1>" in ana.get(url).text

    take_action(ana, url, "withdraw")
    saved = ana.post(url, data={"csrf_token": csrf_token(ana), **edit})

    assert "Cambios guardados." in saved.text
    assert "<h1>Crónica cambiada</h1>" in saved.text


@pytest.mark.parametrize("submit_first, action, message", [
    (True, "submit", "Solo se puede enviar un borrador."),
    (False, "withdraw", "Solo se puede retirar una publicación enviada."),
])
def test_member_submitting_twice_or_withdrawing_a_draft_is_refused_with_a_message(
        client_as, write_post, take_action, status_of, submit_first, action, message):
    ana = client_as("editor")
    url = write_post(ana, title="Crónica del Clásico Regio").headers["location"]
    if submit_first:
        take_action(ana, url, "submit")
    before = status_of(ana, "Crónica del Clásico Regio")

    response = take_action(ana, url, action)

    assert response.status_code == 400
    assert message in response.text
    assert status_of(ana, "Crónica del Clásico Regio") == before
    if before == "Enviada":
        assert "<textarea" not in response.text, "no editor for a post the member cannot change"


def test_only_the_member_who_wrote_it_submits_or_withdraws_it_others_get_403(
        client_as, write_post, take_action, button_action, status_of):
    ana, beto, leader = client_as("editor"), client_as("editor2"), client_as("admin")
    draft = write_post(ana, title="Mi borrador").headers["location"]
    submitted = write_post(ana, title="Mi enviada").headers["location"]
    take_action(ana, submitted, "submit")

    for c in (beto, leader):
        assert button_action(c.get(draft).text, "Enviar para revisión") is None
        assert button_action(c.get(submitted).text, "Retirar") is None
        for url, action in ((draft, "submit"), (submitted, "withdraw")):
            response = take_action(c, url, action)
            assert response.status_code == 403, f"{action} by someone else"
            assert NOT_THE_AUTHOR in response.text

    assert status_of(ana, "Mi borrador") == "Borrador"
    assert status_of(ana, "Mi enviada") == "Enviada"


def test_leader_publishes_a_submitted_post_or_sends_it_back_to_draft(
        client_as, write_post, take_action, button_action, status_of):
    ana, leader = client_as("editor"), client_as("admin")
    to_publish = write_post(ana, title="Crónica para publicar").headers["location"]
    to_send_back = write_post(ana, title="Crónica para devolver").headers["location"]
    for url in (to_publish, to_send_back):
        take_action(ana, url, "submit")
    page = leader.get(to_send_back).text
    assert (button_action(page, "Publicar") or "").endswith(f"{to_send_back}/publish")
    assert (button_action(page, "Devolver a borrador") or "").endswith(f"{to_send_back}/send-back")

    assert take_action(leader, to_publish, "publish").status_code == 303
    sent_back = take_action(leader, to_send_back, "send-back")

    assert sent_back.status_code == 303
    assert status_of(leader, "Crónica para publicar") == "Publicada"
    assert status_of(leader, "Crónica para devolver") == "Borrador"
    assert "<textarea" in ana.get(to_send_back).text, "its member can rework it"


@pytest.mark.parametrize("publish_first", [False, True])
def test_leader_sending_back_a_post_that_is_not_submitted_is_refused_with_a_message(
        client_as, write_post, take_action, status_of, publish_first):
    leader = client_as("admin")
    url = write_post(leader, title="Watch party del Clásico").headers["location"]
    if publish_first:
        take_action(leader, url, "publish")
    before = status_of(leader, "Watch party del Clásico")

    response = take_action(leader, url, "send-back")

    assert response.status_code == 400
    assert "Solo se puede devolver una publicación enviada." in response.text
    assert status_of(leader, "Watch party del Clásico") == before


def test_members_direct_post_to_publish_or_send_back_gets_403_even_on_their_own_submitted_post(
        client_as, write_post, take_action, button_action, status_of):
    ana, beto = client_as("editor"), client_as("editor2")
    url = write_post(ana, title="Crónica del Clásico Regio").headers["location"]
    take_action(ana, url, "submit")

    for member in (ana, beto):
        page = member.get(url).text
        assert button_action(page, "Publicar") is None
        assert button_action(page, "Devolver a borrador") is None
        for action in ("publish", "send-back"):
            response = take_action(member, url, action)
            assert response.status_code == 403, f"member {action}"
            assert "No tienes permiso" in response.text

    assert status_of(ana, "Crónica del Clásico Regio") == "Enviada"


def test_submitted_posts_never_appear_in_the_export(
        client_as, write_post, take_action, published_post, export):
    ana = client_as("editor")
    url = write_post(ana, title="Crónica en revisión",
                     body="Texto que el líder todavía no revisa.").headers["location"]
    take_action(ana, url, "submit")
    published_post(title="Crónica publicada")

    site = export()

    files = {path.relative_to(site).as_posix(): path.read_text()
             for path in site.rglob("*") if path.is_file()}
    assert [path for path in files if path.startswith("posts/")] == ["posts/crónica-publicada.html"]
    for path, html in files.items():
        assert "Crónica en revisión" not in html, f"a submitted post's title reached {path}"
        assert "Texto que el líder todavía no revisa." not in html, f"its body reached {path}"


def test_the_leader_does_not_submit_his_own_draft_direct_post_gets_403_he_publishes_it(
        client_as, write_post, take_action, button_action, status_of):
    leader = client_as("admin")
    url = write_post(leader, title="Watch party del Clásico", topic="fan-club-news").headers["location"]
    assert button_action(leader.get(url).text, "Enviar para revisión") is None

    response = take_action(leader, url, "submit")

    assert response.status_code == 403
    assert NOT_THE_AUTHOR in response.text
    assert status_of(leader, "Watch party del Clásico") == "Borrador"
