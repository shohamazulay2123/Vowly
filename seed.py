"""
Seed Vowly with realistic demo data.

If vendors_cache.json exists (produced by fetch_real_vendors.py) the
database is populated with real Israeli businesses from Foursquare.
Otherwise the built-in mock VENDORS dict is used — no API key required.

Run:
    python seed.py
"""

import json
import re
import sqlite3
import random
from pathlib import Path
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

from config import DATABASE_PATH
from database import init_db

CACHE_FILE = Path(__file__).parent / "vendors_cache.json"


CATEGORIES = [
    ("Venue",            "Wedding venues and reception halls",        12),
    ("DJ",               "Music & entertainment for the event",        6),
    ("Photographer",     "Professional wedding photography",           9),
    ("Videographer",     "Cinematic wedding films",                    9),
    ("Catering",         "Food, service and chefs",                    8),
    ("Makeup Artist",    "Bridal makeup specialists",                  4),
    ("Hair Stylist",     "Bridal hair styling",                        4),
    ("Wedding Dress",    "Bridal dress designers and boutiques",       9),
    ("Groom Suit",       "Suits and tuxedos for grooms",               6),
    ("Rings",            "Wedding & engagement rings",                 6),
    ("Flowers",          "Bouquets, centerpieces & floral design",     5),
    ("Invitations",      "Save-the-dates and invitations",             7),
    ("Transportation",   "Luxury cars and shuttle services",           3),
    ("Wedding Planner",  "Full-service wedding planning",              12),
    ("Rabbi/Officiant",  "Wedding ceremony officiants",                8),
    ("Decor",            "Decoration and lighting design",             5),
    ("Cake/Desserts",    "Wedding cakes and dessert tables",           4),
    ("Alcohol Bar",      "Bar service and beverages",                  4),
]

CITIES = [
    "Tel Aviv", "Ramat Gan", "Herzliya", "Holon", "Rishon LeZion",
    "Jerusalem", "Haifa", "Netanya", "Beer Sheva", "Petah Tikva",
    "Bat Yam", "Kfar Saba", "Ra'anana", "Rehovot", "Ashdod",
]

