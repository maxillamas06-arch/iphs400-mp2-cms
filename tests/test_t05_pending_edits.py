"""T05 (#6): members propose edits to published posts; the leader approves them or
sends them back.

Each test name says which acceptance criterion of #6 it covers.
"""
from __future__ import annotations

import re

PUBLISHED = {"title": "Crónica del Clásico Regio", "topic": "match",
             "body": "Ganamos 3-1 en casa."}
PROPOSED = {"title": "Crónica del Clásico, corregida", "topic": "coach",
            "body": "Ganamos 3-1 y el técnico acertó con los cambios."}


def every_file_in(site) -> str:
    """Everything the export wrote, as one text."""
    return "".join(path.read_text() for path in site.rglob("*") if path.is_file())


def section(html: str, label: str) -> str:
    """The HTML inside the page's <section> with this aria-label."""
    match = re.search(rf'<section[^>]*aria-label="{label}"[^>]*>(.*?)</section>', html, re.S)
    assert match, f"no {label} section"
    return match.group(1)


def review_link(html: str) -> str | None:
    """Where the post page's Revisar cambios propuestos link goes, if it has one."""
    match = re.search(r'<a[^>]*href="([^"]+)"[^>]*>Revisar cambios propuestos</a>', html)
    return match.group(1) if match else None


def test_member_saving_changes_to_own_published_post_creates_a_pending_edit_and_the_published_version_is_unchanged_in_console_and_export(
        client_as, published_post, propose_edit, button_action, cells, export):
    ana, leader = client_as("editor"), client_as("admin")
    url = published_post(**PUBLISHED)
    assert (button_action(ana.get(url).text, "Proponer cambios") or "").endswith(
        f"{url}/propose-edit")

    response = propose_edit(ana, url, **PROPOSED)

    assert response.status_code == 303
    mine = ana.get(url).text
    assert "Cambios propuestos. El líder los revisará" in mine
    assert f'value="{PROPOSED["title"]}"' in mine, "the member picks up her proposal"
    assert f'{PROPOSED["body"]}</textarea>' in mine
    page = leader.get(url).text
    assert f'value="{PUBLISHED["title"]}"' in page and f'{PUBLISHED["body"]}</textarea>' in page
    assert ["Crónica del Clásico Regio", "Partido", "Rayada de Corazón", "Publicada"] in [
        row[:4] for row in cells(leader.get("/admin/content").text)]
    site = export()
    assert PUBLISHED["body"] in (site / "posts" / "crónica-del-clásico-regio.html").read_text()
    assert PROPOSED["title"] not in every_file_in(site)
    assert PROPOSED["body"] not in every_file_in(site)


def test_leader_sees_the_published_version_and_the_pending_edit_side_by_side_as_readers_would(
        client_as, published_post, propose_edit):
    ana, leader = client_as("editor"), client_as("admin")
    url = published_post(title="Crónica del Clásico Regio", topic="match",
                         body="Ganamos **3-1** en casa.")
    propose_edit(ana, url, title="Crónica del Clásico, corregida", topic="coach",
                 body="Ganamos 3-1 y el técnico *acertó*.")
    assert (review_link(leader.get(url).text) or "").endswith(f"{url}/pending-edit")

    response = leader.get(f"{url}/pending-edit")

    assert response.status_code == 200
    assert "Rayada de Corazón" in response.text
    published = section(response.text, "Versión publicada")
    assert "Crónica del Clásico Regio" in published and "Partido" in published
    assert "<strong>3-1</strong>" in published
    proposed = section(response.text, "Cambios propuestos")
    assert "Crónica del Clásico, corregida" in proposed and "Técnico" in proposed
    assert "<em>acertó</em>" in proposed


def test_member_saving_again_replaces_the_pending_edit_so_a_post_has_at_most_one(
        client_as, published_post, propose_edit):
    ana, leader = client_as("editor"), client_as("admin")
    url = published_post(**PUBLISHED)
    propose_edit(ana, url, title="Primera propuesta", body="Primer texto propuesto.")

    propose_edit(ana, url, title="Segunda propuesta", body="Segundo texto propuesto.")

    review = leader.get(f"{url}/pending-edit").text
    proposed = section(review, "Cambios propuestos")
    assert "Segunda propuesta" in proposed and "Segundo texto propuesto." in proposed
    assert "Primera propuesta" not in review and "Primer texto propuesto." not in review
    assert 'value="Segunda propuesta"' in ana.get(url).text


