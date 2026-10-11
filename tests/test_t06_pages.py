"""T06 (#7): the leader writes the fan club's pages; members never see them.

Each test name says which acceptance criterion of #7 it covers.
"""
from __future__ import annotations

import re

import pytest

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


def test_leader_creates_page_saved_as_draft_with_title_slug_body_menu_order_author_and_timestamps(
        client_as, write_page, clock):
    leader = client_as("admin")

    response = write_page(leader, title="Quiénes somos", body="Somos **aficionados**.",
                          menu_order="2")

    assert response.status_code == 303
    page = leader.get(response.headers["location"]).text
    assert field(page, "title") == "Quiénes somos"
    assert field(page, "slug") == "quiénes-somos"
    assert field(page, "menu_order") == "2"
    assert "Somos **aficionados**.</textarea>" in page
    assert "Página · Borrador · de El Capi" in page
    assert "Creada: 04/10/2026 12:30" in page
    assert "Última actualización: 04/10/2026 12:30" in page


def test_leader_edits_a_page_title_body_and_menu_order_and_its_last_update_time_changes(
        client_as, write_page, csrf_token, clock):
    leader = client_as("admin")
    url = write_page(leader, title="Quiénes somos", menu_order="1").headers["location"]
    clock.time = "2026-10-05T18:00:00+00:00"  # 12:00 on the 5th in Monterrey

    response = leader.post(url, data={
        "csrf_token": csrf_token(leader, url), "title": "Quiénes somos y qué hacemos",
        "slug": "quiénes-somos", "body": "Nos juntamos cada partido.", "menu_order": "3"},
        follow_redirects=True)

    assert "Cambios guardados." in response.text
    assert field(response.text, "title") == "Quiénes somos y qué hacemos"
    assert field(response.text, "slug") == "quiénes-somos"
    assert field(response.text, "menu_order") == "3"
    assert "Nos juntamos cada partido.</textarea>" in response.text
    assert "Creada: 04/10/2026 12:30" in response.text
    assert "Última actualización: 05/10/2026 12:00" in response.text


def test_leader_publishes_a_draft_page_and_unpublishes_it_back_to_draft_keeping_first_published(
        client_as, write_page, button_action, clock):
    leader = client_as("admin")
    url = write_page(leader, title="Quiénes somos").headers["location"]
    draft = leader.get(url).text
    assert (button_action(draft, "Publicar") or "").endswith(f"{url}/publish")
    assert button_action(draft, "Despublicar") is None
    clock.time = "2026-10-05T18:00:00+00:00"  # 12:00 on the 5th in Monterrey

    published = leader.post(button_action(draft, "Publicar"), data={
        "csrf_token": field(draft, "csrf_token")}).text

    assert "Página publicada." in published
    assert "Página · Publicada · de El Capi" in published
    assert "Publicada por primera vez: 05/10/2026 12:00" in published
    assert button_action(published, "Publicar") is None
    assert (button_action(published, "Despublicar") or "").endswith(f"{url}/unpublish")
    clock.time = "2026-10-06T18:00:00+00:00"

    unpublished = leader.post(button_action(published, "Despublicar"), data={
        "csrf_token": field(published, "csrf_token")}).text

    assert "La página volvió a ser borrador." in unpublished
    assert "Página · Borrador · de El Capi" in unpublished
    assert "Publicada por primera vez: 05/10/2026 12:00" in unpublished
    assert (button_action(unpublished, "Publicar") or "").endswith(f"{url}/publish")


def test_publishing_a_published_page_or_unpublishing_a_draft_page_is_refused(
        client_as, write_page, take_action):
    leader = client_as("admin")
    url = write_page(leader).headers["location"]

    refused = take_action(leader, url, "unpublish")
    assert refused.status_code == 400
    assert "Solo se puede despublicar una página publicada." in refused.text
    take_action(leader, url, "publish")
    refused = take_action(leader, url, "publish")
    assert refused.status_code == 400
    assert "Esta página ya está publicada." in refused.text


def test_leader_deletes_a_page_only_after_confirming_and_then_it_is_gone(
        client_as, published_page, button_action, csrf_token):
    leader = client_as("admin")
    url = published_page(title="Próximos partidos")
    delete_link = re.search(r'<a class="danger" href="([^"]+)">Borrar</a>', leader.get(url).text)
    assert delete_link, "the page editor has a Borrar link"

    confirm = leader.get(delete_link.group(1)).text

    assert "¿Borrar «Próximos partidos»?" in confirm
    assert leader.get(url).status_code == 200, "opening the confirmation deletes nothing"
    deleted = leader.post(button_action(confirm, "Sí, borrar"),
                          data={"csrf_token": csrf_token(leader, url)})
    assert "Página borrada." in deleted.text
    gone = leader.get(url)
    assert gone.status_code == 404
    assert "No encontramos esa página" in gone.text