# (business_name, city)  — ~15 realistic Israeli businesses per category
VENDORS = {
    "Venue": [
        ("Ocean View Hall",          "Tel Aviv"),
        ("Garden Palace Events",     "Herzliya"),
        ("Urban Loft Tel Aviv",      "Tel Aviv"),
        ("Laguna Event Center",      "Netanya"),
        ("Villa Carmel",             "Haifa"),
        ("Royal Gardens Hall",       "Ramat Gan"),
        ("The Diamond Hall",         "Petah Tikva"),
        ("Seasons Events",           "Rishon LeZion"),
        ("Palmach House",            "Jerusalem"),
        ("Azure Hall",               "Herzliya"),
        ("The Grove",                "Ra'anana"),
        ("Hayarkon Events",          "Tel Aviv"),
        ("Panorama Hall",            "Beer Sheva"),
        ("Ganim Wedding Gardens",    "Kfar Saba"),
        ("Neve Sha'anan Hall",       "Haifa"),
        ("Giva'on Wedding Club",     "Jerusalem"),
        ("Port Events",              "Ashdod"),
        ("Harei Yehuda Estate",      "Beit Shemesh"),
    ],
    "DJ": [
        ("DJ Nova",                  "Tel Aviv"),
        ("BeatHouse Weddings",       "Ramat Gan"),
        ("SoundWave Events",         "Holon"),
        ("DJ Eyal Tenenbaum",        "Tel Aviv"),
        ("Rhythm Nation",            "Herzliya"),
        ("DJ Avi Mizrahi",           "Jerusalem"),
        ("Club Sound IL",            "Rishon LeZion"),
        ("Music Factory Weddings",   "Haifa"),
        ("DJ Ori Shalev",            "Netanya"),
        ("Bass & Vows",              "Tel Aviv"),
        ("DJ Ron Cohen",             "Ramat Gan"),
        ("The Mix Studio",           "Petah Tikva"),
        ("DJ Shir Levy",             "Beer Sheva"),
        ("Pulse Events",             "Kfar Saba"),
        ("DJ Daniel Gur",            "Ra'anana"),
    ],
    "Photographer": [
        ("Luma Studio",              "Tel Aviv"),
        ("Golden Frame Photography", "Jerusalem"),
        ("StoryShot Weddings",       "Herzliya"),
        ("Captured Moments",         "Haifa"),
        ("Eliana Photography",       "Tel Aviv"),
        ("Light & Grace Studios",    "Ramat Gan"),
        ("Shira Ben David Photography", "Netanya"),
        ("The Still Frame",          "Rishon LeZion"),
        ("Moshe Katz Weddings",      "Jerusalem"),
        ("Pixel & Petal",            "Tel Aviv"),
        ("Reut Shachar Studio",      "Ra'anana"),
        ("Natural Light Photography","Herzliya"),
        ("Nir Shlomo Images",        "Petah Tikva"),
        ("Tali Cohen Weddings",      "Ramat Gan"),
        ("Iris Studio",              "Haifa"),
        ("Aviv Wedding Photography", "Beer Sheva"),
    ],
    "Videographer": [
        ("Cinema Vows",              "Tel Aviv"),
        ("Frame & Light",            "Ramat Gan"),
        ("Epic Wedding Films",       "Herzliya"),
        ("Still Life Cinema",        "Jerusalem"),
        ("Reel Weddings",            "Tel Aviv"),
        ("Yaron Films",              "Haifa"),
        ("Motion Picture Weddings",  "Netanya"),
        ("Gold Reel Productions",    "Rishon LeZion"),
        ("Ohad Sagi Films",          "Tel Aviv"),
        ("Chuppah Cinema",           "Petah Tikva"),
        ("Ora Creative Films",       "Ra'anana"),
        ("Dan Peres Videography",    "Kfar Saba"),
        ("Eternal Frame Studio",     "Rehovot"),
        ("Tal Nimrod Video",         "Beer Sheva"),
        ("Cinematic Moments IL",     "Bat Yam"),
    ],
    "Catering": [
        ("Taste & Toast",            "Tel Aviv"),
        ("Elegant Bites",            "Herzliya"),
        ("Feast Studio",             "Holon"),
        ("Gourmet Wedding Catering", "Ramat Gan"),
        ("Chef David Levy Catering", "Jerusalem"),
        ("Rina's Kitchen",           "Tel Aviv"),
        ("The Catering House",       "Haifa"),
        ("Zafrani Events Kitchen",   "Netanya"),
        ("La Cuisine Weddings",      "Petah Tikva"),
        ("Aromas Catering",          "Rishon LeZion"),
        ("Garden Table Events",      "Ra'anana"),
        ("Niv Catering & Events",    "Kfar Saba"),
        ("Rosh Ha'Kerem Catering",   "Jerusalem"),
        ("Tapuz Weddings",           "Beer Sheva"),
        ("Sea & Feast Tel Aviv",     "Tel Aviv"),
        ("Balabusta Catering",       "Haifa"),
    ],
    "Makeup Artist": [
        ("Glow Bride Studio",        "Tel Aviv"),
        ("Rose Beauty Bar",          "Ramat Gan"),
        ("Mira Katz Makeup",         "Jerusalem"),
        ("Studio Orit",              "Herzliya"),
        ("Maayan Beauty Atelier",    "Tel Aviv"),
        ("Sigal Bridal Makeup",      "Haifa"),
        ("The Bridal Chair",         "Netanya"),
        ("Inbar Cohen Beauty",       "Rishon LeZion"),
        ("Glamour by Yael",          "Ra'anana"),
        ("Eitan Glam Studio",        "Tel Aviv"),
        ("Sheli Makeup Artist",      "Petah Tikva"),
        ("The Bridal Glow",          "Beer Sheva"),
        ("Neta Beauty Salon",        "Kfar Saba"),
        ("Bosem Makeup Studio",      "Rehovot"),
        ("Carmit Bridal Beauty",     "Bat Yam"),
    ],
    "Hair Stylist": [
        ("Velvet Hair Studio",       "Tel Aviv"),
        ("Crown Hairstyle",          "Herzliya"),
        ("Hair by Osnat",            "Ramat Gan"),
        ("The Bridal Bun",           "Jerusalem"),
        ("Studio Gal Hair",          "Tel Aviv"),
        ("Limor Hair & Beauty",      "Haifa"),
        ("Ronit Tresses",            "Netanya"),
        ("Lior Bridal Hair",         "Rishon LeZion"),
        ("Bridal Bloom Hair",        "Ra'anana"),
        ("Iris Hairstyle Studio",    "Tel Aviv"),
        ("Dar Shalon Hair",          "Petah Tikva"),
        ("Anat Wedding Hair",        "Beer Sheva"),
        ("Shiran Bridal Studio",     "Kfar Saba"),
        ("Noam Hairstylist",         "Rehovot"),
        ("Tali Hair Artistry",       "Bat Yam"),
    ],
    "Wedding Dress": [
        ("Bianca Bridal",            "Tel Aviv"),
        ("Aurelia Couture",          "Ramat Gan"),
        ("La Mariée",                "Tel Aviv"),
        ("White Lily Bridal",        "Herzliya"),
        ("Studio Eden Bridal",       "Jerusalem"),
        ("Alona Wedding Boutique",   "Haifa"),
        ("Diamond Veil",             "Netanya"),
        ("Hadas Bridal Fashion",     "Petah Tikva"),
        ("Reverie Bridal",           "Rishon LeZion"),
        ("Shoshana Couture",         "Tel Aviv"),
        ("The White Loft Bridal",    "Ra'anana"),
        ("Nuptia",                   "Kfar Saba"),
        ("Tamar Bridal Studio",      "Beer Sheva"),
        ("Rina Wedding Fashion",     "Rehovot"),
        ("Olivia Bridal IL",         "Bat Yam"),
    ],
    "Groom Suit": [
        ("Sartoria Milano IL",       "Tel Aviv"),
        ("The Groom Room",           "Jerusalem"),
        ("Ben Elegance",             "Ramat Gan"),
        ("Suit Club Tel Aviv",       "Tel Aviv"),
        ("Tailor & Co.",             "Herzliya"),
        ("Menswear by Shai",         "Haifa"),
        ("Groom's Atelier",          "Netanya"),
        ("Dress Sharp",              "Rishon LeZion"),
        ("Formal & Fine",            "Ra'anana"),
        ("Midor Suit House",         "Petah Tikva"),
        ("Classic Groom Studio",     "Beer Sheva"),
        ("YB Menswear",              "Kfar Saba"),
        ("The Tie Bar IL",           "Rehovot"),
        ("Erez & Sons Tailors",      "Holon"),
        ("Platinum Suits",           "Bat Yam"),
    ],
    "Rings": [
        ("Goldline Jewelers",        "Tel Aviv"),
        ("Diamond Vow",              "Ramat Gan"),
        ("Eternity Rings",           "Herzliya"),
        ("Ilan Gold Jewels",         "Jerusalem"),
        ("Tiffany's IL",             "Tel Aviv"),
        ("Shlomit Jewelry",          "Haifa"),
        ("Forever Diamonds",         "Netanya"),
        ("Orli Rings Studio",        "Petah Tikva"),
        ("Adena Jewels",             "Rishon LeZion"),
        ("Mazal Diamonds",           "Ra'anana"),
        ("The Ring Atelier",         "Tel Aviv"),
        ("Gold & Stone",             "Beer Sheva"),
        ("Engagement Ring IL",       "Kfar Saba"),
        ("Noy Jewelry",              "Rehovot"),
        ("Pnina Fine Jewelry",       "Bat Yam"),
    ],
    "Flowers": [
        ("Bloom & Vows",             "Tel Aviv"),
        ("Petal Studio",             "Herzliya"),
        ("White Rose Design",        "Holon"),
        ("Ganim Flowers",            "Jerusalem"),
        ("Varda Floral Design",      "Ramat Gan"),
        ("Floria Events",            "Haifa"),
        ("Ora Flower Studio",        "Netanya"),
        ("Naomi Botanica",           "Rishon LeZion"),
        ("Wild Bloom IL",            "Tel Aviv"),
        ("Eden Floral",              "Ra'anana"),
        ("Efrat Flowers & Design",   "Petah Tikva"),
        ("Tamara Bouquets",          "Beer Sheva"),
        ("Lilac Floral Studio",      "Kfar Saba"),
        ("Blossom Art",              "Rehovot"),
        ("Hana Hana Flowers",        "Bat Yam"),
    ],
    "Invitations": [
        ("Paper Love",               "Tel Aviv"),
        ("Ink & Vows",               "Jerusalem"),
        ("Carta Bridal Studio",      "Ramat Gan"),
        ("Simply Invites",           "Herzliya"),
        ("The Paper Garden",         "Haifa"),
        ("Ahuva Stationery",         "Netanya"),
        ("Calligraphy by Noga",      "Tel Aviv"),
        ("Oren Print Studio",        "Petah Tikva"),
        ("Pressed Petal Prints",     "Rishon LeZion"),
        ("Lev Stationery",           "Ra'anana"),
        ("Gold Leaf Invites",        "Beer Sheva"),
        ("Studio Aleph",             "Kfar Saba"),
        ("Rimon Press",              "Rehovot"),
        ("White Letter Co.",         "Tel Aviv"),
        ("Kesem Invitations",        "Bat Yam"),
    ],
    "Transportation": [
        ("Royal Rides",              "Tel Aviv"),
        ("Classic Cars Co.",         "Herzliya"),
        ("Luxury Drive IL",          "Ramat Gan"),
        ("White Limo Service",       "Tel Aviv"),
        ("Gilat Chauffeur",          "Jerusalem"),
        ("Pearl Limousines",         "Haifa"),
        ("VIP Shuttle Weddings",     "Netanya"),
        ("Elegant Wheels",           "Petah Tikva"),
        ("Cavalier Cars",            "Rishon LeZion"),
        ("Diamond Drive",            "Ra'anana"),
        ("Premier Bridal Cars",      "Beer Sheva"),
        ("Golden Coach IL",          "Kfar Saba"),
        ("Ronen's VIP Cars",         "Rehovot"),
        ("Prestige Limos",           "Bat Yam"),
        ("Ashdod Luxury Rides",      "Ashdod"),
    ],
    "Wedding Planner": [
        ("Forever Yours Planning",   "Tel Aviv"),
        ("The Knot Studio",          "Ramat Gan"),
        ("Liron Events",             "Herzliya"),
        ("Dream Day Planning",       "Jerusalem"),
        ("Romi Event Design",        "Tel Aviv"),
        ("Yael's Perfect Day",       "Haifa"),
        ("I Do Events IL",           "Netanya"),
        ("Simcha Planning Co.",      "Petah Tikva"),
        ("Nuptial By Noga",          "Rishon LeZion"),
        ("Adi & Tal Events",         "Ra'anana"),
        ("Chic Events Tel Aviv",     "Tel Aviv"),
        ("Mazel Planner",            "Beer Sheva"),
        ("Shira Galit Events",       "Kfar Saba"),
        ("Plan My Day IL",           "Rehovot"),
        ("Tova Wedding Design",      "Bat Yam"),
    ],
    "Rabbi/Officiant": [
        ("Rabbi Eitan Levi",         "Jerusalem"),
        ("Officiant Maya Ben-David", "Tel Aviv"),
        ("Rabbi Shlomo Katz",        "Ramat Gan"),
        ("Rabbi Dov Friedman",       "Jerusalem"),
        ("Cantor Moshe Peretz",      "Haifa"),
        ("Rabbi Yehuda Goldberg",    "Netanya"),
        ("Rav Yosef Shabtai",        "Beer Sheva"),
        ("Rabbi Amos Regev",         "Petah Tikva"),
        ("Spiritual Ceremonies IL",  "Tel Aviv"),
        ("Rabbi Nachman Haran",      "Rishon LeZion"),
        ("Rav Binyamin Stern",       "Kfar Saba"),
        ("Rabbi Ilan Amitai",        "Ra'anana"),
        ("Cantor Avner Yosef",       "Rehovot"),
        ("Rabbi Tzvi Blum",          "Bat Yam"),
        ("Jewish Ceremonies IL",     "Tel Aviv"),
    ],
    "Decor": [
        ("Lumiere Decor",            "Tel Aviv"),
        ("Grace Design",             "Holon"),
        ("Golden Arch Events",       "Ramat Gan"),
        ("Studio Nir Decor",         "Herzliya"),
        ("Enchanted Events IL",      "Jerusalem"),
        ("Light & Lace Decor",       "Haifa"),
        ("Dafna Event Design",       "Netanya"),
        ("Magic Touch Decor",        "Petah Tikva"),
        ("Ariel Events Lighting",    "Rishon LeZion"),
        ("Prestige Decor IL",        "Ra'anana"),
        ("Yael Tal Event Design",    "Tel Aviv"),
        ("Shimmer Events",           "Beer Sheva"),
        ("Eden Decor Studio",        "Kfar Saba"),
        ("The Decor Lab",            "Rehovot"),
        ("Serenity Events",          "Bat Yam"),
    ],
    "Cake/Desserts": [
        ("Sweet Vows Bakery",        "Tel Aviv"),
        ("Sugar Lane",               "Ramat Gan"),
        ("Cake by Limor",            "Herzliya"),
        ("The Bridal Patisserie",    "Jerusalem"),
        ("Nomi's Cakes",             "Haifa"),
        ("Fiorino Bakery",           "Tel Aviv"),
        ("Ganache Wedding Cakes",    "Netanya"),
        ("Yael's Sweet Studio",      "Petah Tikva"),
        ("Confetti Cakes IL",        "Rishon LeZion"),
        ("White Sponge Bakery",      "Ra'anana"),
        ("Tal Katz Patisserie",      "Beer Sheva"),
        ("Royal Icing Studio",       "Kfar Saba"),
        ("Bridal Sweets",            "Rehovot"),
        ("Bake my Day",              "Bat Yam"),
        ("Esther's Bakery",          "Ashdod"),
    ],
    "Alcohol Bar": [
        ("PourHouse Bar",            "Tel Aviv"),
        ("Crystal Bar Co.",          "Herzliya"),
        ("Cheers Cocktail Bar",      "Ramat Gan"),
        ("The Wedding Bar",          "Tel Aviv"),
        ("Shaker Studio IL",         "Jerusalem"),
        ("Bar HaNamal",              "Haifa"),
        ("Craft Bar Events",         "Netanya"),
        ("Mixology by Guy",          "Petah Tikva"),
        ("Whiskey & Roses",          "Rishon LeZion"),
        ("Open Bar IL",              "Ra'anana"),
        ("Sipster Weddings",         "Tel Aviv"),
        ("The Dry Bar",              "Beer Sheva"),
        ("Oren Cocktails",           "Kfar Saba"),
        ("Bar on Wheels",            "Rehovot"),
        ("Raise a Glass Events",     "Bat Yam"),
    ],
}

