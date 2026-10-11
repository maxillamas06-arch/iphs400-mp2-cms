"""T05 (#6): the demo seed adds a member's published post with a pending edit."""
from __future__ import annotations

import re

from fastapi.testclient import TestClient

from app.main import create_app


def test_seed_adds_one_published_post_with_a_pending_edit_by_a_member_and_it_stays_out_of_the_export(
        tmp_path, login, env_example, run_seed, cells, dashboard_counts, export):
    database = tmp_path / "seeded.db"
    assert run_seed(database).returncode == 0
    leader = TestClient(create_app(database))
    login(leader, "lider@albiazul.example", env_example["CMS_ADMIN_PASSWORD"])

    number, link = dashboard_counts(leader)["Cambios propuestos"]
    listed = leader.get(link).text

    assert number == "1"
    [row] = [row for row in cells(listed) if row]
    title, _, nickname, status, _ = row
    assert status == "Publicada"
    assert nickname in {"Rayada de Corazón", "Furia del Cerro"}
    post_url = re.search(rf'<a href="([^"]+)">{re.escape(title)}</a>', listed).group(1)
    review = leader.get(f"{post_url}/pending-edit").text
    proposed = re.search(r'aria-label="Cambios propuestos".*?<div class="preview-body">(.*?)</div>',
                         review, re.S).group(1)
    every_page = "".join(path.read_text() for path in export(database).rglob("*.html"))
    assert title in every_page, "the published version is on the public site"
    assert proposed not in every_page, "the proposed version is not"
