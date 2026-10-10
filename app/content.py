"""Content: posts, their slugs, and the post lifecycle.

Topics are a fixed list here, not a table: members cannot add topics.
"""
from __future__ import annotations

import re
import sqlite3
import unicodedata
from dataclasses import dataclass

from app import db
from app.accounts import User

# Key stored in the database -> the Spanish name readers see, in the fixed order.
TOPICS = {
    "match": "Partido",
    "lineup": "Alineación",
    "coach": "Técnico",
    "signings": "Fichajes",
    "fan-club-news": "Noticias del club de aficionados",
}

STATUS_NAMES = {"draft": "Borrador", "submitted": "Enviada", "published": "Publicada"}

SLUG_MAX = 80
SLUG_FALLBACK = "publicación"  # for a title with no letters or digits at all


class ContentError(ValueError):
    """A refused change; the message is shown to the person as it is."""


@dataclass(frozen=True)
class PostFields:
    """What a person types into the post editor."""
    title: str
    topic: str
    body: str
    slug: str = ""

    @property
    def typed_slug(self) -> str:
        """The slug as typed, NFC-normalized; empty when left for the title to make."""
        return unicodedata.normalize("NFC", self.slug.strip())


@dataclass(frozen=True)
class Post:
    id: int
    title: str
    slug: str
    body: str
    topic: str
    status: str
    author_id: int
    author_nickname: str | None
    created_at: str
    updated_at: str

    @property
    def topic_name(self) -> str:
        return TOPICS[self.topic]

    @property
    def status_name(self) -> str:
        return STATUS_NAMES[self.status]


def slugify(text: str) -> str:
    """NFC-normalized and lowercased; letters (accents and ñ included) and digits
    kept; every other run of characters becomes one hyphen; at most SLUG_MAX long."""
    text = unicodedata.normalize("NFC", text).lower()
    return re.sub(r"[\W_]+", "-", text).strip("-")[:SLUG_MAX].strip("-") or SLUG_FALLBACK


def _validate(fields: PostFields) -> None:
    if not fields.title.strip():
        raise ContentError("Escribe un título.")
    if fields.topic not in TOPICS:
        raise ContentError("Elige uno de los cinco temas.")


def _slug_for(conn: sqlite3.Connection, fields: PostFields, post_id: int | None = None) -> str:
    """The slug typed into the editor, or one made from the title when left empty."""
    wanted = fields.typed_slug or slugify(fields.title)
    if slugify(wanted) != wanted:
        raise ContentError("El enlace solo puede tener letras minúsculas, números y guiones"
                           f" sueltos, hasta {SLUG_MAX} caracteres. Por ejemplo:"
                           f" {slugify(wanted)}")
    return _free_slug(conn, wanted, post_id)


def _free_slug(conn: sqlite3.Connection, wanted: str, post_id: int | None = None) -> str:
    """`wanted`, or else `wanted-2`, `wanted-3`, …: the first that no other post uses."""
    slug, number = wanted, 1
    while conn.execute("SELECT 1 FROM posts WHERE slug = ? AND id IS NOT ?",
                       (slug, post_id)).fetchone():
        number += 1
        suffix = f"-{number}"
        slug = wanted[:SLUG_MAX - len(suffix)].rstrip("-") + suffix
    return slug


_SELECT = ("SELECT posts.*, users.nickname AS author_nickname"
           " FROM posts JOIN users ON users.id = posts.author_id")


def _post_from_row(row: sqlite3.Row) -> Post:
    return Post(id=row["id"], title=row["title"], slug=row["slug"], body=row["body"],
                topic=row["topic"], status=row["status"], author_id=row["author_id"],
                author_nickname=row["author_nickname"], created_at=row["created_at"],
                updated_at=row["updated_at"])


def create_post(conn: sqlite3.Connection, author: User, fields: PostFields) -> Post:
    """A new draft written by `author`."""
    _validate(fields)
    now = db.now()
    slug = _slug_for(conn, fields)
    with conn:
        cursor = conn.execute(
            "INSERT INTO posts (title, slug, body, topic, status, author_id,"
            " created_at, updated_at) VALUES (?, ?, ?, ?, 'draft', ?, ?, ?)",
            (fields.title, slug, fields.body, fields.topic, author.id, now, now),
        )
    post = get_post(conn, cursor.lastrowid)
    assert post is not None
    return post


def save_post(conn: sqlite3.Connection, post: Post, fields: PostFields) -> Post:
    """Save: new title, topic, body and slug; the status stays as it is."""
    _validate(fields)
    slug = _slug_for(conn, fields, post.id)
    with conn:
        conn.execute(
            "UPDATE posts SET title = ?, slug = ?, body = ?, topic = ?, updated_at = ?"
            " WHERE id = ?",
            (fields.title, slug, fields.body, fields.topic, db.now(), post.id),
        )
    saved = get_post(conn, post.id)
    assert saved is not None
    return saved


def delete_post(conn: sqlite3.Connection, post: Post) -> None:
    with conn:
        conn.execute("DELETE FROM posts WHERE id = ?", (post.id,))


def get_post(conn: sqlite3.Connection, post_id: int | None) -> Post | None:
    row = conn.execute(f"{_SELECT} WHERE posts.id = ?", (post_id,)).fetchone()
    return _post_from_row(row) if row else None


def list_posts(conn: sqlite3.Connection) -> list[Post]:
    """Every post from every author, most recently updated first."""
    rows = conn.execute(f"{_SELECT} ORDER BY posts.updated_at DESC, posts.id DESC").fetchall()
    return [_post_from_row(row) for row in rows]
