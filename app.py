"""
Vowly - Flask wedding planning app.
"""

import os
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, abort
)
from werkzeug.security import generate_password_hash, check_password_hash

from config import SECRET_KEY
from database import init_db, close_db, query, execute, get_db
from suppliers import (
    SUPPLIERS, SUPPLIERS_BY_CODE, GROUPS, STATUSES, DEFAULT_STATUS,
    SUPPLIER_TO_VENDOR_CATEGORY,
    visible_suppliers_for_role, group_by_category,
)


app = Flask(__name__)
app.secret_key = SECRET_KEY
app.teardown_appcontext(close_db)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "error")
            return redirect(url_for("index"))
        # Guard against stale sessions (e.g. after a DB re-seed)
        if not query("SELECT 1 FROM users WHERE user_id = ?", (session["user_id"],), one=True):
            session.clear()
            flash("Session expired — please log in again.", "error")
            return redirect(url_for("index"))
        return view(*args, **kwargs)
    return wrapped


def current_user():
    if "user_id" not in session:
        return None
    return query("SELECT * FROM users WHERE user_id = ?", (session["user_id"],), one=True)


def current_wedding():
    if "user_id" not in session:
        return None
    return query(
        "SELECT * FROM wedding_profiles WHERE user_id = ? "
        "ORDER BY created_at DESC LIMIT 1",
        (session["user_id"],),
        one=True,
    )


@app.context_processor
def inject_globals():
    w = current_wedding()
    liked_count = 0
    if w:
        row = query(
            "SELECT COUNT(*) AS cnt FROM favorite_vendors WHERE wedding_id=?",
            (w["wedding_id"],), one=True,
        )
        liked_count = row["cnt"] if row else 0
    return {"user": current_user(), "wedding": w, "now": datetime.utcnow(),
            "liked_count": liked_count}


# ---------------------------------------------------------------------------
# Welcome / Auth (combined landing)
# ---------------------------------------------------------------------------

@app.route("/", methods=["GET", "POST"])
def index():
    """Combined login + register welcome screen."""
    if "user_id" in session and request.method == "GET":
        return redirect(url_for("checklist"))

    mode = request.args.get("mode", "login")  # 'login' or 'register'

    if request.method == "POST":
        action = request.form.get("action", "login")

        if action == "register":
            full_name = request.form.get("full_name", "").strip()
            email     = request.form.get("email", "").strip().lower()
            password  = request.form.get("password", "")
            city      = request.form.get("city", "").strip()
            phone     = request.form.get("phone", "").strip()
            role      = request.form.get("role", "").strip()  # 'Bride' | 'Groom' | 'Other'

            # Partner details (asked only when the groom is signing up)
            partner_name  = request.form.get("partner_name", "").strip()
            partner_email = request.form.get("partner_email", "").strip().lower()
            partner_phone = request.form.get("partner_phone", "").strip()

            if not (full_name and email and password):
                flash("Name, email and password are required.", "error")
                return redirect(url_for("index", mode="register"))

            if role in ("Bride", "Groom") and not (partner_name and partner_email and partner_phone):
                flash("Please fill in your partner's name, email and phone.", "error")
                return redirect(url_for("index", mode="register"))

            if query("SELECT user_id FROM users WHERE email = ?", (email,), one=True):
                flash("That email is already registered.", "error")
                return redirect(url_for("index", mode="register"))

            uid = execute(
                "INSERT INTO users (full_name, email, password_hash, city, phone, "
                "role, partner_name, partner_email, partner_phone) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (full_name, email, generate_password_hash(password), city, phone,
                 role or None,
                 partner_name or None,
                 partner_email or None,
                 partner_phone or None),
            )
            session["user_id"] = uid
            flash("Welcome to Vowly! Let's set up your wedding checklist.", "success")
            return redirect(url_for("onboarding"))

        # login
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = query("SELECT * FROM users WHERE email = ?", (email,), one=True)
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["user_id"]
            flash(f"Welcome back, {user['full_name'].split()[0]}!", "success")
            return redirect(url_for("checklist"))
        flash("Invalid email or password.", "error")
        return redirect(url_for("index", mode="login"))

    return render_template("index.html", mode=mode)


# Aliases so old links keep working
@app.route("/login")
def login():
    return redirect(url_for("index", mode="login"))


