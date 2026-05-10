# Vowly 💍

A modern wedding planning web app built with **Flask + SQLite + raw SQL** (no ORM),
designed for the **Database Management & Design** course.

Couples sign up, build a wedding profile, work through a categorized checklist,
discover vendors with a Tinder-style **Like / Skip** swipe, save favorites,
shortlist & book selected vendors, schedule appointments, leave reviews and view
a SQL-driven analytics dashboard.

---

## 1. How to run locally

```bash
pip install -r requirements.txt
python seed.py        # optional: populate with realistic demo data
python app.py
```

Then open <http://127.0.0.1:5000>.

### Demo logins (after `python seed.py`)

| Email | Password |
|---|---|
| noa@vowly.dev    | password123 |
| daniel@vowly.dev | password123 |
| maya@vowly.dev   | password123 |
| shira@vowly.dev  | password123 |

---

## 2. Pages / routes

| Route | Purpose |
|---|---|
| `/` | Landing page (logo, hero, features) |
| `/register`, `/login`, `/logout` | Authentication |
| `/dashboard` | Wedding progress overview |
| `/wedding-profile` | Create / edit wedding details |
| `/checklist` | Categorized to-do, status updates |
| `/vendors` | Filter vendors by category, city, rating, price, text |
| `/vendor/<id>` | Vendor profile, photos, reviews, contact |
| `/swipe`, `/swipe/<category_id>` | Tinder-style Like / Skip vendor discovery |
| `/favorites` | Liked vendors grouped by category |
| `/selected-vendors` | Shortlist with status, agreed price, notes |
| `/appointments` | Schedule and manage vendor meetings |
| `/reviews` | Leave & browse reviews |
| `/analytics` | SQL analytics: JOIN, GROUP BY, HAVING, COUNT, AVG, SUM |

---

## 3. Logo

The Vowly logo lives at `static/img/logo.png` and is used as:

- favicon
- navbar brand
- landing-page hero
- login / register cards
- footer

To replace it: drop your PNG file at `static/img/logo.png` (recommended ~256×256, transparent).

---

## 4. Database design

### 4.1 Conceptual ERD (entities)

```
users (1) ─────────< wedding_profiles (N)
wedding_profiles (1) ─────────< checklist_items (N)
vendor_categories (1) ────────< checklist_items (N)
vendor_categories (1) ────────< vendors (N)
vendors (1) ──────────────────< vendor_photos (N)
vendors (1) ──────────────────< vendor_reviews (N)
users   (1) ──────────────────< vendor_reviews (N)
wedding_profiles (1) ─────────< vendor_reviews (N)
users (1) ────────────────────< vendor_swipes (N)
wedding_profiles (1) ─────────< vendor_swipes (N)
vendors (1) ──────────────────< vendor_swipes (N)
wedding_profiles (N) >─ favorite_vendors ─< (N) vendors      ← N:M via junction table
wedding_profiles (1) ─────────< selected_vendors (N)
vendors (1) ──────────────────< selected_vendors (N)
wedding_profiles (1) ─────────< appointments (N)
vendors (1) ──────────────────< appointments (N)
wedding_profiles (1) ─────────< budget_items (N)
vendor_categories (1) ────────< budget_items (N)
```

### 4.2 Physical DSD (tables)

```
users(user_id PK, full_name, email UNIQUE, password_hash, city, phone, created_at)
wedding_profiles(wedding_id PK, user_id FK→users, partner_name, wedding_date,
                 estimated_guests, budget, city, venue_type_preference, created_at)
vendor_categories(category_id PK, category_name UNIQUE, description,
                  default_due_months_before_wedding)
checklist_items(checklist_item_id PK, wedding_id FK, category_id FK,
                title, description, due_date, status, completed_at, created_at)
vendors(vendor_id PK, business_name, category_id FK, city, address, phone, email,
        website, instagram_url, description, price_min, price_max, rating_average,
        is_active, created_at)
vendor_photos(photo_id PK, vendor_id FK, photo_url, caption, uploaded_at)
vendor_swipes(swipe_id PK, user_id FK, wedding_id FK, vendor_id FK,
              action CHECK IN ('Like','Skip'), created_at,
              UNIQUE(wedding_id, vendor_id))
favorite_vendors(wedding_id FK, vendor_id FK, added_at,
                 PRIMARY KEY (wedding_id, vendor_id))   -- junction table for N:M
selected_vendors(selected_vendor_id PK, wedding_id FK, vendor_id FK, category_id FK,
                 status, agreed_price, notes, created_at)
vendor_reviews(review_id PK, vendor_id FK, user_id FK, wedding_id FK,
               rating CHECK 1..5, review_text, created_at)
appointments(appointment_id PK, wedding_id FK, vendor_id FK, appointment_date,
             location, notes, status, created_at)
budget_items(budget_item_id PK, wedding_id FK, category_id FK,
             estimated_amount, actual_amount, notes)
```

