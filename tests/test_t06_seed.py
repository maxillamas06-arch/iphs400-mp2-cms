"""T06 (#7): the demo seed adds the fan club's four pages, published."""
from __future__ import annotations

import re


def text(html: str) -> str:
    """What a reader sees of this HTML: tags dropped, spaces collapsed."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def article(path) -> str:
    """What a reader sees of the exported page at `path`, without header and footer."""
    return text(re.search(r"<article>(.*?)</article>", path.read_text(), re.S).group(1))


def test_seed_adds_the_four_pages_published_in_menu_order_with_house_rules_and_how_to_join(
        tmp_path, run_seed, export):
    database = tmp_path / "seeded.db"
    assert run_seed(database).returncode == 0

    site = export(database)

    menu = re.search(r'<nav class="menu"[^>]*>(.*?)</nav>', (site / "index.html").read_text(),
                     re.S).group(1)
    assert [text(label) for label in re.findall(r"<a [^>]*>(.*?)</a>", menu)] == [
        "Inicio", "Quiénes somos", "Próximos partidos", "Reglas de la casa", "Cómo unirse"]
    rules = article(site / "reglas-de-la-casa.html")
    for rule in ("tiradera", "ataque personal", "amenaza", "el líder revisa"):
        assert rule in rules.lower(), f"Reglas de la casa does not spell out: {rule}"
    assert "unete@albiazul.example" in article(site / "cómo-unirse.html")
    for page in ("quiénes-somos.html", "próximos-partidos.html"):
        assert len(article(site / page)) > 100, f"{page} has real text"
