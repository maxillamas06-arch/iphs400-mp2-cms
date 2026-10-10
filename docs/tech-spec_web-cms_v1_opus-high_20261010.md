# Spec: Club de Aficionados Albiazul CMS (v1)

*Source: the grill session of 2026-10-10 (`/grill-with-docs`, questions Q1–Q17). Vocabulary follows `CONTEXT.md`; decisions respect ADR-001, ADR-002 and ADR-003.*

## Problem Statement

Club de Aficionados Albiazul is an unofficial fan club of Rayados (C.F. Monterrey). Its fans share opinions about the team (how a match went, the lineup, the coach, a signing), but today they post them on X and Facebook, where they are mixed in with everything else and impossible to find again. The fan club wants one place where fan opinions live, organized and easy to read.

The fan club has one hard rule: no aggression toward people, and no threats against people or places, may ever go public. Tiradera toward rival clubs (Tigres especially) is welcome; a personal attack never is. The leader is the only safeguard, so nothing may reach readers without his check. The leader knows the basics on a computer and nothing technical, so the admin side has to be simple.

## Users

- **Leader** (role *admin*): one person. Checks and publishes everything, writes the fan club's pages, creates and manages accounts, and puts changes online. Not technical.
- **Member** (role *editor*): a fan with an account, created by the leader. Writes posts and submits them to the leader; cannot publish, cannot touch pages or accounts.
- **Reader**: any fan visiting the public site on GitHub Pages, usually on a phone. No account; reads only.

## Solution

A small CMS with two halves, per ADR-001:

- An **admin console** that runs only on the leader's computer (FastAPI + Jinja + SQLite, per ADR-002). Members write there; the leader checks, publishes, manages accounts, and runs the site update. Everything people see is in Spanish.
- A **public site**: static HTML regenerated from published content only and deployed to GitHub Pages. A home page with one section per topic, a page per topic, a page per post, and the fan club's pages in the menu. Navy-and-white, playful, unmistakably Monterrey, never official.

Every change readers can see passes through the leader (ADR-003): posts move draft → submitted → published, a member's change to a published post waits as a pending edit, and a member's nickname is chosen once.

### The seven required capabilities, for this client

1. **Login.** The leader and members sign in with email and password and sign out. Passwords are stored only as argon2 hashes. A wrong email and a wrong password get the same message.
2. **Two roles.** *Admin* = the leader: everything. *Editor* = a member: writes, edits and submits their own posts, reads everyone's posts, proposes edits to their own published posts. Editors cannot publish, cannot see or change pages, cannot manage accounts, and cannot run a site update. Enforced on the server for every route, never by hiding links.
3. **Posts.** A post is a fan's opinion: title, slug, Markdown body, exactly one topic, status (draft, submitted, published), author, and created/updated/published timestamps. Full create, read, update, delete, following the lifecycle below.
4. **Pages.** Fixed fan-club information: same fields as a post minus the topic, plus a menu-order number. Only the leader creates, edits, publishes, unpublishes and deletes them. Published pages appear in the public menu in menu order.
5. **Admin console.** A dashboard with counts, a content list filterable by status, topic and (leader only) post vs page, and an editor with a *Vista previa* that shows the sanitized result.
6. **User management.** Leader only: create accounts, change roles, set a nickname, set a new temporary password, deactivate and reactivate. A deactivated user cannot log in, and an existing session stops working on its next request.
7. **Public site and site update.** `cms publish` regenerates the public site from published posts and pages only, with sanitized Markdown, a menu built from published pages, and relative paths only. `cms deploy` pushes it to GitHub Pages. The leader's *Actualizar el sitio* button does both.

## User Stories

### Leader

