"""
Vowly — real vendor data fetcher (Foursquare Places API v3).

Searches for real Israeli wedding businesses across 8 cities for all 18
vendor categories, deduplicates by Foursquare place ID, and writes the
results to vendors_cache.json.

Usage
-----
1.  Your key is already in .env (FOURSQUARE_KEY).
2.  Install dependencies:
        pip install requests python-dotenv
3.  Run:
        python fetch_real_vendors.py
4.  Then seed the database:
        python seed.py

Re-running is safe — if vendors_cache.json already exists the script
skips all API calls. Delete it to force a refresh.
"""

import json
import os
import re
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

API_KEY    = os.environ.get("FOURSQUARE_KEY", "")
CACHE_FILE = Path(__file__).parent / "vendors_cache.json"

# Foursquare Places Search endpoint (v3)
SEARCH_URL = "https://api.foursquare.com/v3/places/search"
PHOTOS_URL = "https://api.foursquare.com/v3/places/{fsq_id}/photos"

# Israeli cities to sweep — broad geographic coverage
SEARCH_CITIES = [
    "Tel Aviv, Israel",
    "Jerusalem, Israel",
    "Haifa, Israel",
    "Ramat Gan, Israel",
    "Herzliya, Israel",
    "Netanya, Israel",
    "Beer Sheva, Israel",
    "Petah Tikva, Israel",
]

LIMIT_PER_SEARCH    = 10   # results per city per category
MAX_PER_CATEGORY    = 50   # cap after dedup across all cities
REQUEST_DELAY_S     = 0.25 # polite pause between calls

# Fields to request (reduces response size)
FIELDS = "fsq_id,name,location,tel,website,rating,price,photos,description"

# ---------------------------------------------------------------------------
# Category → search query
# Each key must exactly match the category_name in the app DB.
# ---------------------------------------------------------------------------
CATEGORY_QUERIES = {
    "Venue":           "wedding venue event hall",
    "DJ":              "DJ music entertainment",
    "Photographer":    "photographer photography studio",
    "Videographer":    "videographer film production",
    "Catering":        "catering food events",
    "Makeup Artist":   "makeup artist beauty studio",
    "Hair Stylist":    "hair salon hairdresser",
    "Wedding Dress":   "bridal wedding dress boutique",
    "Groom Suit":      "suit tailor men formalwear",
    "Rings":           "jewelry rings diamonds",
    "Flowers":         "florist flowers arrangements",
    "Invitations":     "printing stationery invitations",
    "Transportation":  "limousine car hire luxury",
    "Wedding Planner": "event planner coordinator",
    "Rabbi/Officiant": "rabbi synagogue",
    "Decor":           "event decor rental lighting",
    "Cake/Desserts":   "bakery cake pastry desserts",
    "Alcohol Bar":     "bar cocktail lounge",
}

# ---------------------------------------------------------------------------
# Price level → ₪ range
# Foursquare: 1=cheap, 2=moderate, 3=expensive, 4=very expensive
# ---------------------------------------------------------------------------
PRICE_MAP = {
    1: (3_000,  8_000),
    2: (8_000,  20_000),
    3: (20_000, 50_000),
    4: (50_000, 120_000),
}
DEFAULT_PRICE = (5_000, 15_000)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower().replace("&", "and"))


def _headers() -> dict:
    return {
        "Accept":        "application/json",
        "Authorization": API_KEY,
    }


def _photo_url(place: dict) -> str:
    """Return a usable photo URL from the inline photos array, if present."""
    photos = place.get("photos") or []
    if not photos:
        return ""
    p = photos[0]
    prefix = p.get("prefix", "")
    suffix = p.get("suffix", "")
    if prefix and suffix:
        return f"{prefix}800x600{suffix}"
    return ""


def _fetch_photos(fsq_id: str) -> str:
    """Fetch the first photo for a place via the dedicated photos endpoint."""
    try:
        r = requests.get(
            PHOTOS_URL.format(fsq_id=fsq_id),
            headers=_headers(),
            params={"limit": 1},
            timeout=10,
        )
        if r.status_code == 200:
            data = r.json()
            if data:
                p = data[0]
                prefix = p.get("prefix", "")
                suffix = p.get("suffix", "")
                if prefix and suffix:
                    return f"{prefix}800x600{suffix}"
    except requests.RequestException:
        pass
    return ""


