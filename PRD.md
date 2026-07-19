# Vowly 💍 — Product Requirements Document (PRD)

> A wedding-planning web app, built as a final project for the **Database Management & Design** course.
> Stack: Flask + SQLite + raw SQL (no ORM).

---

## 1. Purpose & Problem — What we're building and why

**The problem.** Planning a wedding in Israel is a scattered, stressful process: the couple juggles vendors, budget, guests, and tasks across many disconnected places (WhatsApp, spreadsheets, friends' recommendations, Google searches). There is no single view that shows "how far along are we", "how much money is left", and "which vendors have we already booked".

**What we're building.** *Vowly* — a single web app that centralizes the entire wedding-planning journey:
- **Tinder-style** vendor discovery (Like / Skip) with filtering by category, city, rating, and price.
- A categorized **Checklist** with statuses and due dates.
- Management of **Budget**, **Guests**, vendor **Appointments**, and **Reviews**.
- A SQL-driven **analytics Dashboard** that surfaces progress and insights.

**Why (the academic rationale).** Beyond user value, the product is designed to demonstrate database-design principles in practice: an ERD→DSD model, normalization (1NF/2NF/3NF), foreign keys, an N:M junction table, `CHECK`/`UNIQUE` constraints, and rich SQL queries (`JOIN`, `GROUP BY`, `HAVING`, `COUNT`/`AVG`/`SUM`, `LIKE`, `BETWEEN`, `IN`, `DISTINCT`).

---

## 2. Target User / Usage Scenario

**Primary user.** An engaged Israeli couple (ages ~25–40) starting to plan their wedding, comfortable with an app-style digital interface, looking for one tool to centralize the process.

**Secondary user (course context).** The lecturer / grader evaluating the project on database design and SQL-query quality.

**Primary usage scenario (User Journey):**
1. The couple signs up (email + password, or Google/Facebook) and fills in a **wedding profile** — date, estimated guest count, budget, city, preferred venue type (Onboarding).
2. On the **Discover / Swipe** screen the couple "swipes" through vendors by category, marking Like / Skip.
3. Liked vendors go to **Favorites**; from there the couple promotes vendors to a **Selected Vendors** shortlist with status, agreed price, and notes.
4. The couple schedules **Appointments**, writes **Reviews**, updates the **Checklist** and **Budget**, and manages the **Guest** list.
5. On the **Dashboard / Analytics** the couple sees the overall picture: checklist completion %, budget vs. actual spend, top vendors, and average ratings.

---

## 3. Scope

### ✅ In Scope
- Registration & login: email + password (hashed) and OAuth for Google/Facebook.
- Onboarding + create/edit wedding profile.
- Vendor catalog with filtering (category, city, minimum rating, maximum price, text search) and a detailed vendor page (photos, reviews, contact).
- Swipe mechanism (Like/Skip) with swipe history and no-double-swipe protection.
- Favorites, Selected Vendors shortlist, Appointments, Reviews (rating 1–5).
- Categorized checklist, budget management, guest management.
- SQL-driven analytics dashboard.
- Importing real vendor data from the **Google Places API** into a local DB (one-time cache).
- A normalized database (3NF) with documented ERD/DSD.

### ❌ Explicitly Out of Scope
- **Payments / checkout** — no billing, digital wallet, or paid bookings.
- **Real-time chat / messaging** between couple and vendor (contact is via the vendor's details only).
- **Native mobile app** (iOS/Android) — the product is responsive Web only.
- **Vendor-facing admin portal** — vendors are not registered users; there is no self-service for them.
- **Push notifications / automated emails** (reminders, newsletter).
- **Full multi-language / i18n** and **full accessibility (WCAG)** at a certification level.
- **ML-based recommendation engine** — filtering is criteria-based, not a learned model.
- **Continuous live sync from Google** — data is imported once into the cache, not auto-refreshed.
- **Multi-tenancy / organizations** — a simple user→wedding model.

---

## 4. Functional Requirements — User Stories / Features

| # | As a user I want to… | So that… | Status |
|---|---|---|---|
| US-1 | sign up and log in (email/password or Google/Facebook) | my data is saved and secure | ✅ |
| US-2 | fill in a wedding profile (date, guests, budget, city, venue type) | the app adapts to my wedding | ✅ |
| US-3 | discover vendors Swipe-style with Like/Skip | quickly filter vendors that interest me | ✅ |
| US-4 | filter and search vendors (category/city/rating/price/text) | find exactly what I need | ✅ |
| US-5 | view a full vendor page (photos, reviews, contact) | evaluate a vendor before deciding | ✅ |
| US-6 | save vendors to favorites and promote them to a selected list | manage a shortlist with status/agreed price/notes | ✅ |
| US-7 | manage a categorized checklist with status and due date | never forget a planning step | ✅ |
| US-8 | manage a budget per category (estimated vs. actual) | avoid exceeding the budget | ✅ |
| US-9 | manage a guest list | track the number of invitees and confirmations | ✅ |
| US-10 | schedule and manage vendor appointments | coordinate my schedule | ✅ |
| US-11 | write and read reviews (rating 1–5) | benefit from other couples' experience | ✅ |
| US-12 | view an analytics dashboard (progress, budget, top vendors) | understand the overall picture | ✅ |

**Non-functional requirements (NFR):** reasonable performance on SQLite; passwords stored as a hash; input validation on forms; responsive UI; reasonable page-load time on desktop and mobile.

---

## 5. Technical Choices — Stack, Libraries, Constraints

**Backend**
- **Flask 3** (Python) — web server and routing.
- **`sqlite3` from the standard library** — DB access with **raw SQL, no ORM** (course requirement: show real SQL).
- **Werkzeug** — password hashing and utilities.
- **Authlib** — OAuth (Google / Facebook).
- **python-dotenv** — loads configuration from `.env`.
- **requests** — calls to the Google Places API during the data-import step.

**Frontend**
- **Jinja2** templates; **hand-written** HTML/CSS/JS (no framework), fonts Inter + Cormorant Garamond.

**Configuration / running**
- `python seed.py` to populate demo data → `python app.py` (default: `http://127.0.0.1:5000`).
- Deployment: Render / gunicorn (`gunicorn app:app`), with an option to migrate to PostgreSQL in production.

**Constraints & limitations**
- **No ORM** — all DB access is hand-written SQL (a deliberate course decision).
- **SQLite** as the default DB — suitable for the project/demo; production would require migrating to Postgres.
- OAuth requires valid `CLIENT_ID/SECRET` and `VOWLY_PUBLIC_BASE_URL`; without them only email/password login is active.
- Importing real vendors requires `GOOGLE_PLACES_API_KEY`; otherwise we rely on `vendors_cache.json` / `seed.py`.

---

## 6. Data — Data Sources & Core Entities

### Data sources
- **Real vendor data:** imported once from the **Google Places API** (`fetch_google_vendors.py`) across several Israeli cities, normalized into `vendors_cache.json`, and loaded into the DB via `seed.py`. If the cache already exists, no further API calls are made (no live sync).
- **User/wedding data:** created **locally** by the user (profile, swipes, favorites, tasks, budget, guests, appointments, reviews) and stored in **SQLite** (`instance/vowly.db`).
- **Demo data:** `seed.py` populates demo users and weddings for demonstration (e.g. `noa@vowly.dev` / `password123`).

### Core entities
| Entity | Description | Key relationships |
|---|---|---|
| `users` | A registered user | 1:N to `wedding_profiles`, `vendor_reviews`, `vendor_swipes` |
| `wedding_profiles` | Details of the planned wedding | belongs to `users`; parent of most child entities |
| `vendor_categories` | Lookup table of vendor categories | 1:N to `vendors`, `checklist_items`, `budget_items` |
| `vendors` | A vendor (venue, DJ, photographer, etc.) | belongs to `vendor_categories`; parent of `vendor_photos`, `vendor_reviews` |
| `vendor_photos` | Photos of a vendor | 1:N from `vendors` (keeps 1NF) |
| `vendor_swipes` | Historical log of Like/Skip | `UNIQUE(wedding_id, vendor_id)` prevents a double-swipe |
| `favorite_vendors` | **N:M junction table** between wedding and vendors | composite PK `(wedding_id, vendor_id)` |
| `selected_vendors` | Shortlist with status/agreed price/notes | links `wedding_profiles`↔`vendors` |
| `checklist_items` | Categorized wedding tasks | belongs to `wedding_profiles` + `vendor_categories` |
| `budget_items` | Estimated vs. actual budget per category | belongs to `wedding_profiles` + `vendor_categories` |
| `appointments` | Meetings with vendors | links `wedding_profiles`↔`vendors` |
| `vendor_reviews` | Review + rating 1–5 | links `users`/`wedding_profiles`↔`vendors` |

> The database is normalized to **3NF**: category names and user details are stored in exactly one place and referenced by a foreign key (see the full breakdown in `README.md` section 4).

---

## 7. Success Criteria — Definition of Done

The project is considered "done" when **all** of the following hold:

- [x] **Full local run:** `pip install -r requirements.txt` → `python seed.py` → `python app.py` starts with no errors.
- [x] **End-to-end user journey works:** register → wedding profile → Swipe → favorites → selected vendors → appointments → reviews → dashboard.
- [x] **All User Stories (US-1…US-12)** are implemented and demonstrable.
- [x] **Normalized database (3NF)** with documented ERD and DSD, including an N:M junction table and `CHECK`/`UNIQUE` constraints.
- [x] **The analytics dashboard** actually runs `JOIN` + `GROUP BY` + `HAVING` + aggregate functions.
- [x] **The vendor catalog** is displayed with real data (Google Places) and supports all filters.
- [x] **Baseline security:** passwords hashed, input validation, and secrets loaded from `.env`.
- [x] **README** is complete: run instructions, route table, DB-schema documentation, and SQL examples.
- [ ] **Screenshots** of the main screens are added to `docs/` and embedded in the README (nice-to-have).

---

## 8. Sketch / Wireframe

**Navigation map (Site Map):**

```
Landing (/)
  └── Register / Login  ──►  Onboarding (wedding profile)
                                   │
                                   ▼
                            ┌─────────────┐
                            │  Dashboard  │  progress · budget · top vendors
                            └─────┬───────┘
        ┌──────────┬─────────────┼──────────────┬───────────┐
        ▼          ▼             ▼              ▼           ▼
    Discover/   Vendors      Checklist       Budget      Analytics
     Swipe      (filter)      (tasks)        (budget)     (SQL)
        │          │
        ▼          ▼
   Favorites ─► Selected ─► Appointments ─► Reviews
                Vendors     (meetings)      (reviews)
   (also: Guests · Settings · Vendor Detail)
```

**Swipe / Discover screen (core screen):**

```
┌───────────────────────────────────────────────┐
│  Vowly 💍     Discover  Vendors  Checklist  ⚙  │  ← Navbar
├───────────────────────────────────────────────┤
│        Category: [ Venues ▼ ]  City: [ TLV ▼ ] │
│                                                 │
│        ┌───────────────────────────┐            │
│        │                           │            │
│        │      [ vendor photo ]     │            │
│        │                           │            │
│        │  Vendor name · City       │            │
│        │  ⭐ 4.6   ₪₪   category    │            │
│        │  Short description...      │            │
│        └───────────────────────────┘            │
│                                                 │
│         [ ✖ Skip ]         [ ♥ Like ]           │
│                                                 │
│              ◄ next card shown ►                │
└───────────────────────────────────────────────┘
```

**Dashboard / Analytics screen:**

```
┌───────────────────────────────────────────────┐
│  Hi Noa 👋   |  ⏳ 84 days to the wedding        │
├───────────────┬───────────────┬────────────────┤
│  Tasks        │  Budget       │  Selected       │
│  12/20 ✅     │  ₪78K/₪120K   │  5 booked       │
│  ▓▓▓▓▓▓░░ 60% │  ▓▓▓▓▓░░░ 65% │                │
├───────────────┴───────────────┴────────────────┤
│  📊 Average rating per category (JOIN+AVG+GROUP)│
│    Venues        ████████████ 4.7               │
│    Photographers ██████████   4.3               │
│    DJ            █████████     4.1              │
├─────────────────────────────────────────────────┤
│  🔥 Top vendors (COUNT likes · ORDER BY)         │
│    1. Studio Or   · 2. Gan Vradim · 3. DJ Adam   │
└─────────────────────────────────────────────────┘
```

> The sketches are low-fidelity concepts; the actual design is implemented in `templates/` and `static/css/style.css` (fonts Inter + Cormorant Garamond, Vowly brand palette).