1. As the leader, I want to log in with my email and password, so that only I can use the leader's powers.
2. As the leader, I want a dashboard showing how many posts are waiting for review, so that I know at a glance whether I have checking to do.
3. As the leader, I want the dashboard to count drafts, submitted posts, published posts, pending edits, pages and active members, so that I can see the state of the site without opening lists.
4. As the leader, I want the dashboard to show when the site was last updated, so that I know whether readers are seeing my latest decisions.
5. As the leader, I want to filter the content list to submitted posts, so that my review queue is one click away.
6. As the leader, I want to filter the content list to posts with a pending edit, so that I can review changes to published posts.
7. As the leader, I want to filter the content list by topic and by post vs page, so that I can find things quickly.
8. As the leader, I want to read a submitted post exactly as readers would see it, so that I can judge whether it crosses from tiradera into a personal attack.
9. As the leader, I want to publish a submitted post, so that it goes public at the next site update.
10. As the leader, I want to send back a submitted post to draft, so that its member can rework it.
11. As the leader, I want to see a pending edit side by side with the published version, so that I can judge exactly what would change.
12. As the leader, I want to approve a pending edit, so that the improved version replaces the published one.
13. As the leader, I want to send back a pending edit, so that the published version stays untouched.
14. As the leader, I want to unpublish a published post, so that it disappears from the public site at the next site update.
15. As the leader, I want to be stopped from unpublishing a post while a pending edit waits, so that a member's proposed change is never silently thrown away.
16. As the leader, I want to edit any post directly, so that I can fix a typo without a round trip; my edits to published posts go live at the next site update.
17. As the leader, I want to write my own posts and publish them directly, so that fan club news does not wait on a review of myself.
18. As the leader, I want to delete any post after confirming, so that content that should never have existed is gone.
19. As the leader, I want to create, edit, publish, unpublish and delete pages, so that *Quiénes somos*, *Próximos partidos*, *Reglas de la casa* and *Cómo unirse* stay accurate.
20. As the leader, I want to set each page's menu-order number, so that the public menu reads in the order I choose.
21. As the leader, I want to be prevented from giving a page a name the site already uses (such as the home page or a topic page), so that nothing on the site is overwritten.
22. As the leader, I want to create a member account with an email, role and temporary password, so that a fan who asked to join can start writing.
23. As the leader, I want to promote a member to admin or demote an admin to editor, so that I can share the job if I need to.
24. As the leader, I want to be unable to remove my own admin role or deactivate myself, so that I cannot lock myself out.
25. As the leader, I want to deactivate an account, so that a member who breaks the house rules can no longer log in.
26. As the leader, I want to reactivate an account, so that a member can come back.
27. As the leader, I want a deactivated member's posts to stay up under their nickname, so that the fan club's archive is not broken.
28. As the leader, I want a deactivated member's submitted posts and pending edits to stay in my queue, so that I still decide what happens to them.
29. As the leader, I want to change any member's nickname, so that I can fix a nickname that breaks the house rules.
30. As the leader, I want to set a new temporary password for a member, so that a member who forgot theirs can get back in.
31. As the leader, I want one *Actualizar el sitio* button that regenerates the public site and uploads it, so that I never need a terminal.
32. As the leader, I want the button to tell me in plain Spanish what happened at each step, so that I know whether readers can see my changes or what went wrong.
33. As the leader, I want a success or error message after every save, so that I always know whether my action worked.

### Member

34. As a member, I want to log in with the email and temporary password the leader gave me, so that I can start writing.
35. As a member, I want to choose my nickname at my first login, so that readers know me by the name I picked.
36. As a member, I want the site to refuse a nickname someone else already uses, so that nobody can pass as me or I as them.
37. As a member, I want to change my password on *Mi cuenta*, so that the leader no longer knows it.
38. As a member, I want to write a post with a title, a topic and a Markdown body, so that I can share my opinion.
39. As a member, I want the slug to be made from my title, keeping accents and ñ, so that the link reads like my title.
40. As a member, I want to edit the slug until my post is first published, so that I can tidy the link.
41. As a member, I want to press *Vista previa* and see exactly what readers will see, so that my formatting is right before I submit.
42. As a member, I want to save a draft and come back later, so that I can finish a match opinion the next morning.
43. As a member, I want to submit a finished draft to the leader, so that he knows it is ready to check.
44. As a member, I want to withdraw a submitted post back to draft, so that I can fix something before the leader reads it.
45. As a member, I want to delete my own draft, so that I can drop an opinion I changed my mind about.
46. As a member, I want to propose an edit to my own published post, so that I can correct it while the published version stays up.
47. As a member, I want my new pending edit to replace my previous one, so that the leader always sees my latest proposal.
48. As a member, I want to see every post in the content list, including other members', so that I know what has already been written about Saturday's match.
49. As a member, I want to be refused when I try to change someone else's post or reach a leader screen, so that the rules are real.
50. As a member, I want a clear "no tienes permiso" page when I am refused, so that I understand what happened.

### Reader

