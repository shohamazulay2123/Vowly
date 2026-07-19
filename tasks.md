# Vowly 💍 — Work Plan (tasks.md)

A breakdown of the [PRD](PRD.md) into a practical, ordered work plan.
Each task is **commit-sized**, and the milestones below follow the **real git history** of the project
(commit hash + date shown per milestone). Check items off as they land so this list mirrors real progress.

> **Note on history.** The bulk of the app shipped in one large initial commit, so the sub-tasks inside
> Milestone 1 are a logical decomposition of that commit rather than eight separate commits. From
> Milestone 2 onward, each milestone maps 1:1 to an actual commit.

**Progress:** 43 / 45 done (2 remaining)

---

## Milestone 1 — Initial build `76a4703` · 2026-05-10
> The entire first version: schema, all routes, seed data, and all core templates.

- [x] Add `.gitignore`, `requirements.txt`, `config.py`, `wsgi.py` (project scaffolding)
- [x] `database.py`: connection helper + full schema (`init_db()`) — all 12 tables, `CHECK`/`UNIQUE`, N:M junction
- [x] `app.py`: auth (register / login / logout / sessions) with `werkzeug` password hashing (US-1)
- [x] Wedding profile + onboarding routes and templates (US-2)
- [x] `fetch_real_vendors.py` + `suppliers.py`: first vendor-data fetcher
- [x] `seed.py`: populate categories, vendors, photos, demo users/weddings
- [x] Vendors catalog + filters + `vendor_detail` page (US-4, US-5)
- [x] Swipe / Like-Skip discovery flow with no-double-swipe (US-3)
- [x] Favorites + selected-vendors shortlist (US-6)
- [x] Checklist, appointments, reviews routes + templates (US-7, US-10, US-11)
- [x] Analytics dashboard with JOIN / GROUP BY / HAVING / aggregates (US-12)
- [x] Landing page (`index.html`), base layout, `style.css`, `main.js`, error page
- [x] Initial `README.md` (routes, schema, SQL examples)

## Milestone 2 — Interactive ERD view `a5ddee8` · 2026-05-10
- [x] Add fullscreen interactive `erd.html` entity-flow view
- [x] Swipe-screen + base-layout polish and supporting CSS/JS

## Milestone 3 — ERD upgrade `0619c66` · 2026-05-18
- [x] Expand the interactive ERD (`templates/erd.html`) with entity-flow navigation
- [x] Wire an `/erd` route and nav entry in `app.py` / `base.html`

## Milestone 4 — Fix vendor images `ee646c7` · 2026-05-19
- [x] Replace broken `loremflickr` image URLs with `picsum.photos` in `seed.py`

## Milestone 5 — Switch to Google Places importer `3312069` · 2026-06-10
- [x] Add `fetch_google_vendors.py` (Google Places API → `vendors_cache.json`)
- [x] Add `settings.html` + settings route
- [x] Refactor checklist and swipe templates/logic; small `database.py` tweak
- [x] Remove the standalone `erd.html` interactive view (superseded)
- [x] Add `Vowly_project_brief.docx`

## Milestone 6 — UI & features overhaul `08ac6cd` · 2026-06-14
- [x] Add Budget page + routes (estimated vs. actual per category) (US-8)
- [x] Add Guests page + add/update/delete routes (US-9)
- [x] Add Discover entry screen (`discover.html`)
- [x] Add Home / Plan dashboard pages (`home.html`, `plan.html`)
- [x] Add shared `_components.html` partials and `logo.svg`
- [x] Major `style.css` rework (brand palette, Inter/Cormorant, responsive)
- [x] Add `vowly_wedding_planning_logic_israel.md` domain notes

## Milestone 7 — OAuth social login `88e857c` · 2026-06-14
- [x] Add Authlib-based `/auth/<provider>` + callback routes (Google/Facebook) (US-1 extended)
- [x] Add OAuth env vars to `config.py`
- [x] Document OAuth env vars and callback URLs in the README

## Milestone 8 — Cleanup & refactor `0de6fce` · 2026-06-15
- [x] Slim down / refactor `app.py` (remove dead code, ~460 lines deleted)
- [x] Small fixes to `database.py`, `fetch_google_vendors.py`, base/index/settings templates

## Milestone 9 — Docs & final polish (in progress)
- [x] Author `PRD.md` and this `tasks.md`
- [ ] Capture screenshots of the main screens into `docs/` and embed them in the README
- [ ] Final end-to-end pass: fresh clone → `seed.py` → `app.py` → walk the full journey

---

### How to use this file
- Milestones follow the real commit order; each `[ ]` inside is roughly one commit's worth of work.
- Flip `[ ]` → `[x]` the moment a task lands, and update the **Progress** counter at the top.
- New work goes under **Milestone 9** (or a new milestone) as fresh checkboxes — don't rewrite past history.
