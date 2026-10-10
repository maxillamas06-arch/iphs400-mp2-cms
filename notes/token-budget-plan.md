# Token budget plan

Written 2026-10-10, before the first `/implement`. Plan in percent of my own
meters (5-hour window and weekly cap), not tokens. Re-forecast with
`uv run python scripts/usage_report.py --remaining N` after T01 and after T03.

## Model plan

| Stage | Model | Effort | Estimate (% of a 5-hour window) |
|---|---|---|---|
| `/research`, quick lookups | Haiku 4.5 | low | ~2% each |
| `/grill-with-docs`, `/to-spec`, `/to-tickets` | Opus 5.5 | xhigh | **actual: 16% for the grill (28 turns), ~2% for spec + tickets** |
| `/implement` + `/tdd` (per ticket) | Sonnet 5.5 | medium | ~20% per ticket (T03 and T07 likely ~30%) |
| `/code-review` (per ticket) | Sonnet 5.5 | high | ~5% per ticket |
| Exercises A and B (`/tdd`) | Opus 5.5 | xhigh | ~2% total |

Planning ran on Opus 5.5 at xhigh because it was already my default. That is the
expensive end; everything from T01 on switches to Sonnet 5.5 (`/model`, then
`/effort medium`).

## Forecast

- **Tickets:** 8 core tickets × ~25% (implement + review) ≈ 200% of a window,
  so **about 2–3 five-hour windows**, assuming I `/clear` between tickets.
- **Weekly cap:** the grill spent 2% of the weekly cap for 16% of a window
  (about 1 : 8 on Opus). Sonnet should be cheaper per window, so I expect
  roughly 3% weekly per ticket, **about 25–30% of one week** for all 8. Weekly
  was at 4% when this plan was written.
- **Verdict:** fits, with room for one `stretch` ticket only if the T03
  re-forecast says FITS.

## If I am wrong, cut in this order

1. Lower effort on `/implement` (medium → low) for the mechanical tickets
   (T04, T06).
2. Drop the `stretch` ticket.
3. Cut T08's visual extras (Cerro de la Silla banner, stadium silhouette) to
   plain stripes and the disclaimer.
4. `/clear` more often; split a ticket that crosses 60% context.
5. Plan B backend (manual Part 9), declared in the README, commit trailers and
   ledger.

Never cut: `/code-review` on every ticket, the findings comment, and the
`Closes #N` commits. Those are graded.