51. As a reader, I want a home page with one section per topic showing its three newest posts, so that I can see what fans are saying about each subject.
52. As a reader, I want a *Ver todos* link on each section, so that I can read every post in a topic.
53. As a reader, I want each post to show its title, the author's nickname, its topic, and *Publicado el …* (and *Actualizado el …* if it changed after publishing), so that I know who said what and when.
54. As a reader, I want the menu to list the fan club's pages, so that I can find the house rules and how to join.
55. As a reader, I want to read *Reglas de la casa*, so that I know where the line between tiradera and a personal attack is.
56. As a reader, I want *Cómo unirse* to tell me how to ask the leader for an account, so that I can start writing too.
57. As a reader, I want the site to work on my phone without sideways scrolling, so that I can read it at the stadium.
58. As a reader, I want links to keep working after I share them on X or Facebook, so that my friends land on the same post.
59. As a reader, I want to see the disclaimer on every page, so that nobody mistakes the site for an official Rayados site.
60. As a reader, I never want to see drafts, submitted posts, pending edits, or anything the leader has not approved.

## Implementation Decisions

### Modules

Deep modules with small interfaces; the web layer stays thin.

- **Accounts.** Password hashing and verification (argon2), login, logout, session handling, loading the current user on every request and rejecting deactivated users, nickname rules, and the user-management operations. Interface: authenticate(email, password) → user or failure; current_user(request); create/update/deactivate/reactivate operations that enforce the self-lockout rules.
- **Policy.** The single place that answers "may this person do this action to this item?" from role, ownership and status. Every write route asks it; templates may use it to hide buttons, but hiding is never the control.
- **Content.** Posts, pages and pending edits: storage, slug generation, and the post lifecycle as an explicit set of transitions (table below). Invalid transitions are refused here, not in the routes.
- **Markdown rendering.** One function: Markdown text in, sanitized HTML out (markdown-it-py, then nh3 with an allowlist). Used by *Vista previa*, the leader's review screens and the site export, so the preview is always exactly what readers get.
- **Site export.** Renders every published post and published page, the topic pages and the home page into an output directory with relative, percent-encoded links. Called by `cms publish` and by the site update.
- **Site update.** Export, then deploy (push the output to the `gh-pages` branch), then record the time of the last site update. The deploy step is injectable so tests never push. Called by *Actualizar el sitio* and mirrored by the `cms publish` / `cms deploy` CLI.
- **Admin web layer.** Routes and Spanish templates for login, first-login nickname, *Mi cuenta*, dashboard, content list, post editor, page editor, review screens, users, site update, and the refusal page.
- **Public templates.** Home, topic page, post page, page, shared layout with menu, topic links and disclaimer.
- **Seed.** Rebuilds the demo database from scratch with fictional data.

### Data model

- **User**: id, email (unique, used to log in), password hash (argon2), nickname (unique ignoring case; empty until chosen), role (*admin* or *editor*), active flag, created and updated timestamps.
- **Post**: id, title, slug (unique among posts), Markdown body, topic, status (*draft*, *submitted*, *published*), author (a user), created and updated timestamps, first-published timestamp (set once, never cleared; its presence locks the slug), and an edited-after-publishing timestamp (drives *Actualizado el …*).
- **Pending edit**: at most one per post; proposed title, topic and Markdown body, created and updated timestamps. The slug is never part of a pending edit.
- **Page**: id, title, slug (unique among pages, and never a reserved name), Markdown body, status (*draft* or *published*), menu-order number, author, created, updated and first-published timestamps.
- **Site state**: the time of the last successful export.
- **Topics** are a fixed list in code, not a table: Match (*Partido*), Lineup (*Alineación*), Coach (*Técnico*), Signings (*Fichajes*), Fan club news (*Noticias del club de aficionados*).

### Post lifecycle

| Action | Who | From | Result |
|---|---|---|---|
| Save | the member who wrote it; the leader | draft | stays draft |
| Submit | the member who wrote it | draft | submitted |
| Withdraw | the member who wrote it | submitted | draft |
| Publish | leader | draft or submitted | published; sets first-published the first time |
| Send back | leader | submitted | draft |
| Unpublish | leader | published, with no pending edit | draft |
| Propose edit | the member who wrote it | published | stays published; creates or replaces its pending edit |
| Approve | leader | pending edit | the edit replaces title, topic and body; pending edit removed; edited-after-publishing set |
| Send back (pending edit) | leader | pending edit | pending edit removed; published version untouched |
| Edit directly | leader | any status | same status; if published, sets edited-after-publishing |
| Delete | the member who wrote it, drafts only; the leader, any post | any | post and its pending edit removed |

The leader's own posts may be published straight from draft. A member never changes a submitted or published post directly. A member may read every post in the admin console but act only on their own.

Pages have two statuses only (*draft*, *published*) and no submitted step, because only the leader writes them.

### Accounts and access

