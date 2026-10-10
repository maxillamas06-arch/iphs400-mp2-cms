"""T02 (#3): the demo seed adds a member's draft."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_seed_adds_one_draft_written_by_a_member(tmp_path, login, env_example, run_seed, cells):
    database = tmp_path / "seeded.db"
    assert run_seed(database).returncode == 0
    member = TestClient(create_app(database))
    login(member, "beto@albiazul.example", env_example["CMS_EDITOR_PASSWORD"])

    rows = [row for row in cells(member.get("/admin/content").text) if row]

    drafts = [row for row in rows if row[3] == "Borrador"]
    assert len(drafts) == 1
    title, topic, nickname, _, _ = drafts[0]
    assert title and topic
    assert nickname in {"Rayada de Corazón", "Furia del Cerro"}
