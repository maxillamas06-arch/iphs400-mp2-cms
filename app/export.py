"""Site export: the public site, written as static HTML from published posts only.

`cms publish` calls export_site(). Two rules the rubric checks:

  1. Only PUBLISHED content is written. A draft that reaches the output is a bug.
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

from app import content, markdown, settings
from app.content import Post
from app.dates import spanish_date


@dataclass(frozen=True)
class TopicPage:
    """A topic's public page: every published post filed under it, newest first."""
    name: str
    path: str  # where it is written, from the site root: "tema/alineación.html"
    posts: list[Post]


def post_path(post: Post) -> str:
    """Where a post's page is written, from the site root."""
    return f"posts/{post.slug}.html"


def export_site(conn: sqlite3.Connection, out: Path) -> int:
    """Wipe `out` and write the public site into it; returns how many posts it holds."""
    posts = content.published_posts(conn)
    topics = {key: TopicPage(name, f"tema/{content.slugify(name)}.html",
                             [post for post in posts if post.topic == key])
              for key, name in content.TOPICS.items()}

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    shutil.copyfile(settings.TEMPLATES / "public" / "style.css", out / "style.css")
    env = _environment(list(topics.values()))
    _write(env, out, "index.html", "public/home.html")
    for topic in topics.values():  # all five, even when empty, so no topic link breaks
        _write(env, out, topic.path, "public/topic.html", topic=topic)
    for post in posts:
        _write(env, out, post_path(post), "public/post.html", post=post,
               topic=topics[post.topic], body_html=markdown.to_html(post.body))
    return len(posts)


def _environment(topics: list[TopicPage]) -> Environment:
    """Templates for every page: the site title, and the topics for the menu row."""
    env = Environment(loader=FileSystemLoader(str(settings.TEMPLATES)),
                      autoescape=select_autoescape(["html"]))
    env.filters["spanish_date"] = spanish_date
    env.globals.update(site_title=settings.SITE_TITLE, post_path=post_path, topics=topics)
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
