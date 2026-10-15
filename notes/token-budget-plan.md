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

## Re-forecast after T01 (2026-10-10)

`uv run python scripts/usage_report.py --remaining 7` (T02–T08 left):

```text
T01      4 turns   5h 7.0%   weekly 1.0%   Opus 5.5
Tickets done: 2 · average weekly cost per ticket: 0.5%
Forecast: 7 tickets need ~4% of the weekly cap; 93% remains → FITS
```

**The report undercounts T01.** Corrected from the raw ledger:

- **Weekly: 3%, not 1%.** The weekly meter never resets. It read 4% at the last
  row before T01 (18:54) and 7% at the end of T01 (20:11). The report counts
  only rises *between rows of the same phase*, so the 4 → 6 jump into the
  first T01 row is assigned to no phase.
- **5-hour window: at least 11%, not 7%.** The window reset in the middle of
  T01's one long `/implement` turn: 31% at 18:54, 4% at 20:04. Whatever T01
  spent before the reset is lost, and the 4% after the reset is dropped for
  the same phase-boundary reason.
- **Tickets done: 1, not 2.** The single `T02` row is T01 wrap-up, logged after
  the phase file was switched to `T02`.

**Model plan vs. actual.** T01 ran on **Opus 5.5 at xhigh**, not Sonnet 5.5 at
medium. That was my choice, kept on purpose. Even so, it cost about 3% weekly,
which is exactly what the plan expected per ticket on Sonnet. The full
`/implement` + `/tdd` + two-reviewer `/code-review` loop fit in one session at
19% context.

**Corrected forecast.**

- **Weekly cap:** 7 tickets × ~3% ≈ 21%. Weekly is at 7% now, so I expect
  ~28% of one week at the end, inside the original 25–30%.
- **5-hour windows:** at ~15–25% per ticket, 7 tickets need about 1.5–2 windows.
- **Verdict:** **FITS** on Opus 5.5 at xhigh. I will re-check after T03, where
  the lifecycle makes it the biggest ticket, before switching anything.

**Measurement fixes for the next tickets:**

1. Write the phase before the first turn of a ticket, and change it only after
   that ticket's last turn.
2. Check the meter before starting a long `/implement` turn near a window reset.
3. A possible fix to `usage_report.py` (not made): count the rise between the
   last row of one phase and the first row of the next toward the new phase.

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
