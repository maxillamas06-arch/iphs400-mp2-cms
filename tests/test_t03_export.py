"""T03 (#4): the site export writes the public site from published posts only.

Each test name says which acceptance criterion of #4 it covers.
"""
from __future__ import annotations

import re
from urllib.parse import unquote

from app import cli, settings


def inside(html: str, tag: str) -> str:
    """The HTML inside the page's first <tag>, e.g. "article" for the post itself
    or "main" for what the page says without the shared header and footer."""
    match = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", html, re.S)
    assert match, f"no <{tag}>"
    return match.group(1)


def text(html: str) -> str:
    """What a reader sees of this HTML: tags dropped, spaces collapsed."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def sections(html: str) -> list[str]:
    return re.findall(r"<section[^>]*>(.*?)</section>", html, re.S)


def list_items(html: str) -> list[str]:
    return [text(item) for item in re.findall(r"<li[^>]*>(.*?)</li>", html, re.S)]


def links(html: str) -> dict[str, str]:
    """Each link's text -> where it points."""
    return {text(label): href for href, label in re.findall(r'<a href="([^"]*)"[^>]*>(.*?)</a>',
                                                             html, re.S)}


def every_file_in(site) -> dict[str, str]:
    """Each exported file's path from the site root -> its contents."""
    return {path.relative_to(site).as_posix(): path.read_text()
            for path in site.rglob("*") if path.is_file()}


def test_export_writes_a_page_per_published_post_with_title_nickname_topic_link_spanish_date_and_body(
        client_as, write_post, take_action, mark_submitted, clock, export):
    ana, leader = client_as("editor"), client_as("admin")
    url = write_post(ana, title="Crónica del Clásico Regio", topic="match",
                     body="Ganamos **3-1** en casa.").headers["location"]
    mark_submitted(url)
    clock.time = "2026-10-05T01:15:00+00:00"  # already the 5th in UTC; 19:15 on the 4th in Monterrey
    take_action(leader, url, "publish")

    post = inside((export() / "posts" / "crónica-del-clásico-regio.html").read_text(), "article")

    assert "<h1>Crónica del Clásico Regio</h1>" in post
    assert "Rayada de Corazón" in post
    assert '<a href="../tema/partido.html">Partido</a>' in post
    assert "Publicado el 4 de octubre de 2026" in post
    assert "<strong>3-1</strong>" in post


def test_cms_publish_regenerates_site_from_scratch_from_the_database(
        published_post, database_path, tmp_path, monkeypatch, capsys):
    published_post(title="Crónica del Clásico Regio")
    site = tmp_path / "site"
    (site / "posts").mkdir(parents=True)
    (site / "posts" / "una-vieja.html").write_text("left over from an earlier export")
    monkeypatch.setattr(settings, "DATABASE_PATH", database_path)
    monkeypatch.setattr(settings, "SITE", site)

    assert cli.main(["publish"]) == 0

    assert not (site / "posts" / "una-vieja.html").exists()
    assert (site / "posts" / "crónica-del-clásico-regio.html").exists()
    assert (site / "index.html").exists() and (site / "style.css").exists()
    assert "1 published post" in capsys.readouterr().out


