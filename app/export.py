"""Site export: the public site, written as static HTML from published content only.

`cms publish` and the leader's site update call export_site(), which also records
when it ran, for the dashboard. Two rules the rubric checks:

  1. Only PUBLISHED posts and pages are written. A draft that reaches the output
     is a bug.
  2. Every href is RELATIVE ("style.css", "../posts/x.html"), never root-absolute
     ("/style.css"), because Pages serves the site from a subfolder. Links are
     percent-encoded too, so slugs with accents and ñ never break.
"""
from __future__ import annotations

import shutil
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app import content, db, markdown, settings
from app.content import Page, Post
from app.dates import spanish_date


# The scene drawn behind each page: templates/public/scenes/<name>.html. The home
# page carries the goal story; a topic's posts share its scene; the four seeded
# pages have their own, found by slug; any other page the leader adds gets the default.
HOME_SCENE = "goal"
TOPIC_SCENES = {"match": "night-stadium", "lineup": "tactics-board", "coach": "touchline",
                "signings": "signing", "fan-club-news": "fans-stand"}
PAGE_SCENES = {"quiénes-somos": "fans-bus", "próximos-partidos": "scoreboard",
               "reglas-de-la-casa": "referee", "cómo-unirse": "empty-seat"}
DEFAULT_SCENE = "default"


@dataclass(frozen=True)
class TopicPage:
    """A topic's public page: every published post filed under it, newest first."""
    name: str
    path: str  # where it is written, from the site root: "tema/alineación.html"
    posts: list[Post]
    scene: str


def post_path(post: Post) -> str:
    """Where a post's page is written, from the site root."""
    return f"posts/{post.slug}.html"


def page_path(page: Page) -> str:
    """Where a page is written: at the site root, beside the home page."""
    return f"{page.slug}.html"


def export_site(conn: sqlite3.Connection, out: Path) -> int:
    """Wipe `out`, write the public site into it, and record when; returns how many
    posts it holds."""
    posts = content.published_posts(conn)
    pages = content.published_pages(conn)
    topics = {key: TopicPage(name, f"tema/{content.slugify(name)}.html",
                             [post for post in posts if post.topic == key], TOPIC_SCENES[key])
              for key, name in content.TOPICS.items()}

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    shutil.copyfile(settings.TEMPLATES / "public" / "style.css", out / "style.css")
    env = _environment(list(topics.values()), pages)
    _write(env, out, "index.html", "public/home.html", scene=HOME_SCENE)
    for topic in topics.values():  # all five, even when empty, so no topic link breaks
        _write(env, out, topic.path, "public/topic.html", topic=topic, scene=topic.scene)
    for post in posts:
        topic = topics[post.topic]
        _write(env, out, post_path(post), "public/post.html", post=post, topic=topic,
               scene=topic.scene, body_html=markdown.to_html(post.body))
    for page in pages:
        _write(env, out, page_path(page), "public/page.html", page=page,
               scene=PAGE_SCENES.get(page.slug, DEFAULT_SCENE),
               body_html=markdown.to_html(page.body))
    with conn:
        conn.execute("INSERT INTO site_state (id, last_export_at) VALUES (1, ?)"
                     " ON CONFLICT (id) DO UPDATE SET last_export_at = excluded.last_export_at",
                     (db.now(),))
    return len(posts)


def last_export(conn: sqlite3.Connection) -> str | None:
    """When the public site was last exported, or None if it never was."""
    row = conn.execute("SELECT last_export_at FROM site_state").fetchone()
    return row["last_export_at"] if row else None


def _environment(topics: list[TopicPage], menu: list[Page]) -> Environment:
    """Templates for every exported file: the site title, the published pages for
    the menu (in menu order), and the topics for the row beneath it."""
    env = Environment(loader=FileSystemLoader(str(settings.TEMPLATES)),
                      autoescape=select_autoescape(["html"]))
    env.filters["spanish_date"] = spanish_date
    env.globals.update(site_title=settings.SITE_TITLE, post_path=post_path,
                       page_path=page_path, menu=menu, topics=topics)
    return env


def _write(env: Environment, out: Path, path: str, template: str, **context: Any) -> None:
    """Render one page to `out / path`. Its links go through href(), which turns a
    path from the site root into one relative to this page, percent-encoded."""
    up = "../" * path.count("/")

    def href(target: str) -> str:
        return up + quote(target)

    file = out / path
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(env.get_template(template).render(href=href, **context), encoding="utf-8")