- Login identifier is the email. The test helper in `tests/conftest.py` already posts `email` and `password` to `/login`; its demo users are updated to match the seed's emails.
- Wrong email and wrong password both show *"Correo o contraseña incorrectos."*
- Sessions use a signed, HTTP-only, same-site cookie holding the user id and a CSRF token. The user is reloaded on every request, so deactivation takes effect immediately.
- Every state-changing request is a POST carrying a CSRF token in a hidden field, including login, logout, *Vista previa* and the site update. A POST without a valid token gets 403.
- Anonymous requests to any admin route redirect to `/login`. An editor requesting a leader-only route, or acting on someone else's post, gets 403 with a Spanish refusal page that keeps the admin menu. Unknown ids get 404.
- A user without a nickname is sent to the first-login nickname screen before anything else. Seeded users already have nicknames so the judge's walkthrough is never interrupted.
- Nickname: 2–40 characters, unique ignoring case; afterwards only the leader can change it.
- Passwords: at least 8 characters when set or changed.
- The leader cannot change their own role or deactivate themselves. Users are never deleted.

### Admin routes (contract)

Paths and form field names are English; everything people read is Spanish.

- `/login` (GET, POST), `/logout` (POST)
- `/admin` dashboard; `/admin/nickname` first-login nickname; `/admin/account` *Mi cuenta*
- `/admin/content` content list with `status`, `topic`, `pending` and (leader only) `type` filters
- `/admin/posts/new`, `/admin/posts/{id}` and one POST route per lifecycle action, plus a preview POST
- `/admin/posts/{id}/pending-edit` side-by-side review (leader)
- `/admin/pages/...` create, edit, publish, unpublish, delete, preview (leader only)
- `/admin/users/...` list, create, change role, set nickname, set temporary password, deactivate, reactivate (leader only)
- `/admin/site-update` (POST, leader only)

Every leader-only route is declared as such in one place, so a test can enumerate all of them.

### Slugs

Made from the title: Unicode-normalized (NFC), lowercased, letters (including á é í ó ú ü ñ) and digits kept, every other run of characters replaced by a single hyphen, trimmed, capped at 80 characters. Example: *"Crónica del Clásico Regio"* → `crónica-del-clásico-regio`. A taken slug gets `-2`, `-3`, … A manually entered slug follows the same rules. A post's slug is editable until it is first published, then locked forever, so shared links keep working. Page slugs may not be a reserved name: `index`, `tema`, `posts`, `style`.

### Markdown

Rendered with markdown-it-py, then sanitized with nh3 using an allowlist of text-formatting tags, lists, blockquotes, code and links. Scripts, event-handler attributes and `javascript:` links are removed. **Images are removed too**: photo uploads are out of scope and the site must carry no official photos. Links get `rel="noopener noreferrer"`.

### Public site (contract)

- `index.html`: one section per topic in the fixed order, each with its three newest published posts (title, nickname, date) and a *Ver todos* link; a topic with no published posts is hidden on the home page. A Cerro de la Silla banner on top.
- `tema/<topic-slug>.html`: all published posts in that topic, newest first. All five topic pages are always generated (an empty one says so), so no link ever breaks.
- `posts/<slug>.html`: title, nickname, topic link, *Publicado el …*, *Actualizado el …* when edited after publishing, and the body.
- `<page-slug>.html`: a published page.
- `style.css` at the root.
- Every page shares a menu (*Inicio* plus published pages by menu order), a row of topic links, and the footer with a stadium silhouette above the disclaimer: *"Sitio de aficionados. Sin afiliación con el Club de Fútbol Monterrey."* with *"Fan site, not affiliated with Club de Fútbol Monterrey."* beneath.
- Every `href` and `src` is relative (`../style.css` from nested pages) and percent-encoded, so accented slugs never break a link. File names are written in NFC.
- The output directory is wiped and regenerated on every export, so unpublished and deleted content disappears.
- Dates are shown in Spanish (*4 de octubre de 2026*) in Monterrey time, a fixed UTC−6 offset, so no time-zone database is needed.

### Look