@pytest.mark.parametrize("reserved, used_for", [
    ("index", "la portada"), ("tema", "las páginas de los temas"),
    ("posts", "las publicaciones"), ("style", "el estilo del sitio")])
def test_page_slug_refuses_the_reserved_names_index_tema_posts_and_style_typed_or_from_title(
        client_as, write_page, reserved, used_for):
    leader = client_as("admin")

    typed = write_page(leader, title="Mi página", slug=reserved)
    from_title = write_page(leader, title=reserved.capitalize())

    for refused in (typed, from_title):
        assert refused.status_code == 400
        assert (f"El enlace «{reserved}» ya lo usa el sitio para {used_for}: elige otro."
                in refused.text)
    assert field(typed.text, "title") == "Mi página", "what was typed stays in the editor"


def save(c, url: str, token: str, title: str = "Reglas de la casa", slug: str = "",
         body: str = "Tiradera sí; ataques personales, nunca.", menu_order: str = "3"):
    """The leader saving the page editor at `url` with these fields."""
    return c.post(url, data={"csrf_token": token, "title": title, "slug": slug, "body": body,
                             "menu_order": menu_order}, follow_redirects=False)


def test_page_slug_follows_the_post_slug_rules_and_is_unique_among_pages_only(
        client_as, write_page, write_post):
    leader = client_as("admin")
    write_post(leader, title="Cómo unirse", topic="fan-club-news")  # a post may use it too

    first = leader.get(write_page(leader, title="Cómo unirse").headers["location"]).text
    typed = leader.get(write_page(leader, title="Únete", slug="cómo-unirse")
                       .headers["location"]).text
    from_title = leader.get(write_page(leader, title="¡Cómo unirse!").headers["location"]).text
    refused = write_page(leader, title="Reglas", slug="Reglas de la Casa")

    assert field(first, "slug") == "cómo-unirse"
    assert field(typed, "slug") == "cómo-unirse-2"
    assert "El enlace «cómo-unirse» ya era de otra página: quedó «cómo-unirse-2»." in typed
    assert field(from_title, "slug") == "cómo-unirse-3"
    assert refused.status_code == 400 and SLUG_REFUSED in refused.text


def test_page_slug_can_change_until_the_page_is_first_published_then_never(
        client_as, write_page, take_action, csrf_token):
    leader = client_as("admin")
    url = write_page(leader, title="Reglas").headers["location"]
    token = csrf_token(leader, url)

    assert save(leader, url, token, slug="reglas-de-la-casa").status_code == 303
    take_action(leader, url, "publish")
    take_action(leader, url, "unpublish")  # back to draft, and the slug stays locked
    refused = save(leader, url, token, slug="reglas")

    assert refused.status_code == 400
    assert "El enlace ya no se puede cambiar" in refused.text
    editor = leader.get(url).text
    assert field(editor, "slug") == "reglas-de-la-casa"
    assert re.search(r'<input[^>]*name="slug"[^>]*readonly', editor)
    assert save(leader, url, token, slug="reglas-de-la-casa", title="Reglas de la casa"
                ).status_code == 303, "saving with the same slug still works"


@pytest.mark.parametrize("menu_order", ["", "uno", "-1", "1.5", "1000"])
def test_page_menu_order_must_be_a_whole_number_from_0_to_999(
        client_as, write_page, menu_order):
    refused = write_page(client_as("admin"), title="Quiénes somos", menu_order=menu_order)

    assert refused.status_code == 400
    assert "El orden en el menú es un número entero del 0 al 999" in refused.text
    assert field(refused.text, "title") == "Quiénes somos"


def test_page_vista_previa_shows_the_body_sanitized_like_posts_without_saving_it(
        client_as, write_page, csrf_token):
    leader = client_as("admin")
    url = write_page(leader, title="Quiénes somos", body="Texto guardado.").headers["location"]
    typed = {"csrf_token": csrf_token(leader, url), "title": "Quiénes somos", "slug": "",
             "menu_order": "1", "body": ("Hola <script>window.__xss=1</script> afición.\n\n"
                                         '<img src=x onerror="window.__xss=2">\n\n'
                                         "**Arriba el Monterrey**")}

    previews = [leader.post(preview_button(leader.get(editor).text), data=typed)
                for editor in ("/admin/pages/new", url)]

    for response in previews:
        assert response.status_code == 200
        shown = preview(response.text)
        assert "<strong>Arriba el Monterrey</strong>" in shown
        assert "<script" not in shown and "onerror" not in shown and "__xss" not in shown
        assert "**Arriba el Monterrey**</textarea>" in response.text, "the editor keeps the text"
    assert "Texto guardado.</textarea>" in leader.get(url).text, "previewing saves nothing"
