"""
Vowly database helper.

Uses raw sqlite3 (no ORM) so the SQL and schema stay visible
for the Database Management & Design course.

Schema highlights:
  - Every entity is its own table with a primary key.
  - 1:N relationships use a foreign key on the "many" side.
  - N:M relationships are decomposed via junction tables
    (favorite_vendors is the classic example here).
  - All tables are in 1NF/2NF/3NF (atomic columns, no partial
    or transitive dependencies).
"""

import sqlite3
from flask import g
from config import DATABASE_PATH


def get_db():
    """Get a per-request SQLite connection."""
    if "db" not in g:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        g.db = conn
    return g.db


def close_db(_e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

SCHEMA_SQL = """
-- 1. USERS  (entity: registered couple member)
CREATE TABLE IF NOT EXISTS users (
    user_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name      TEXT NOT NULL,
    email          TEXT NOT NULL UNIQUE,
    password_hash  TEXT NOT NULL,
    city           TEXT,
    phone          TEXT,
    role           TEXT,            -- 'Bride' | 'Groom' | 'Other'
    partner_name   TEXT,
    partner_email  TEXT,
    partner_phone  TEXT,
    language       TEXT DEFAULT 'en',
    distance_km    INTEGER DEFAULT 50,
    created_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 2. WEDDING PROFILES  (1 user : N wedding profiles)
CREATE TABLE IF NOT EXISTS wedding_profiles (
    wedding_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id                 INTEGER NOT NULL,
    partner_name            TEXT,
    wedding_date            TEXT,
    estimated_guests        INTEGER,
    budget                  REAL,
    city                    TEXT,
    venue_type_preference   TEXT,
    created_at              TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- 3. VENDOR CATEGORIES  (lookup table -- avoids repeating category names)
CREATE TABLE IF NOT EXISTS vendor_categories (
    category_id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    category_name                     TEXT NOT NULL UNIQUE,
    description                       TEXT,
    default_due_months_before_wedding INTEGER DEFAULT 6
);

-- 4. CHECKLIST ITEMS  (wedding 1:N items, category 1:N items)
CREATE TABLE IF NOT EXISTS checklist_items (
    checklist_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    wedding_id        INTEGER NOT NULL,
    category_id       INTEGER,
    title             TEXT NOT NULL,
    description       TEXT,
    due_date          TEXT,
    status            TEXT NOT NULL DEFAULT 'Pending'
                      CHECK (status IN ('Pending','In Progress','Completed','Skipped')),
    completed_at      TEXT,
    created_at        TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (wedding_id)  REFERENCES wedding_profiles(wedding_id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES vendor_categories(category_id)
);

-- 5. VENDORS  (category 1:N vendors)
CREATE TABLE IF NOT EXISTS vendors (
    vendor_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    business_name  TEXT NOT NULL,
    category_id    INTEGER NOT NULL,
    city           TEXT,
    address        TEXT,
    phone          TEXT,
    email          TEXT,
    website        TEXT,
    instagram_url  TEXT,
    description    TEXT,
    price_min      REAL,
    price_max      REAL,
    rating_average REAL DEFAULT 0,
    is_active      INTEGER NOT NULL DEFAULT 1,
    created_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES vendor_categories(category_id)
);

-- 6. VENDOR PHOTOS  (vendor 1:N photos)
CREATE TABLE IF NOT EXISTS vendor_photos (
    photo_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    vendor_id   INTEGER NOT NULL,
    photo_url   TEXT NOT NULL,
    caption     TEXT,
    uploaded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vendor_id) REFERENCES vendors(vendor_id) ON DELETE CASCADE
);

-- 7. VENDOR SWIPES  (Tinder-style behavior log)
CREATE TABLE IF NOT EXISTS vendor_swipes (
    swipe_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    wedding_id  INTEGER NOT NULL,
    vendor_id   INTEGER NOT NULL,
    action      TEXT NOT NULL CHECK (action IN ('Like','Skip')),
    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id)    REFERENCES users(user_id)              ON DELETE CASCADE,
    FOREIGN KEY (wedding_id) REFERENCES wedding_profiles(wedding_id) ON DELETE CASCADE,
    FOREIGN KEY (vendor_id)  REFERENCES vendors(vendor_id)           ON DELETE CASCADE,
    UNIQUE (wedding_id, vendor_id)   -- one swipe decision per wedding/vendor pair
);

-- 8. FAVORITE VENDORS  (junction table => N:M between wedding_profiles & vendors)
CREATE TABLE IF NOT EXISTS favorite_vendors (
    wedding_id INTEGER NOT NULL,
    vendor_id  INTEGER NOT NULL,
    added_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (wedding_id, vendor_id),
    FOREIGN KEY (wedding_id) REFERENCES wedding_profiles(wedding_id) ON DELETE CASCADE,
    FOREIGN KEY (vendor_id)  REFERENCES vendors(vendor_id)           ON DELETE CASCADE
);

-- 9. SELECTED VENDORS
CREATE TABLE IF NOT EXISTS selected_vendors (
    selected_vendor_id INTEGER PRIMARY KEY AUTOINCREMENT,
    wedding_id         INTEGER NOT NULL,
    vendor_id          INTEGER NOT NULL,
    category_id        INTEGER NOT NULL,
    status             TEXT NOT NULL DEFAULT 'Considering'
                       CHECK (status IN ('Considering','Contacted','Meeting Scheduled','Booked','Rejected')),
    agreed_price       REAL,
    notes              TEXT,
    created_at         TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (wedding_id)  REFERENCES wedding_profiles(wedding_id) ON DELETE CASCADE,
    FOREIGN KEY (vendor_id)   REFERENCES vendors(vendor_id),
    FOREIGN KEY (category_id) REFERENCES vendor_categories(category_id)
);

-- 10. VENDOR REVIEWS
CREATE TABLE IF NOT EXISTS vendor_reviews (
    review_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    vendor_id   INTEGER NOT NULL,
    user_id     INTEGER NOT NULL,
    wedding_id  INTEGER,
    rating      INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    review_text TEXT,
    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vendor_id)  REFERENCES vendors(vendor_id)            ON DELETE CASCADE,
    FOREIGN KEY (user_id)    REFERENCES users(user_id)                ON DELETE CASCADE,
    FOREIGN KEY (wedding_id) REFERENCES wedding_profiles(wedding_id)  ON DELETE SET NULL
);

-- 11. APPOINTMENTS
CREATE TABLE IF NOT EXISTS appointments (
    appointment_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    wedding_id       INTEGER NOT NULL,
    vendor_id        INTEGER NOT NULL,
    appointment_date TEXT NOT NULL,
    location         TEXT,
    notes            TEXT,
    status           TEXT NOT NULL DEFAULT 'Scheduled'
                     CHECK (status IN ('Scheduled','Completed','Cancelled')),
    created_at       TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (wedding_id) REFERENCES wedding_profiles(wedding_id) ON DELETE CASCADE,
    FOREIGN KEY (vendor_id)  REFERENCES vendors(vendor_id)
);

-- 12. BUDGET ITEMS
CREATE TABLE IF NOT EXISTS budget_items (
    budget_item_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    wedding_id        INTEGER NOT NULL,
    category_id       INTEGER NOT NULL,
    estimated_amount  REAL DEFAULT 0,
    actual_amount     REAL DEFAULT 0,
    notes             TEXT,
    FOREIGN KEY (wedding_id)  REFERENCES wedding_profiles(wedding_id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES vendor_categories(category_id)
);

-- 13. WEDDING SUPPLIER STATUS  (per-wedding state for the supplier checklist)
--     supplier_code is a stable string id from suppliers.py (NOT a FK to vendor_categories).
CREATE TABLE IF NOT EXISTS wedding_supplier_status (
    wedding_id      INTEGER NOT NULL,
    supplier_code   TEXT    NOT NULL,
    status          TEXT    NOT NULL DEFAULT 'Not started'
                    CHECK (status IN ('Not started','In progress','Booked','Not relevant')),
    notes           TEXT,
    budget          REAL,
    updated_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (wedding_id, supplier_code),
    FOREIGN KEY (wedding_id) REFERENCES wedding_profiles(wedding_id) ON DELETE CASCADE
);
"""


def init_db():
    """Create all tables if they do not exist, and apply lightweight migrations."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.executescript(SCHEMA_SQL)

    # --- Lightweight migrations: add new columns to existing users table ---
    existing = {row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
    for col, ddl in (
        ("role",          "ALTER TABLE users ADD COLUMN role TEXT"),
        ("partner_name",  "ALTER TABLE users ADD COLUMN partner_name TEXT"),
        ("partner_email", "ALTER TABLE users ADD COLUMN partner_email TEXT"),
        ("partner_phone", "ALTER TABLE users ADD COLUMN partner_phone TEXT"),
        ("language",      "ALTER TABLE users ADD COLUMN language TEXT DEFAULT 'en'"),
        ("distance_km",   "ALTER TABLE users ADD COLUMN distance_km INTEGER DEFAULT 50"),
    ):
        if col not in existing:
            conn.execute(ddl)

    conn.commit()
    conn.close()


def query(sql, params=(), one=False):
    """Run a SELECT and return rows (or a single row)."""
    cur = get_db().execute(sql, params)
    rows = cur.fetchall()
    cur.close()
    return (rows[0] if rows else None) if one else rows


def execute(sql, params=()):
    """Run an INSERT/UPDATE/DELETE and return the cursor lastrowid."""
    db = get_db()
    cur = db.execute(sql, params)
    db.commit()
    last_id = cur.lastrowid
    cur.close()
    return last_id
