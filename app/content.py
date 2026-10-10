"""Content: posts, their slugs, and the post lifecycle.

Topics are a fixed list here, not a table: members cannot add topics.
"""
from __future__ import annotations

import re
import sqlite3
import unicodedata
from dataclasses import dataclass
from enum import StrEnum

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


class Status(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    PUBLISHED = "published"


STATUS_NAMES = {Status.DRAFT: "Borrador", Status.SUBMITTED: "Enviada",
                Status.PUBLISHED: "Publicada"}

SLUG_MAX = 80
SLUG_FALLBACK = "publicación"  # for a title with no letters or digits at all


class ContentError(ValueError):
    """A refused change; the message is shown to the person as it is."""


@dataclass(frozen=True)
class Transition:
    starts: frozenset[Status]  # the statuses this action may start from
    leads_to: Status
    refused: str               # shown when the post's status is not one of `starts`


# The post lifecycle (spec #1), one transition per action. Who may take each
# action is Policy's question; these only say which moves exist.

# Publish: readers see it from the next site update on.
PUBLISH = Transition(frozenset({Status.DRAFT, Status.SUBMITTED}), Status.PUBLISHED,
                     "Esta publicación ya está publicada.")
# Unpublish: back to draft; gone from the public site at the next site update.
UNPUBLISH = Transition(frozenset({Status.PUBLISHED}), Status.DRAFT,
                       "Solo se puede despublicar una publicación publicada.")


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
    status: Status
    author_id: int
    author_nickname: str | None
    created_at: str
    updated_at: str
    first_published_at: str | None  # set once, never cleared

    @property
    def slug_locked(self) -> bool:
        """Once first published, the slug never changes: shared links keep working."""
        return self.first_published_at is not None

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


def _slug_for(conn: sqlite3.Connection, fields: PostFields, post: Post | None = None) -> str:
    """The slug typed into the editor, or one made from the title when left empty.
    A post first published keeps the slug it has."""
    if post is not None and post.slug_locked:
        if fields.typed_slug not in ("", post.slug):
            raise ContentError("El enlace ya no se puede cambiar: la publicación ya se publicó"
                               " y alguien pudo haber compartido su enlace.")
        return post.slug
    wanted = fields.typed_slug or slugify(fields.title)
    if slugify(wanted) != wanted:
        raise ContentError("El enlace solo puede tener letras minúsculas, números y guiones"
                           f" sueltos, hasta {SLUG_MAX} caracteres. Por ejemplo:"
                           f" {slugify(wanted)}")
    return _free_slug(conn, wanted, post.id if post else None)


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
                topic=row["topic"], status=Status(row["status"]), author_id=row["author_id"],
                author_nickname=row["author_nickname"], created_at=row["created_at"],
                updated_at=row["updated_at"], first_published_at=row["first_published_at"])


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
    slug = _slug_for(conn, fields, post)
    with conn:
        conn.execute(
            "UPDATE posts SET title = ?, slug = ?, body = ?, topic = ?, updated_at = ?"
            " WHERE id = ?",
            (fields.title, slug, fields.body, fields.topic, db.now(), post.id),
        )
    saved = get_post(conn, post.id)
    assert saved is not None
    return saved


def move(conn: sqlite3.Connection, post: Post, transition: Transition) -> Post:
    """Take a lifecycle step, refused unless the post's status allows it. Becoming
    published sets first-published the first time only."""
    if post.status not in transition.starts:
        raise ContentError(transition.refused)
    now = db.now()
    first_published = post.first_published_at or (
        now if transition.leads_to == Status.PUBLISHED else None)
    with conn:
        conn.execute("UPDATE posts SET status = ?, updated_at = ?, first_published_at = ?"
                     " WHERE id = ?", (transition.leads_to, now, first_published, post.id))
    moved = get_post(conn, post.id)
    assert moved is not None
    return moved


def delete_post(conn: sqlite3.Connection, post: Post) -> None:
    with conn:
        conn.execute("DELETE FROM posts WHERE id = ?", (post.id,))


def get_post(conn: sqlite3.Connection, post_id: int | None) -> Post | None:
    row = conn.execute(f"{_SELECT} WHERE posts.id = ?", (post_id,)).fetchone()
    return _post_from_row(row) if row else None


def published_posts(conn: sqlite3.Connection) -> list[Post]:
    """Every published post, the most recently first published first: all that
    readers ever see."""
    rows = conn.execute(f"{_SELECT} WHERE posts.status = ?"
                        " ORDER BY posts.first_published_at DESC, posts.id DESC",
                        (Status.PUBLISHED,)).fetchall()
    return [_post_from_row(row) for row in rows]


def list_posts(conn: sqlite3.Connection) -> list[Post]:
    """Every post from every author, most recently updated first."""
    rows = conn.execute(f"{_SELECT} ORDER BY posts.updated_at DESC, posts.id DESC").fetchall()
    return [_post_from_row(row) for row in rows]
