"""
Vowly - real vendor data fetcher (Google Places API).

Searches for real Israeli wedding businesses across several cities, normalizes
Google Places results into the same vendors_cache.json format used by seed.py,
and then lets the existing app display those vendors.

Usage:
    1. Put GOOGLE_PLACES_API_KEY in .env.
    2. Run:   python fetch_google_vendors.py
    3. Run:   python seed.py

If vendors_cache.json already exists, this script skips API calls. Delete that
file first when you want to refresh the imported vendor data.
"""

import json
import os
import re
import time
from pathlib import Path
from urllib.parse import quote

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY", "")
CACHE_FILE = Path(__file__).parent / "vendors_cache.json"

SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
PHOTO_URL = "https://places.googleapis.com/v1/{photo_name}/media"

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

LIMIT_PER_SEARCH = 10
MAX_PER_CATEGORY = 50
REQUEST_DELAY_S = 0.35

FIELD_MASK = ",".join([
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.internationalPhoneNumber",
    "places.websiteUri",
    "places.rating",
    "places.priceLevel",
    "places.photos",
])

CATEGORY_QUERIES = {
    "Venue":           "wedding venue event hall",
    "DJ":              "wedding DJ music entertainment",
    "Photographer":    "wedding photographer photography studio",
    "Videographer":    "wedding videographer film production",
    "Catering":        "wedding catering food events",
    "Makeup Artist":   "bridal makeup artist beauty studio",
    "Hair Stylist":    "bridal hair salon hairdresser",
    "Wedding Dress":   "bridal wedding dress boutique",
    "Groom Suit":      "groom suit tailor men formalwear",
    "Rings":           "wedding rings jewelry diamonds",
    "Flowers":         "wedding florist flowers arrangements",
    "Invitations":     "wedding invitations printing stationery",
    "Transportation":  "wedding limousine car hire luxury",
    "Wedding Planner": "wedding planner event coordinator",
    "Rabbi/Officiant": "wedding rabbi officiant",
    "Decor":           "wedding event decor rental lighting",
    "Cake/Desserts":   "wedding cake bakery pastry desserts",
    "Alcohol Bar":     "wedding bar cocktail catering",
}

PRICE_MAP = {
    "PRICE_LEVEL_INEXPENSIVE": (3_000, 8_000),
    "PRICE_LEVEL_MODERATE": (8_000, 20_000),
    "PRICE_LEVEL_EXPENSIVE": (20_000, 50_000),
    "PRICE_LEVEL_VERY_EXPENSIVE": (50_000, 120_000),
}
DEFAULT_PRICE = (5_000, 15_000)


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower().replace("&", "and"))


def _headers() -> dict:
    return {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": FIELD_MASK,
    }


def _display_name(place: dict) -> str:
    name = place.get("displayName") or {}
    return (name.get("text") or "").strip()


def _city_from_address(address: str, fallback_city: str) -> str:
    for part in reversed([p.strip() for p in address.split(",")]):
        if part and not part.lower().startswith("israel"):
            return part
    return fallback_city.split(",")[0].strip() or "Israel"


def _photo_url(place: dict) -> str:
    photos = place.get("photos") or []
    if not photos:
        return ""

    photo_name = photos[0].get("name", "")
    if not photo_name:
        return ""

    encoded_name = quote(photo_name, safe="/")
    return (
        PHOTO_URL.format(photo_name=encoded_name)
        + f"?maxWidthPx=800&key={API_KEY}"
    )


def _price_range(place: dict) -> tuple[int, int]:
    return PRICE_MAP.get(place.get("priceLevel"), DEFAULT_PRICE)


def _search_google(text_query: str) -> list[dict]:
    body = {
        "textQuery": text_query,
        "languageCode": "en",
        "regionCode": "IL",
        "pageSize": LIMIT_PER_SEARCH,
    }

    try:
        response = requests.post(
            SEARCH_URL,
            headers=_headers(),
            json=body,
            timeout=15,
        )
    except requests.RequestException as exc:
        print(f"      [network error] {exc}")
        return []

    if response.status_code == 429:
        print("      [rate limit] sleeping 10 s")
        time.sleep(10)
        return []

    if response.status_code != 200:
        print(f"      [HTTP {response.status_code}] {response.text[:220]}")
        return []

    return response.json().get("places") or []


def search_category(category: str, query: str) -> list[dict]:
    seen_ids: set[str] = set()
    vendors: list[dict] = []

    for city in SEARCH_CITIES:
        if len(vendors) >= MAX_PER_CATEGORY:
            break

        places = _search_google(f"{query} in {city}")

        for place in places:
            place_id = place.get("id", "")
            if not place_id or place_id in seen_ids:
                continue
            seen_ids.add(place_id)

            name = _display_name(place)
            if not name:
                continue

            address = place.get("formattedAddress") or city
            city_name = _city_from_address(address, city)
            price_min, price_max = _price_range(place)
            slug = _slug(name)

            vendors.append({
                "google_place_id": place_id,
                "business_name": name,
                "category": category,
                "city": city_name,
                "address": address,
                "phone": place.get("internationalPhoneNumber") or "",
                "email": f"hello@{slug}.co.il",
                "website": place.get("websiteUri") or "",
                "instagram_url": f"https://instagram.com/{slug}",
                "description": (
                    f"{name} is a real {category.lower()} provider listed on "
                    f"Google Places in {city_name}."
                ),
                "price_min": price_min,
                "price_max": price_max,
                "rating_average": float(place.get("rating") or 0.0),
                "photo_url": _photo_url(place),
            })

            if len(vendors) >= MAX_PER_CATEGORY:
                break

        time.sleep(REQUEST_DELAY_S)

    return vendors


def main() -> None:
    if CACHE_FILE.exists():
        print(f"Cache already exists at {CACHE_FILE.name} - skipping fetch.")
        print("Delete vendors_cache.json and re-run to refresh the data.")
        return

    if not API_KEY:
        print("ERROR: GOOGLE_PLACES_API_KEY is not set in .env")
        return

    print(
        "Fetching real Israeli vendor data from Google Places "
        f"({len(CATEGORY_QUERIES)} categories x {len(SEARCH_CITIES)} cities)..."
    )
    print()

    all_vendors: dict[str, list[dict]] = {}
    grand_total = 0

    for category, query in CATEGORY_QUERIES.items():
        print(f"  {category:<22} (query: '{query}')")
        vendors = search_category(category, query)
        all_vendors[category] = vendors
        grand_total += len(vendors)
        print(f"    -> {len(vendors)} vendors found")

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
