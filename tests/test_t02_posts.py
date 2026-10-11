"""T02 (#3): members write draft posts, and only change their own.

Each test name says which acceptance criterion of #3 it covers.
"""
from __future__ import annotations

import re
import unicodedata

import pytest

NOT_YOURS = "Solo puedes cambiar o borrar tus propios borradores."
SLUG_REFUSED = "El enlace solo puede tener letras minúsculas, números y guiones sueltos"


def field(html: str, name: str) -> str:
    """The value of the editor's input with this name."""
    match = re.search(rf'<input[^>]*name="{name}"[^>]*value="([^"]*)"', html)
    assert match, f"no {name} field"
    return match.group(1)


def preview_button(html: str) -> str:
    """Where the editor's Vista previa button sends the form."""
    match = re.search(r'<button[^>]*formaction="([^"]+)"[^>]*>Vista previa</button>', html)
    assert match, "no Vista previa button"
    return match.group(1)


def preview(html: str) -> str:
    """The HTML inside the Vista previa section."""
    match = re.search(r'<section[^>]*aria-label="Vista previa"[^>]*>(.*?)</section>', html, re.S)
    assert match, "no Vista previa section"
    return match.group(1)


def form_actions(html: str) -> list[str]:
    """Where the page's POST forms send, leaving out the menu's Salir form."""
    return [action for action in re.findall(r'<form[^>]*method="post"[^>]*action="([^"]+)"', html)
            if not action.endswith("/logout")]


def test_member_creates_post_saved_as_draft_with_member_as_author_and_timestamps(
        client_as, write_post, clock, cells):
    member = client_as("editor")

    response = write_post(member, title="Crónica del Clásico Regio", topic="match",
                          body="Ganamos **3-1** en casa.")

    assert response.status_code == 303
    page = member.get(response.headers["location"]).text
    assert 'value="Crónica del Clásico Regio"' in page
    assert '<option value="match" selected>Partido</option>' in page
    assert "Ganamos **3-1** en casa.</textarea>" in page
    assert "Creada: 04/10/2026 12:30" in page
    assert "Última actualización: 04/10/2026 12:30" in page
    rows = cells(member.get("/admin/content").text)
    assert ["Crónica del Clásico Regio", "Partido", "Rayada de Corazón", "Borrador",
            "04/10/2026 12:30"] in rows


def test_unknown_post_id_gets_404_spanish_page_that_keeps_admin_menu(client_as, csrf_token):
    member = client_as("editor")

    for response in (member.get("/admin/posts/999"), member.get("/admin/posts/abc"),
                     member.post("/admin/posts/999", data={"csrf_token": csrf_token(member)})):
        assert response.status_code == 404
        assert "No encontramos esa publicación" in response.text
        assert 'aria-label="Menú de administración"' in response.text


@pytest.mark.parametrize("title, slug", [
    ("Crónica del Clásico Regio", "crónica-del-clásico-regio"),
    (unicodedata.normalize("NFD", "Crónica del Clásico Regio"), "crónica-del-clásico-regio"),
    ("¡Año 2026: la Pandilla, otra vez!", "año-2026-la-pandilla-otra-vez"),
    ("  Güero --  y   Peña_  ", "güero-y-peña"),
    ("x" * 79 + " y más", "x" * 79),  # capped at 80, never ending in a hyphen
    ("⚽ ⚽ ⚽", "publicación"),         # no letters or digits at all
])
def test_slug_is_generated_from_title_nfc_normalized_keeping_accents_and_ñ(
        client_as, write_post, title, slug):
    member = client_as("editor")

    page = member.get(write_post(member, title=title).headers["location"]).text

    assert field(page, "slug") == slug


def test_taken_slug_gets_2_then_3_whoever_wrote_the_first(client_as, write_post):
    ana, beto = client_as("editor"), client_as("editor2")

    slugs = [field(c.get(write_post(c, title="Crónica del Clásico Regio")
                         .headers["location"]).text, "slug") for c in (ana, beto, ana)]

    assert slugs == ["crónica-del-clásico-regio", "crónica-del-clásico-regio-2",
                     "crónica-del-clásico-regio-3"]