def _price_range(place: dict) -> tuple[int, int]:
    return PRICE_MAP.get(place.get("price"), DEFAULT_PRICE)


def _extract_city(location: dict) -> str:
    """Pull the city name out of a Foursquare location object."""
    for key in ("locality", "admin_region", "region"):
        val = location.get(key, "").strip()
        if val:
            return val
    return "Israel"


def search_category(category: str, query: str) -> list[dict]:
    """
    Search all Israeli cities for one vendor category.
    Returns a deduplicated list of normalized vendor dicts.
    """
    seen_ids: set[str] = set()
    vendors: list[dict] = []

    for city in SEARCH_CITIES:
        if len(vendors) >= MAX_PER_CATEGORY:
            break

        params = {
            "query":  query,
            "near":   city,
            "limit":  LIMIT_PER_SEARCH,
            "fields": FIELDS,
        }

        try:
            r = requests.get(SEARCH_URL, headers=_headers(), params=params, timeout=12)
        except requests.RequestException as exc:
            print(f"      [net error] {city}: {exc}")
            time.sleep(1)
            continue

        if r.status_code == 429:
            print("      [rate limit] sleeping 5 s…")
            time.sleep(5)
            continue

        if r.status_code != 200:
            print(f"      [HTTP {r.status_code}] {city}: {r.text[:120]}")
            time.sleep(REQUEST_DELAY_S)
            continue

        places = r.json().get("results") or []

        for p in places:
            fsq_id = p.get("fsq_id", "")
            if not fsq_id or fsq_id in seen_ids:
                continue
            seen_ids.add(fsq_id)

            name = p.get("name", "").strip()
            if not name:
                continue

            location = p.get("location") or {}
            city_name = _extract_city(location)
            address   = location.get("formatted_address") or location.get("address") or city_name

            phone   = p.get("tel") or ""
            website = p.get("website") or f"https://{_slug(name)}.co.il"
            rating  = float(p.get("rating") or 0.0)  # Foursquare scale 0–10
            # Normalise to 0–5 to match app's star rating display
            rating_5 = round(rating / 2, 1) if rating else 0.0

            price_min, price_max = _price_range(p)
            description = (p.get("description") or "").strip()
            if not description:
                description = (
                    f"{name} is a highly regarded {category.lower()} provider "
                    f"in {city_name}, trusted by couples across Israel."
                )

            # Try inline photo first, then dedicated endpoint
            photo = _photo_url(p)
            if not photo:
                time.sleep(REQUEST_DELAY_S)
                photo = _fetch_photos(fsq_id)

            slug = _slug(name)
            vendors.append({
                "fsq_id":          fsq_id,
                "business_name":   name,
                "category":        category,
                "city":            city_name,
                "address":         address,
                "phone":           phone,
                "email":           f"hello@{slug}.co.il",
                "website":         website,
                "instagram_url":   f"https://instagram.com/{slug}",
                "description":     description,
                "price_min":       price_min,
                "price_max":       price_max,
                "rating_average":  rating_5,
                "photo_url":       photo,
            })

            if len(vendors) >= MAX_PER_CATEGORY:
                break

        time.sleep(REQUEST_DELAY_S)

    return vendors


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    if CACHE_FILE.exists():
        print(f"Cache already exists at {CACHE_FILE.name} — skipping fetch.")
        print("Delete vendors_cache.json and re-run to refresh the data.")
        return

    if not API_KEY:
        print("ERROR: FOURSQUARE_KEY is not set in .env")
        return

    print(f"Fetching real Israeli vendor data ({len(CATEGORY_QUERIES)} categories × {len(SEARCH_CITIES)} cities)…")
    print()

    all_vendors: dict[str, list[dict]] = {}
    grand_total = 0

    for category, query in CATEGORY_QUERIES.items():
        print(f"  {category:<22} (query: '{query}')")
        vendors = search_category(category, query)
        all_vendors[category] = vendors
        grand_total += len(vendors)
        print(f"    → {len(vendors)} vendors found")

    CACHE_FILE.write_text(
        json.dumps(all_vendors, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print()
    print(f"Done. {grand_total} total vendors across {len(all_vendors)} categories.")
    print(f"Cache saved to: {CACHE_FILE}")
    print()
    print("Next:  python seed.py")


if __name__ == "__main__":
    main()
