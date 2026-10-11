"""Content: posts, pages, their slugs, and the post lifecycle.

Topics are a fixed list here, not a table: members cannot add topics.
"""
from __future__ import annotations

import re
import sqlite3
import unicodedata
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

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

# The leader's content list filters posts vs pages: key -> the name people see.
CONTENT_TYPES = {"post": "Publicaciones", "page": "Páginas"}

SLUG_MAX = 80
SLUG_FALLBACK = "publicación"  # for a title with no letters or digits at all
# Pages are written at the site root, so a page may not take a name the site
# already uses there. Each name -> what the site uses it for.
RESERVED_PAGE_SLUGS = {"index": "la portada", "tema": "las páginas de los temas",
                       "posts": "las publicaciones", "style": "el estilo del sitio"}


# The tables whose rows have a slug and a status, named in the SQL built below.
Table = Literal["posts", "pages"]


class ContentError(ValueError):
    """A refused change; the message is shown to the person as it is."""


@dataclass(frozen=True)
class Transition:
    starts: frozenset[Status]  # the statuses this action may start from
    leads_to: Status
    refused: str               # shown when the post's status is not one of `starts`
    # Shown when the post has a pending edit and this action must wait for the
    # leader to answer it; None when a pending edit does not matter.
    refused_pending_edit: str | None = None


# The post lifecycle (spec #1), one transition per action. Who may take each
# action is Policy's question; these only say which moves exist.

# Submit: the member hands their finished draft to the leader for checking.
SUBMIT = Transition(frozenset({Status.DRAFT}), Status.SUBMITTED,
                    "Solo se puede enviar un borrador.")
# Withdraw: the member takes their submitted post back to keep working on it.
WITHDRAW = Transition(frozenset({Status.SUBMITTED}), Status.DRAFT,
                      "Solo se puede retirar una publicación enviada.")
# Publish: readers see it from the next site update on.
PUBLISH = Transition(frozenset({Status.DRAFT, Status.SUBMITTED}), Status.PUBLISHED,
                     "Esta publicación ya está publicada.")
# Send back: the leader says no to a submitted post; its member can rework it.
SEND_BACK = Transition(frozenset({Status.SUBMITTED}), Status.DRAFT,
                       "Solo se puede devolver una publicación enviada.")
# Unpublish: back to draft; gone from the public site at the next site update.
# Never while a pending edit waits, so a member's proposal is not silently lost.
UNPUBLISH = Transition(frozenset({Status.PUBLISHED}), Status.DRAFT,
                       "Solo se puede despublicar una publicación publicada.",
                       "No se puede despublicar mientras haya cambios propuestos sin revisar:"
                       " apruébalos o devuélvelos primero.")

# Pages have no submitted step: only the leader writes them, and publishes them
# straight from draft.
PUBLISH_PAGE = Transition(frozenset({Status.DRAFT}), Status.PUBLISHED,
                          "Esta página ya está publicada.")
UNPUBLISH_PAGE = Transition(frozenset({Status.PUBLISHED}), Status.DRAFT,
                            "Solo se puede despublicar una página publicada.")


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
class PendingEdit:
    """A member's proposed change to their published post: the published version
    stays public until the leader approves it or sends it back. Never the slug."""
    title: str
    topic: str
    body: str
    created_at: str
    updated_at: str

    @property
    def topic_name(self) -> str:
        return TOPICS[self.topic]


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
    edited_at: str | None  # last changed while published: "Actualizado el …"
    pending_edit: PendingEdit | None  # at most one, only while published

    @property
    def edited_since_pending_edit(self) -> bool:
        """The published version was edited directly after its pending edit was
        first proposed, so approving the edit would also undo that edit. (Stored
        times share one UTC format, so they compare as text.)"""
        return (self.pending_edit is not None and self.edited_at is not None
                and self.edited_at > self.pending_edit.created_at)

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


@dataclass(frozen=True)
class PageFields:
    """What the leader types into the page editor."""
    title: str
    body: str
    menu_order: str
    slug: str = ""

    @property
    def typed_slug(self) -> str:
        """The slug as typed, NFC-normalized; empty when left for the title to make."""
        return unicodedata.normalize("NFC", self.slug.strip())


@dataclass(frozen=True)
class Page:
    """Fixed fan-club information shown in the public menu. Only the leader writes
    pages, so a page is a draft or published, never submitted."""
    id: int
    title: str
    slug: str
    body: str
    status: Status
    menu_order: int  # the public menu lists published pages from the lowest up
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