def test_numbered_slug_still_fits_in_80_characters(client_as, write_post):
    member = client_as("editor")

    slugs = [field(member.get(write_post(member, title="x" * 100).headers["location"]).text,
                   "slug") for _ in range(2)]

    assert slugs == ["x" * 80, "x" * 78 + "-2"]


def test_member_saves_own_draft_and_edits_its_slug_while_never_published(
        client_as, write_post, csrf_token, clock):
    member = client_as("editor")
    url = write_post(member, title="Crónica del Clásico Regio").headers["location"]
    clock.time = "2026-10-05T01:15:00+00:00"  # 19:15 on the 4th in Monterrey

    response = member.post(url, data={
        "csrf_token": csrf_token(member), "title": "El Clásico Regio 120", "topic": "coach",
        "body": "Ganamos **otra vez**.", "slug": "clásico-120"}, follow_redirects=False)

    assert response.status_code == 303
    page = member.get(url).text
    assert field(page, "title") == "El Clásico Regio 120"
    assert field(page, "slug") == "clásico-120"
    assert '<option value="coach" selected>Técnico</option>' in page
    assert "Ganamos **otra vez**.</textarea>" in page
    assert "Borrador" in page
    assert "Creada: 04/10/2026 12:30" in page
    assert "Última actualización: 04/10/2026 19:15" in page


def test_a_taken_manual_slug_gets_a_number_and_the_message_says_so(
        client_as, write_post, csrf_token):
    ana = client_as("editor")
    write_post(ana, title="Uno")
    url = write_post(ana, title="Dos").headers["location"]

    saved = ana.post(url, data={"csrf_token": csrf_token(ana), "title": "Dos", "topic": "match",
                                "body": "", "slug": "uno"})
    created = ana.get(write_post(ana, title="Tres", slug="uno").headers["location"])

    taken = "El enlace «uno» ya era de otra publicación"
    assert field(saved.text, "slug") == "uno-2"
    assert f"Cambios guardados. {taken}: quedó «uno-2»." in saved.text
    assert field(created.text, "slug") == "uno-3"
    assert f"Borrador guardado. {taken}: quedó «uno-3»." in created.text


@pytest.mark.parametrize("slug", ["Con-Mayúsculas", "con espacios", "-guion-al-principio",
                                  "doble--guion", "signos!", "x" * 81])
def test_invalid_manual_slug_is_refused_with_a_message_and_nothing_changes(
        client_as, write_post, csrf_token, slug):
    member = client_as("editor")
    url = write_post(member, title="Crónica del Clásico Regio").headers["location"]

    response = member.post(url, data={"csrf_token": csrf_token(member), "slug": slug,
                                      "title": "Otro título", "topic": "match", "body": ""})

    assert response.status_code == 400
    assert SLUG_REFUSED in response.text
    assert field(response.text, "title") == "Otro título"  # what they typed is kept
    page = member.get(url).text
    assert field(page, "slug") == "crónica-del-clásico-regio"
    assert field(page, "title") == "Crónica del Clásico Regio"


def test_invalid_manual_slug_on_a_new_post_is_refused_and_nothing_is_created(
        client_as, write_post):
    member = client_as("editor")

    response = write_post(member, title="Crónica del Clásico Regio", slug="Mal Enlace")

    assert response.status_code == 400
    assert SLUG_REFUSED in response.text
    assert "Crónica del Clásico Regio" not in member.get("/admin/content").text


def test_vista_previa_renders_markdown_below_the_form_without_saving_a_new_post(
        client_as, csrf_token):
    member = client_as("editor")
    button = preview_button(member.get("/admin/posts/new").text)

    response = member.post(button, data={
        "csrf_token": csrf_token(member), "title": "Previa del Clásico", "topic": "match",
        "slug": "", "body": "Ganamos **3-1** y _bailamos_."})

    assert response.status_code == 200
    html = response.text
    assert html.index("</form>") < html.index('aria-label="Vista previa"')
    assert "<strong>3-1</strong>" in preview(html) and "<em>bailamos</em>" in preview(html)
    assert field(html, "title") == "Previa del Clásico"
    assert "Previa del Clásico" not in member.get("/admin/content").text


