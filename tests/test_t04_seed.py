"""T04 (#5): the demo seed adds a member's submitted post, waiting for review."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_seed_adds_one_submitted_post_written_by_a_member_and_it_stays_out_of_the_export(
        tmp_path, login, env_example, run_seed, cells, export):
    database = tmp_path / "seeded.db"
    assert run_seed(database).returncode == 0
    leader = TestClient(create_app(database))
    login(leader, "lider@albiazul.example", env_example["CMS_ADMIN_PASSWORD"])

    rows = [row for row in cells(leader.get("/admin/content").text) if row]

    submitted = [row for row in rows if row[3] == "Enviada"]
    assert len(submitted) == 1
    title, topic, nickname, _, _ = submitted[0]
    assert title and topic
    assert nickname in {"Rayada de Corazón", "Furia del Cerro"}
    every_page = "".join(path.read_text() for path in export(database).rglob("*.html"))
    assert title not in every_page
