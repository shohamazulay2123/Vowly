"""
Vowly — wedding supplier catalog.

A flat, easy-to-extend list of suppliers grouped under three top-level
categories. Each entry is rendered as a checklist card in the onboarding
flow and on the supplier checklist page.

Each supplier has:
  - code:        stable string id used as the DB key (do not rename casually)
  - name:        display name
  - category:    one of GROUP_* constants
  - description: short helper text for the card
  - applies_to:  list containing any of: 'shared', 'bride', 'groom'
                   * 'shared'  -> always visible
                   * 'bride'   -> visible to brides (and when role unknown)
                   * 'groom'   -> visible to grooms (and when role unknown)
                 A user signed up as a Bride sees shared + bride.
                 A user signed up as a Groom sees shared + groom.
                 Anyone else (no role) sees everything.
"""

GROUP_MUST_HAVE  = "Must-have suppliers"
GROUP_EXTRAS     = "Important extras"
GROUP_PERSONAL   = "Personal preparation"

GROUPS = [GROUP_MUST_HAVE, GROUP_EXTRAS, GROUP_PERSONAL]

STATUSES = ["Not started", "In progress", "Booked", "Not relevant"]
DEFAULT_STATUS = "Not started"


SUPPLIERS = [
    # ---- 1. Must-have suppliers --------------------------------------------
    {
        "code": "venue", "name": "Wedding venue / hall / garden",
        "category": GROUP_MUST_HAVE, "applies_to": ["shared"],
        "description": "The place itself — date availability, capacity, parking, accessibility, basic design and what's included.",
    },
    {
        "code": "catering", "name": "Catering / food",
        "category": GROUP_MUST_HAVE, "applies_to": ["shared"],
        "description": "Sometimes included with the venue, sometimes separate. Menu, tastings, vegetarian/vegan, kids' meals, late-night food.",
    },
    {
        "code": "bar", "name": "Bar / alcohol supplier",
        "category": GROUP_MUST_HAVE, "applies_to": ["shared"],
        "description": "Basic bar, premium bar, cocktails, wine, beer, soft drinks, coffee station.",
    },
    {
        "code": "photographer", "name": "Photographer",
        "category": GROUP_MUST_HAVE, "applies_to": ["shared"],
        "description": "Still photography for the couple, family, ceremony, party and details.",
    },
    {
        "code": "videographer", "name": "Videographer",
        "category": GROUP_MUST_HAVE, "applies_to": ["shared"],
        "description": "Full wedding video, highlights video, ceremony recording, drone footage if relevant.",
    },
    {
        "code": "dj", "name": "DJ / music",
        "category": GROUP_MUST_HAVE, "applies_to": ["shared"],
        "description": "Ceremony music, reception music, party music, microphones, sound system, backup equipment.",
    },
    {
        "code": "florist", "name": "Wedding designer / florist",
        "category": GROUP_MUST_HAVE, "applies_to": ["shared"],
        "description": "Chuppah/ceremony design, table centerpieces, entrance design, bridal bouquet, car decoration if needed.",
    },
    {
        "code": "bride_dress", "name": "Bride dress",
        "category": GROUP_MUST_HAVE, "applies_to": ["bride"],
        "description": "Wedding dress, shoes, accessories, second outfit if relevant.",
    },
    {
        "code": "groom_suit", "name": "Groom suit",
        "category": GROUP_MUST_HAVE, "applies_to": ["groom"],
        "description": "Groom suit, shoes, tie/bow tie, cufflinks, accessories, second outfit if relevant.",
    },
    {
        "code": "hair_stylist", "name": "Hair stylist",
        "category": GROUP_MUST_HAVE, "applies_to": ["bride"],
        "description": "Usually for the bride, sometimes also for family members or bridesmaids.",
    },
    {
        "code": "makeup", "name": "Makeup artist",
        "category": GROUP_MUST_HAVE, "applies_to": ["bride"],
        "description": "Bride makeup, trial session, touch-up kit, family makeup if needed.",
    },
    {
        "code": "rings", "name": "Wedding rings",
        "category": GROUP_MUST_HAVE, "applies_to": ["shared"],
        "description": "Rings, engraving, resizing, delivery timeline.",
    },
    {
        "code": "invitations", "name": "Invitations / digital invitations",
        "category": GROUP_MUST_HAVE, "applies_to": ["shared"],
        "description": "Save the date, formal invitation, RSVP system, WhatsApp invite, seating confirmation.",
    },
    {
        "code": "officiant", "name": "Rabbi / officiant / ceremony leader",
        "category": GROUP_MUST_HAVE, "applies_to": ["shared"],
        "description": "Depending on the type of ceremony. Includes legal/religious documents and coordination.",
    },
    {
        "code": "transportation", "name": "Transportation",
        "category": GROUP_MUST_HAVE, "applies_to": ["shared"],
        "description": "Car for the couple, shuttle buses for guests, taxis, parking arrangements.",
    },
    {
        "code": "planner", "name": "Wedding planner / event manager",
        "category": GROUP_MUST_HAVE, "applies_to": ["shared"],
        "description": "Optional but very useful. Handles supplier coordination, timeline, payments and problems on the wedding day.",
    },

    # ---- 2. Important extras -----------------------------------------------
    {
        "code": "seating_system", "name": "Seating arrangement system",
        "category": GROUP_EXTRAS, "applies_to": ["shared"],
        "description": "Guest list management, table planning, RSVP tracking, guest confirmations.",
    },
    {
        "code": "attractions", "name": "Attractions for guests",
        "category": GROUP_EXTRAS, "applies_to": ["shared"],
        "description": "Magnets, photo booth, mirror booth, live painter, smoke machine, confetti, fireworks, glow sticks.",
    },
    {
        "code": "lighting", "name": "Lighting and sound upgrades",
        "category": GROUP_EXTRAS, "applies_to": ["shared"],
        "description": "Stage lighting, dance floor lighting, screens, projectors, special effects.",
    },
    {
        "code": "cake", "name": "Cake / dessert table",
        "category": GROUP_EXTRAS, "applies_to": ["shared"],
        "description": "Wedding cake, sweets table, custom desserts, late-night snacks.",
    },
    {
        "code": "accommodation", "name": "Accommodation",
        "category": GROUP_EXTRAS, "applies_to": ["shared"],
        "description": "Hotel rooms for couple, family, or guests coming from far away.",
    },
    {
        "code": "guest_gifts", "name": "Gifts for guests",
        "category": GROUP_EXTRAS, "applies_to": ["shared"],
        "description": "Small souvenirs, branded items, candies, candles, personalized gifts.",
    },
    {
        "code": "kids_entertainment", "name": "Kids' entertainment",
        "category": GROUP_EXTRAS, "applies_to": ["shared"],
        "description": "Babysitter, kids' table, games, small activity area.",
    },
    {
        "code": "security", "name": "Security / first aid",
        "category": GROUP_EXTRAS, "applies_to": ["shared"],
        "description": "Depending on venue size and requirements.",
    },
    {
        "code": "cleaning", "name": "Cleaning / restroom service",
        "category": GROUP_EXTRAS, "applies_to": ["shared"],
        "description": "Usually handled by the venue, but worth confirming.",
    },
    {
        "code": "after_party", "name": "After-party supplier",
        "category": GROUP_EXTRAS, "applies_to": ["shared"],
        "description": "Separate bar, club, food, transportation, playlist/DJ extension.",
    },

    # ---- 3. Personal preparation suppliers ---------------------------------
    {
        "code": "nails", "name": "Nails",
        "category": GROUP_PERSONAL, "applies_to": ["bride"],
        "description": "Manicure, pedicure, trial color.",
    },
    {
        "code": "spa", "name": "Spa / skincare",
        "category": GROUP_PERSONAL, "applies_to": ["bride", "groom"],
        "description": "Facial treatment, waxing, laser, tanning, massage.",
    },
    {
        "code": "fitness", "name": "Fitness / nutrition coach",
        "category": GROUP_PERSONAL, "applies_to": ["bride", "groom"],
        "description": "Optional if the couple wants a plan before the wedding.",
    },
    {
        "code": "tailor", "name": "Tailor / alterations",
        "category": GROUP_PERSONAL, "applies_to": ["bride", "groom"],
        "description": "Dress and suit adjustments close to the date.",
    },
    {
        "code": "jewelry", "name": "Jewelry and accessories",
        "category": GROUP_PERSONAL, "applies_to": ["bride", "groom"],
        "description": "Earrings, necklace, cufflinks, hair accessories.",
    },
    {
        "code": "grooming", "name": "Grooming / barber",
        "category": GROUP_PERSONAL, "applies_to": ["groom"],
        "description": "Haircut, beard trim, skincare, grooming appointment before the wedding.",
    },
]

