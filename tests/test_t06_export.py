"""T06 (#7): the site export writes published pages and lists them in the menu.

Each test name says which acceptance criterion of #7 it covers.
"""
from __future__ import annotations

import re


def inside(html: str, tag: str) -> str:
    """The HTML inside the page's first <tag>."""
    match = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", html, re.S)
    assert match, f"no <{tag}>"
    return match.group(1)


def text(html: str) -> str:
    """What a reader sees of this HTML: tags dropped, spaces collapsed."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def links(html: str) -> dict[str, str]:
    """Each link's text -> where it points, in the order they appear."""
    return {text(label): href for href, label in re.findall(r'<a href="([^"]*)"[^>]*>(.*?)</a>',
                                                             html, re.S)}


def menu(html: str) -> dict[str, str]:
    """The public menu's links: each one's text -> where it points."""
    match = re.search(r'<nav class="menu"[^>]*>(.*?)</nav>', inside(html, "header"), re.S)
    assert match, "no menu"
    return links(match.group(1))


def every_html_file_in(site) -> dict[str, str]:
    """Each exported page's path from the site root -> its HTML."""
    return {path.relative_to(site).as_posix(): path.read_text() for path in site.rglob("*.html")}


def test_export_writes_each_published_page_at_the_site_root_with_its_title_and_sanitized_body(
        published_page, export):
    published_page(title="Cómo unirse", menu_order="4", body=(
        "Escríbenos a **unete@albiazul.example**.\n\n<script>window.__xss=1</script>"))

    html = (export() / "cómo-unirse.html").read_text()

    article = inside(html, "article")
    assert "<h1>Cómo unirse</h1>" in article
    assert "<strong>unete@albiazul.example</strong>" in article
    assert "<script" not in html and "__xss" not in html
    assert "<title>Cómo unirse · Club de Aficionados Albiazul</title>" in html


def test_every_public_page_menu_lists_inicio_then_published_pages_in_menu_order(
        published_page, published_post, export):
    published_page(title="Cómo unirse", menu_order="4")
    published_page(title="Quiénes somos", menu_order="1")
    published_page(title="Reglas de la casa", menu_order="3")
    published_post(title="Crónica del Clásico Regio")

    pages = every_html_file_in(export())

    assert len(pages) == 1 + 5 + 1 + 3  # home, the five topic pages, the post, the pages
    for path, html in pages.items():
        up = "../" * path.count("/")
        assert menu(html) == {
            "Inicio": f"{up}index.html",
            "Quiénes somos": f"{up}qui%C3%A9nes-somos.html",
            "Reglas de la casa": f"{up}reglas-de-la-casa.html",
            "Cómo unirse": f"{up}c%C3%B3mo-unirse.html",
        }, path
        assert list(menu(html)) == ["Inicio", "Quiénes somos", "Reglas de la casa",
                                    "Cómo unirse"], path


def test_draft_and_unpublished_pages_appear_nowhere_in_the_export(
        client_as, write_page, published_page, take_action, export):
    leader = client_as("admin")
    write_page(leader, title="Página en borrador", body="Texto que nadie debe leer todavía.",
               menu_order="2")
    published_page(title="Quiénes somos", menu_order="1")
    url = published_page(title="Próximos partidos", body="Sábado: Clásico Regio.",
                         menu_order="3")
    assert "próximos-partidos.html" in every_html_file_in(export())

    take_action(leader, url, "unpublish")
    pages = every_html_file_in(export())

    assert sorted(path for path in pages if "/" not in path) == ["index.html",
                                                                 "quiénes-somos.html"]
    for path, html in pages.items():
        assert list(menu(html)) == ["Inicio", "Quiénes somos"], path
        for secret in ("Página en borrador", "Texto que nadie debe leer todavía.",
                       "Próximos partidos", "Sábado: Clásico Regio."):
            assert secret not in html, f"an unpublished page's words reached {path}"
