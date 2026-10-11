"""T04 (#5): the dashboard counts posts by status; the content list filters them.

Each test name says which acceptance criterion of #5 it covers.
"""
from __future__ import annotations

import re


def text(html: str) -> str:
    """What a reader sees of this HTML: tags dropped, spaces collapsed."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def counts(html: str) -> dict[str, str]:
    """The dashboard's counts: each label -> its number, as a reader sees them."""
    return {text(label): text(number)
            for label, number in re.findall(r"<dt>(.*?)</dt>\s*<dd>(.*?)</dd>", html, re.S)}


def test_dashboard_counts_drafts_submitted_labelled_waiting_for_review_and_published(
        client_as, write_post, take_action, published_post):
    ana, beto, leader = client_as("editor"), client_as("editor2"), client_as("admin")
    assert counts(leader.get("/admin").text) == {
        "Borradores": "0", "Esperando revisión": "0", "Publicadas": "0",
        "Cambios propuestos": "0"}

    write_post(ana, title="Borrador de Ana")
    write_post(leader, title="Borrador del Capi", topic="fan-club-news")
    for c, title in ((ana, "Enviada por Ana"), (beto, "Enviada por Beto")):
        take_action(c, write_post(c, title=title).headers["location"], "submit")
    published_post(title="Ya publicada")

    for viewer in (leader, ana):
        assert counts(viewer.get("/admin").text) == {
            "Borradores": "2", "Esperando revisión": "2", "Publicadas": "1",
            "Cambios propuestos": "0"}


def selected(html: str, name: str) -> str:
    """The value chosen in the filter <select> with this name."""
    select = re.search(rf'<select[^>]*name="{name}"[^>]*>(.*?)</select>', html, re.S)
    assert select, f"no {name} filter"
    choice = re.search(r'<option value="([^"]*)" selected', select.group(1))
    return choice.group(1) if choice else ""


def test_content_list_filters_by_status_and_by_topic(
        client_as, write_post, take_action, published_post, cells):
    ana, leader = client_as("editor"), client_as("admin")
    write_post(ana, title="Borrador de partido", topic="match")
    for title, topic in (("Enviada de partido", "match"), ("Enviada de técnico", "coach")):
        take_action(ana, write_post(ana, title=title, topic=topic).headers["location"], "submit")
    published_post(title="Publicada de partido", topic="match")

    def titles(query: str) -> list[str]:
        return sorted(row[0] for row in cells(leader.get(f"/admin/content{query}").text) if row)

    assert titles("?status=submitted") == ["Enviada de partido", "Enviada de técnico"]
    assert titles("?topic=match") == ["Borrador de partido", "Enviada de partido",
                                      "Publicada de partido"]
    assert titles("?status=submitted&topic=match") == ["Enviada de partido"]
    assert titles("?status=&topic=") == titles("") and len(titles("")) == 4
    page = leader.get("/admin/content?status=submitted&topic=coach").text
    assert selected(page, "status") == "submitted" and selected(page, "topic") == "coach"


def test_content_list_filter_with_no_match_says_so(client_as, write_post):
    ana = client_as("editor")
    write_post(ana, title="Borrador de partido", topic="match")

    page = ana.get("/admin/content?status=published&topic=coach").text

    assert "Borrador de partido" not in page
    assert "Ninguna publicación coincide con estos filtros." in page


def test_each_dashboard_count_opens_the_content_list_filtered_to_that_status(
        client_as, write_post, take_action, cells):
    ana, leader = client_as("editor"), client_as("admin")
    write_post(ana, title="Borrador de Ana")
    take_action(ana, write_post(ana, title="Enviada por Ana").headers["location"], "submit")

    links = {text(label): href for label, href in re.findall(
        r'<dt>(.*?)</dt>\s*<dd><a href="([^"]+)"', leader.get("/admin").text, re.S)}

    # T05 (#6) adds Cambios propuestos, which opens posts with a pending edit.
    assert set(links) == {"Borradores", "Esperando revisión", "Publicadas", "Cambios propuestos"}
    queue = leader.get(links["Esperando revisión"]).text
    assert [row[0] for row in cells(queue) if row] == ["Enviada por Ana"]
    drafts = leader.get(links["Borradores"]).text
    assert [row[0] for row in cells(drafts) if row] == ["Borrador de Ana"]
