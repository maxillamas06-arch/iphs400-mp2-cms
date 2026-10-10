"""T03 (#4): the demo seed publishes a post in every topic."""
from __future__ import annotations

import re


def test_seed_publishes_at_least_one_post_per_topic_including_a_tiradera_aimed_at_tigres(
        tmp_path, run_seed, export):
    database = tmp_path / "seeded.db"
    assert run_seed(database).returncode == 0

    site = export(database)

    topic_pages = list((site / "tema").iterdir())
    assert len(topic_pages) == 5
    for page in topic_pages:
        assert "Todavía no hay publicaciones sobre este tema." not in page.read_text(), page.name
    titles = [re.search(r"<h1>(.*?)</h1>", page.read_text()).group(1)
              for page in (site / "posts").iterdir()]
    assert any("Tigres" in title for title in titles), titles
    every_page = "".join(path.read_text() for path in site.rglob("*.html"))
    assert "Lo que se vio desde la cabecera norte" not in every_page, "the seed's draft stays out"