Navy and white, with vertical stripes (*rayas*) across the top of every public page, an original Cerro de la Silla silhouette on the home page, and a generic stadium silhouette (not labelled with any sponsor's name) in the footer. All drawings are inline vector graphics written for this site: no crest, logos, photos or image files. Fun to look at, but every page stays readable at 390 px with no horizontal scrolling. The admin console uses the same colors in a calmer, plain layout, with a persistent menu.

### Site update

- `cms publish` exports to `site/`; `cms deploy` pushes `site/` to `gh-pages`. Both keep working exactly as the assignment expects.
- *Actualizar el sitio* (leader only) runs export then deploy and reports each step, for example *"Sitio generado ✓ · Subido a GitHub ✓"*, or a plain Spanish error when the upload fails. A failed upload does not undo a successful export. The dashboard shows the time of the last successful export.

### Configuration

All secrets and settings come from the environment (`.env`, never committed): secret key, database path, site title (*Club de Aficionados Albiazul*), demo passwords, base path. `.env.example` is updated with the new site title and a `CMS_STUDENT=first-last` placeholder for the transcript hook.

### Demo data (all fictional)

The seed wipes and rebuilds the database. It creates: the leader and two members, all with fictional nicknames and emails under `albiazul.example`, passwords from the environment; at least one published post in each of the five topics, including an obvious tiradera aimed at Tigres; one draft, one submitted post, and one published post with a pending edit; and the four pages, published, in menu order (*Quiénes somos*, *Próximos partidos*, *Reglas de la casa*, *Cómo unirse*). *Reglas de la casa* spells out the house rules; *Cómo unirse* gives `unete@albiazul.example`. The README lists the demo emails.

## Testing Decisions

- **Good tests check behaviour from the outside**: what a person can do and see through HTTP, and what files the export writes. They never assert on internal function calls, SQL, or template internals.
- **Seam 1: the HTTP interface**, driven through FastAPI's test client against a fresh temporary SQLite database per test, seeded with the test demo users. Prior art: `tests/test_t00.py` and the `client` / `client_as(role)` fixtures in `tests/conftest.py`. The app factory accepts a database path so tests never touch `cms.db`. A second editor fixture covers ownership rules.
- **Seam 2: the export output**, generated into a temporary directory and inspected as files and HTML. The deploy step is replaced with a fake that records the call, so no test pushes to GitHub.
- **Access-control matrix (D3):** a test enumerates every leader-only route from the single declaration and asserts an editor gets 403 and an anonymous visitor is redirected to `/login`. New leader-only routes are covered automatically.
- **CSRF (D2):** a test replays every POST route without a token and asserts 403.
- **Sanitizing (D4):** a post containing `<script>` and `onerror=` is checked in *Vista previa* and in the exported page; neither survives.
- **Drafts never leak (checklist #8):** the export is searched for every draft, submitted post and pending edit; none appears.
- **Relative paths (F2):** the export is grepped for `href="/` and `src="/`; every internal link, including an accented slug, resolves to a generated file.
- **Lifecycle:** every row of the lifecycle table has a test, including the refusals (member publishing, member editing a submitted or published post, unpublishing with a pending edit).
- **Accounts:** stored passwords start with `$argon2`; wrong password and unknown email give the same message; a deactivated user cannot log in and an open session is rejected; the leader cannot demote or deactivate themselves; nicknames are unique ignoring case.
- **Persistence (C3):** a post created through one app instance is still there through a new instance on the same database file.
- **Traceability (E2):** each ticket's acceptance criteria map to at least one test whose name says which criterion it covers.

## Out of Scope

- Comments and likes; readers only read.
- Members writing from their own phones or computers. In v1 the admin console runs only on the leader's computer (ADR-001). *Next step, the client's own idea: put only "write and submit" online, keep the leader's powers on his computer.*
- Self sign-up; the leader creates every account.
- Photo uploads, and images inside posts.
- Live scores, match statistics, and any integration with Rayados or league data.
- Multiple clubs or multiple sites.
- Revision history and rollback (a pending edit is the only stored alternative version).
- Search, scheduled publishing, per-fan pages, categories or tags beyond the five fixed topics.
- A bilingual site or a language switch.
- WYSIWYG editing and drag-and-drop page building (excluded by the assignment).

## Further Notes

- **Rubric labels:** this spec is the `spec` issue; tickets are labelled `ticket` (core) or `stretch`, each with acceptance criteria and a `Blocked by:` line. See `docs/agents/issue-tracker.md`.
- **Tracer bullets:** every ticket should cut through model, route, template and test, and be demoable alone. The first tickets should get login, posts and a published post on GitHub Pages as early as possible.
- **Known trade-off (Q9):** members can read other members' unchecked drafts. Accepted by the client.
- **Stretch candidates, only after the seven capabilities pass:** revision history with rollback (extends pending edits), switchable theme, live admin deploy.
- **Deadline:** the Stage 2 grace period ended on 2026-10-07; keep tickets thin.