@app.route("/register")
def register():
    return redirect(url_for("index", mode="register"))


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))


# ---------------------------------------------------------------------------
# Wedding profile
# ---------------------------------------------------------------------------

@app.route("/wedding-profile", methods=["GET", "POST"])
@login_required
def wedding_profile():
    w = current_wedding()
    if request.method == "POST":
        partner   = request.form.get("partner_name", "").strip()
        wdate     = request.form.get("wedding_date", "").strip() or None
        guests    = request.form.get("estimated_guests", "").strip() or None
        budget    = request.form.get("budget", "").strip() or None
        city      = request.form.get("city", "").strip()
        venue_pref= request.form.get("venue_type_preference", "").strip()
        if w:
            execute(
                """UPDATE wedding_profiles
                   SET partner_name=?, wedding_date=?, estimated_guests=?, budget=?,
                       city=?, venue_type_preference=?
                   WHERE wedding_id=?""",
                (partner, wdate, guests, budget, city, venue_pref, w["wedding_id"]),
            )
            flash("Wedding profile updated.", "success")
        else:
            execute(
                """INSERT INTO wedding_profiles
                   (user_id, partner_name, wedding_date, estimated_guests, budget,
                    city, venue_type_preference)
                   VALUES (?,?,?,?,?,?,?)""",
                (session["user_id"], partner, wdate, guests, budget, city, venue_pref),
            )
            flash("Wedding profile created. Welcome to Vowly!", "success")
        return redirect(url_for("checklist"))
    return render_template("wedding_profile.html", w=w)


# ---------------------------------------------------------------------------
# Checklist (supplier-based)
# ---------------------------------------------------------------------------

def _ensure_wedding():
    """Return the current wedding row, creating an empty one if none exists.
    Used by the onboarding flow so a brand-new user can immediately store
    supplier statuses without filling out the wedding profile first."""
    w = current_wedding()
    if w:
        return w
    try:
        execute(
            "INSERT INTO wedding_profiles (user_id) VALUES (?)",
            (session["user_id"],),
        )
    except Exception:
        # User ID no longer valid (e.g. stale session after re-seed) — clear it
        session.clear()
        from flask import abort
        abort(redirect(url_for("index")))
    return current_wedding()


def _supplier_state_map(wedding_id):
    """Return {supplier_code: row} of saved status/notes/budget for a wedding."""
    rows = query(
        "SELECT * FROM wedding_supplier_status WHERE wedding_id = ?",
        (wedding_id,),
    )
    return {r["supplier_code"]: r for r in rows}


def _decorate_suppliers(suppliers, state_map):
    """Attach the saved status/notes/budget to each supplier dict (as a copy)."""
    out = []
    for s in suppliers:
        st = state_map.get(s["code"])
        out.append({
            **s,
            "status": st["status"] if st else DEFAULT_STATUS,
            "notes":  st["notes"]  if st else "",
            "budget": st["budget"] if st else None,
        })
    return out


@app.route("/onboarding", methods=["GET", "POST"])
@login_required
def onboarding():
    """Post-signup welcome screen: 'What would you like to start with?'

    The user picks one or more suppliers as starting points; each picked
    supplier is set to 'In progress'. Then we redirect to the full checklist.
    """
    user = current_user()
    role = (user["role"] if user else None) or ""
    suppliers = visible_suppliers_for_role(role)

    if request.method == "POST":
        w = _ensure_wedding()
        picked = request.form.getlist("start_with")
        valid_codes = {s["code"] for s in suppliers}
        picked = [c for c in picked if c in valid_codes]

        for code in picked:
            execute(
                """INSERT INTO wedding_supplier_status (wedding_id, supplier_code, status)
                   VALUES (?, ?, 'In progress')
                   ON CONFLICT(wedding_id, supplier_code) DO UPDATE SET
                       status     = excluded.status,
                       updated_at = CURRENT_TIMESTAMP""",
                (w["wedding_id"], code),
            )
        if picked:
            flash(f"Great \u2014 we marked {len(picked)} supplier(s) as in progress.", "success")
        return redirect(url_for("checklist"))

    grouped = group_by_category(suppliers)
    state   = _supplier_state_map(current_wedding()["wedding_id"]) if current_wedding() else {}
    return render_template(
        "onboarding.html",
        grouped_suppliers=grouped,
        state=state,
        role=role,
    )


