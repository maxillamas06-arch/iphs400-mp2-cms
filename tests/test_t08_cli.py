"""T08 (#9): `cms publish` and `cms deploy` still work as before, and the button's
real upload goes to gh-pages the way `cms deploy` does.

Each test name says which acceptance criterion of #9 it covers. Every upload here
runs with git replaced by a fake, so no test uploads anything to GitHub.
"""
from __future__ import annotations

import re
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient

from app import cli, settings, site_update
from app.main import create_app


class FakeGit:
    """Stands in for subprocess.run: records each command and answers with `returncode`."""

    def __init__(self, returncode: int = 0) -> None:
        self.commands: list[list[str]] = []
        self.envs: list[dict[str, str] | None] = []
        self.returncode = returncode

    stalled = False  # the connection hangs: git never finishes on its own

    def __call__(self, command, *args, env=None, timeout=None, **kwargs):
        self.commands.append(command)
        self.envs.append(env)
        if self.stalled:
            assert timeout is not None, "the upload would wait forever"
            raise subprocess.TimeoutExpired(command, timeout)
        return subprocess.CompletedProcess(command, self.returncode)


@pytest.fixture
def git(monkeypatch) -> FakeGit:
    fake = FakeGit()
    monkeypatch.setattr(subprocess, "run", fake)
    return fake


@pytest.fixture
def cli_site(tmp_path, monkeypatch, database_path):
    """Point the CLI at this test's database and a temporary site/ folder."""
    site = tmp_path / "site"
    monkeypatch.setattr(settings, "DATABASE_PATH", database_path)
    monkeypatch.setattr(settings, "SITE", site)
    return site


def test_cms_publish_still_exports_and_counts_as_the_last_export_on_the_dashboard(
        cli_site, published_post, client_as, clock, capsys):
    published_post(title="Crónica del Clásico Regio")
    clock.time = "2026-10-04T18:30:00+00:00"  # 12:30 in Monterrey

    assert cli.main(["publish"]) == 0

    assert (cli_site / "posts" / "crónica-del-clásico-regio.html").exists()
    assert "1 published post" in capsys.readouterr().out
    dashboard = re.sub(r"\s+", " ", client_as("admin").get("/admin").text)
    assert "Sitio generado por última vez: 04/10/2026 12:30" in dashboard


def test_cms_deploy_still_uploads_site_to_gh_pages_and_says_how_to_turn_on_pages(
        cli_site, git, capsys):
    cli_site.mkdir()

    assert cli.main(["deploy"]) == 0

    assert git.commands == [[sys.executable, "-m", "ghp_import", "-n", "-p", "-m",
                             "Publish site", str(cli_site)]]
    assert "Pushed to gh-pages" in capsys.readouterr().out


def test_cms_deploy_still_reports_a_failed_upload_and_a_missing_site(cli_site, git, capsys):
    assert cli.main(["deploy"]) == 1
    assert "run `uv run cms publish` first" in capsys.readouterr().out
    assert git.commands == []

    cli_site.mkdir()
    git.returncode = 128
    assert cli.main(["deploy", "--message", "Otra vez"]) != 0
    assert git.commands[0][-3:] == ["-m", "Otra vez", str(cli_site)]
    assert "Pushed to gh-pages" not in capsys.readouterr().out


def test_button_runs_the_export_then_the_real_upload_and_a_failed_upload_shows_the_plain_error_instead_of_hanging(
        database_path, public_site, git, login, demo_users, csrf_token):
    leader = TestClient(create_app(database_path, site=public_site,
                                   upload=site_update.upload_to_github_pages))  # the real one
    login(leader, demo_users["admin"]["email"], demo_users["admin"]["password"])

    page = leader.post("/admin/site-update", data={"csrf_token": csrf_token(leader)}).text

    assert "Subido a GitHub ✓" in page
    [command] = git.commands
    assert command[:5] == [sys.executable, "-m", "ghp_import", "-n", "-p"]
    assert command[-1] == str(public_site) and (public_site / "index.html").exists()
    # Nobody at the console can answer git's password question, so it must not ask.
    assert git.envs[0]["GIT_TERMINAL_PROMPT"] == "0"

    git.returncode = 128
    page = leader.post("/admin/site-update", data={"csrf_token": csrf_token(leader)}).text
    assert "No se pudo subir a GitHub" in page

    git.stalled = True  # a dropped connection gives up in time, with the same error
    page = leader.post("/admin/site-update", data={"csrf_token": csrf_token(leader)}).text
    assert "No se pudo subir a GitHub" in page
