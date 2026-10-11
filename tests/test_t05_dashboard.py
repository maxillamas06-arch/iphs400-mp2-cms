"""T05 (#6): the dashboard counts pending edits; the content list filters to them.

Each test name says which acceptance criterion of #6 it covers.
"""
from __future__ import annotations

import re


def test_dashboard_counts_pending_edits_and_the_count_opens_the_posts_that_have_one(
        client_as, published_post, propose_edit, dashboard_counts, cells):
    ana, beto, leader = client_as("editor"), client_as("editor2"), client_as("admin")
    anas = published_post(title="Crónica de Ana")
    betos = published_post(by="editor2", title="Crónica de Beto")
    published_post(by="editor2", title="Crónica sin cambios")
    assert dashboard_counts(leader)["Cambios propuestos"][0] == "0"

    propose_edit(ana, anas, title="Crónica de Ana, primera corrección")
    propose_edit(beto, betos, title="Crónica de Beto, corregida")
    propose_edit(ana, anas, title="Crónica de Ana, segunda corrección")  # replaces her first

    for viewer in (leader, ana):
        assert dashboard_counts(viewer)["Cambios propuestos"][0] == "2"
    _, link = dashboard_counts(leader)["Cambios propuestos"]
    assert sorted(row[0] for row in cells(leader.get(link).text) if row) == [
        "Crónica de Ana", "Crónica de Beto"], "listed by their published titles"


def test_content_list_filters_to_posts_with_a_pending_edit_alone_or_with_status_and_topic(
        client_as, published_post, propose_edit, write_post, cells):
    ana, leader = client_as("editor"), client_as("admin")
    for title, topic in (("Partido con cambios", "match"), ("Técnico con cambios", "coach"),
                         ("Partido sin cambios", "match")):
        url = published_post(title=title, topic=topic)
        if "con cambios" in title:
            propose_edit(ana, url, title=f"{title}, corregida", topic=topic)
    write_post(ana, title="Borrador de partido", topic="match")

    def titles(query: str) -> list[str]:
        return sorted(row[0] for row in cells(leader.get(f"/admin/content{query}").text) if row)

    assert titles("?pending=1") == ["Partido con cambios", "Técnico con cambios"]
    assert titles("?pending=1&topic=match") == ["Partido con cambios"]
    assert titles("?pending=1&status=draft") == []
    assert titles("?pending=") == titles("") and len(titles("")) == 4
    checkbox = re.search(r'<input[^>]*name="pending"[^>]*>', leader.get("/admin/content?pending=1").text)
    assert checkbox and "checked" in checkbox.group(0)