@app.route("/checklist")
@login_required
def checklist():
    user = current_user()
    role = (user["role"] if user else None) or ""
    w = _ensure_wedding()

    suppliers = visible_suppliers_for_role(role)
    state     = _supplier_state_map(w["wedding_id"])
    decorated = _decorate_suppliers(suppliers, state)
    grouped   = group_by_category(decorated)

    # Map supplier code -> vendor_categories.category_id (for the swipe link)
    cat_rows = query("SELECT category_id, category_name FROM vendor_categories")
    name_to_id = {r["category_name"]: r["category_id"] for r in cat_rows}
    code_to_category_id = {
        code: name_to_id.get(name)
        for code, name in SUPPLIER_TO_VENDOR_CATEGORY.items()
        if name_to_id.get(name)
    }

    # ------------------------------------------------------------------
    # Derive each supplier's status automatically from real activity:
    #   - "Booked"     : a vendor in the matching category has been
    #                    selected/booked (selected_vendors.status='Booked')
    #   - "In progress": the user has swiped at least one vendor in that
    #                    category (vendor_swipes row exists)
    #   - "Not started": otherwise
    # The persisted wedding_supplier_status table is no longer used to
    # drive the card UI — it remains for legacy notes/budget storage.
    # ------------------------------------------------------------------
    swipe_cat_ids = {
        r["category_id"] for r in query(
            """SELECT DISTINCT v.category_id
                 FROM vendor_swipes vs
                 JOIN vendors v ON v.vendor_id = vs.vendor_id
                WHERE vs.wedding_id = ?""",
            (w["wedding_id"],),
        )
    }
    booked_cat_ids = {
        r["category_id"] for r in query(
            "SELECT category_id FROM selected_vendors "
            "WHERE wedding_id = ? AND status = 'Booked'",
            (w["wedding_id"],),
        )
    }
    for s in decorated:
        cid = code_to_category_id.get(s["code"])
        if cid and cid in booked_cat_ids:
            s["status"] = "Booked"
        elif cid and cid in swipe_cat_ids:
            s["status"] = "In progress"
        else:
            s["status"] = "Not started"

    # progress per category and overall
    def _progress(items):
        total = len([i for i in items if i["status"] != "Not relevant"])
        booked = len([i for i in items if i["status"] == "Booked"])
        in_progress = len([i for i in items if i["status"] == "In progress"])
        pct = round((booked / total) * 100) if total else 0
        return {"total": total, "booked": booked, "in_progress": in_progress, "pct": pct}

    category_progress = {cat: _progress(items) for cat, items in grouped.items()}
    overall = _progress(decorated)

    # Countdown to wedding (None if not set)
    days_until_wedding = None
    wedding_date_display = None
    wd_raw = w["wedding_date"] if w and "wedding_date" in w.keys() else None
    if wd_raw:
        try:
            wd = datetime.strptime(wd_raw[:10], "%Y-%m-%d").date()
            days_until_wedding = (wd - datetime.utcnow().date()).days
            wedding_date_display = wd.strftime("%b %d, %Y")
        except (ValueError, TypeError):
            pass

    # Top 3 "next up" suggestions: not started, ordered by group importance
    group_weight = {g: i for i, g in enumerate(GROUPS)}
    next_up = sorted(
        [s for s in decorated if s["status"] == "Not started"],
        key=lambda s: (group_weight.get(s["category"], 99), s["name"]),
    )[:3]

    partner_name = (w["partner_name"] if w and "partner_name" in w.keys() else None) \
                   or (user["partner_name"] if user else None)

    # Liked vendors strip — most recently liked, up to 20
    liked_vendors = query(
        """SELECT v.vendor_id, v.business_name, v.city, v.rating_average,
                  vc.category_name,
                  (SELECT photo_url FROM vendor_photos
                   WHERE vendor_id = v.vendor_id LIMIT 1) AS photo_url
             FROM favorite_vendors fv
             JOIN vendors v  ON v.vendor_id   = fv.vendor_id
             JOIN vendor_categories vc ON vc.category_id = v.category_id
            WHERE fv.wedding_id = ?
            ORDER BY fv.added_at DESC
            LIMIT 20""",
        (w["wedding_id"],),
    )

    return render_template(
        "checklist.html",
        grouped=grouped,
        category_progress=category_progress,
        overall=overall,
        statuses=STATUSES,
        groups=GROUPS,
        role=role,
        code_to_category_id=code_to_category_id,
        days_until_wedding=days_until_wedding,
        wedding_date_display=wedding_date_display,
        next_up=next_up,
        partner_name=partner_name,
        liked_vendors=liked_vendors,
    )


