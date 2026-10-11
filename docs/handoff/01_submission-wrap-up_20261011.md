# Handoff: from T08 to the submission wrap-up (2026-10-11)

## Where things stand

- Every core ticket, T01–T08 (#2–#9), is implemented and committed on `main`. The last one is
  `dda4384`, "T08: The leader updates the site with one button…". The commits for T06–T08 end
  in `Closes #7`, `Closes #8` and `Closes #9`, but `main` is **not pushed yet**, so those
  three issues are still open on GitHub. The spec, #1, stays open.
- Each ticket's `/code-review` findings and resolutions are posted on its issue. T08's are
  at #9.
- `uv run pytest`: 226 passed. `mypy app scripts/seed_demo.py` (run as
  `uvx mypy --python-executable .venv/bin/python …`) reports no issues.
- The 12 screenshots are in `docs/screenshots/`. They were taken from a freshly seeded
  scratch database, with the console's upload replaced by a fake.
- The README has *Live URL* and *Run locally* sections.

## What is still missing (`uv run python scripts/check_submission.py --stage 2`: 16/22)

1. **Report** `docs/iphs400_mp2-web-cms_report_{first}-{last}_{YYYYMMDD}.md`. The student
   writes it. The rubric marks down AI-sounding prose (A3, A4).
2. **AI Use Statement** in the README, with a *Backends used* table. The student writes it:
   two real prompts, one real model failure, the models and skills used. A real failure from
   this session is in "Gotchas" below.
3. **Compaction log** `docs/process/compaction-log.md`. Only the PreCompact hook writes it,
   and no compaction has happened yet.
4. **Tag** `mp2-final`, pushed, on the last commit, after the report. (`mp2-mvp` is pushed,
   on the T03 commit `faec347`, with a message saying it was tagged on 2026-10-11.)
5. ~~Push `main`, and update the live site~~: done. `main` is pushed, and `cms.db` was
   re-seeded, exported and uploaded (`gh-pages` `97f2599`). The live site shows the final
   version.

## Updating the live site later

`cms.db` holds the seeded demo data. After changing content, update the site with the
leader's *Actualizar el sitio* button, or run:

```bash
uv run cms publish                   # site/ from the published content; records the export time
uv run cms deploy                    # gh-pages
```

## Gotchas

- **Tests never reach GitHub or `site/`.** The autouse fixture `nothing_goes_online` in
  `tests/conftest.py` makes the default upload fail and points `settings.SITE` at a temporary
  folder. A test that wants the real upload passes `upload=` in explicitly, with
  `subprocess.run` faked.
- **Why that guard exists.** During T08, a red test ran before the guard did. It uploaded an
  empty test site to `gh-pages` as `c000bb7`; `959d617` restored the T03 files. To run tests
  with pushes blocked as a second safety net, set
  `GIT_CONFIG_COUNT=2 GIT_CONFIG_KEY_0=remote.origin.pushurl
  GIT_CONFIG_VALUE_0=/nonexistent GIT_CONFIG_KEY_1=remote.origin.url
  GIT_CONFIG_VALUE_1=/nonexistent`.
- **Don't press *Actualizar el sitio* in a console you only meant to look at.** The real
  button uploads for real. For demos and screenshots, build the app with
  `create_app(db, site=…, upload=fake)`, as the screenshots were taken.
- **The README's starter-template text is gone.** It now describes this project. The AI Use
  Statement placeholder is the only template text left, for the student to replace.
- **Uncommitted, not from this session:** changes to `.gitignore` (`.gstack/`) and
  `notes/`, and `docs/transcripts/`. They are the student's to review and commit.
