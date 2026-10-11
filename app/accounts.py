"""Accounts: who people are, and proving it with a password.

Passwords are stored only as argon2 hashes and are never logged.
"""
from __future__ import annotations

import sqlite3
import unicodedata
from dataclasses import dataclass
from enum import StrEnum

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app import db

_hasher = PasswordHasher()

class Role(StrEnum):
    ADMIN = "admin"    # the leader
    EDITOR = "editor"  # a member


ROLE_NAMES = {Role.ADMIN: "Líder", Role.EDITOR: "Miembro"}
PASSWORD_MIN = 8
NICKNAME_MIN, NICKNAME_MAX = 2, 40


class AccountError(ValueError):
    """A refused change; the message is shown to the person as it is."""


@dataclass(frozen=True)
class User:
    id: int
    email: str
    nickname: str | None
    role: Role
    active: bool

    @property
    def is_leader(self) -> bool:
        return self.role == Role.ADMIN


def _user_from_row(row: sqlite3.Row) -> User:
    return User(id=row["id"], email=row["email"], nickname=row["nickname"],
                role=Role(row["role"]), active=bool(row["active"]))


def _hash_new_password(password: str) -> str:
    """The argon2 hash to store, if this password is long enough."""
    if len(password) < PASSWORD_MIN:
        raise AccountError(f"La contraseña debe tener al menos {PASSWORD_MIN} caracteres.")
    return _hasher.hash(password)


def _check_role(role: str) -> Role:
    try:
        return Role(role)
    except ValueError:
        raise AccountError("Elige un rol: líder o miembro.") from None


def _fold(nickname: str) -> str:
    """A nickname as compared with the others: case ignored, accents included."""
    return unicodedata.normalize("NFC", nickname).casefold()


def _check_nickname(conn: sqlite3.Connection, nickname: str, user_id: int | None) -> str:
    """The nickname as stored, if the user with this id may take it: 2–40 characters,
    and no one else's ignoring case. Compared here because SQLite's NOCASE folds
    only ASCII, so it would let "RAYADA DE CORAZÓN" pass as someone else."""
    nickname = unicodedata.normalize("NFC", nickname.strip())
    if not NICKNAME_MIN <= len(nickname) <= NICKNAME_MAX:
        raise AccountError(f"El apodo debe tener entre {NICKNAME_MIN} y {NICKNAME_MAX}"
                           " caracteres.")
    others = conn.execute("SELECT nickname FROM users WHERE nickname IS NOT NULL AND id IS NOT ?",
                          (user_id,))
    if any(_fold(row["nickname"]) == _fold(nickname) for row in others):
        raise AccountError(f"El apodo «{nickname}» ya lo usa otra persona. Elige otro.")
    return nickname


def create_user(conn: sqlite3.Connection, *, email: str, password: str, role: str,
                nickname: str | None = None, active: bool = True) -> User:
    """A new account. A fan the leader lets in has no nickname yet: they choose it
    at their first login."""
    email = email.strip()
    if "@" not in email:
        raise AccountError("Escribe un correo válido.")
    # The email column ignores case, so ANA@… is taken once ana@… is.
    if conn.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
        raise AccountError(f"Ya hay una cuenta con el correo «{email}».")
    password_hash, checked_role = _hash_new_password(password), _check_role(role)
    if nickname is not None:
        nickname = _check_nickname(conn, nickname, None)
    now = db.now()
    with conn:
        cursor = conn.execute(
            "INSERT INTO users (email, password_hash, nickname, role, active,"
            " created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (email, password_hash, nickname, checked_role, int(active), now, now),
        )
    user = get_user(conn, cursor.lastrowid)
    assert user is not None
    return user


def _update(conn: sqlite3.Connection, user: User, **columns: str | int) -> User:
    """Change these columns of this user's row (names from this module, never from
    a form) and return the user as now stored."""
    assignments = "".join(f"{column} = ?, " for column in columns)
    with conn:
        conn.execute(f"UPDATE users SET {assignments}updated_at = ? WHERE id = ?",
                     (*columns.values(), db.now(), user.id))
    updated = get_user(conn, user.id)
    assert updated is not None
    return updated


def choose_nickname(conn: sqlite3.Connection, user: User, nickname: str) -> User:
    """A user's first-login choice of the name readers see on their posts. Chosen
    once: after that only the leader changes it, with set_nickname."""
    if user.nickname is not None:
        raise AccountError(f"Tu apodo ya es «{user.nickname}». Solo el líder puede cambiarlo.")
    return set_nickname(conn, user, nickname)


def set_nickname(conn: sqlite3.Connection, user: User, nickname: str) -> User:
    """Any user's nickname, set by the leader; still unique."""
    return _update(conn, user, nickname=_check_nickname(conn, nickname, user.id))


def set_password(conn: sqlite3.Connection, user: User, password: str) -> User:
    """A new password for this user: the leader's temporary one, or their own."""
    return _update(conn, user, password_hash=_hash_new_password(password))


def change_role(conn: sqlite3.Connection, by: User, user: User, role: str) -> User:
    """The leader making `user` a leader or a member. Never their own role, so the
    leader can never lock themselves out."""
    if by.id == user.id:
        raise AccountError("No puedes cambiar tu propio rol: así nunca te quedas sin poder"
                           " administrar el sitio.")
    return _update(conn, user, role=_check_role(role))


def deactivate(conn: sqlite3.Connection, by: User, user: User) -> User:
    """The leader closing `user`'s account: they cannot log in, and an open session
    stops working on its next request. Never their own account. Users are never
    deleted, so their posts stay under their nickname."""
    if by.id == user.id:
        raise AccountError("No puedes desactivar tu propia cuenta: así nunca te quedas fuera.")
    return _update(conn, user, active=0)


def reactivate(conn: sqlite3.Connection, user: User) -> User:
    return _update(conn, user, active=1)


def get_user(conn: sqlite3.Connection, user_id: int | None) -> User | None:
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return _user_from_row(row) if row else None


def active_user(conn: sqlite3.Connection, user_id: int | None) -> User | None:
    """The user a session belongs to, or None once their account is inactive."""
    user = get_user(conn, user_id)
    return user if user and user.active else None


def authenticate(conn: sqlite3.Connection, email: str, password: str) -> User | None:
    """The active user with this email and password, or None."""
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email.strip(),)).fetchone()
    if row is None or not row["active"] or not _matches(row, password):
        return None
    return _user_from_row(row)


def _matches(row: sqlite3.Row, password: str) -> bool:
    """Whether this is the password of the user in this row."""
    try:
        return _hasher.verify(row["password_hash"], password)
    except (VerificationError, InvalidHashError):
        return False


def change_password(conn: sqlite3.Connection, user: User, current: str, new: str) -> User:
    """A user's own new password, on Mi cuenta: only with their current one."""
    row = conn.execute("SELECT password_hash FROM users WHERE id = ?", (user.id,)).fetchone()
    if not _matches(row, current):
        raise AccountError("La contraseña actual no es correcta.")
    return set_password(conn, user, new)


def count_active_members(conn: sqlite3.Connection) -> int:
    """Members (the editor role, not leaders) whose account is active."""
    return conn.execute("SELECT COUNT(*) FROM users WHERE role = ? AND active",
                        (Role.EDITOR,)).fetchone()[0]


def list_users(conn: sqlite3.Connection) -> list[User]:
    """Every account, the leader's first, then by email."""
    rows = conn.execute("SELECT * FROM users ORDER BY role = ? DESC, email",
                        (Role.ADMIN,)).fetchall()
    return [_user_from_row(row) for row in rows]
