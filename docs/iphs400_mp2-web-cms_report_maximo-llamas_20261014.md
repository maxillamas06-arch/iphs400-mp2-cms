# IPHS 400 MP2 report: a CMS for the Club de Aficionados Albiazul

Maximo Llamas · 2026-10-14
Repo: <https://github.com/maxillamas06-arch/iphs400-mp2-cms> · Site:
<https://maxillamas06-arch.github.io/iphs400-mp2-cms/> · Tag: `mp2-final`

## 1. What I built, and which grill decisions were mine

I built a small CMS for an unofficial Rayados fan club. Members write posts about the team,
and the leader checks each one before it goes public. The admin console (FastAPI, Jinja and
SQLite) runs only on the leader's computer. His *Actualizar el sitio* button exports the
published posts and pages to static HTML and uploads it to GitHub Pages. All seven
capabilities are in spec #1 and tickets #2–#9; #10 is the public site's look. Every ticket
is closed with its review findings in a comment. The suite has 230 tests.

The grill (transcript 02, 2026-10-10) is where my decisions are:

- **The club's name.** My first prompt called it "Peña Albiazul". When the grill asked, I
  changed it to "Club de Aficionados Albiazul", and `CONTEXT.md` now lists "peña" under
  *Avoid*.
- **Accents.** The AI proposed slugs that strip accents. I wrote "i dont like the fact that u
  erase accens, dont do that". Slugs now keep á, é, í, ó, ú, ü and ñ (spec #1, user story 39).
- **Nicknames.** The AI recommended public nicknames that members couldn't change. I wanted
  "a nickname that the own user itself assigns", so members choose their own at first login
  (T07).
- **The look.** I asked for the team's colours and "the stadium or the cerro de la silla or
  symbolic things", as long as they don't get in the way of the disclaimer. T08 drew both as
  inline SVG, with no logos or photos. Later I asked for more life (T09, #10): a drawn scene
  behind every page, and Suazo's 90th-minute goal in the Apertura 2009 final told as you
  scroll the home page.
- **Phones.** This one went back and forth. I first said fans should write from their
  phones, then "ok nvm lets do it ur way". The AI took that as "put the console online later"
  and wrote an ADR-004 for it. I corrected it: "no i meant that u can only wirte from the
  computer of the admin". It deleted the ADR, and phone writing moved to the next version.

Not every answer was mine. Some I answered with a single letter, and at one point I wrote "do
the one that you think is the best for the set … I just want to have a good grade."

**[Write this yourself: one decision you would make differently now, and why.]**

## 2. Where the AI drifted, and what caught it

**Caught by the workflow.** In T03 (#4) the AI wrote a `PUBLISH` rule that let the leader
publish *anyone's draft*. ADR-003, written in the grill, says the leader publishes a
*submitted* post, so drafts should never skip review. The implementer didn't flag the
conflict. The Standards reviewer in `/code-review` checked the code against the ADR and
caught it (S1 in the #4 comment), and it was fixed test-first before the commit.

**Not caught in time.** In T08 (#9) the AI was adding a test to prove that no test can push
to GitHub. It ran that test once *before* writing the guard it tested. The test used the real
upload, so at 13:56 on 2026-10-11 an empty site built from the test database went live on
`gh-pages` (`c000bb7`). Nothing secret was in it, only demo HTML. The AI stopped, told me,
and asked how to fix it. I chose a restore commit rather than a force-push. `959d617` (13:58)
put the T03 site back, and the fixture `nothing_goes_online` in `tests/conftest.py` now makes
every test's default upload fail. The Spec reviewer had flagged that exact hole as
"fragile" (Spec finding 5 in the #9 comment), and it bit while it was being fixed.

**In T09 (#10), one of each.** The Spec reviewer caught the first caption saying Suazo
scored "el gol del campeonato". At 1–1 Rayados already led on aggregate, so it now says he
sealed it. No test or reviewer caught the other: with reduced motion turned on, the confetti
landed on the scoreboard. It turned up only when I asked for a bug hunt, which drove the site
in Chromium, WebKit (Safari's engine) and Firefox, and it was fixed in `7d05e69`.

## 3. Skills, prompts and resources

- `/grill-with-docs`, then `/to-spec` and `/to-tickets` (transcript 02). The grill wrote
  `CONTEXT.md`, the ADRs and the field notes, and the spec and tickets went to GitHub Issues.
- `/mattpocock-skills:implement #N` once per ticket, in a fresh session after `/clear`
  (transcripts 03–10 for T01–T08, and 11 for T09). It runs `/tdd` at the agreed seams and
  ends with the two-axis `/code-review`: a Standards and a Spec reviewer in parallel.
- gstack `browse` in T08, to check 390 px widths and take the 12 screenshots, and in T09 to
  watch the scenes at 390 and 1280 px. Playwright's WebKit and Firefox for the bug hunt.
- Resources: the client brief, WordPress Playground (my field notes in
  `notes/cms-field-notes.md`), the manual and the rubric.

**[Write this yourself: why these skills. For example, what the grill got out of you that you
would have skipped, and whether any review finding changed something you cared about.]**

## 4. What I'd add next, and what the budget data said

**Next:** my own idea from the grill. Members write and submit from their phones, and the
leader's powers stay on his computer. That means a hosted server with HTTPS and a
rate-limited login, which is the rubric's "live admin deploy". Smaller things I'd fix: the
failed-upload message shows in the same calm blue box as success, and `usage_report.py`
undercounts at phase boundaries (below).

**Budget.** My plan (`notes/token-budget-plan.md`, committed before the first `/implement`)
said Sonnet 5.5 at medium for the tickets, about 3% of the weekly cap each, and 25–30% for
all eight. I never switched: every session ran on Opus 5.5 at xhigh ("dont worry i want this
model"). From `notes/usage-ledger.csv`:

| Ticket | T01 | T02 | T03 | T04 | T05 | T06 | T07 | T08 | T09 |
|---|---|---|---|---|---|---|---|---|---|
| Weekly cap used | 3% | 4% | 4% | 3% | 3% | 3% | 3% | 3% | 5% |
| Peak context | 19% | 27% | 29% | 24% | 25% | 25% | 22% | 26% | 32% |

The eight tickets took 26% of the week (4% → 30%), inside the plan, even on the expensive
model. The submission wrap-up after T08 took another 4%. T01–T08 never passed 29% context,
so the rule to split a ticket that crosses 60% never came up for them. T09 came after the
wrap-up and was the most expensive ticket: eleven drawings, then browser checks in three
engines. **[Check T09's final numbers in `notes/usage-ledger.csv` once its session ends; the
table shows the ledger up to 21:27 on 2026-10-15.]** The 5-hour window was the real
limit: it reached 99% during the T08 wrap-up, and I had to wait for it to reset. That same
long session later ran out of context and compacted itself on 2026-10-12. It's the only
compaction in `docs/process/compaction-log.md`, and it was `auto`, not the manual kind the
manual asks for.

The numbers above count from the last ledger row *before* each ticket. After T01 I found
that `usage_report.py` only counts rises between rows of the same phase. It reported T01 as
1% weekly when the ledger shows 3%, because the jump into a new phase belongs to no phase.
I wrote the fix down in the plan but didn't make it.