DEMO_USERS = [
    ("Noa Levi",      "noa@vowly.dev",     "password123", "Tel Aviv",      "050-1110001"),
    ("Daniel Cohen",  "daniel@vowly.dev",  "password123", "Ramat Gan",     "050-1110002"),
    ("Maya Azulay",   "maya@vowly.dev",    "password123", "Herzliya",      "050-1110003"),
    ("Shira Peretz",  "shira@vowly.dev",   "password123", "Jerusalem",     "050-1110004"),
]

REVIEW_TEXTS = [
    "Absolutely amazing experience, made our day perfect!",
    "Professional and warm, highly recommended.",
    "Beautiful work, lovely people.",
    "Very responsive and creative team.",
    "Loved every moment working with them.",
    "Exceeded our expectations.",
    "Quality was great, communication could be faster.",
    "Stunning results, would book again in a heartbeat.",
]

CHECKLIST_TEMPLATE = [
    ("Venue",          "Book reception venue",        12),
    ("Venue",          "Confirm guest count with venue", 2),
    ("DJ",             "Hire DJ",                     6),
    ("Photographer",   "Book photographer",           9),
    ("Videographer",   "Book videographer",           9),
    ("Catering",       "Finalize catering menu",      4),
    ("Makeup Artist",  "Trial makeup session",        2),
    ("Hair Stylist",   "Trial hair styling",          2),
    ("Wedding Dress",  "Choose wedding dress",        9),
    ("Groom Suit",     "Order groom suit",            6),
    ("Rings",          "Buy wedding rings",           4),
    ("Flowers",        "Order bouquets and centerpieces", 5),
    ("Invitations",    "Send invitations",            7),
    ("Transportation", "Arrange transportation",      3),
    ("Cake/Desserts",  "Order wedding cake",          4),
]


