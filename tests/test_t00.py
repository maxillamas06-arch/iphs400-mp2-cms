"""T00: the walking skeleton. These pass in the fresh template.

Do not delete them. If a change breaks them, the change broke the app's front
door.
"""


def test_admin_console_answers(client_as):
    # T01 put the console behind login (#2), so the front door is the leader's
    # dashboard rather than the T00 "hello admin" page.
    response = client_as("admin").get("/admin")
    assert response.status_code == 200
    assert "Hola" in response.text


def test_front_door_leads_into_the_admin_console(client):
    # Was test_public_home_answers. T03 (#4): the public home is index.html in the
    # export (ADR-001; see the export tests below), so / leads into the console.
    response = client.get("/")
    assert response.status_code == 200
    assert response.url.path == "/login"


# T03 (#4) renamed app/publish.py to app/export.py ("publish" is now the status
# change) and the export reads the database, so these use the `export` fixture.
def test_publish_writes_a_site(export):
    out = export()
    assert (out / "index.html").exists() and (out / "style.css").exists()


def test_published_html_uses_relative_paths(export):
    """Root-absolute paths break on GitHub Pages project URLs (rubric F2)."""
    html = (export() / "index.html").read_text()
    assert 'href="/' not in html and 'src="/' not in html