@app.route("/checklist/<code>/update", methods=["POST"])
@login_required
def checklist_update(code):
    """Update status / notes / budget for one supplier on the current wedding."""
    if code not in SUPPLIERS_BY_CODE:
        abort(404)
    w = _ensure_wedding()

    status = request.form.get("status", DEFAULT_STATUS)
    if status not in STATUSES:
        abort(400)
    notes  = request.form.get("notes", "").strip() or None
    budget_raw = request.form.get("budget", "").strip()
    try:
        budget = float(budget_raw) if budget_raw else None
    except ValueError:
        budget = None

    execute(
        """INSERT INTO wedding_supplier_status
               (wedding_id, supplier_code, status, notes, budget)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(wedding_id, supplier_code) DO UPDATE SET
               status     = excluded.status,
               notes      = excluded.notes,
               budget     = excluded.budget,
               updated_at = CURRENT_TIMESTAMP""",
        (w["wedding_id"], code, status, notes, budget),
    )

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return {"ok": True, "code": code, "status": status}, 200
    return redirect(url_for("checklist") + f"#sup-{code}")


# ---------------------------------------------------------------------------
# Vendors
# ---------------------------------------------------------------------------

@app.route("/vendors")
@login_required
def vendors():
    cat_id   = request.args.get("category_id", type=int)
    city     = request.args.get("city", "").strip()
    min_rate = request.args.get("min_rating", type=float)
    max_price= request.args.get("max_price", type=float)
    search   = request.args.get("q", "").strip()

    sql = """SELECT v.*, vc.category_name FROM vendors v
             JOIN vendor_categories vc ON vc.category_id = v.category_id
             WHERE v.is_active = 1"""
    params = []
    if cat_id:    sql += " AND v.category_id = ?";       params.append(cat_id)
    if city:      sql += " AND v.city LIKE ?";           params.append(f"%{city}%")
    if min_rate is not None: sql += " AND v.rating_average >= ?"; params.append(min_rate)
    if max_price is not None: sql += " AND v.price_min <= ?";     params.append(max_price)
    if search:
        sql += " AND (v.business_name LIKE ? OR v.description LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    sql += " ORDER BY v.rating_average DESC, v.business_name"

    vendor_rows = query(sql, tuple(params))
    categories  = query("SELECT * FROM vendor_categories ORDER BY category_name")
    cities      = query("SELECT DISTINCT city FROM vendors WHERE city IS NOT NULL ORDER BY city")
    return render_template("vendors.html",
                           vendors=vendor_rows, categories=categories, cities=cities,
                           filters={"category_id": cat_id, "city": city,
                                    "min_rating": min_rate, "max_price": max_price, "q": search})


@app.route("/vendor/<int:vendor_id>")
@login_required
def vendor_detail(vendor_id):
    v = query(
        """SELECT v.*, vc.category_name FROM vendors v
           JOIN vendor_categories vc ON vc.category_id = v.category_id
           WHERE v.vendor_id = ?""",
        (vendor_id,), one=True,
    )
    if not v: abort(404)
    photos = query("SELECT * FROM vendor_photos WHERE vendor_id=? ORDER BY uploaded_at", (vendor_id,))
    reviews = query(
        """SELECT vr.*, u.full_name FROM vendor_reviews vr
           JOIN users u ON u.user_id = vr.user_id
           WHERE vr.vendor_id = ? ORDER BY vr.created_at DESC""",
        (vendor_id,),
    )
    w = current_wedding()
    is_fav = False
    if w:
        is_fav = bool(query(
            "SELECT 1 FROM favorite_vendors WHERE wedding_id=? AND vendor_id=?",
            (w["wedding_id"], vendor_id), one=True,
        ))
    return render_template("vendor_detail.html",
                           v=v, photos=photos, reviews=reviews, is_fav=is_fav)


