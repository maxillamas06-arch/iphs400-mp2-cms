"""T08 (#9): the public site's final look, drawn inline with no image files.

Each test name says which acceptance criterion of #9 it covers. Whether the
drawings are original, and readable at 390 px, is checked by hand.
"""
from __future__ import annotations

import re


def footer(html: str) -> str:
    return re.search(r"<footer[^>]*>(.*?)</footer>", html, re.S).group(1)


def test_home_page_has_an_inline_cerro_de_la_silla_banner_and_no_other_page_does(
        published_post, published_page, export):
    published_post(title="Crónica del Clásico Regio")
    published_page(title="Quiénes somos")

    site = export()

    home = (site / "index.html").read_text()
    banner = re.search(r'<svg\b[^>]*aria-label="Cerro de la Silla"[^>]*>', home)
    assert banner and 'role="img"' in banner.group(0)
    assert home.index('aria-label="Cerro de la Silla"') < home.index("<main"), "on top"
    for path in site.rglob("*.html"):
        if path.name != "index.html":
            assert 'aria-label="Cerro de la Silla"' not in path.read_text(), path.name


def test_every_public_page_has_a_stadium_silhouette_above_the_disclaimer(
        published_post, published_page, export):
    published_post(title="Crónica del Clásico Regio")
    published_page(title="Quiénes somos")

    pages = list(export().rglob("*.html"))

    assert len(pages) == 1 + 5 + 1 + 1  # home, five topics, the post, the page
    for path in pages:
        bottom = footer(path.read_text())
        stadium = re.search(r'<svg\b[^>]*class="stadium"[^>]*>', bottom)
        assert stadium, f"no stadium silhouette in the footer of {path.name}"
        assert 'aria-hidden="true"' in stadium.group(0), "decoration, skipped by screen readers"
        assert bottom.index('class="stadium"') < bottom.index("Sitio de aficionados."), path.name


def test_the_drawings_are_inline_with_no_image_files_or_photos(
        published_post, published_page, export):
    published_post(title="Crónica del Clásico Regio", body="![escudo](escudo.png) Ganamos.")
    published_page(title="Quiénes somos")

    site = export()

    files = [path for path in site.rglob("*") if path.is_file()]
    assert {path.suffix for path in files} == {".html", ".css"}, "no image files"
    for path in files:
        page = path.read_text()
        assert not re.search(r"<img\b|<image\b|<picture\b|url\(|\bsrc=", page), (
            f"{path.name} loads a picture")