def _slug_for(conn: sqlite3.Connection, table: Table, fields: PostFields | PageFields,
              item: Post | Page | None = None) -> str:
    """The slug typed into the editor, or one made from the title when left empty,
    free among the rows of `table` ("posts" or "pages"). A post or page first
    published keeps the slug it has."""
    if item is not None and item.slug_locked:
        if fields.typed_slug not in ("", item.slug):
            raise ContentError("El enlace ya no se puede cambiar: ya se publicó"
                               " y alguien pudo haber compartido su enlace.")
        return item.slug
    wanted = fields.typed_slug or slugify(fields.title)
    if slugify(wanted) != wanted:
        raise ContentError("El enlace solo puede tener letras minúsculas, números y guiones"
                           f" sueltos, hasta {SLUG_MAX} caracteres. Por ejemplo:"
                           f" {slugify(wanted)}")
    return _free_slug(conn, table, wanted, item.id if item else None)


def _free_slug(conn: sqlite3.Connection, table: Table, wanted: str,
               item_id: int | None = None) -> str:
    """`wanted`, or else `wanted-2`, `wanted-3`, …: the first no other row of `table` uses."""
    slug, number = wanted, 1
    while conn.execute(f"SELECT 1 FROM {table} WHERE slug = ? AND id IS NOT ?",
                       (slug, item_id)).fetchone():
        number += 1
        suffix = f"-{number}"
        slug = wanted[:SLUG_MAX - len(suffix)].rstrip("-") + suffix
    return slug


_SELECT = ("SELECT posts.*, users.nickname AS author_nickname,"
           " pending_edits.title AS pending_title, pending_edits.topic AS pending_topic,"
           " pending_edits.body AS pending_body, pending_edits.created_at AS pending_created_at,"
           " pending_edits.updated_at AS pending_updated_at"
           " FROM posts JOIN users ON users.id = posts.author_id"
           " LEFT JOIN pending_edits ON pending_edits.post_id = posts.id")


def _post_from_row(row: sqlite3.Row) -> Post:
    pending_edit = None if row["pending_title"] is None else PendingEdit(
        title=row["pending_title"], topic=row["pending_topic"], body=row["pending_body"],
        created_at=row["pending_created_at"], updated_at=row["pending_updated_at"])
    return Post(id=row["id"], title=row["title"], slug=row["slug"], body=row["body"],
                topic=row["topic"], status=Status(row["status"]), author_id=row["author_id"],
                author_nickname=row["author_nickname"], created_at=row["created_at"],
                updated_at=row["updated_at"], first_published_at=row["first_published_at"],
                edited_at=row["edited_at"], pending_edit=pending_edit)


def create_post(conn: sqlite3.Connection, author: User, fields: PostFields) -> Post:
    """A new draft written by `author`."""
    _validate(fields)
    now = db.now()
    slug = _slug_for(conn, "posts", fields)
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
    """Save: new title, topic, body and slug; the status stays as it is. Saving a
    published post (the leader's direct edit) marks it as edited after publishing."""
    _validate(fields)
    slug = _slug_for(conn, "posts", fields, post)
    now = db.now()
    edited = now if post.status == Status.PUBLISHED else post.edited_at
    with conn:
        conn.execute(
            "UPDATE posts SET title = ?, slug = ?, body = ?, topic = ?, updated_at = ?,"
            " edited_at = ? WHERE id = ?",
            (fields.title, slug, fields.body, fields.topic, now, edited, post.id),
        )
    saved = get_post(conn, post.id)
    assert saved is not None
    return saved


def propose_edit(conn: sqlite3.Connection, post: Post, fields: PostFields) -> Post:
    """Propose edit: the member's new title, topic and body wait for the leader as
    the post's pending edit, replacing any earlier one. The published version
    stays as it is, and so does the slug."""
    if post.status != Status.PUBLISHED:
        raise ContentError("Solo se pueden proponer cambios a una publicación publicada.")
    _validate(fields)
    _slug_for(conn, "posts", fields, post)  # the slug is locked: a different one is refused
    now = db.now()
    with conn:
        conn.execute(
            "INSERT INTO pending_edits (post_id, title, topic, body, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT (post_id) DO UPDATE SET"
            " title = excluded.title, topic = excluded.topic, body = excluded.body,"
            " updated_at = excluded.updated_at",
            (post.id, fields.title, fields.topic, fields.body, now, now),
        )
    proposed = get_post(conn, post.id)
    assert proposed is not None
    return proposed