def main():
    init_db()
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    cur = conn.cursor()

    # Wipe existing data (preserve schema)
    for t in ["vendor_swipes","favorite_vendors","selected_vendors","vendor_reviews",
              "appointments","budget_items","checklist_items","vendor_photos",
              "vendors","wedding_profiles","users","vendor_categories"]:
        cur.execute(f"DELETE FROM {t}")
    conn.commit()

    # Categories
    cat_ids = {}
    for name, desc, months in CATEGORIES:
        cur.execute(
            "INSERT INTO vendor_categories (category_name, description, default_due_months_before_wedding) "
            "VALUES (?,?,?)", (name, desc, months),
        )
        cat_ids[name] = cur.lastrowid

    # Users
    user_ids = []
    for name, email, pw, city, phone in DEMO_USERS:
        cur.execute(
            "INSERT INTO users (full_name, email, password_hash, city, phone) "
            "VALUES (?,?,?,?,?)",
            (name, email, generate_password_hash(pw), city, phone),
        )
        user_ids.append(cur.lastrowid)

    # Wedding profiles (one per user)
    wedding_ids = []
    base_date = datetime(2026, 9, 15)
    partners = ["Yossi", "Tamar", "Ron", "Eden"]
    venue_prefs = ["Garden", "Hall", "Beach", "Loft"]
    for i, uid in enumerate(user_ids):
        wd = (base_date + timedelta(days=30 * i)).date().isoformat()
        cur.execute(
            """INSERT INTO wedding_profiles
               (user_id, partner_name, wedding_date, estimated_guests, budget, city, venue_type_preference)
               VALUES (?,?,?,?,?,?,?)""",
            (uid, partners[i], wd, 150 + i * 25, 120000 + i * 30000,
             DEMO_USERS[i][3], venue_prefs[i]),
        )
        wedding_ids.append(cur.lastrowid)

    # ------------------------------------------------------------------
    # Vendors + photos
    # Use real Foursquare data if cache exists, else mock data.
    # ------------------------------------------------------------------
    def _slug(name: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", name.lower().replace("&", "and"))

    vendor_ids: list[tuple] = []

    if CACHE_FILE.exists():
        print(f"Loading real vendor data from {CACHE_FILE.name} …")
        cache: dict = json.loads(CACHE_FILE.read_text(encoding="utf-8"))

        for cat_name, vendors in cache.items():
            cid = cat_ids.get(cat_name)
            if cid is None:
                continue
            for v in vendors:
                biz = (v.get("business_name") or "").strip()
                if not biz:
                    continue
                city      = v.get("city")        or "Israel"
                address   = v.get("address")     or city
                phone     = v.get("phone")       or ""
                email     = v.get("email")       or f"hello@{_slug(biz)}.co.il"
                website   = v.get("website")     or f"https://{_slug(biz)}.co.il"
                instagram = v.get("instagram_url") or f"https://instagram.com/{_slug(biz)}"
                desc      = v.get("description") or (
                    f"{biz} is a top-rated {cat_name.lower()} in {city}, "
                    "loved by couples across Israel."
                )
                price_min = int(v.get("price_min") or 5_000)
                price_max = int(v.get("price_max") or 15_000)
                rating    = float(v.get("rating_average") or 0.0)

                cur.execute(
                    """INSERT INTO vendors
                       (business_name, category_id, city, address, phone, email, website,
                        instagram_url, description, price_min, price_max, rating_average, is_active)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,1)""",
                    (biz, cid, city, address, phone, email, website,
                     instagram, desc, price_min, price_max, rating),
                )
                vid = cur.lastrowid
                vendor_ids.append((vid, cid, cat_name))

                # Real photo (if fetched) + two picsum supplements for the gallery
                photo_url = v.get("photo_url") or ""
                if photo_url:
                    cur.execute(
                        "INSERT INTO vendor_photos (vendor_id, photo_url, caption) VALUES (?,?,?)",
                        (vid, photo_url, f"{biz} – photo 1"),
                    )
                for j in range(1 if photo_url else 0, 3):
                    cur.execute(
                        "INSERT INTO vendor_photos (vendor_id, photo_url, caption) VALUES (?,?,?)",
                        (vid, f"https://picsum.photos/seed/{vid}-{j}/800/520", f"{biz} – photo {j+1}"),
                    )

        print(f"  {len(vendor_ids)} vendors inserted from cache.")

    else:
        print("vendors_cache.json not found — using built-in mock data.")
        print("Tip: run  python fetch_real_vendors.py  first for real businesses.")

        # Israeli area codes by city
        AREA = {
            "Tel Aviv": "03", "Ramat Gan": "03", "Holon": "03", "Bat Yam": "03",
            "Rishon LeZion": "03", "Herzliya": "09", "Netanya": "09",
            "Ra'anana": "09", "Kfar Saba": "09", "Petah Tikva": "03",
            "Jerusalem": "02", "Beit Shemesh": "02",
            "Haifa": "04", "Rehovot": "08", "Ashdod": "08",
            "Beer Sheva": "08", "Eilat": "08",
        }

        # Realistic street names by city
        STREETS = {
            "Tel Aviv":       ["Dizengoff", "Ben Yehuda", "Allenby", "Rothschild", "Ibn Gvirol", "Yehuda Halevi"],
            "Ramat Gan":      ["Bnei Brak", "Bialik", "Chaim Ozer", "Jabotinsky"],
            "Herzliya":       ["Sokolov", "Ha-Yarkon", "Maskit", "Rabin"],
            "Jerusalem":      ["Jaffa", "King George", "Ben Yehuda", "Herzl", "Yafo"],
            "Haifa":          ["Moriah", "HaNassi", "Ben Gurion", "Jaffa"],
            "Netanya":        ["Herzl", "Ha-Atzmaut", "Shmuel Hanagid"],
            "Petah Tikva":    ["Jabotinsky", "Herzl", "Eliezer Kaplan"],
            "Rishon LeZion":  ["Rothschild", "Herzl", "Ben Zvi"],
            "Ra'anana":       ["Ahuza", "Ha'Hayal", "Weizmann"],
            "Beer Sheva":     ["Rager", "Keren Kayemet", "Ben Gurion"],
            "Rehovot":        ["Weizmann", "Herzl", "Bialik"],
            "Ashdod":         ["Ha-Nesi'im", "Nordau", "Jabotinsky"],
            "Bat Yam":        ["Ben Gurion", "Balfour", "Ha'Azmaut"],
            "Kfar Saba":      ["Weizmann", "Einav", "Nordau"],
            "Holon":          ["Sokolov", "Golda Meir", "Shapira"],
        }

        # Category price ranges (min, max)
        CAT_PRICES = {
            "Venue":          (18000, 80000),
            "DJ":             (3500,  12000),
            "Photographer":   (6000,  22000),
            "Videographer":   (5000,  18000),
            "Catering":       (15000, 60000),
            "Makeup Artist":  (1500,  6000),
            "Hair Stylist":   (1200,  5000),
            "Wedding Dress":  (4000,  25000),
            "Groom Suit":     (2000,  10000),
            "Rings":          (3000,  30000),
            "Flowers":        (2500,  12000),
            "Invitations":    (800,   4000),
            "Transportation": (2000,  8000),
            "Wedding Planner":(5000,  25000),
            "Rabbi/Officiant":(1000,  4500),
            "Decor":          (4000,  20000),
            "Cake/Desserts":  (1500,  7000),
            "Alcohol Bar":    (2500,  12000),
        }

        # Category → loremflickr keywords for relevant swipe photos
        CAT_PHOTOS = {
            "Venue":          "wedding,venue,hall",
            "DJ":             "dj,music,nightclub",
            "Photographer":   "wedding,photography,couple",
            "Videographer":   "camera,film,cinematic",
            "Catering":       "food,catering,dinner",
            "Makeup Artist":  "makeup,beauty,bridal",
            "Hair Stylist":   "hairstyle,bride,hair",
            "Wedding Dress":  "wedding,dress,bridal",
            "Groom Suit":     "suit,groom,tuxedo",
            "Rings":          "wedding,ring,jewelry",
            "Flowers":        "flowers,bouquet,floral",
            "Invitations":    "invitation,stationery,paper",
            "Transportation": "limousine,luxury,car",
            "Wedding Planner":"wedding,planning,event",
            "Rabbi/Officiant":"wedding,ceremony,chuppah",
            "Decor":          "decoration,lights,event",
            "Cake/Desserts":  "wedding,cake,dessert",
            "Alcohol Bar":    "cocktail,bar,drinks",
        }

        # Category description templates
        CAT_DESC = {
            "Venue":          "An elegant event venue in {city} hosting unforgettable weddings for up to 400 guests.",
            "DJ":             "Professional DJ and entertainment services in {city}, blending Israeli and international music.",
            "Photographer":   "Award-winning wedding photographer in {city} capturing every emotional moment in stunning detail.",
            "Videographer":   "Cinematic wedding films crafted in {city} — emotional, artistic and timeless.",
            "Catering":       "Gourmet catering in {city} specialising in Israeli, Mediterranean and fusion wedding menus.",
            "Makeup Artist":  "Bridal makeup artist in {city} renowned for natural, long-lasting, camera-ready looks.",
            "Hair Stylist":   "Creative bridal hair stylist in {city} specialising in updos, braids and modern styles.",
            "Wedding Dress":  "Exclusive bridal boutique in {city} offering designer gowns, alterations and fittings.",
            "Groom Suit":     "Premium menswear and tailoring in {city} for grooms who want to look impeccable.",
            "Rings":          "Fine jewellery and custom wedding rings in {city}, crafted in gold, platinum and diamonds.",
            "Flowers":        "Bespoke floral design studio in {city} creating bouquets, arches and centrepieces.",
            "Invitations":    "Luxury stationery studio in {city} designing hand-lettered invitations and save-the-dates.",
            "Transportation": "Luxury wedding transportation in {city} — limousines, classic cars and bridal shuttles.",
            "Wedding Planner":"Full-service wedding planning studio in {city} handling every detail from venue to dessert.",
            "Rabbi/Officiant":"Experienced wedding officiant in {city} performing heartfelt, personalised Jewish ceremonies.",
            "Decor":          "Creative event décor and lighting design in {city} transforming spaces into magical settings.",
            "Cake/Desserts":  "Artisan wedding cakes and dessert tables in {city}, baked fresh with premium ingredients.",
            "Alcohol Bar":    "Professional bar service in {city} offering cocktails, fine wines and craft spirits.",
        }

        for cat_name, items in VENDORS.items():
            cid = cat_ids[cat_name]
            pmin_base, pmax_base = CAT_PRICES.get(cat_name, (5000, 15000))
            desc_tmpl = CAT_DESC.get(cat_name, "{biz} is a top-rated {cat} provider in {city}.")
            for biz, city in items:
                slug = _slug(biz)
                area = AREA.get(city, "03")
                streets = STREETS.get(city, ["Herzl", "Jabotinsky", "Ben Gurion"])
                street = random.choice(streets)
                number = random.randint(2, 120)
                price_min = pmin_base + random.randint(0, (pmax_base - pmin_base) // 3)
                price_max = price_min + random.randint(
                    (pmax_base - pmin_base) // 3,
                    pmax_base - pmin_base,
                )
                description = desc_tmpl.format(biz=biz, city=city, cat=cat_name.lower())
                cur.execute(
                    """INSERT INTO vendors
                       (business_name, category_id, city, address, phone, email, website,
                        instagram_url, description, price_min, price_max, rating_average, is_active)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,1)""",
                    (biz, cid, city,
                     f"{number} {street} St, {city}",
                     f"{area}-{random.randint(1000000, 9999999)}",
                     f"hello@{slug}.co.il",
                     f"https://www.{slug}.co.il",
                     f"https://instagram.com/{slug}.weddings",
                     description,
                     price_min, price_max, 0),
                )
                vid = cur.lastrowid
                vendor_ids.append((vid, cid, cat_name))
                kw = CAT_PHOTOS.get(cat_name, "wedding")
                for j in range(3):
                    lock = vid * 10 + j          # unique lock → same photo every seed
                    cur.execute(
                        "INSERT INTO vendor_photos (vendor_id, photo_url, caption) VALUES (?,?,?)",
                        (vid, f"https://picsum.photos/seed/{kw}-{lock}/800/520", f"{biz} – photo {j+1}"),
                    )

    # Reviews — only generate fake reviews for vendors that have no real
    # rating yet (rating_average == 0 means mock/unrated data).
    for vid, _cid, _cat in vendor_ids:
        row = cur.execute("SELECT rating_average FROM vendors WHERE vendor_id=?", (vid,)).fetchone()
        if row and float(row[0]) > 0:
            continue  # keep the real Foursquare rating as-is
        n_reviews = random.randint(2, 6)
        for _ in range(n_reviews):
            uid = random.choice(user_ids)
            wid = wedding_ids[user_ids.index(uid)]
            rating = random.choices([3, 4, 5], weights=[1, 3, 6])[0]
            cur.execute(
                """INSERT INTO vendor_reviews (vendor_id, user_id, wedding_id, rating, review_text)
                   VALUES (?,?,?,?,?)""",
                (vid, uid, wid, rating, random.choice(REVIEW_TEXTS)),
            )
    # Recompute rating averages only for vendors that got fake reviews
    cur.execute("""
        UPDATE vendors
        SET rating_average = COALESCE((
            SELECT ROUND(AVG(rating),2) FROM vendor_reviews
            WHERE vendor_reviews.vendor_id = vendors.vendor_id
        ), rating_average)
    """)

    # Per-wedding seed: checklist, swipes, favorites, selections, appointments, budget
    for idx, wid in enumerate(wedding_ids):
        uid = user_ids[idx]
        wedding_date = base_date + timedelta(days=30 * idx)

        # Checklist
        for cat, title, months_before in CHECKLIST_TEMPLATE:
            due = (wedding_date - timedelta(days=months_before * 30)).date().isoformat()
            status = random.choices(
                ["Pending", "In Progress", "Completed", "Skipped"],
                weights=[4, 3, 4, 1],
            )[0]
            completed_at = datetime.utcnow().isoformat(timespec="seconds") if status == "Completed" else None
            cur.execute(
                """INSERT INTO checklist_items
                   (wedding_id, category_id, title, description, due_date, status, completed_at)
                   VALUES (?,?,?,?,?,?,?)""",
                (wid, cat_ids[cat], title, f"{title} for the wedding.",
                 due, status, completed_at),
            )

        # Swipes + favorites + selections
        sample_vendors = random.sample(vendor_ids, k=min(20, len(vendor_ids)))
        for vid, cid, _cat in sample_vendors:
            action = random.choices(["Like", "Skip"], weights=[2, 1])[0]
            cur.execute(
                "INSERT OR IGNORE INTO vendor_swipes (user_id, wedding_id, vendor_id, action) "
                "VALUES (?,?,?,?)",
                (uid, wid, vid, action),
            )
            if action == "Like":
                cur.execute(
                    "INSERT OR IGNORE INTO favorite_vendors (wedding_id, vendor_id) VALUES (?,?)",
                    (wid, vid),
                )

        # Pick 4 selected vendors per wedding
        for vid, cid, _cat in random.sample(sample_vendors, k=min(4, len(sample_vendors))):
            status = random.choice(["Considering","Contacted","Meeting Scheduled","Booked"])
            cur.execute(
                """INSERT INTO selected_vendors (wedding_id, vendor_id, category_id, status, agreed_price, notes)
                   VALUES (?,?,?,?,?,?)""",
                (wid, vid, cid, status,
                 random.choice([None, 6500, 9000, 12000]),
                 "Looks like a great fit."),
            )

        # Appointments
        for vid, _cid, _cat in random.sample(sample_vendors, k=3):
            adate = (datetime.utcnow() + timedelta(days=random.randint(5, 60))).isoformat(timespec="minutes")
            cur.execute(
                """INSERT INTO appointments (wedding_id, vendor_id, appointment_date, location, notes, status)
                   VALUES (?,?,?,?,?,?)""",
                (wid, vid, adate, "Vendor studio", "Initial meeting",
                 random.choice(["Scheduled","Scheduled","Completed"])),
            )

        # Budget items (one per main category)
        for cat in ["Venue","DJ","Photographer","Catering","Flowers","Wedding Dress","Cake/Desserts"]:
            est = random.choice([5000, 8000, 12000, 25000, 40000])
            actual = est + random.randint(-2000, 4000)
            cur.execute(
                """INSERT INTO budget_items (wedding_id, category_id, estimated_amount, actual_amount, notes)
                   VALUES (?,?,?,?,?)""",
                (wid, cat_ids[cat], est, actual, f"{cat} budget"),
            )

    conn.commit()
    conn.close()
    print("Vowly seed complete.")
    print("Demo logins (password = password123):")
    for u in DEMO_USERS:
        print(f"  - {u[1]}")


if __name__ == "__main__":
    main()
