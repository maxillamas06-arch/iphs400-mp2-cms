"""T08 (#9): the seed matches the spec's demo data list.

Each test name says which acceptance criterion of #9 it covers. Earlier tickets'
seed tests check each piece in depth; this one checks the whole list at once.
"""
from __future__ import annotations

import re

from fastapi.testclient import TestClient


def text(html: str) -> str:
    """What a reader sees of this HTML: tags dropped, spaces collapsed."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def test_seed_matches_the_spec_demo_data_list_and_runs_clean_from_env_example(
        tmp_path, run_seed, app_for, login, env_example, dashboard_counts, export):
    database = tmp_path / "seeded.db"

    result = run_seed(database)

    assert result.returncode == 0 and result.stderr == "", result.stderr
    leader = TestClient(app_for(database))
    assert login(leader, "lider@albiazul.example",
                 env_example["CMS_ADMIN_PASSWORD"]).status_code == 303
    counts = {label: number for label, (number, _) in dashboard_counts(leader).items()}
    assert counts == {"Borradores": "1", "Esperando revisión": "1", "Publicadas": "5",
                      "Cambios propuestos": "1", "Páginas": "4", "Miembros activos": "2"}
    assert "Sitio generado por última vez: nunca" in text(leader.get("/admin").text)

    site = export(database)
    home = (site / "index.html").read_text()
    topics = [text(h2) for h2 in re.findall(r"<h2>(.*?)</h2>", home, re.S)]
    assert topics == ["Partido", "Alineación", "Técnico", "Fichajes",
                      "Noticias del club de aficionados"], "a published post in every topic"
    match = text((site / "tema" / "partido.html").read_text())
    assert "Tigres" in match, "an obvious tiradera aimed at Tigres"
    menu = re.search(r'<nav class="menu"[^>]*>(.*?)</nav>', home, re.S).group(1)
    assert text(menu) == "Inicio Quiénes somos Próximos partidos Reglas de la casa Cómo unirse"
    every_page = "".join(path.read_text() for path in site.rglob("*.html"))
    emails = set(re.findall(r"[\w.+-]+@[\w.-]+", every_page))
    assert emails == {"unete@albiazul.example"}, "no member's email reaches the public site"