def approve_edit(conn: sqlite3.Connection, post: Post) -> Post:
    """Approve: the pending edit replaces the published title, topic and body and
    is removed. Readers see the new version, marked "Actualizado el …", from the
    next site update on."""
    edit = _require_pending_edit(post)
    now = db.now()
    with conn:
        conn.execute("UPDATE posts SET title = ?, topic = ?, body = ?, updated_at = ?,"
                     " edited_at = ? WHERE id = ?",
                     (edit.title, edit.topic, edit.body, now, now, post.id))
        conn.execute("DELETE FROM pending_edits WHERE post_id = ?", (post.id,))
    approved = get_post(conn, post.id)
    assert approved is not None
    return approved


def send_back_edit(conn: sqlite3.Connection, post: Post) -> Post:
    """Send back a pending edit: it is thrown away; the published version stays
    as it is."""
    _require_pending_edit(post)
    with conn:
        conn.execute("DELETE FROM pending_edits WHERE post_id = ?", (post.id,))
    sent_back = get_post(conn, post.id)
    assert sent_back is not None
    return sent_back


def _require_pending_edit(post: Post) -> PendingEdit:
    if post.pending_edit is None:
        raise ContentError("Esta publicación no tiene cambios propuestos.")
    return post.pending_edit


def move(conn: sqlite3.Connection, post: Post, transition: Transition) -> Post:
    """Take a lifecycle step, refused unless the post's status allows it. Becoming
    published sets first-published the first time only."""
    if post.status not in transition.starts:
        raise ContentError(transition.refused)
    if post.pending_edit is not None and transition.refused_pending_edit:
        raise ContentError(transition.refused_pending_edit)
    _set_status(conn, "posts", post, transition.leads_to)
    moved = get_post(conn, post.id)
    assert moved is not None
    return moved


def _set_status(conn: sqlite3.Connection, table: Table, item: Post | Page,
                status: Status) -> None:
    """Becoming published sets first-published the first time only."""
    now = db.now()
    first_published = item.first_published_at or (
        now if status == Status.PUBLISHED else None)
    with conn:
        conn.execute(f"UPDATE {table} SET status = ?, updated_at = ?, first_published_at = ?"
                     " WHERE id = ?", (status, now, first_published, item.id))


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


def count_by_status(conn: sqlite3.Connection) -> dict[Status, int]:
    """How many posts there are in each status, every author's, zeros included."""
    found = {row["status"]: row["number"] for row in conn.execute(
        "SELECT status, COUNT(*) AS number FROM posts GROUP BY status")}
    return {status: found.get(status, 0) for status in Status}


def count_pending_edits(conn: sqlite3.Connection) -> int:
    """How many published posts have a pending edit waiting for the leader."""
    return conn.execute("SELECT COUNT(*) FROM pending_edits").fetchone()[0]


def list_posts(conn: sqlite3.Connection, status: Status | None = None,
               topic: str | None = None, with_pending_edit: bool = False) -> list[Post]:
    """Every post from every author, most recently updated first; only those in
    this status, filed under this topic, or with a pending edit, when asked."""
    rows = conn.execute(f"{_SELECT} WHERE (:status IS NULL OR posts.status = :status)"
                        " AND (:topic IS NULL OR posts.topic = :topic)"
                        " AND (NOT :with_pending_edit OR pending_edits.post_id IS NOT NULL)"
                        " ORDER BY posts.updated_at DESC, posts.id DESC",
                        {"status": status, "topic": topic,
                         "with_pending_edit": with_pending_edit}).fetchall()
    return [_post_from_row(row) for row in rows]


def _validate_page(fields: PageFields) -> None:
    if not fields.title.strip():
        raise ContentError("Escribe un título.")
    if not re.fullmatch(r"[0-9]{1,3}", fields.menu_order.strip()):
        raise ContentError("El orden en el menú es un número entero del 0 al 999:"
                           " el menú lista primero el número más bajo.")


_SELECT_PAGES = ("SELECT pages.*, users.nickname AS author_nickname"
                 " FROM pages JOIN users ON users.id = pages.author_id")