SUPPLIERS_BY_CODE = {s["code"]: s for s in SUPPLIERS}

# Map supplier checklist codes to the matching vendor_categories.category_name.
# Used to wire a supplier card to its Tinder-style swipe queue.
SUPPLIER_TO_VENDOR_CATEGORY = {
    "venue":          "Venue",
    "catering":       "Catering",
    "bar":            "Alcohol Bar",
    "photographer":   "Photographer",
    "videographer":   "Videographer",
    "dj":             "DJ",
    "florist":        "Flowers",
    "bride_dress":    "Wedding Dress",
    "groom_suit":     "Groom Suit",
    "hair_stylist":   "Hair Stylist",
    "makeup":         "Makeup Artist",
    "rings":          "Rings",
    "invitations":    "Invitations",
    "officiant":      "Rabbi/Officiant",
    "transportation": "Transportation",
    "planner":        "Wedding Planner",
    "cake":           "Cake/Desserts",
}


def visible_suppliers_for_role(role):
    """Return suppliers visible for a user with the given role.

    role: 'Bride', 'Groom', or anything else / None  -> show everything.
    """
    role_l = (role or "").strip().lower()
    if role_l == "bride":
        keep = {"shared", "bride"}
    elif role_l == "groom":
        keep = {"shared", "groom"}
    else:
        keep = {"shared", "bride", "groom"}
    return [s for s in SUPPLIERS if any(a in keep for a in s["applies_to"])]


def group_by_category(suppliers):
    """Return an OrderedDict-like dict: {category_name: [supplier, ...]}
    preserving the GROUPS ordering."""
    grouped = {g: [] for g in GROUPS}
    for s in suppliers:
        grouped.setdefault(s["category"], []).append(s)
    # drop empty categories
    return {k: v for k, v in grouped.items() if v}
