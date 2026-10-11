"""T06 (#7): pages in the leader's content list and dashboard, never in a member's.

Each test name says which acceptance criterion of #7 it covers.
"""
from __future__ import annotations

import re


def menu_links(html: str) -> list[str]:
    """The admin menu's link texts."""
    menu = re.search(r'<nav class="menu" aria-label="Menú de administración">(.*?)</nav>',
                     html, re.S)
    assert menu, "no admin menu"
    return re.findall(r"<a [^>]*>(.*?)</a>", menu.group(1))


def test_leader_content_list_shows_posts_and_pages_and_filters_posts_vs_pages(
        client_as, write_post, write_page, published_page, cells, clock):
    leader = client_as("admin")
    write_post(leader, title="Watch party del Clásico", topic="fan-club-news")
    clock.time = "2026-10-05T18:00:00+00:00"  # 12:00 on the 5th in Monterrey
    published_page(title="Quiénes somos", menu_order="1")
    write_page(leader, title="Cómo unirse", menu_order="4")

    def rows(query: str) -> list[list[str]]:
        return [row for row in cells(leader.get(f"/admin/content{query}").text) if row]

    assert [row[0] for row in rows("")] == ["Cómo unirse", "Quiénes somos",
                                            "Watch party del Clásico"]
    assert ["Quiénes somos", "Página", "El Capi", "Publicada", "05/10/2026 12:00"] in rows("")
    assert [row[0] for row in rows("?type=post")] == ["Watch party del Clásico"]
    assert [row[0] for row in rows("?type=page")] == ["Cómo unirse", "Quiénes somos"]
    assert [row[0] for row in rows("?type=page&status=published")] == ["Quiénes somos"]
    assert [row[0] for row in rows("?topic=fan-club-news")] == ["Watch party del Clásico"]
    assert rows("?type=page&status=submitted") == []
    listed = leader.get("/admin/content?type=page").text
    assert re.search(r'<option value="page" selected>Páginas</option>', listed)
    page_url = re.search(r'<a href="([^"]+)">Quiénes somos</a>', listed).group(1)
    assert "Página · Publicada" in leader.get(page_url).text, "a page's title opens its editor"
    assert "Ninguna página coincide con estos filtros." in leader.get(
        "/admin/content?type=page&status=submitted").text


def test_leader_menu_and_content_list_lead_to_pages_and_a_new_page(client_as):
    leader = client_as("admin")

    assert "Páginas" in menu_links(leader.get("/admin").text)
    listed = leader.get("/admin/content?type=page").text
    assert "Todavía no hay páginas." in listed
    new_page = re.search(r'<a class="button" href="([^"]+)">Nueva página</a>', listed)
    assert new_page and "Nueva página" in leader.get(new_page.group(1)).text


def test_member_sees_no_pages_in_their_admin_menu_or_content_list_even_when_asking(
        client_as, published_page, write_page, write_post, cells):
    published_page(title="Quiénes somos", menu_order="1")
    write_page(client_as("admin"), title="Cómo unirse", menu_order="4")
    ana = client_as("editor")
    write_post(ana, title="Crónica del Clásico Regio")

    assert "Páginas" not in menu_links(ana.get("/admin").text)
    for query in ("", "?type=page", "?status=published", "?status=draft"):
        html = ana.get(f"/admin/content{query}").text
        assert "Quiénes somos" not in html and "Cómo unirse" not in html, query
        assert 'name="type"' not in html and "Nueva página" not in html, query
    assert [row[0] for row in cells(ana.get("/admin/content?type=page").text) if row] == [
        "Crónica del Clásico Regio"], "a filter the list does not offer is no filter at all"


def test_leader_dashboard_shows_the_page_count_which_opens_the_pages_and_members_see_none(
        client_as, published_page, write_page, dashboard_counts, cells):
    leader = client_as("admin")
    assert dashboard_counts(leader)["Páginas"][0] == "0"

    published_page(title="Quiénes somos", menu_order="1")
    write_page(leader, title="Cómo unirse", menu_order="4")

    number, link = dashboard_counts(leader)["Páginas"]
    assert number == "2"
    assert sorted(row[0] for row in cells(leader.get(link).text) if row) == [
        "Cómo unirse", "Quiénes somos"]
    assert "Páginas" not in dashboard_counts(client_as("editor"))


def test_each_dashboard_post_count_still_opens_just_the_posts_it_counts_when_there_are_pages(
        client_as, published_page, write_page, published_post, write_post, take_action,
        dashboard_counts, cells):
    leader, ana = client_as("admin"), client_as("editor")
    published_page(title="Quiénes somos", menu_order="1")
    write_page(leader, title="Cómo unirse", menu_order="4")
    published_post(title="Crónica publicada")
    write_post(leader, title="Borrador del Capi", topic="fan-club-news")
    take_action(ana, write_post(ana, title="Enviada por Ana").headers["location"], "submit")

    for label, counted in (("Borradores", ["Borrador del Capi"]),
                           ("Esperando revisión", ["Enviada por Ana"]),
                           ("Publicadas", ["Crónica publicada"])):
        number, link = dashboard_counts(leader)[label]
        assert number == str(len(counted)), label
        assert [row[0] for row in cells(leader.get(link).text) if row] == counted, label