def _page_from_row(row: sqlite3.Row) -> Page:
    return Page(id=row["id"], title=row["title"], slug=row["slug"], body=row["body"],
                status=Status(row["status"]), menu_order=row["menu_order"],
                author_id=row["author_id"], author_nickname=row["author_nickname"],
                created_at=row["created_at"], updated_at=row["updated_at"],
                first_published_at=row["first_published_at"])


def _page_slug_for(conn: sqlite3.Connection, fields: PageFields, page: Page | None = None) -> str:
    """A post's slug rules, and never a name the site uses at its root."""
    slug = _slug_for(conn, "pages", fields, page)
    if slug in RESERVED_PAGE_SLUGS:
        raise ContentError(f"El enlace «{slug}» ya lo usa el sitio para"
                           f" {RESERVED_PAGE_SLUGS[slug]}: elige otro.")
    return slug


def create_page(conn: sqlite3.Connection, author: User, fields: PageFields) -> Page:
    """A new draft page written by `author`, the leader."""
    _validate_page(fields)
    slug = _page_slug_for(conn, fields)
    now = db.now()
    with conn:
        cursor = conn.execute(
            "INSERT INTO pages (title, slug, body, status, menu_order, author_id,"
            " created_at, updated_at) VALUES (?, ?, ?, 'draft', ?, ?, ?, ?)",
            (fields.title, slug, fields.body, int(fields.menu_order), author.id, now, now),
        )
    page = get_page(conn, cursor.lastrowid)
    assert page is not None
    return page


def get_page(conn: sqlite3.Connection, page_id: int | None) -> Page | None:
    row = conn.execute(f"{_SELECT_PAGES} WHERE pages.id = ?", (page_id,)).fetchone()
    return _page_from_row(row) if row else None


def save_page(conn: sqlite3.Connection, page: Page, fields: PageFields) -> Page:
    """Save: new title, slug, body and menu order; the status stays as it is."""
    _validate_page(fields)
    slug = _page_slug_for(conn, fields, page)
    with conn:
        conn.execute("UPDATE pages SET title = ?, slug = ?, body = ?, menu_order = ?,"
                     " updated_at = ? WHERE id = ?",
                     (fields.title, slug, fields.body, int(fields.menu_order), db.now(),
                      page.id))
    saved = get_page(conn, page.id)
    assert saved is not None
    return saved


def move_page(conn: sqlite3.Connection, page: Page, transition: Transition) -> Page:
    """Publish or unpublish a page, refused unless its status allows it."""
    if page.status not in transition.starts:
        raise ContentError(transition.refused)
    _set_status(conn, "pages", page, transition.leads_to)
    moved = get_page(conn, page.id)
    assert moved is not None
    return moved


def published_pages(conn: sqlite3.Connection) -> list[Page]:
    """Every published page in menu order: the public menu, after Inicio."""
    rows = conn.execute(f"{_SELECT_PAGES} WHERE pages.status = ?"
                        " ORDER BY pages.menu_order, pages.id", (Status.PUBLISHED,)).fetchall()
    return [_page_from_row(row) for row in rows]


def delete_page(conn: sqlite3.Connection, page: Page) -> None:
    with conn:
        conn.execute("DELETE FROM pages WHERE id = ?", (page.id,))


def list_pages(conn: sqlite3.Connection, status: Status | None = None) -> list[Page]:
    """Every page, most recently updated first; only those in this status, when asked."""
    rows = conn.execute(f"{_SELECT_PAGES} WHERE (:status IS NULL OR pages.status = :status)"
                        " ORDER BY pages.updated_at DESC, pages.id DESC",
                        {"status": status}).fetchall()
    return [_page_from_row(row) for row in rows]


def list_content(conn: sqlite3.Connection, status: Status | None = None,
                 topic: str | None = None, with_pending_edit: bool = False,
                 posts: bool = True, pages: bool = True) -> list[Post | Page]:
    """Posts, pages or both, most recently updated first, filtered as list_posts()
    filters. A page has no topic and never a pending edit, so either filter leaves
    every page out."""
    found: list[Post | Page] = []
    if posts:
        found += list_posts(conn, status, topic, with_pending_edit)
    if pages and topic is None and not with_pending_edit:
        found += list_pages(conn, status)
    return sorted(found, key=lambda item: item.updated_at, reverse=True)


def count_pages(conn: sqlite3.Connection) -> int:
    """How many pages there are, drafts and published."""
    return conn.execute("SELECT COUNT(*) FROM pages").fetchone()[0]
