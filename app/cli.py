"""The `cms` command: serve, publish, deploy.

    uv run cms serve      # admin console at http://localhost:8000/admin
    uv run cms publish    # export site/ from published posts
    uv run cms deploy     # push site/ to the gh-pages branch (Pages serves it)
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from contextlib import closing

from app import db, settings
from app.export import export_site


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cms")
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve", help="run the admin console locally")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--reload", action="store_true", default=True)
    sub.add_parser("publish", help="export site/ from published posts")
    deploy = sub.add_parser("deploy", help="push site/ to gh-pages")
    deploy.add_argument("--message", default="Publish site")
    args = parser.parse_args(argv)

    if args.command == "serve":
        import uvicorn

        uvicorn.run("app.main:create_app", factory=True, port=args.port,
                    reload=args.reload)
        return 0

    if args.command == "publish":
        db.init(settings.DATABASE_PATH)  # a fresh clone exports an empty site
        with closing(db.connect(settings.DATABASE_PATH)) as conn:
            count = export_site(conn, settings.SITE)
        print(f"Wrote {settings.SITE} with {count} published post{'' if count == 1 else 's'}."
              f" Preview it with:  python3 -m http.server -d {settings.SITE} 8001")
        if count == 0:
            print("Nothing is published yet. For demo content run"
                  " `uv run python scripts/seed_demo.py`, then publish again.")
        return 0

    if args.command == "deploy":
        if not settings.SITE.exists():
            print("site/ does not exist yet — run `uv run cms publish` first.")
            return 1
        result = subprocess.run(
            [sys.executable, "-m", "ghp_import", "-n", "-p", "-m", args.message,
             str(settings.SITE)],
        )
        if result.returncode == 0:
            print("Pushed to gh-pages. Settings -> Pages -> Deploy from a branch -> "
                  "gh-pages / root, then wait up to 10 minutes.")
        return result.returncode
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