def test_vista_previa_of_an_existing_draft_does_not_save_it(client_as, write_post, csrf_token):
    member = client_as("editor")
    url = write_post(member, title="Crónica del Clásico Regio",
                     body="Original").headers["location"]
    button = preview_button(member.get(url).text)

    response = member.post(button, data={
        "csrf_token": csrf_token(member), "title": "Título nuevo", "topic": "match",
        "slug": "", "body": "Cambiado **ya**"})

    assert response.status_code == 200
    assert "<strong>ya</strong>" in preview(response.text)
    page = member.get(url).text
    assert "Original</textarea>" in page and field(page, "title") == "Crónica del Clásico Regio"


@pytest.mark.parametrize("body, removed", [
    ("Hola <script>alert('rayados')</script> mundo", ["<script", "alert("]),
    ('<img src="x" onerror="alert(1)">', ["onerror", "<img"]),
    ('<p onclick="alert(1)">hola</p>', ["onclick"]),
    ('<a href="javascript:alert(1)">clic</a>', ["javascript:"]),
    ("![foto del estadio](https://example.com/estadio.jpg)", ["<img", "estadio.jpg"]),
])
def test_vista_previa_removes_scripts_event_handlers_javascript_links_and_images(
        client_as, csrf_token, body, removed):
    member = client_as("editor")

    response = member.post("/admin/posts/new/preview", data={
        "csrf_token": csrf_token(member), "title": "Prueba", "topic": "match", "body": body})

    assert response.status_code == 200
    shown = preview(response.text)
    for unsafe in removed:
        assert unsafe not in shown
    assert "<script" not in response.text


def test_vista_previa_drops_root_absolute_links_so_published_html_stays_relative(
        client_as, csrf_token):
    member = client_as("editor")

    response = member.post("/admin/posts/new/preview", data={
        "csrf_token": csrf_token(member), "title": "Prueba", "topic": "match",
        "body": "Ver [el panel](/admin) y [otro sitio](//example.com/x)."})

    shown = preview(response.text)
    assert 'href="/' not in shown
    assert "el panel" in shown and "otro sitio" in shown


def test_vista_previa_keeps_links_and_opens_them_with_noopener_noreferrer(client_as, csrf_token):
    member = client_as("editor")

    response = member.post("/admin/posts/new/preview", data={
        "csrf_token": csrf_token(member), "title": "Prueba", "topic": "match",
        "body": "Lean [la crónica](https://example.com/cronica)."})

    assert ('<a href="https://example.com/cronica" rel="noopener noreferrer">la crónica</a>'
            in preview(response.text))


@pytest.mark.parametrize("token", [None, "forged-token"])
def test_vista_previa_post_without_a_valid_csrf_token_gets_403(client_as, write_post, token):
    member = client_as("editor")
    url = write_post(member).headers["location"]
    data = {"title": "Prueba", "topic": "match", "body": "**hola**"}
    if token is not None:
        data["csrf_token"] = token

    for path in ("/admin/posts/new/preview", f"{url}/preview"):
        response = member.post(path, data=data)
        assert response.status_code == 403, path
        assert "Formulario caducado" in response.text
        assert "<strong>hola</strong>" not in response.text


