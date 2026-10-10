#!/usr/bin/env python3
"""Rebuild the demo database from scratch, with fictional data only.

    uv run python scripts/seed_demo.py

Wipes the database at CMS_DATABASE and creates the leader, two members, a
member's draft post, and one published post in each topic.
Passwords come from CMS_ADMIN_PASSWORD and CMS_EDITOR_PASSWORD (read from .env,
or from .env.example on a fresh clone); they are never printed.
"""
from __future__ import annotations

import os
import sys
from contextlib import closing

from app import accounts, content, db, settings
from app.content import PostFields

# (email, nickname, role, environment variable holding the password).
# tests/conftest.py uses the same emails and nicknames.
DEMO_USERS = [
    ("lider@albiazul.example", "El Capi", "admin", "CMS_ADMIN_PASSWORD"),
    ("ana@albiazul.example", "Rayada de Corazón", "editor", "CMS_EDITOR_PASSWORD"),
    ("beto@albiazul.example", "Furia del Cerro", "editor", "CMS_EDITOR_PASSWORD"),
]

# A post its member is still writing (written by ana@).
DRAFT = PostFields(
    title="Lo que se vio desde la cabecera norte",
    topic="match",
    body=(
        "Todavía lo estoy escribiendo, pero va la idea:\n\n"
        "- El primer tiempo fue **puro Rayados**.\n"
        "- En el segundo nos faltó *cerrar el partido*.\n\n"
        "> Aquí se viene a alentar, no a sufrir. (Mi tío, cada sábado.)\n\n"
        "Mañana le agrego lo del gol del triunfo.\n"
    ),
)

# One published post per topic, as (author's email, post). The Partido one is a
# tiradera aimed at Tigres: allowed by the house rules, which forbid only
# personal attacks. No real person is named.
PUBLISHED = [
    ("beto@albiazul.example", PostFields(
        title="Tigres, traigan pañuelos al Clásico Regio",
        topic="match",
        body=(
            "Se viene otro Clásico Regio y en la cabecera ya estamos listos.\n\n"
            "A los de **Tigres**, con cariño: vayan comprando pañuelos, porque el sábado"
            " el Cerro de la Silla se pinta de azul y blanco. Mucho rugido entre semana"
            " y puro maullido en la cancha.\n\n"
            "- Llegar temprano.\n"
            "- Cantar los noventa minutos.\n"
            "- Volver a casa con los tres puntos.\n"
        ),
    )),
    ("ana@albiazul.example", PostFields(
        title="El once que yo pondría el sábado",
        topic="lineup",
        body=(
            "Sin nombres, que luego se enojan en el grupo. Lo que pido es **orden atrás**"
            " y velocidad por las bandas:\n\n"
            "1. El portero de siempre, que anda en racha.\n"
            "2. Línea de cuatro, con el lateral izquierdo bien ofensivo.\n"
            "3. Dos de contención, para que no nos agarren al contragolpe.\n"
            "4. Arriba, el nueve fijo y alguien que llegue desde atrás.\n\n"
            "¿Ustedes cómo lo armarían?\n"
        ),
    )),
    ("ana@albiazul.example", PostFields(
        title="Al técnico hay que darle tiempo",
        topic="coach",
        body=(
            "Llevamos pocas jornadas con el cuerpo técnico nuevo y ya hay quien pide"
            " cambios. Yo digo que no.\n\n"
            "> Los procesos se juzgan al final del torneo, no después de un empate.\n\n"
            "Ya se nota la idea: presión alta y salir jugando desde atrás. Falta afinar,"
            " pero vamos bien.\n"
        ),
    )),
    ("beto@albiazul.example", PostFields(
        title="Lo que nos falta en el mercado de invierno",
        topic="signings",
        body=(
            "Con un **lateral izquierdo** y un central rápido nos alcanza para pelear"
            " arriba. No hace falta tirar la casa por la ventana: hace falta acertar.\n\n"
            "Y que esta vez lleguen *antes* de la pretemporada.\n"
        ),
    )),
    ("lider@albiazul.example", PostFields(
        title="Watch party del Clásico Regio",
        topic="fan-club-news",
        body=(
            "Este sábado vemos el Clásico juntos. Traigan su jersey, su bandera y su"
            " mejor garganta.\n\n"
            "- **Hora:** una hora antes del partido.\n"
            "- **Lugar:** se lo mandamos por mensaje a cada miembro.\n"
            "- **Regla de oro:** la tiradera a Tigres se vale; las faltas de respeto, no.\n"
        ),
    )),
]


def main() -> int:
    missing = sorted({var for *_, var in DEMO_USERS if not os.environ.get(var)})
    if missing:
        print(f"Set {', '.join(missing)} in .env (copy .env.example).")
        return 1

    path = settings.DATABASE_PATH
    path.unlink(missing_ok=True)
    db.init(path)
    with closing(db.connect(path)) as conn:
        users = {email: accounts.create_user(conn, email=email, password=os.environ[var],
                                             role=role, nickname=nickname)
                 for email, nickname, role, var in DEMO_USERS}
        content.create_post(conn, users["ana@albiazul.example"], DRAFT)
        for email, fields in PUBLISHED:
            # The seed acts as the leader; in the console a member's post is
            # submitted before the leader can publish it.
            post = content.create_post(conn, users[email], fields)
            content.move(conn, post, content.PUBLISH)

    print(f"Rebuilt {path} with these demo accounts:")
    for email, nickname, role, var in DEMO_USERS:
        print(f"  {email:<26} {role:<7} {nickname}  (password: ${var})")
    print(f"one draft post ({DRAFT.title}) and {len(PUBLISHED)} published posts,"
          " one per topic. Run `uv run cms publish` to export them to site/.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