# ---------------------------------------------------------------------------
# Swipe
# ---------------------------------------------------------------------------

@app.route("/swipe")
@login_required
def swipe_pick_category():
    # Legacy entry point: send users to the checklist where each supplier card
    # opens its own swipe queue.
    return redirect(url_for("checklist"))


@app.route("/swipe/<int:category_id>")
@login_required
def swipe(category_id):
    w = _ensure_wedding()
    category = query("SELECT * FROM vendor_categories WHERE category_id=?", (category_id,), one=True)
    if not category: abort(404)

    sort = request.args.get("sort", "recommended")
    if sort not in ("recommended", "near"):
        sort = "recommended"

    # Optional ?supplier=<code> ties the swipe queue back to a specific
    # checklist supplier so we can show its notes/budget side-by-side.
    supplier_code = (request.args.get("supplier") or "").strip()
    supplier = SUPPLIERS_BY_CODE.get(supplier_code) if supplier_code else None
    supplier_state = None
    if supplier:
        supplier_state = query(
            "SELECT notes, budget FROM wedding_supplier_status "
            "WHERE wedding_id = ? AND supplier_code = ?",
            (w["wedding_id"], supplier["code"]),
            one=True,
        )

    user = current_user()
    user_city = ((user["city"] if user else "") or "").strip()

    if sort == "near" and user_city:
        sql = """SELECT v.*,
                        CASE WHEN LOWER(v.city) = LOWER(?) THEN 0 ELSE 1 END AS distance_rank
                 FROM vendors v
                 WHERE v.category_id = ? AND v.is_active = 1
                   AND v.vendor_id NOT IN (SELECT vendor_id FROM vendor_swipes WHERE wedding_id = ?)
                 ORDER BY distance_rank ASC, v.rating_average DESC
                 LIMIT 8"""
        params = (user_city, category_id, w["wedding_id"])
    else:
        sql = """SELECT v.* FROM vendors v
                 WHERE v.category_id = ? AND v.is_active = 1
                   AND v.vendor_id NOT IN (SELECT vendor_id FROM vendor_swipes WHERE wedding_id = ?)
                 ORDER BY v.rating_average DESC
                 LIMIT 8"""
        params = (category_id, w["wedding_id"])

    vendors = query(sql, params)

    # Lookup one photo per vendor in a single query.
    photo_map = {}
    if vendors:
        ids = [v["vendor_id"] for v in vendors]
        placeholders = ",".join(["?"] * len(ids))
        photos = query(
            f"SELECT vendor_id, photo_url FROM vendor_photos WHERE vendor_id IN ({placeholders})",
            tuple(ids),
        )
        for p in photos:
            photo_map.setdefault(p["vendor_id"], p["photo_url"])

    # Vendors already liked in this category (shown at bottom)
    liked_in_category = query(
        """SELECT v.vendor_id, v.business_name, v.city, v.rating_average,
                  (SELECT photo_url FROM vendor_photos
                   WHERE vendor_id = v.vendor_id LIMIT 1) AS photo_url
             FROM favorite_vendors fv
             JOIN vendors v ON v.vendor_id = fv.vendor_id
            WHERE fv.wedding_id = ? AND v.category_id = ?
            ORDER BY fv.added_at DESC""",
        (w["wedding_id"], category_id),
    )

    return render_template("swipe.html",
                           category=category, vendors=vendors,
                           photo_map=photo_map, sort=sort,
                           user_city=user_city,
                           supplier=supplier, supplier_state=supplier_state,
                           liked_in_category=liked_in_category)


@app.route("/swipe/<int:category_id>/<int:vendor_id>/<action>", methods=["POST"])
@login_required
def swipe_action(category_id, vendor_id, action):
    if action not in ("Like", "Skip"): abort(400)
    w = _ensure_wedding()
    db = get_db()
    db.execute(
        "INSERT OR IGNORE INTO vendor_swipes (user_id, wedding_id, vendor_id, action) "
        "VALUES (?,?,?,?)",
        (session["user_id"], w["wedding_id"], vendor_id, action),
    )
    if action == "Like":
        db.execute(
            "INSERT OR IGNORE INTO favorite_vendors (wedding_id, vendor_id) VALUES (?,?)",
            (w["wedding_id"], vendor_id),
        )
    db.commit()
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return {"ok": True, "action": action, "vendor_id": vendor_id}, 200
    sort = request.args.get("sort", "recommended")
    return redirect(url_for("swipe", category_id=category_id, sort=sort))