def test_cms_publish_on_a_fresh_clone_writes_an_empty_site_and_points_to_the_seed(
        tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(settings, "DATABASE_PATH", tmp_path / "cms.db")
    monkeypatch.setattr(settings, "SITE", tmp_path / "site")

    assert cli.main(["publish"]) == 0

    assert "Todavía no hay publicaciones." in (tmp_path / "site" / "index.html").read_text()
    out = capsys.readouterr().out
    assert "0 published posts" in out and "seed_demo.py" in out


def test_home_has_a_section_per_topic_in_fixed_order_with_three_newest_and_ver_todos_hiding_empty_topics(
        published_post, client_as, write_post, export):
    for day in (1, 2, 3, 4):
        published_post(day=day, title=f"Crónica de la jornada {day}", topic="match")
    published_post(day=5, title="Al técnico hay que darle tiempo",  # newest of all, but Técnico comes second
                   topic="coach")
    published_post(by="admin", day=2, title="Watch party del Clásico", topic="fan-club-news")
    write_post(client_as("editor"), title="Un borrador de alineación", topic="lineup")  # never published

    home = (export() / "index.html").read_text()

    found = sections(home)
    assert [text(inside(s, "h2")) for s in found] == [
        "Partido", "Técnico", "Noticias del club de aficionados"]
    match = found[0]
    assert list_items(match) == [
        "Crónica de la jornada 4 Rayada de Corazón · 4 de octubre de 2026",
        "Crónica de la jornada 3 Rayada de Corazón · 3 de octubre de 2026",
        "Crónica de la jornada 2 Rayada de Corazón · 2 de octubre de 2026",
    ]
    assert links(match)["Crónica de la jornada 4"] == "posts/cr%C3%B3nica-de-la-jornada-4.html"
    assert links(match)["Ver todos"] == "tema/partido.html"
    assert links(found[2])["Ver todos"] == "tema/noticias-del-club-de-aficionados.html"
    assert "El Capi" in list_items(found[2])[0]


def test_home_with_nothing_published_says_so(export):
    home = (export() / "index.html").read_text()

    assert sections(home) == []
    assert "Todavía no hay publicaciones." in home


def test_all_five_topic_pages_are_written_newest_first_and_an_empty_one_says_so(
        published_post, export):
    for day, title in ((1, "Crónica vieja"), (3, "Crónica nueva"), (2, "Crónica de en medio")):
        published_post(day=day, title=title, topic="match")

    site = export()

    assert sorted(path.name for path in (site / "tema").iterdir()) == sorted([
        "partido.html", "alineación.html", "técnico.html", "fichajes.html",
        "noticias-del-club-de-aficionados.html"])
    match = inside((site / "tema" / "partido.html").read_text(), "main")
    assert "<h1>Partido</h1>" in match
    assert list_items(match) == [
        "Crónica nueva Rayada de Corazón · 3 de octubre de 2026",
        "Crónica de en medio Rayada de Corazón · 2 de octubre de 2026",
        "Crónica vieja Rayada de Corazón · 1 de octubre de 2026",
    ]
    assert links(match)["Crónica nueva"] == "../posts/cr%C3%B3nica-nueva.html"
    lineup = inside((site / "tema" / "alineación.html").read_text(), "main")
    assert "<h1>Alineación</h1>" in lineup
    assert "Todavía no hay publicaciones sobre este tema." in lineup


def test_only_published_posts_reach_the_export_and_drafts_appear_nowhere(
        published_post, client_as, write_post, export):
    write_post(client_as("editor"), title="Borrador secreto de Ana",
               body="Texto que nadie debe leer todavía.")
    write_post(client_as("admin"), title="Borrador del Capi", topic="fan-club-news",
               body="Fecha por confirmar.")
    published_post(title="Crónica publicada")

    files = every_file_in(export())

    assert [path for path in files if path.startswith("posts/")] == ["posts/crónica-publicada.html"]
    for path, html in files.items():
        for secret in ("Borrador secreto de Ana", "Texto que nadie debe leer todavía.",
                       "Borrador del Capi", "Fecha por confirmar."):
            assert secret not in html, f"a draft's words reached {path}"


def test_a_post_unpublished_since_the_last_export_disappears_from_the_next_one(
        published_post, client_as, take_action, export):
    url = published_post(title="Crónica del Clásico Regio")
    assert "posts/crónica-del-clásico-regio.html" in every_file_in(export())

    take_action(client_as("admin"), url, "unpublish")
    files = every_file_in(export())

    assert "posts/crónica-del-clásico-regio.html" not in files
    assert not any("Crónica del Clásico Regio" in html for html in files.values())


def test_exported_markdown_is_sanitized_so_script_and_onerror_do_not_survive(
        published_post, export):
    published_post(title="Prueba de seguridad", body=(
        "Hola <script>window.__xss=1</script> afición.\n\n"
        '<img src=x onerror="window.__xss=2">\n\n**Arriba el Monterrey**'))

    files = every_file_in(export())

    post = inside(files["posts/prueba-de-seguridad.html"], "article")
    assert "<strong>Arriba el Monterrey</strong>" in post
    for html in files.values():
        assert "<script" not in html and "onerror" not in html and "__xss" not in html


def test_every_href_and_src_is_relative_percent_encoded_and_resolves_to_a_generated_file(
        published_post, export):
    published_post(title="Crónica del Clásico Regio", topic="lineup",
                   body="Más en [la liga](https://example.com/liga).")
    published_post(title="Año de la Pandilla", topic="signings")
    site = export()

    checked = set()
    for path, html in every_file_in(site).items():
        for link in re.findall(r'(?:href|src)="([^"]*)"', html):
            assert not link.startswith("/"), f"root-absolute {link} in {path}"
            assert link.isascii(), f"{link} in {path} is not percent-encoded"
            if re.match(r"(https?|mailto):", link):
                continue
            target = ((site / path).parent / unquote(link)).resolve()
            assert target.is_file(), f"{link} in {path} leads nowhere"
            assert target.is_relative_to(site.resolve())
            checked.add(link)

    assert "../posts/cr%C3%B3nica-del-cl%C3%A1sico-regio.html" in checked
    assert "posts/a%C3%B1o-de-la-pandilla.html" in checked
    assert "tema/alineaci%C3%B3n.html" in checked


def test_every_public_page_has_the_striped_header_menu_with_inicio_topic_links_and_the_disclaimer(
        published_post, export):
    published_post(title="Crónica del Clásico Regio")
    files = every_file_in(export())

    stripes = re.search(r"\.stripes\s*\{[^}]*\}", files["style.css"])
    assert stripes and "repeating-linear-gradient" in stripes.group(0)
    assert "var(--navy)" in stripes.group(0) and "#fff" in stripes.group(0)
    pages = {path: html for path, html in files.items() if path.endswith(".html")}
    assert len(pages) == 1 + 5 + 1  # home, the five topic pages, the post
    for path, html in pages.items():
        header = inside(html, "header")
        assert 'class="stripes"' in header, path
        menu = re.search(r'<nav class="menu"[^>]*>(.*?)</nav>', header, re.S).group(1)
        assert "Inicio" in links(menu), path
        topics = re.search(r'<nav class="topics"[^>]*>(.*?)</nav>', header, re.S).group(1)
        assert list(links(topics)) == ["Partido", "Alineación", "Técnico", "Fichajes",
                                       "Noticias del club de aficionados"], path
        assert text(inside(html, "footer")) == (
            "Sitio de aficionados. Sin afiliación con el Club de Fútbol Monterrey."
            " Fan site, not affiliated with Club de Fútbol Monterrey."), path
