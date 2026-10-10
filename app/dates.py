"""How stored times are shown: always in Monterrey time.

Monterrey keeps a fixed UTC-6 offset, so no time-zone database is needed.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

MONTERREY = timezone(timedelta(hours=-6))

MONTHS = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
          "septiembre", "octubre", "noviembre", "diciembre")


def _in_monterrey(stored: str) -> datetime:
    return datetime.fromisoformat(stored).astimezone(MONTERREY)


def monterrey_time(stored: str) -> str:
    """A stored UTC timestamp for the admin console: 04/10/2026 12:30."""
    return _in_monterrey(stored).strftime("%d/%m/%Y %H:%M")


def spanish_date(stored: str) -> str:
    """A stored UTC timestamp for readers: 4 de octubre de 2026."""
    when = _in_monterrey(stored)
    return f"{when.day} de {MONTHS[when.month - 1]} de {when.year}"