def test_content_list_shows_every_post_from_every_author_with_topic_nickname_status_and_update(
        client_as, write_post, clock, cells):
    ana, beto, leader = client_as("editor"), client_as("editor2"), client_as("admin")
    write_post(ana, title="Crónica del Clásico Regio", topic="match")
    clock.time = "2026-10-05T02:00:00+00:00"  # 20:00 on the 4th in Monterrey
    write_post(beto, title="El once para el sábado", topic="lineup")
    write_post(leader, title="Watch party en la Fundidora", topic="fan-club-news")

    for viewer in (ana, beto, leader):
        rows = cells(viewer.get("/admin/content").text)
        assert ["Crónica del Clásico Regio", "Partido", "Rayada de Corazón", "Borrador",
                "04/10/2026 12:30"] in rows
        assert ["El once para el sábado", "Alineación", "Furia del Cerro", "Borrador",
                "04/10/2026 20:00"] in rows
        assert ["Watch party en la Fundidora", "Noticias del club de aficionados", "El Capi",
                "Borrador", "04/10/2026 20:00"] in rows


def test_member_opens_another_members_post_read_only(client_as, write_post):
    ana, beto = client_as("editor"), client_as("editor2")
    url = write_post(ana, title="Crónica del Clásico Regio", topic="match",
                     body="Ganamos **3-1** en casa.").headers["location"]

    response = beto.get(url)

    assert response.status_code == 200
    html = response.text
    assert "<h1>Crónica del Clásico Regio</h1>" in html
    assert "Rayada de Corazón" in html and "Partido" in html and "Borrador" in html
    assert "<strong>3-1</strong>" in html  # the body as readers would see it
    assert form_actions(html) == []
    assert "Guardar" not in html and "Borrar" not in html and "<textarea" not in html


def test_member_direct_post_to_save_or_preview_another_members_post_gets_403(
        client_as, write_post, csrf_token):
    ana, beto = client_as("editor"), client_as("editor2")
    url = write_post(ana, title="Crónica del Clásico Regio", body="Original").headers["location"]

    for path in (url, f"{url}/preview"):
        response = beto.post(path, data={"csrf_token": csrf_token(beto), "title": "Hackeado",
                                         "topic": "coach", "body": "Otro", "slug": "hackeado"})
        assert response.status_code == 403, path
        assert "No tienes permiso" in response.text and NOT_YOURS in response.text
        assert "solo para el líder" not in response.text

    page = ana.get(url).text
    assert field(page, "title") == "Crónica del Clásico Regio"
    assert field(page, "slug") == "crónica-del-clásico-regio"
    assert "Original</textarea>" in page


def test_leader_edits_any_members_post(client_as, write_post, csrf_token):
    ana, leader = client_as("editor"), client_as("admin")
    url = write_post(ana, body="Ganamos 3-1.").headers["location"]
    assert "Ganamos 3-1.</textarea>" in leader.get(url).text

    response = leader.post(url, data={
        "csrf_token": csrf_token(leader), "title": "Crónica del Clásico", "topic": "match",
        "body": "Ganamos 3-1 (typo corregido).", "slug": "crónica-del-clásico-regio"},
        follow_redirects=False)

    assert response.status_code == 303
    page = ana.get(url).text
    assert field(page, "title") == "Crónica del Clásico"
    assert "Ganamos 3-1 (typo corregido).</textarea>" in page
    assert "Rayada de Corazón" in page  # still Ana's post


def test_member_can_only_read_their_own_post_once_it_is_submitted(
        client_as, write_post, take_action, csrf_token):
    # Once published, the member proposes an edit instead: T05 (#6).
    ana = client_as("editor")
    url = write_post(ana, title="Crónica del Clásico Regio", body="Original").headers["location"]
    take_action(ana, url, "submit")

    assert "<textarea" not in ana.get(url).text
    response = ana.post(url, data={"csrf_token": csrf_token(ana), "title": "Cambiado",
                                   "topic": "match", "body": "Cambiado"})
    assert response.status_code == 403
    assert NOT_YOURS in response.text
    assert "<h1>Crónica del Clásico Regio</h1>" in ana.get(url).text


