"""T08 (#9): the leader updates the site with one button.

Each test name says which acceptance criterion of #9 it covers. The upload is the
fake from conftest.py, so no test uploads anything to GitHub.
"""
from __future__ import annotations

import re

from fastapi.testclient import TestClient

from app import settings
from app.main import create_app


def text(html: str) -> str:
    """What a reader sees of this HTML: tags dropped, spaces collapsed."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def update_site(c, button_action, csrf_token):
    """Press Actualizar el sitio on the dashboard; returns the page it leads to."""
    action = button_action(c.get("/admin").text, "Actualizar el sitio")
    assert action, "the dashboard has an Actualizar el sitio button"
    return c.post(action, data={"csrf_token": csrf_token(c)})


def test_leader_button_exports_then_uploads_and_reports_each_step(
        client_as, published_post, button_action, csrf_token, uploads, public_site):
    published_post(title="Crónica del Clásico Regio")
    leader = client_as("admin")

    page = update_site(leader, button_action, csrf_token)

    assert page.status_code == 200
    assert "Sitio generado ✓ · Subido a GitHub ✓" in text(page.text)
    [sent] = uploads.sent
    assert {"index.html", "style.css", "posts/crónica-del-clásico-regio.html"} <= sent, (
        "the upload ran after the export and was handed the exported site")
    assert (public_site / "posts" / "crónica-del-clásico-regio.html").exists()


def test_failed_upload_shows_a_plain_spanish_error_and_the_successful_export_still_counts(
        client_as, published_post, button_action, csrf_token, uploads, public_site):
    published_post(title="Crónica del Clásico Regio")
    leader = client_as("admin")
    uploads.failing = True

    page = text(update_site(leader, button_action, csrf_token).text)

    assert "Sitio generado ✓" in page
    assert "No se pudo subir a GitHub" in page
    assert "Subido a GitHub ✓" not in page
    assert "could not read" not in page, "git's own words never reach the leader"
    assert (public_site / "posts" / "crónica-del-clásico-regio.html").exists()


def test_dashboard_shows_when_the_last_successful_export_was_even_when_the_upload_failed(
        client_as, button_action, csrf_token, uploads, clock):
    leader = client_as("admin")
    assert "Sitio generado por última vez: nunca" in text(leader.get("/admin").text)

    clock.time = "2026-10-04T18:30:00+00:00"  # 12:30 in Monterrey
    update_site(leader, button_action, csrf_token)
    assert "Sitio generado por última vez: 04/10/2026 12:30" in text(leader.get("/admin").text)

    uploads.failing = True
    clock.time = "2026-10-05T01:15:00+00:00"  # 19:15 on the 4th in Monterrey
    update_site(leader, button_action, csrf_token)
    assert "Sitio generado por última vez: 04/10/2026 19:15" in text(leader.get("/admin").text)


def test_member_gets_403_on_the_site_update_and_nothing_is_exported_or_uploaded(
        client_as, published_post, button_action, csrf_token, uploads, public_site):
    published_post(title="Crónica del Clásico Regio")
    ana = client_as("editor")
    dashboard = ana.get("/admin").text
    assert button_action(dashboard, "Actualizar el sitio") is None
    assert "Sitio generado por última vez" not in dashboard

    response = ana.post("/admin/site-update", data={"csrf_token": csrf_token(ana)})

    assert response.status_code == 403
    assert "No tienes permiso" in response.text
    assert uploads.sent == [] and not public_site.exists()


def test_failed_export_shows_a_plain_spanish_error_and_nothing_is_uploaded(
        client_as, button_action, csrf_token, uploads, public_site):
    leader = client_as("admin")
    public_site.write_text("not a folder")  # the export cannot write the site here

    page = text(update_site(leader, button_action, csrf_token).text)

    assert "No se pudo generar el sitio" in page
    assert "Subido a GitHub" not in page and "Sitio generado ✓" not in page
    assert uploads.sent == []
    assert "Sitio generado por última vez: nunca" in page


def test_every_test_app_without_a_fake_still_never_uploads_or_writes_site(
        database_path, login, demo_users, csrf_token):
    leader = TestClient(create_app(database_path))  # no folder, no fake upload given
    login(leader, demo_users["admin"]["email"], demo_users["admin"]["password"])

    page = text(leader.post("/admin/site-update", data={"csrf_token": csrf_token(leader)}).text)

    assert "No se pudo subir a GitHub" in page, "the guard in conftest.py refused the upload"
    assert settings.SITE != settings.ROOT / "site", "the export went to a temporary folder"
