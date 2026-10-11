"""Site update: export the public site, then upload it to GitHub Pages.

The leader's *Actualizar el sitio* button runs update(); `cms publish` runs the
export alone and `cms deploy` the upload alone. The button's upload is passed in,
so tests hand over a fake and nothing goes online.
"""
from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from app.export import export_site

Upload = Callable[[Path], None]

# A site this size goes up in seconds; a button still waiting after this has lost
# its connection.
UPLOAD_TIMEOUT_SECONDS = 120


class ExportFailed(Exception):
    """The public site could not be written to its folder; nothing was uploaded."""


class UploadFailed(Exception):
    """The exported site did not reach GitHub Pages; readers still see the old one."""


def upload_to_github_pages(site: Path, message: str = "Actualizar el sitio",
                           from_terminal: bool = False) -> None:
    """Upload: put `site` on the gh-pages branch, which GitHub Pages serves. Git's own
    output goes to the terminal that started the command. Only `cms deploy`, typed
    in a terminal, may wait on git: there it can ask for a password. From the
    console nobody would see the question, so git fails instead of asking, and a
    stalled connection gives up after UPLOAD_TIMEOUT_SECONDS: the button never hangs."""
    env = None if from_terminal else {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    try:
        result = subprocess.run([sys.executable, "-m", "ghp_import", "-n", "-p", "-m", message,
                                 str(site)], env=env,
                                timeout=None if from_terminal else UPLOAD_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired as stalled:
        raise UploadFailed("ghp-import timed out") from stalled
    if result.returncode != 0:
        raise UploadFailed(f"ghp-import exited with {result.returncode}")


def update(conn: sqlite3.Connection, site: Path, upload: Upload) -> None:
    """Export, then upload. Raises ExportFailed when the site's folder cannot be
    written, and then uploads nothing. Raises UploadFailed when the upload fails; the
    export has been written and recorded by then, and stays."""
    try:
        export_site(conn, site)
    except OSError as error:
        raise ExportFailed(str(error)) from error
    upload(site)
