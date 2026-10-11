# Club de Aficionados Albiazul CMS (IPHS 400 Mini-Project #2)

A small CMS for an unofficial fan club of Rayados (C.F. Monterrey). Members write posts about
the team, and the leader checks each one before it goes public. Fans read the result on a
static public site. The admin console (FastAPI, Jinja and SQLite) runs only on the leader's
computer; `cms publish` exports the published content to `site/`, and `cms deploy` puts it
on GitHub Pages (ADR-001).

The spec is issue #1 and the tickets are #2–#9, each with its code-review findings in a
comment. The vocabulary is in `CONTEXT.md`, and the decisions that shaped the design are in
`docs/adr/`.

## Live URL

The public site, the Club de Aficionados Albiazul fan site, is at
<https://maxillamas06-arch.github.io/iphs400-mp2-cms/>. It shows only what the leader has
published, as of the last *Actualizar el sitio*. Screenshots of the admin console at 1280 px
and 390 px are in `docs/screenshots/`.

## Run locally

```bash
uv sync
cp .env.example .env                  # optional: without it, .env.example is used
uv run python scripts/seed_demo.py    # wipes and rebuilds cms.db with demo accounts
uv run cms serve                      # then open http://localhost:8000/admin
uv run cms publish                    # export the public site to site/ from published posts and pages
python3 -m http.server -d site 8001   # preview it at http://localhost:8001
uv run cms deploy                     # put site/ online (the gh-pages branch)
```

In the console, the leader's *Actualizar el sitio* button on the *Panel* does both
`cms publish` and `cms deploy`, says how each step went, and the *Panel* shows when the site
was last generated.

Demo accounts (all fictional; passwords are the values in `.env`):

| Email | Role | Nickname | Password |
|---|---|---|---|
| `lider@albiazul.example` | leader (admin) | El Capi | `CMS_ADMIN_PASSWORD` |
| `ana@albiazul.example` | member (editor) | Rayada de Corazón | `CMS_EDITOR_PASSWORD` |
| `beto@albiazul.example` | member (editor) | Furia del Cerro | `CMS_EDITOR_PASSWORD` |

The seed also adds one draft post written by Rayada de Corazón (open *Publicaciones*), one
post by Furia del Cerro waiting for the leader's review (the *Esperando revisión* count on the
leader's *Panel*), and one published post in each of the five topics, so the exported site has
something in every section. Rayada de Corazón has also proposed changes to her published lineup
post: the *Cambios propuestos* count on the *Panel* opens it, and the leader compares the two
versions side by side before approving or sending them back. Last, the seed publishes the fan
club's four pages, which the public menu lists in this order: *Quiénes somos*, *Próximos
partidos*, *Reglas de la casa* and *Cómo unirse*. The leader manages them under *Páginas*;
members never see them in the admin console.

## What is here

```text
app/               the CMS: accounts, policy, content, markdown, export, site_update, routes/
templates/         admin/ for the console, public/ for the exported site (inline SVG drawings)
tests/             one file per ticket (test_t0N_*.py), each test named for its criterion;
                   shared helpers such as client_as("editor") in conftest.py
scripts/           seed_demo.py, check_submission.py, usage_report.py
.claude/hooks/     the context meter, usage ledger and transcript hooks
docs/              adr/, screenshots/, handoff/, transcripts/, the manual and the rubric
CONTEXT.md         the glossary
```

Before submitting, run `uv run python scripts/check_submission.py --stage 2`.

## Generative AI Use Statement

*(Required. Replace this section: name the models and skills you used, quote two
prompts you really sent, describe one real model failure, and include a
"Backends used" table if you ever switched providers.)*