def test_leader_approves_and_the_edit_replaces_title_topic_and_body_and_the_next_export_shows_actualizado_el(
        client_as, published_post, propose_edit, take_action, button_action, status_of, export,
        clock):
    ana, leader = client_as("editor"), client_as("admin")
    url = published_post(day=4, **PUBLISHED)
    propose_edit(ana, url, **PROPOSED)
    assert "Actualizado el" not in every_file_in(export())
    assert (button_action(leader.get(f"{url}/pending-edit").text, "Aprobar cambios") or "").endswith(
        f"{url}/pending-edit/approve")
    clock.time = "2026-10-07T18:00:00+00:00"  # noon on the 7th in Monterrey

    response = take_action(leader, url, "pending-edit/approve")

    assert response.status_code == 303
    assert leader.get(f"{url}/pending-edit").status_code == 404, "the pending edit is gone"
    page = leader.get(url).text
    assert f'value="{PROPOSED["title"]}"' in page and f'{PROPOSED["body"]}</textarea>' in page
    assert review_link(page) is None
    assert status_of(leader, PROPOSED["title"]) == "Publicada"
    post = (export() / "posts" / "crónica-del-clásico-regio.html").read_text()
    assert f"<h1>{PROPOSED['title']}</h1>" in post and PROPOSED["body"] in post
    assert ">Técnico</a>" in post
    assert "Publicado el 4 de octubre de 2026" in post
    assert "Actualizado el 7 de octubre de 2026" in post


def test_a_pending_edit_never_changes_the_slug(
        client_as, published_post, propose_edit, take_action, button_action, export):
    ana, leader = client_as("editor"), client_as("admin")
    url = published_post(**PUBLISHED)

    refused = propose_edit(ana, url, **PROPOSED, slug="crónica-corregida")

    assert refused.status_code == 400
    assert "El enlace ya no se puede cambiar" in refused.text
    assert (button_action(refused.text, "Proponer cambios") or "").endswith(f"{url}/propose-edit")
    assert leader.get(f"{url}/pending-edit").status_code == 404, "nothing was proposed"
    # The editor sends the locked slug back as it shows it; the new title makes no new slug.
    propose_edit(ana, url, **PROPOSED, slug="crónica-del-clásico-regio")
    take_action(leader, url, "pending-edit/approve")
    assert [path.name for path in (export() / "posts").iterdir()] == [
        "crónica-del-clásico-regio.html"]


def test_leader_sends_back_the_pending_edit_and_the_published_version_stays_untouched(
        client_as, published_post, propose_edit, take_action, button_action, export):
    ana, leader = client_as("editor"), client_as("admin")
    url = published_post(**PUBLISHED)
    propose_edit(ana, url, **PROPOSED)
    assert (button_action(leader.get(f"{url}/pending-edit").text, "Devolver los cambios")
            or "").endswith(f"{url}/pending-edit/send-back")

    response = take_action(leader, url, "pending-edit/send-back")

    assert response.status_code == 303
    assert leader.get(f"{url}/pending-edit").status_code == 404, "the pending edit is gone"
    page = leader.get(url).text
    assert f'value="{PUBLISHED["title"]}"' in page and f'{PUBLISHED["body"]}</textarea>' in page
    assert review_link(page) is None
    assert f'value="{PUBLISHED["title"]}"' in ana.get(url).text, "her editor shows the published version again"
    site = export()
    post = (site / "posts" / "crónica-del-clásico-regio.html").read_text()
    assert PUBLISHED["body"] in post and "Actualizado el" not in post
    assert PROPOSED["title"] not in every_file_in(site)


def test_unpublishing_a_post_with_a_pending_edit_is_refused_with_a_message(
        client_as, published_post, propose_edit, take_action, button_action, status_of):
    ana, leader = client_as("editor"), client_as("admin")
    url = published_post(**PUBLISHED)
    propose_edit(ana, url, **PROPOSED)
    assert button_action(leader.get(url).text, "Despublicar") is None

    response = take_action(leader, url, "unpublish")

    assert response.status_code == 400
    assert "No se puede despublicar mientras haya cambios propuestos sin revisar" in response.text
    assert status_of(leader, PUBLISHED["title"]) == "Publicada"
    assert leader.get(f"{url}/pending-edit").status_code == 200, "the pending edit still waits"
    take_action(leader, url, "pending-edit/send-back")
    assert take_action(leader, url, "unpublish").status_code == 303, "answered, it can go"


