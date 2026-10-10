"""T01 (#2): the demo seed and `.env.example`.

Each test name says which acceptance criterion of #2 it covers.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import accounts, db, settings
from app.main import create_app

ROOT = Path(__file__).resolve().parents[1]


def env_example() -> dict[str, str]:
    pairs = (line.split("=", 1) for line in (ROOT / ".env.example").read_text().splitlines()
             if line.strip() and not line.startswith("#"))
    return {key.strip(): value.strip() for key, value in pairs}


def run_seed(database: Path) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if not k.startswith("CMS_")}
    env |= env_example() | {"CMS_DATABASE": str(database)}
    return subprocess.run([sys.executable, "scripts/seed_demo.py"], cwd=ROOT, env=env,
                          capture_output=True, text=True)


def test_env_example_sets_site_title_and_student_placeholder():
    values = env_example()

    assert values["CMS_SITE_TITLE"] == "Club de Aficionados Albiazul"
    assert values["CMS_STUDENT"] == "first-last"


def test_seed_runs_clean_from_env_example_and_its_users_log_in_by_nickname(
        tmp_path, login, demo_users):
    database = tmp_path / "seeded.db"
    passwords = {"admin": env_example()["CMS_ADMIN_PASSWORD"],
                 "editor": env_example()["CMS_EDITOR_PASSWORD"],
                 "editor2": env_example()["CMS_EDITOR_PASSWORD"]}

    for _ in range(2):  # the seed wipes and rebuilds, so a second run is clean too
        result = run_seed(database)
        assert result.returncode == 0, result.stdout + result.stderr
    assert not any(p in result.stdout + result.stderr for p in passwords.values())

    for role, user in demo_users.items():
        c = TestClient(create_app(database))
        assert login(c, user["email"], passwords[role]).status_code == 303, role
        assert user["nickname"] in c.get("/admin").text


def test_seed_creates_the_leader_and_two_members_matching_the_test_helper(
        tmp_path, login, demo_users):
    database = tmp_path / "seeded.db"
    assert run_seed(database).returncode == 0
    leader = TestClient(create_app(database))
    login(leader, "lider@albiazul.example", env_example()["CMS_ADMIN_PASSWORD"])

    page = leader.get("/admin/users").text

    assert page.count("@albiazul.example") == 3
    assert page.count("<td>Líder</td>") == 1 and page.count("<td>Miembro</td>") == 2
    for user in demo_users.values():
        assert f"<td>{user['email']}</td>" in page
        assert f"<td>{user['nickname']}</td>" in page


@pytest.mark.parametrize("run", ["first", "second"])
def test_each_test_runs_against_its_own_fresh_temporary_database(
        client_as, database_path, tmp_path, demo_users, run):
    assert database_path.parent == tmp_path
    assert database_path != settings.DATABASE_PATH
    leader = client_as("admin")

    # Both runs add the same account; a shared database would make the second
    # run see it (and refuse the duplicate email).
    assert leader.get("/admin/users").text.count("@albiazul.example") == len(demo_users)
    conn = db.connect(database_path)
    accounts.create_user(conn, email="extra@albiazul.example", password="extra-pw",
                         role="editor", nickname=f"Extra {run}")
    conn.close()
