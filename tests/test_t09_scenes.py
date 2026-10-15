"""T09 (#10): the public site comes alive, with a drawn scene behind every page.

Each test name says which acceptance criterion of #10 it covers. A page's scene is
the inline <svg> carrying data-scene="<name>". The motion (scroll-driven, played
once on load, still under reduced motion), readability over the scenes and the
390 px layout are checked by hand in a browser.
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


def scenes(html: str) -> list[str]:
    """The name of each scene drawn on the page, in order."""
    return re.findall(r'<svg\b[^>]*\bdata-scene="([^"]+)"', html)


def test_home_page_carries_the_goal_scene_and_a_caption_naming_the_moment_inviting_a_scroll(
        export):
    home = (export() / "index.html").read_text()

    assert scenes(home) == ["goal"]
    story = text(inside(home, "main"))
    for words in ("Suazo", "90'", "final del Apertura 2009", "Cruz Azul 1–2 Rayados",
                  "global 4–6", "Desliza"):
        assert words in story, words


def test_each_topic_page_carries_its_own_scene_and_a_post_carries_its_topics_scene(
        published_post, export):
    published_post(title="El once que yo pondría el sábado", topic="lineup")
    published_post(by="admin", title="Watch party del Clásico Regio", topic="fan-club-news")

    site = export()

    assert {path: scenes((site / path).read_text()) for path in (
        "tema/partido.html", "tema/alineación.html", "tema/técnico.html", "tema/fichajes.html",
        "tema/noticias-del-club-de-aficionados.html")} == {
        "tema/partido.html": ["night-stadium"],
        "tema/alineación.html": ["tactics-board"],
        "tema/técnico.html": ["touchline"],
        "tema/fichajes.html": ["signing"],
        "tema/noticias-del-club-de-aficionados.html": ["fans-stand"],
    }
    post = site / "posts" / "el-once-que-yo-pondría-el-sábado.html"
    assert scenes(post.read_text()) == ["tactics-board"]
    news = site / "posts" / "watch-party-del-clásico-regio.html"
    assert scenes(news.read_text()) == ["fans-stand"]


def test_each_seeded_page_carries_its_own_scene_and_any_other_page_the_default_scene(
        published_page, export):
    for title in ("Quiénes somos", "Próximos partidos", "Reglas de la casa", "Cómo unirse",
                  "Galería de trapos"):
        published_page(title=title)

    site = export()

    assert {path: scenes((site / path).read_text()) for path in (
        "quiénes-somos.html", "próximos-partidos.html", "reglas-de-la-casa.html",
        "cómo-unirse.html", "galería-de-trapos.html")} == {
        "quiénes-somos.html": ["fans-bus"],
        "próximos-partidos.html": ["scoreboard"],
        "reglas-de-la-casa.html": ["referee"],
        "cómo-unirse.html": ["empty-seat"],
        "galería-de-trapos.html": ["default"],
    }


def test_no_public_page_carries_a_script_so_the_scenes_move_with_css_alone(
        published_post, published_page, export):
    published_post(title="El once que yo pondría el sábado", topic="lineup")
    published_page(title="Reglas de la casa")
    published_page(title="Galería de trapos")

    pages = list(export().rglob("*.html"))

    assert len(pages) == 1 + 5 + 1 + 2  # home, five topics, the post, two pages
    for path in pages:
        assert "<script" not in path.read_text().lower(), path.name