# ---------------------------------------------------------------------------
# Favorites
# ---------------------------------------------------------------------------

@app.route("/liked")
def liked_redirect():
    return redirect(url_for("favorites"))


@app.route("/favorites")
@login_required
def favorites():
    w = current_wedding()
    if not w: return redirect(url_for("wedding_profile"))
    rows = query(
        """SELECT v.*, vc.category_name, fv.added_at,
                  (SELECT photo_url FROM vendor_photos
                   WHERE vendor_id = v.vendor_id LIMIT 1) AS photo_url
             FROM favorite_vendors fv
             JOIN vendors v            ON v.vendor_id   = fv.vendor_id
             JOIN vendor_categories vc ON vc.category_id = v.category_id
            WHERE fv.wedding_id = ? ORDER BY vc.category_name, fv.added_at DESC""",
        (w["wedding_id"],),
    )
    grouped = {}
    for r in rows:
        grouped.setdefault(r["category_name"], []).append(r)
    return render_template("favorites.html", grouped=grouped)


@app.route("/favorites/add/<int:vendor_id>", methods=["POST"])
@login_required
def favorites_add(vendor_id):
    w = current_wedding()
    if not w: return redirect(url_for("wedding_profile"))
    db = get_db()
    db.execute(
        "INSERT OR IGNORE INTO favorite_vendors (wedding_id, vendor_id) VALUES (?,?)",
        (w["wedding_id"], vendor_id),
    )
    db.commit()
    flash("Added to favorites.", "success")
    return redirect(request.referrer or url_for("vendor_detail", vendor_id=vendor_id))


@app.route("/favorites/remove/<int:vendor_id>", methods=["POST"])
@login_required
def favorites_remove(vendor_id):
    w = current_wedding()
    if not w: return redirect(url_for("wedding_profile"))
    execute(
        "DELETE FROM favorite_vendors WHERE wedding_id=? AND vendor_id=?",
        (w["wedding_id"], vendor_id),
    )
    flash("Removed from favorites.", "success")
    return redirect(request.referrer or url_for("favorites"))


# ---------------------------------------------------------------------------
# Selected vendors
# ---------------------------------------------------------------------------

@app.route("/selected-vendors")
@login_required
def selected_vendors():
    w = current_wedding()
    if not w: return redirect(url_for("wedding_profile"))
    rows = query(
        """SELECT sv.*, v.business_name, vc.category_name FROM selected_vendors sv
           JOIN vendors v            ON v.vendor_id   = sv.vendor_id
           JOIN vendor_categories vc ON vc.category_id = sv.category_id
           WHERE sv.wedding_id = ? ORDER BY sv.created_at DESC""",
        (w["wedding_id"],),
    )
    return render_template("selected_vendors.html", rows=rows)


@app.route("/selected-vendors/add/<int:vendor_id>", methods=["POST"])
@login_required
def selected_vendors_add(vendor_id):
    w = current_wedding()
    if not w: return redirect(url_for("wedding_profile"))
    v = query("SELECT category_id FROM vendors WHERE vendor_id=?", (vendor_id,), one=True)
    if not v: abort(404)
    execute(
        """INSERT INTO selected_vendors (wedding_id, vendor_id, category_id, status)
           VALUES (?,?,?, 'Considering')""",
        (w["wedding_id"], vendor_id, v["category_id"]),
    )
    flash("Vendor added to your shortlist.", "success")
    return redirect(url_for("selected_vendors"))


@app.route("/selected-vendors/<int:sid>/update", methods=["POST"])
@login_required
def selected_vendors_update(sid):
    status = request.form.get("status", "Considering")
    price  = request.form.get("agreed_price") or None
    notes  = request.form.get("notes", "")
    if status not in ("Considering","Contacted","Meeting Scheduled","Booked","Rejected"):
        abort(400)
    execute(
        "UPDATE selected_vendors SET status=?, agreed_price=?, notes=? WHERE selected_vendor_id=?",
        (status, price, notes, sid),
    )
    flash("Selection updated.", "success")
    return redirect(url_for("selected_vendors"))