@pytest.mark.parametrize("deleter", ["editor", "admin"])  # the author; the leader
def test_deleting_asks_for_confirmation_on_a_separate_step_then_the_post_is_gone(
        client_as, write_post, csrf_token, deleter):
    ana = client_as("editor")
    url = write_post(ana, title="Crónica del Clásico Regio").headers["location"]
    c = ana if deleter == "editor" else client_as("admin")
    delete_link = re.search(r'<a[^>]*href="([^"]+)"[^>]*>Borrar</a>', c.get(url).text)
    assert delete_link, "the editor has a Borrar link"

    confirmation = c.get(delete_link.group(1))

    assert confirmation.status_code == 200
    assert "¿Borrar «Crónica del Clásico Regio»?" in confirmation.text
    assert ana.get(url).status_code == 200, "opening the confirmation deletes nothing"
    [action] = form_actions(confirmation.text)
    response = c.post(action, data={"csrf_token": csrf_token(c, delete_link.group(1))},
                      follow_redirects=False)
    assert response.status_code == 303
    assert ana.get(url).status_code == 404
    assert "Crónica del Clásico Regio" not in ana.get("/admin/content").text


def test_member_direct_request_to_delete_another_members_post_gets_403_and_it_stays(
        client_as, write_post, csrf_token):
    ana, beto = client_as("editor"), client_as("editor2")
    url = write_post(ana, title="Crónica del Clásico Regio").headers["location"]

    for response in (beto.get(f"{url}/delete"),
                     beto.post(f"{url}/delete", data={"csrf_token": csrf_token(beto)})):
        assert response.status_code == 403
        assert NOT_YOURS in response.text
    assert ana.get(url).status_code == 200


def test_every_save_and_delete_shows_a_message_once(client_as, write_post, csrf_token):
    ana = client_as("editor")

    url = write_post(ana).headers["location"]
    assert "Borrador guardado." in ana.get(url).text
    assert "Borrador guardado." not in ana.get(url).text, "shown once, not on every visit"

    # The test client follows the redirect, so .text is the page the person lands on.
    saved = ana.post(url, data={"csrf_token": csrf_token(ana), "title": "Crónica",
                                "topic": "match", "body": "Texto"})
    assert saved.url.path == url and "Cambios guardados." in saved.text

    deleted = ana.post(f"{url}/delete", data={"csrf_token": csrf_token(ana)})
    assert deleted.url.path == "/admin/content" and "Publicación borrada." in deleted.text


@pytest.mark.parametrize("title, topic, message", [
    ("", "match", "Escribe un título."),
    ("   ", "match", "Escribe un título."),
    ("Crónica del Clásico Regio", "", "Elige uno de los cinco temas."),
    ("Crónica del Clásico Regio", "basquetbol", "Elige uno de los cinco temas."),
])
def test_missing_title_or_topic_is_refused_with_a_message_and_nothing_is_saved(
        client_as, write_post, csrf_token, cells, title, topic, message):
    ana = client_as("editor")
    url = write_post(ana, title="Original", topic="coach").headers["location"]

    created = write_post(ana, title=title, topic=topic, body="Nuevo texto")
    saved = ana.post(url, data={"csrf_token": csrf_token(ana), "title": title, "topic": topic,
                                "body": "Nuevo texto"})

    for response in (created, saved):
        assert response.status_code == 400
        assert message in response.text
    assert "Nuevo texto" not in ana.get("/admin/content").text
    assert field(ana.get(url).text, "title") == "Original"
    assert len(cells(ana.get("/admin/content").text)) == 2  # header row + the original


@pytest.mark.parametrize("status", ["submitted", "published"])
def test_leader_edits_any_post_whatever_its_status(
        client_as, write_post, take_action, csrf_token, status):
    ana, leader = client_as("editor"), client_as("admin")
    url = write_post(ana, title="Crónica del Clásico Regio").headers["location"]
    take_action(ana, url, "submit")
    if status == "published":
        take_action(leader, url, "publish")
    assert ">Guardar cambios</button>" in leader.get(url).text

    saved = leader.post(url, data={"csrf_token": csrf_token(leader), "topic": "match",
                                   "title": "Crónica corregida", "body": "Sin typos."})

    assert "Cambios guardados." in saved.text
    assert "<h1>Crónica corregida</h1>" in ana.get(url).text