### 4.3 Normalization (1NF / 2NF / 3NF)

- **1NF — atomic columns.** Every column stores a single value (no comma-separated
  vendor lists, no multi-valued fields). Photos live in their own `vendor_photos`
  table instead of `photo1`, `photo2`, `photo3` columns.
- **2NF — no partial dependencies.** All tables use a single-column surrogate PK
  except `favorite_vendors`, where the composite PK `(wedding_id, vendor_id)` is
  fully used: the only non-key column `added_at` depends on the whole key.
- **3NF — no transitive dependencies.** A vendor's `category_name` is **not**
  duplicated in `vendors`; only `category_id` is stored, and the name is looked up
  via `vendor_categories`. The same applies to user details (never duplicated into
  `wedding_profiles`) and category names (never duplicated into `checklist_items`,
  `selected_vendors`, `budget_items`).

### 4.4 Why each table exists

- **users / wedding_profiles** — a user is a person; a wedding profile is the event
  being planned. A user can technically own several wedding profiles, so this is
  modeled as 1:N.
- **vendor_categories** — a lookup table that prevents the category name from being
  repeated across `vendors`, `checklist_items`, `budget_items`, etc. (avoids
  update anomalies).
- **vendors / vendor_photos** — one vendor has many photos → 1:N to keep 1NF.
- **vendor_swipes** — historical log of every Like/Skip decision. Separate table
  so the swipe history is preserved even if the user later un-favorites someone.
  `UNIQUE(wedding_id, vendor_id)` enforces "no double-swipe".
- **favorite_vendors** — pure N:M between `wedding_profiles` and `vendors`. Has
  no surrogate PK; the composite PK forbids duplicate rows.
- **selected_vendors** — the couple's shortlist, with extra attributes
  (`status`, `agreed_price`, `notes`). It is modeled as its own entity because
  these attributes describe the *relationship*, not the vendor itself.
- **vendor_reviews / appointments / budget_items** — each is its own entity with
  its own attributes; storing them anywhere else would break 1NF/3NF.

### 4.5 ERD → DSD conversion summary

1. Every entity in the ERD became its own table.
2. Each entity received a primary key (single-column surrogate `*_id`, except the
   junction table which uses a composite key).
3. Every 1:N relationship was implemented by adding a foreign key on the **many**
   side — e.g. `wedding_profiles.user_id`, `vendors.category_id`,
   `checklist_items.wedding_id`.
4. The N:M relationship between **wedding_profiles** and **vendors** was
   decomposed into two 1:N relationships through the **favorite_vendors**
   junction table.
5. CHECK constraints encode enumerations (`status`, `action`, `rating`).
6. UNIQUE constraints prevent duplicates (`users.email`,
   `vendor_categories.category_name`, `vendor_swipes(wedding_id, vendor_id)`).

---

## 5. SQL examples (used inside the app)

### A. Vendors of a category, sorted by rating (JOIN + WHERE + ORDER BY)
```sql
SELECT vc.category_name, v.business_name, v.city, v.price_min, v.price_max, v.rating_average
FROM vendors v
JOIN vendor_categories vc ON v.category_id = vc.category_id
WHERE vc.category_name = 'DJ'
ORDER BY v.rating_average DESC;
```

### B. Most liked vendors (JOIN + GROUP BY + COUNT + ORDER BY)
```sql
SELECT v.business_name, COUNT(vs.swipe_id) AS total_likes
FROM vendor_swipes vs
JOIN vendors v ON vs.vendor_id = v.vendor_id
WHERE vs.action = 'Like'
GROUP BY v.business_name
ORDER BY total_likes DESC;
```

### C. Average rating per category (JOIN + AVG + GROUP BY)
```sql
SELECT vc.category_name, AVG(vr.rating) AS average_rating
FROM vendor_reviews vr
JOIN vendors v             ON vr.vendor_id  = v.vendor_id
JOIN vendor_categories vc  ON v.category_id = vc.category_id
GROUP BY vc.category_name
ORDER BY average_rating DESC;
```

### D. Categories whose average rating ≥ 4 (HAVING)
```sql
SELECT vc.category_name, AVG(vr.rating) AS average_rating
FROM vendor_reviews vr
JOIN vendors v            ON vr.vendor_id  = v.vendor_id
JOIN vendor_categories vc ON v.category_id = vc.category_id
GROUP BY vc.category_name
HAVING AVG(vr.rating) >= 4
ORDER BY average_rating DESC;
```

### E. Checklist progress per wedding (JOIN + COUNT + SUM CASE)
```sql
SELECT wp.wedding_id,
       COUNT(ci.checklist_item_id) AS total_items,
       SUM(CASE WHEN ci.status='Completed' THEN 1 ELSE 0 END) AS completed_items
FROM wedding_profiles wp
JOIN checklist_items ci ON wp.wedding_id = ci.wedding_id
GROUP BY wp.wedding_id;
```