def test_leaders_direct_edit_of_a_published_post_saves_immediately_and_marks_it_as_edited_after_publishing(
        client_as, published_post, write_post, take_action, csrf_token, export, clock):
    leader = client_as("admin")
    url = published_post(day=4, **PUBLISHED)
    draft = write_post(leader, title="Watch party del Clásico", topic="fan-club-news").headers["location"]
    clock.time = "2026-10-06T18:00:00+00:00"  # noon on the 6th in Monterrey

    saved = leader.post(url, data={"csrf_token": csrf_token(leader, url), **PROPOSED})
    leader.post(draft, data={"csrf_token": csrf_token(leader, draft),
                             "title": "Watch party del Clásico", "topic": "fan-club-news",
                             "body": "Cambiado cuando todavía era borrador."})
    take_action(leader, draft, "publish")

    assert "Cambios guardados." in saved.text
    assert leader.get(f"{url}/pending-edit").status_code == 404, "saved, not proposed"
    site = export()
    post = (site / "posts" / "crónica-del-clásico-regio.html").read_text()
    assert f"<h1>{PROPOSED['title']}</h1>" in post and PROPOSED["body"] in post
    assert "Publicado el 4 de octubre de 2026 · Actualizado el 6 de octubre de 2026" in post
    assert "Actualizado el" not in (site / "posts" / "watch-party-del-clásico.html").read_text()


def test_members_cannot_approve_send_back_or_propose_edits_to_another_members_post_direct_posts_get_403(
        client_as, published_post, write_post, propose_edit, take_action, button_action,
        csrf_token):
    ana, beto, leader = client_as("editor"), client_as("editor2"), client_as("admin")
    url = published_post(**PUBLISHED)  # Ana's
    propose_edit(ana, url, **PROPOSED)

    for member in (ana, beto):
        assert member.get(f"{url}/pending-edit").status_code == 403
        assert review_link(member.get(url).text) is None
        for action in ("pending-edit/approve", "pending-edit/send-back"):
            response = take_action(member, url, action)
            assert response.status_code == 403, f"member {action}"
            assert "No tienes permiso" in response.text
    assert button_action(beto.get(url).text, "Proponer cambios") is None
    refused = propose_edit(beto, url, title="Hackeado", body="Otro texto.")
    assert refused.status_code == 403 and "No tienes permiso" in refused.text
    # Ana's own post: published, she proposes; she never saves it directly.
    direct = ana.post(url, data={"csrf_token": csrf_token(ana, url), **PROPOSED, "title": "Directo"})
    assert direct.status_code == 403
    draft = write_post(ana, title="Mi borrador").headers["location"]
    assert propose_edit(ana, draft).status_code == 403, "a draft is saved, not proposed"

    proposed = section(leader.get(f"{url}/pending-edit").text, "Cambios propuestos")
    assert PROPOSED["title"] in proposed
    assert "Hackeado" not in proposed and "Directo" not in proposed


def test_pending_edits_never_appear_in_the_export_not_even_under_their_proposed_topic(
        client_as, published_post, propose_edit, export):
    ana = client_as("editor")
    url = published_post(**PUBLISHED)  # filed under Partido
    propose_edit(ana, url, **PROPOSED)  # would move it to Técnico

    site = export()

    assert PUBLISHED["title"] in (site / "tema" / "partido.html").read_text()
    assert PUBLISHED["title"] not in (site / "tema" / "técnico.html").read_text()
    assert PROPOSED["title"] not in every_file_in(site)
    assert PROPOSED["body"] not in every_file_in(site)


def test_deleting_a_post_deletes_its_pending_edit(
        client_as, published_post, propose_edit, csrf_token, dashboard_counts):
    ana, leader = client_as("editor"), client_as("admin")
    url = published_post(**PUBLISHED)
    propose_edit(ana, url, **PROPOSED)
    assert dashboard_counts(leader)["Cambios propuestos"][0] == "1"

    response = leader.post(f"{url}/delete", data={"csrf_token": csrf_token(leader, url)},
                           follow_redirects=False)

    assert response.status_code == 303
    assert leader.get(url).status_code == 404
    assert dashboard_counts(leader)["Cambios propuestos"][0] == "0"


def test_member_previews_changes_to_own_published_post_without_proposing_them(
        client_as, published_post, csrf_token, dashboard_counts):
    ana, leader = client_as("editor"), client_as("admin")
    url = published_post(**PUBLISHED)

    response = ana.post(f"{url}/preview", data={"csrf_token": csrf_token(ana, url), **PROPOSED,
                                                "body": "Ganamos **3-1** <script>x()</script>"})

    assert response.status_code == 200
    preview = section(response.text, "Vista previa")
    assert "<strong>3-1</strong>" in preview and "<script" not in preview
    assert dashboard_counts(leader)["Cambios propuestos"][0] == "0", "nothing was proposed"