@app.route("/selected-vendors/<int:sid>/delete", methods=["POST"])
@login_required
def selected_vendors_delete(sid):
    execute("DELETE FROM selected_vendors WHERE selected_vendor_id=?", (sid,))
    return redirect(url_for("selected_vendors"))


# ---------------------------------------------------------------------------
# Appointments
# ---------------------------------------------------------------------------

@app.route("/appointments", methods=["GET", "POST"])
@login_required
def appointments():
    w = current_wedding()
    if not w: return redirect(url_for("wedding_profile"))
    if request.method == "POST":
        vendor_id = request.form.get("vendor_id", type=int)
        adate     = request.form.get("appointment_date")
        location  = request.form.get("location", "")
        notes     = request.form.get("notes", "")
        if not (vendor_id and adate):
            flash("Vendor and date are required.", "error")
        else:
            execute(
                """INSERT INTO appointments (wedding_id, vendor_id, appointment_date, location, notes)
                   VALUES (?,?,?,?,?)""",
                (w["wedding_id"], vendor_id, adate, location, notes),
            )
            flash("Appointment scheduled.", "success")
        return redirect(url_for("appointments"))
    rows = query(
        """SELECT a.*, v.business_name, vc.category_name FROM appointments a
           JOIN vendors v            ON v.vendor_id  = a.vendor_id
           JOIN vendor_categories vc ON vc.category_id = v.category_id
           WHERE a.wedding_id = ? ORDER BY a.appointment_date""",
        (w["wedding_id"],),
    )
    vendors_list = query(
        """SELECT v.vendor_id, v.business_name, vc.category_name FROM vendors v
           JOIN vendor_categories vc ON vc.category_id = v.category_id
           ORDER BY vc.category_name, v.business_name""",
    )
    return render_template("appointments.html", rows=rows, vendors=vendors_list)


@app.route("/appointments/<int:aid>/status", methods=["POST"])
@login_required
def appointments_status(aid):
    status = request.form.get("status", "Scheduled")
    if status not in ("Scheduled","Completed","Cancelled"): abort(400)
    execute("UPDATE appointments SET status=? WHERE appointment_id=?", (status, aid))
    return redirect(url_for("appointments"))


# ---------------------------------------------------------------------------
# Reviews
# ---------------------------------------------------------------------------

@app.route("/reviews", methods=["GET", "POST"])
@login_required
def reviews():
    w = current_wedding()
    if request.method == "POST":
        vendor_id = request.form.get("vendor_id", type=int)
        rating    = request.form.get("rating", type=int)
        text      = request.form.get("review_text", "").strip()
        if not (vendor_id and rating and 1 <= rating <= 5):
            flash("Vendor and a 1-5 rating are required.", "error")
        else:
            execute(
                """INSERT INTO vendor_reviews (vendor_id, user_id, wedding_id, rating, review_text)
                   VALUES (?,?,?,?,?)""",
                (vendor_id, session["user_id"], w["wedding_id"] if w else None, rating, text),
            )
            avg = query(
                "SELECT AVG(rating) AS a FROM vendor_reviews WHERE vendor_id=?",
                (vendor_id,), one=True,
            )["a"] or 0
            execute("UPDATE vendors SET rating_average=? WHERE vendor_id=?",
                    (round(avg, 2), vendor_id))
            flash("Review posted.", "success")
        return redirect(url_for("reviews"))
    rows = query(
        """SELECT vr.*, v.business_name, u.full_name FROM vendor_reviews vr
           JOIN vendors v ON v.vendor_id = vr.vendor_id
           JOIN users   u ON u.user_id   = vr.user_id
           ORDER BY vr.created_at DESC LIMIT 50""",
    )
    vendors_list = query("SELECT vendor_id, business_name FROM vendors ORDER BY business_name")
    return render_template("reviews.html", rows=rows, vendors=vendors_list)


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