### F. Budget per category (SUM + GROUP BY)
```sql
SELECT vc.category_name,
       SUM(bi.estimated_amount) AS estimated_total,
       SUM(bi.actual_amount)    AS actual_total
FROM budget_items bi
JOIN vendor_categories vc ON bi.category_id = vc.category_id
GROUP BY vc.category_name
ORDER BY actual_total DESC;
```

### Other operators demonstrated in the codebase

- `WHERE … AND …` — `vendors` filter route uses category + city + min_rating + max_price.
- `LIKE` — vendor search: `WHERE business_name LIKE ? OR description LIKE ?`.
- `BETWEEN` / `IN` — review check `rating BETWEEN 1 AND 5`,
  status checks `status IN ('Pending','In Progress','Completed','Skipped')`.
- `DISTINCT` — `SELECT DISTINCT city FROM vendors` for the city filter dropdown.
- `INSERT / UPDATE / DELETE` — every form route in `app.py` performs DML.

---

## 6. Academic database design explanation

**Entities & primary keys.** Each real-world concept (user, wedding, category,
vendor, photo, swipe, favorite, selected vendor, review, appointment, budget item)
is its own table with a primary key — usually a surrogate `*_id` integer, except
`favorite_vendors` which uses the composite PK `(wedding_id, vendor_id)` because
it represents a pure association.

**Foreign keys & cardinality.** Every 1:N relationship is implemented by placing a
foreign key on the *many* side. Example: a wedding has many checklist items, so
`checklist_items.wedding_id` references `wedding_profiles.wedding_id`. This is the
standard ERD-to-DSD rule.

**N:M relationships and junction tables.** A wedding can favorite many vendors,
and a vendor can be favorited by many weddings — a true N:M relationship. SQL
cannot store N:M directly, so we decompose it into two 1:N relationships using
the **favorite_vendors** junction table.

**Avoiding duplicated data.** Category names live in **one** place
(`vendor_categories.category_name`); user details live in **one** place
(`users`). Other tables reference them via foreign keys, never copy them. This
prevents the classic update anomaly (changing a name in one row but not another).

**1NF.** Every column stores a single, atomic value — no comma-separated lists,
no `vendor1`, `vendor2`, `vendor3` columns, no JSON blobs. Multi-valued data
(photos, reviews, swipes, budget items) lives in its own child table.

**2NF.** Tables built on a composite PK have all non-key attributes depend on the
whole key. `favorite_vendors(wedding_id, vendor_id, added_at)` satisfies this
trivially: `added_at` describes that exact pair.

**3NF.** No non-key attribute depends on another non-key attribute. We never
store `category_name` next to `category_id`, never store `user_full_name` next to
`user_id`, etc. Looking up the readable name is a JOIN, not a duplicated column.

**Analytics dashboard.** `/analytics` showcases the SQL learning outcomes:
multi-table `JOIN`s, `GROUP BY` aggregations, `HAVING` filters on aggregates,
and the full set of aggregate functions (`COUNT`, `AVG`, `SUM`, `MIN`, `MAX`).
The page directly mirrors the queries listed above.

**Why these auxiliary tables exist.**
- `vendor_swipes` = behavioral log; needed to power "don't show me twice".
- `favorite_vendors` = N:M junction; cleanly separates favoriting from booking.
- `vendor_reviews` = ratings + text + author; can grow without touching `vendors`.
- `budget_items` = per-wedding, per-category numbers — a classic 1:N split.
- `checklist_items` = per-wedding tasks tagged by category — never repeated columns.

---

## 7. Screenshots

> Add screenshots to `docs/` and embed them here.

- `docs/landing.png`
- `docs/dashboard.png`
- `docs/swipe.png`
- `docs/analytics.png`

---

## 8. Deployment notes (Render)

- Runtime: Python 3.11+
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app`
  *(add `gunicorn` to `requirements.txt` for production)*
- Set environment variable `VOWLY_SECRET` to a strong random string.
- For production move from SQLite to **PostgreSQL** (e.g. Supabase). The schema
  in `database.py` uses standard SQL (`AUTOINCREMENT` → `SERIAL`/`IDENTITY`,
  `INTEGER`/`TEXT`/`REAL` map cleanly) so the migration is straightforward.

---

## 9. Tech stack

- **Backend:** Flask 3
- **DB driver:** stdlib `sqlite3` (raw SQL — no ORM)
- **Templates:** Jinja2
- **Auth:** Flask sessions + `werkzeug.security` password hashing
- **Frontend:** Hand-written HTML, CSS, vanilla JS
- **Fonts:** Inter + Cormorant Garamond
