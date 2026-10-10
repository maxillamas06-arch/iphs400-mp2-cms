# ADR-003: Everything readers can see passes through the leader

**Status:** accepted
**Date:** 2026-10-10

## Context

The client brief has one hard rule: no aggression toward people and no threats
against people or places may ever go public. Trash talk toward rival clubs
(*tiradera*) is fine. The leader's check is the only safeguard, so any path by
which a member's words reach readers without that check breaks the brief.

The obvious CMS designs each leave such a path: two statuses only (the leader
cannot tell a finished post from a half-written one), authors editing their own
published posts (the change ships at the next site update unseen), and display
names editable at any time (a rename reprints unchecked text on every past post).

## Decision

- Posts move **draft → submitted → published**. Members cannot publish; the
  leader publishes a submitted post or sends it back to draft. A member may
  withdraw their own submitted post to draft. Only the leader's own posts may be
  published straight from draft (settled in the T03 review, #4).
- A member's change to their own published post becomes a **pending edit** (at
  most one per post). The published version stays public until the leader
  approves the edit or sends it back.
- A member chooses their **nickname** once, at first login. After that only the
  leader can change it.
- **Pages** are written by the leader only.
- Members can read every post in the admin console but change only their own.
- Every rule is enforced on the server, route by route. Hiding a button is never
  the control.

## Considered options

- Two statuses, draft and published — rejected: no explicit review queue.
- Editing a published post sends it back to submitted — rejected: a typo fix
  takes the post offline.
- Nicknames editable at any time, with or without review — rejected in favour of
  choosing once.

## Consequences

- Posts carry a third status and an optional pending edit; every write route
  checks role, ownership, and status.
- The leader's dashboard has a review queue: submitted posts plus pending edits.
- Unchecked drafts are visible to other members (accepted in the grill, Q9).
- A future revision history with rollback would extend pending edits rather than
  replace them.

## Why this is an ADR

It is hard to reverse (it shapes the data model and the permission check on
every write route), surprising without context (a reader would expect members to
edit their own published posts), and the result of real trade-offs made in the
grill (Q1, Q2, Q9, Q11).