@app.route("/analytics")
@login_required
def analytics():
    totals = {
        "users":    query("SELECT COUNT(*) AS c FROM users",            one=True)["c"],
        "weddings": query("SELECT COUNT(*) AS c FROM wedding_profiles", one=True)["c"],
        "vendors":  query("SELECT COUNT(*) AS c FROM vendors",          one=True)["c"],
        "reviews":  query("SELECT COUNT(*) AS c FROM vendor_reviews",   one=True)["c"],
    }
    vendors_by_cat = query("""
        SELECT vc.category_name, COUNT(v.vendor_id) AS total_vendors
        FROM vendor_categories vc
        LEFT JOIN vendors v ON v.category_id = vc.category_id
        GROUP BY vc.category_name ORDER BY total_vendors DESC
    """)
    avg_rating_by_cat = query("""
        SELECT vc.category_name, ROUND(AVG(vr.rating),2) AS average_rating, COUNT(vr.review_id) AS reviews
        FROM vendor_reviews vr
        JOIN vendors v            ON vr.vendor_id  = v.vendor_id
        JOIN vendor_categories vc ON v.category_id = vc.category_id
        GROUP BY vc.category_name ORDER BY average_rating DESC
    """)
    most_liked = query("""
        SELECT v.business_name, COUNT(vs.swipe_id) AS total_likes
        FROM vendor_swipes vs JOIN vendors v ON vs.vendor_id = v.vendor_id
        WHERE vs.action = 'Like' GROUP BY v.business_name
        ORDER BY total_likes DESC LIMIT 10
    """)
    most_skipped = query("""
        SELECT v.business_name, COUNT(vs.swipe_id) AS total_skips
        FROM vendor_swipes vs JOIN vendors v ON vs.vendor_id = v.vendor_id
        WHERE vs.action = 'Skip' GROUP BY v.business_name
        ORDER BY total_skips DESC LIMIT 10
    """)
    popular_categories = query("""
        SELECT vc.category_name, COUNT(vs.swipe_id) AS interactions
        FROM vendor_swipes vs
        JOIN vendors v            ON v.vendor_id   = vs.vendor_id
        JOIN vendor_categories vc ON vc.category_id = v.category_id
        GROUP BY vc.category_name ORDER BY interactions DESC
    """)
    checklist_progress = query("""
        SELECT wp.wedding_id, u.full_name,
               COUNT(ci.checklist_item_id) AS total_items,
               SUM(CASE WHEN ci.status='Completed' THEN 1 ELSE 0 END) AS completed_items
        FROM wedding_profiles wp
        JOIN users u ON u.user_id = wp.user_id
        LEFT JOIN checklist_items ci ON wp.wedding_id = ci.wedding_id
        GROUP BY wp.wedding_id, u.full_name ORDER BY completed_items DESC
    """)
    budget_by_cat = query("""
        SELECT vc.category_name,
               SUM(bi.estimated_amount) AS estimated_total,
               SUM(bi.actual_amount)    AS actual_total
        FROM budget_items bi
        JOIN vendor_categories vc ON bi.category_id = vc.category_id
        GROUP BY vc.category_name ORDER BY actual_total DESC
    """)
    top_cities = query("""
        SELECT city, COUNT(vendor_id) AS vendor_count FROM vendors
        WHERE city IS NOT NULL GROUP BY city ORDER BY vendor_count DESC
    """)
    elite_vendors = query("""
        SELECT v.business_name, vc.category_name,
               ROUND(AVG(vr.rating),2) AS avg_rating, COUNT(vr.review_id) AS reviews
        FROM vendors v
        JOIN vendor_categories vc ON vc.category_id = v.category_id
        JOIN vendor_reviews    vr ON vr.vendor_id   = v.vendor_id
        GROUP BY v.vendor_id HAVING AVG(vr.rating) >= 4.5
        ORDER BY avg_rating DESC, reviews DESC
    """)
    return render_template("analytics.html",
        totals=totals, vendors_by_cat=vendors_by_cat,
        avg_rating_by_cat=avg_rating_by_cat, most_liked=most_liked,
        most_skipped=most_skipped, popular_categories=popular_categories,
        checklist_progress=checklist_progress, budget_by_cat=budget_by_cat,
        top_cities=top_cities, elite_vendors=elite_vendors)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def not_found(_e):
    return render_template("error.html", code=404, message="Page not found"), 404

@app.errorhandler(500)
def server_error(_e):
    return render_template("error.html", code=500, message="Something went wrong"), 500


if __name__ == "__main__":
    init_db()
    app.run(debug=os.getenv("FLASK_DEBUG", "0") == "1")
