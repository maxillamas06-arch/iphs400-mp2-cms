"""Configuration, read from the environment (never hard-code secrets).

Values come from the real environment first, then from `.env`, then (on a fresh
clone with no `.env`) from `.env.example`, so the seed and `cms serve` run with no
manual steps.
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"
SITE = ROOT / "site"


def _load_env_file() -> None:
    path = ROOT / ".env"
    if not path.exists():
        path = ROOT / ".env.example"
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


_load_env_file()

SECRET_KEY = os.environ.get("CMS_SECRET_KEY", "dev-only-not-for-production")
# A relative CMS_DATABASE is relative to the project folder, not the shell's.
DATABASE_PATH = ROOT / os.environ.get("CMS_DATABASE", "cms.db")
SITE_TITLE = os.environ.get("CMS_SITE_TITLE", "Club de Aficionados Albiazul")
# Set this to your Pages URL once you deploy, e.g.
# https://yourname.github.io/iphs400-mp2-cms/
BASE_PATH = os.environ.get("CMS_BASE_PATH", "")
