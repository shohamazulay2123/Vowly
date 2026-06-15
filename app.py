"""
Vowly - Flask wedding planning app.
"""

import os
import math
import re
import requests
from datetime import datetime
from functools import wraps
from urllib.parse import quote

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, abort, jsonify
)
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash, check_password_hash

from authlib.integrations.flask_client import OAuth

from config import (
    SECRET_KEY,
    GOOGLE_PLACES_API_KEY,
    VOWLY_PUBLIC_BASE_URL,
    GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET,
    FACEBOOK_CLIENT_ID, FACEBOOK_CLIENT_SECRET,
)
from database import init_db, close_db, query, execute, get_db
from suppliers import (
    SUPPLIERS, SUPPLIERS_BY_CODE, GROUPS, STATUSES, DEFAULT_STATUS,
    SUPPLIER_TO_VENDOR_CATEGORY,
    visible_suppliers_for_role, group_by_category,
)


app = Flask(__name__)
app.secret_key = SECRET_KEY
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
app.teardown_appcontext(close_db)

# ── OAuth ────────────────────────────────────────────────────────────────
oauth = OAuth(app)

if GOOGLE_CLIENT_ID:
    oauth.register(
        name='google',
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'},
    )

if FACEBOOK_CLIENT_ID:
    oauth.register(
        name='facebook',
        client_id=FACEBOOK_CLIENT_ID,
        client_secret=FACEBOOK_CLIENT_SECRET,
        authorize_url='https://www.facebook.com/dialog/oauth',
        access_token_url='https://graph.facebook.com/oauth/access_token',
        api_base_url='https://graph.facebook.com/v18.0/',
        client_kwargs={'scope': 'email public_profile'},
    )


DEFAULT_LANGUAGE = "he"


TRANSLATIONS = {
    "he": {
        "app_title": "Vowly · תכנון חתונה מושלם",
        "brand_tagline": "מאצ׳ים עם הספקים שמתאימים לחתונה שלכם.",
        "home": "בית",
        "liked": "מועדפים",
        "settings": "הגדרות",
        "logout": "התנתקות",
        "login": "התחברות",
        "sign_up": "הרשמה",
        "footer": "נבנה באהבה לזוגות שמתכננים חתונה.",
        "settings_title": "הגדרות",
        "settings_subtitle": "בחרו איך Vowly תרגיש ואילו ספקים יופיעו קודם.",
        "about_us": "עלינו",
        "about_text": "Vowly עוזרת לזוגות לתכנן חתונה במקום אחד רגוע: לעקוב אחרי התקדמות ספקים, לגלות ספקים, לשמור מועדפים ולהתקדם להחלטה הבאה.",
        "preferences": "העדפות",
        "distance": "מרחק ספקים",
        "distance_value": "{value} ק״מ",
        "distance_hint": "משמש במסך הסווייפ כדי לתעדף ספקים ליד העיר שלכם.",
        "save_settings": "שמירת הגדרות",
        "settings_saved": "ההגדרות נשמרו.",
        "home_title": "בית",
        "welcome_back": "בית",
        "days_until": "ימים עד",
        "day_until": "יום עד",
        "set_wedding_date": "הגדרת תאריך חתונה",
        "booked": "נסגר",
        "in_progress": "בתהליך",
        "to_do": "לביצוע",
        "search_vendors": "חיפוש ספקים",
        "all": "הכול",
        "no_suppliers": "אין ספקים שתואמים לסינון.",
        "search_supplier": "חיפוש ספק",
        "no_suppliers_found": "לא נמצאו ספקים",
        "try_another_search": "נסו חיפוש אחר.",
        "open_menu": "פתיחת תפריט",
        "main_navigation": "ניווט ראשי",
        "close": "סגירה",
        "back": "חזרה",
        "back_home": "חזרה לבית",
        "back_to_home": "חזרה לבית",
        "save": "שמירה",
        "saved": "נשמר",
        "could_not_save": "לא הצלחנו לשמור",
        "view": "צפייה",
        "select": "בחירה",
        "remove": "הסרה",
        "new": "חדש",
        "match": "מאצ׳",
        "skip": "דילוג",
        "like": "אהבתי",
        "more_info": "עוד פרטים",
        "view_profile": "צפייה בפרופיל",
        "see_all": "לכל המועדפים",
        "start_swiping": "לבחירה",
        "no_liked_vendors": "עדיין אין ספקים שאהבתם",
        "liked_subtitle": "ספקים שסימנתם בלב בזמן הסווייפ. מכאן בוחרים את מי להכניס לשורטליסט.",
        "match_queue": "תור המאצ׳ים",
        "tap_card_hint": "לחצו על כרטיס לפרטים · גררו או השתמשו בחצים",
        "home_greeting": "היי {name}",
        "home_greeting_pair": "היי {name} ו{partner}",
        "mazel_tov_past": "מזל טוב — החתונה כבר הייתה",
        "booked_ratio": "{booked} / {total} נסגרו",
        "category_meta": "{booked}/{total} נסגרו · {progress} בתהליך",
        "next_match": "המאצ׳ים הבאים",
        "profile_title_create": "יצירת פרופיל חתונה",
        "profile_title_edit": "עריכת פרופיל חתונה",
        "partner_name": "שם בן/בת הזוג",
        "wedding_date": "תאריך החתונה",
        "estimated_guests": "מספר אורחים משוער",
        "total_budget": "תקציב כולל",
        "city": "עיר",
        "venue_type": "העדפת סוג מקום",
        "choose": "בחירה",
        "save_changes": "שמירת שינויים",
        "create_profile": "יצירת פרופיל",
        "discover_vendors": "גילוי ספקים",
        "search_business": "חיפוש עסק או תיאור",
        "all_categories": "כל הקטגוריות",
        "all_cities": "כל הערים",
        "min_rating": "דירוג מינימלי",
        "max_price": "מחיר מקסימלי",
        "filter": "סינון",
        "no_vendors": "אין ספקים שתואמים לסינון.",
        "about": "על הספק",
        "contact": "יצירת קשר",
        "reviews": "ביקורות",
        "no_reviews": "עדיין אין ביקורות",
        "leave_first_review": "כתבו את הראשונה",
        "remove_favorite": "הסרה מהמועדפים",
        "add_favorite": "הוספה למועדפים",
        "select_vendor": "בחירת ספק",
        "selected_vendors": "ספקים שנבחרו",
        "agreed_price": "מחיר שסוכם",
        "notes": "הערות",
        "vendor": "ספק",
        "category": "קטגוריה",
        "status": "סטטוס",
        "no_selected_vendors": "עדיין לא בחרתם ספקים.",
        "remove_selected_confirm": "להסיר מהנבחרים?",
        "chosen": "נבחר",
        "per_meal": "למנה",
        "guest_count_est": "מספר אורחים משוער",
        "price_per_meal": "מחיר למנה (₪)",
        "venue_select_title": "פרטי האולם",
        "confirm_select": "הוספה לנבחרים",
        "cancel": "ביטול",
        "appointments": "פגישות",
        "schedule_new": "קביעת פגישה חדשה",
        "select_vendor_placeholder": "בחרו ספק...",
        "location": "מיקום",
        "schedule": "קביעה",
        "date": "תאריך",
        "no_appointments": "עדיין אין פגישות.",
        "leave_review": "כתיבת ביקורת",
        "tell_couples": "ספרו לזוגות אחרים מה חשבתם",
        "post_review": "פרסום ביקורת",
        "latest_reviews": "ביקורות אחרונות",
        "analytics": "אנליטיקה",
        "analytics_subtitle": "נתוני תכנון חיים מתוך בסיס הנתונים של Vowly.",
        "users": "משתמשים",
        "weddings": "חתונות",
        "vendors": "ספקים",
        "vendors_per_category": "ספקים לפי קטגוריה",
        "avg_rating_per_category": "דירוג ממוצע לפי קטגוריה",
        "most_liked_vendors": "הספקים הכי אהובים",
        "most_skipped_vendors": "הספקים שדולגו הכי הרבה",
        "popular_categories": "קטגוריות פופולריות",
        "top_cities": "ערים מובילות",
        "checklist_progress": "התקדמות חתונות",
        "budget_estimated_actual": "תקציב משוער מול בפועל",
        "elite_vendors": "ספקים מצטיינים",
        "interactions": "אינטראקציות",
        "likes": "לייקים",
        "skips": "דילוגים",
        "average_rating": "דירוג ממוצע",
        "completed": "הושלם",
        "total": "סה״כ",
        "actual": "בפועל",
        "estimated": "משוער",
        "couple": "זוג",
        "onboarding_title": "ברוכים הבאים ל-Vowly{name}",
        "onboarding_subtitle": "בחרו את הספקים שתרצו להתחיל איתם. נסמן אותם כבתהליך ונבנה סביבם את דק התכנון שלכם.",
        "showing_role": "מציגים ספקים שרלוונטיים ל: {role}.",
        "suppliers_count": "{count} ספקים",
        "skip_home": "דילוג לבית",
        "start_planning": "מתחילים לתכנן",
        "auth_headline": "מוצאים את הספקים ששווה להגיד להם כן.",
        "auth_login_title": "ברוכים השבים",
        "auth_login_subtitle": "התחברו כדי להמשיך למצוא את הספקים הנכונים.",
        "auth_register_title": "יצירת חשבון",
        "auth_register_subtitle": "מתחילים לתכנן חתונה בכמה דקות.",
        "email": "אימייל",
        "password": "סיסמה",
        "full_name": "שם מלא",
        "phone": "טלפון",
        "select_city": "בחרו עיר...",
        "i_am_the": "אני",
        "select_one": "בחרו...",
        "bride": "כלה",
        "groom": "חתן",
        "partner_details": "פרטי בן/בת הזוג",
        "partner_email": "אימייל בן/בת הזוג",
        "partner_phone": "טלפון בן/בת הזוג",
        "create_account": "יצירת חשבון",
        "new_to_vowly": "חדשים ב-Vowly?",
        "create_account_link": "צרו חשבון",
        "already_account": "כבר יש לכם חשבון?",
        "login_required": "כדי להמשיך צריך להתחבר.",
        "session_expired": "הסשן פג. התחברו שוב בבקשה.",
        "missing_register_fields": "שם, אימייל וסיסמה הם שדות חובה.",
        "missing_partner_fields": "מלאו בבקשה שם, אימייל וטלפון של בן/בת הזוג.",
        "email_registered": "האימייל הזה כבר רשום.",
        "welcome_setup": "ברוכים הבאים ל-Vowly! בואו נבנה את דשבורד המאצ׳ים שלכם.",
        "welcome_back_name": "ברוכים השבים, {name}!",
        "invalid_login": "אימייל או סיסמה לא נכונים.",
        "oauth_failed": "ההתחברות נכשלה. נסו שוב.",
        "oauth_no_email": "לא הצלחנו לקבל את כתובת האימייל שלכם.",
        "oauth_not_configured": "אמצעי כניסה זה עדיין לא מוגדר.",
        "continue_google": "המשך עם Google",
        "continue_facebook": "המשך עם Facebook",
        "continue_apple": "המשך עם Apple",
        "or_divider": "או",
        "logged_out": "התנתקתם בהצלחה.",
        "profile_updated": "פרופיל החתונה עודכן.",
        "profile_created": "פרופיל החתונה נוצר. ברוכים הבאים ל-Vowly!",
        "picked_suppliers": "מעולה. סימנו {count} ספקים כבתהליך.",
        "favorite_added": "הספק נוסף למועדפים.",
        "favorite_removed": "הספק הוסר מהמועדפים.",
        "shortlist_added": "הספק נוסף לשורטליסט.",
        "selection_updated": "הבחירה עודכנה.",
        "appointment_required": "צריך לבחור ספק ותאריך.",
        "appointment_scheduled": "הפגישה נקבעה.",
        "review_required": "צריך לבחור ספק ודירוג בין 1 ל-5.",
        "review_posted": "הביקורת פורסמה.",
        "page_not_found": "העמוד לא נמצא",
        "server_error": "משהו השתבש",
        # --- Vowly 2.0 ---
        "plan": "תכנון",
        "discover": "גילוי",
        "profile": "פרופיל",
        "plan_title": "התוכנית שלכם",
        "plan_subtitle": "כל הספקים ליום הגדול, ברשימה אחת.",
        "discover_title": "גילוי",
        "discover_subtitle": "החליקו בין ספקים וסמנו לייק לאלה שתגידו להם כן.",
        "left_in_queue": "{count} לבדיקה",
        "all_caught_up": "עברתם על הכול!",
        "caught_up_sub": "ראיתם את כל הספקים כאן. בחרו קטגוריה אחרת כדי להמשיך.",
        "your_wedding": "החתונה שלכם",
        "days_to_go": "ימים נשארו",
        "day_to_go": "יום נשאר",
        "add_wedding_date": "הוסיפו תאריך חתונה",
        "planning_progress": "התקדמות התכנון",
        "of_suppliers_booked": "{booked} מתוך {total} נסגרו",
        "keep_matching": "להמשיך למאצ׳ים",
        "view_full_plan": "לתוכנית המלאה",
        "up_next": "הבא בתור",
        "recently_liked": "לייקים אחרונים",
        "good_morning": "בוקר טוב",
        "good_afternoon": "צהריים טובים",
        "good_evening": "ערב טוב",
        "step_of": "שלב {step} מתוך {total}",
        "wizard_basics_title": "ספרו לנו על היום הגדול",
        "wizard_basics_sub": "כמה פרטים כדי ש-Vowly תתאים הכול בשבילכם. אפשר לשנות בכל רגע.",
        "wizard_pick_title": "במה תרצו להתחיל?",
        "wizard_pick_sub": "בחרו כמה ספקים להתמקד בהם. נבנה סביבם את תור המאצ׳ים שלכם.",
        "next_step": "הבא",
        "skip_for_now": "דלגו בינתיים",
        "wedding_details": "פרטי החתונה",
        "edit": "עריכה",
        "guests": "אורחים",
        "budget": "תקציב",
        "account": "חשבון",
        "more_tools": "כלים נוספים",
        "not_set": "לא הוגדר",
        "next_appointment": "הפגישה הבאה",
        "auth_welcome": "להגיד כן לספקים הנכונים.",
        "auth_welcome_sub": "Vowly עושה לכם מאצ׳ עם ספקי חתונה שתאהבו — מחליקים, שומרים, סוגרים.",
        # ── Dashboard ──
        "dash_overview": "החתונה שלכם במבט אחד",
        "stat_completed": "משימות הושלמו",
        "stat_in_progress": "בתהליך",
        "stat_meetings": "פגישות",
        "stat_favorites": "מועדפים",
        "your_journey": "מסע התכנון שלכם",
        "upcoming_tasks": "המשימות הקרובות שלך",
        "all_tasks": "לכל המשימות",
        "tasks_all_done": "הכול בשליטה — אין משימות פתוחות 🎉",
        "recommended": "מומלץ עכשיו",
        "vendor_categories": "גילוי ספקים",
        "browse_all": "לכל הקטגוריות",
        "next_step_label": "השלב הבא שלכם",
        "next_step_book": "לבחור {name}",
        "continue_planning": "המשיכו לתכנון",
        "all_set": "סידרתם הכול",
        "all_set_sub": "כל הספקים נסגרו — הגיע הזמן לחגוג!",
        "stage_venue": "בחירת אולם",
        "stage_vendors": "ספקים",
        "stage_tasting": "טעימות",
        "stage_invites": "הזמנות",
        "stage_seating": "סידורי הושבה",
        "stage_week": "שבוע החתונה",
        # NBA
        "nba_set_date": "הגדרת תאריך חתונה",
        "nba_set_date_sub": "הלו״ז שלכם וכל תזכורות הספקים נבנים סביבו.",
        "nba_set_guests": "הערכת מספר אורחים",
        "nba_set_guests_sub": "זה משפיע על בחירת המקום והתקציב.",
        "nba_set_budget": "הגדרת תקציב כולל",
        "nba_set_budget_sub": "נעזור לכם לעקוב אחרי כל שקל.",
        "nba_find_venue": "בחרו 3–5 אולמות לביקור",
        "nba_find_venue_sub": "המקום קובע את התאריך, קיבולת האורחים, הקייטרינג וכל ספק אחר.",
        "nba_core_vendor": "מצאו {name}",
        "nba_core_vendor_sub": "{name} טובים נסגרים חודשים מראש — אל תחכו.",
        "nba_ceremony_route": "בחרו את מסלול הטקס",
        "nba_ceremony_route_sub": "Vowly תבנה עבורכם את רשימת המשימות הנכונה.",
        "nba_rabbinate_docs": "פתחו תיק נישואין ברבנות",
        "nba_rabbinate_docs_sub": "הגשת מסמכים לרבנות לוקחת זמן — כדאי להתחיל מוקדם.",
        "nba_guest_list": "צרו רשימת אורחים",
        "nba_guest_list_sub": "הוסיפו שמות, צדדים ופרטי קשר למעקב אישורי הגעה.",
        "nba_rsvp_followup": "מעקב אחרי אורחים",
        "nba_rsvp_followup_sub": "{count} אורחים עדיין לא ענו.",
        "nba_wedding_month": "חודש החתונה — נשארו {days} ימים",
        "nba_wedding_month_sub": "אשרו את כל הספקים, סיימו ההושבה ונקו יתרות תשלום.",
        "nba_wedding_day": "היום החתונה שלכם!",
        "nba_wedding_day_sub": "התמקדו בלו״ז, אנשי קשר של ספקים, ורשימת הבדיקה הסופית.",
        # Guests
        "guest_list": "רשימת אורחים",
        "add_guest": "הוספת אורח",
        "no_guests": "עדיין לא הוספתם אורחים.",
        "guest_added": "האורח נוסף.",
        "guest_deleted": "האורח הוסר.",
        "guest_updated": "האורח עודכן.",
        "rsvp_unknown": "לא ענה",
        "rsvp_invited": "הוזמן",
        "rsvp_coming": "מגיע",
        "rsvp_not_coming": "לא מגיע",
        "rsvp_maybe": "אולי",
        "rsvp_needs_follow_up": "צריך מעקב",
        "rsvp_status": "סטטוס הגעה",
        "side_bride": "צד הכלה",
        "side_groom": "צד החתן",
        "side_shared": "משותף",
        "side_family": "משפחה",
        "side_work": "עבודה",
        "side_friends": "חברים",
        "total_guests": "סה״כ אורחים",
        "confirmed_coming": "אישרו הגעה",
        "not_answered": "לא ענו",
        "invitation_sent_label": "הזמנה נשלחה",
        "meal_notes": "הערות אוכל",
        "table_number": "שולחן",
        "guest_notes": "הערות",
        "guest_side": "צד",
        "guest_group": "קבוצה",
        "guest_phone": "טלפון",
        # Budget
        "budget_title": "תקציב",
        "budget_subtitle": "מעקב אחרי כל עלות — מהמשוער לתשלום סופי.",
        "add_budget_item": "הוספת פריט",
        "budget_category": "קטגוריה",
        "estimated_amount": "משוער",
        "actual_amount": "בפועל",
        "paid_amount": "שולם",
        "remaining": "נשאר",
        "due_date": "תאריך תשלום",
        "payment_status": "סטטוס תשלום",
        "not_paid": "לא שולם",
        "deposit_paid": "מקדמה שולמה",
        "partially_paid": "שולם חלקית",
        "paid_full": "שולם במלואו",
        "budget_total_estimated": "סה״כ משוער",
        "budget_total_actual": "סה״כ בפועל",
        "budget_total_paid": "שולם עד כה",
        "budget_over": "חורגים מהתקציב",
        "budget_under": "מתחת לתקציב",
        "budget_item_added": "פריט התקציב נוסף.",
        "budget_item_updated": "פריט התקציב עודכן.",
        "budget_item_deleted": "פריט התקציב הוסר.",
        "price_per_guest": "מחיר משוער לאורח (₪)",
        "next_payment_due": "התשלום הבא",
        "no_budget_items": "עדיין אין פריטי תקציב.",
        "budget_required_fields": "קטגוריה וסכום משוער הם שדות חובה.",
        # Ceremony
        "ceremony_route": "מסלול טקס",
        "ceremony_route_label": "איך אתם מתחתנים?",
        "route_rabbinate": "רבנות",
        "route_private_rabbi": "רב פרטי",
        "route_civil_abroad": "נישואים אזרחיים בחו״ל",
        "route_utah_online": "יוטה / נישואים אזרחיים אונליין",
        "route_symbolic": "טקס סמלי",
        "route_other": "אחר",
        "route_unknown": "עדיין לא החלטנו",
        # Wedding month
        "wedding_month_mode": "חודש החתונה",
        "see_plan": "לתוכנית המלאה",
        "see_guests": "לרשימת האורחים",
        "see_budget": "לתקציב",
        "confirm_suppliers": "אישור ספקים",
    },
}


DISPLAY_TRANSLATIONS = {
    "he": {
        "status": {
            "Not started": "עוד לא התחיל",
            "In progress": "בתהליך",
            "Booked": "נסגר",
            "Not relevant": "לא רלוונטי",
            "Considering": "בבדיקה",
            "Contacted": "יצרנו קשר",
            "Meeting Scheduled": "נקבעה פגישה",
            "Rejected": "ירד מהפרק",
            "Scheduled": "נקבעה",
            "Completed": "הושלמה",
            "Cancelled": "בוטלה",
        },
        "role": {"Bride": "כלה", "Groom": "חתן", "Other": "אחר"},
        "group": {
            "Must-have suppliers": "ספקי חובה",
            "Important extras": "שדרוגים חשובים",
            "Personal preparation": "הכנות אישיות",
        },
        "category": {
            "Venue": "מקום לאירוע", "Catering": "קייטרינג", "Alcohol Bar": "בר אלכוהול",
            "Photographer": "צילום סטילס", "Videographer": "צילום וידאו", "DJ": "די-ג׳יי",
            "Flowers": "עיצוב ופרחים", "Wedding Dress": "שמלת כלה", "Groom Suit": "חליפת חתן",
            "Hair Stylist": "עיצוב שיער", "Makeup Artist": "איפור", "Rings": "טבעות",
            "Invitations": "הזמנות", "Rabbi/Officiant": "רב / עורך טקס",
            "Transportation": "הסעות", "Wedding Planner": "מפיק / מנהל אירוע",
            "Cake/Desserts": "עוגה וקינוחים",
        },
        "venue_type": {
            "Garden": "גן אירועים", "Hall": "אולם", "Beach": "חוף", "Loft": "לופט",
            "Vineyard": "יקב", "Rooftop": "גג",
        },
    },
}


SUPPLIER_DISPLAY = {
    "he": {
        "venue": ("אולם / גן אירועים", "המקום עצמו: זמינות תאריכים, קיבולת, חניה, נגישות ומה כלול."),
        "catering": ("קייטרינג / אוכל", "תפריט, טעימות, מנות צמחוניות/טבעוניות, ילדים ונשנושים לשעות המאוחרות."),
        "bar": ("בר / אלכוהול", "בר בסיסי או פרימיום, קוקטיילים, יין, בירה, שתייה קלה ועמדת קפה."),
        "photographer": ("צלם סטילס", "צילום הזוג, המשפחה, הטקס, המסיבה וכל הפרטים הקטנים."),
        "videographer": ("צלם וידאו", "סרט מלא, היילייטס, צילום טקס ורחפן אם רלוונטי."),
        "dj": ("די-ג׳יי / מוזיקה", "מוזיקה לקבלת פנים, חופה ורחבה, מיקרופונים וגיבוי טכני."),
        "florist": ("מעצב/ת אירוע ופרחים", "עיצוב חופה, מרכזי שולחן, כניסה, זר כלה וקישוטים משלימים."),
        "bride_dress": ("שמלת כלה", "שמלה, נעליים, אקססוריז ולוק שני אם רוצים."),
        "groom_suit": ("חליפת חתן", "חליפה, נעליים, עניבה או פפיון, חפתים ואקססוריז."),
        "hair_stylist": ("עיצוב שיער", "בדרך כלל לכלה, ולעיתים גם למשפחה או מלוות."),
        "makeup": ("מאפר/ת", "איפור כלה, ניסיון, ערכת טאצ׳-אפ ואיפור למשפחה אם צריך."),
        "rings": ("טבעות נישואין", "טבעות, חריטה, התאמת מידה ולוח זמנים לקבלה."),
        "invitations": ("הזמנות / הזמנות דיגיטליות", "Save the date, הזמנה רשמית, RSVP ואישורי הגעה."),
        "officiant": ("רב / עורך טקס", "מסמכים, תיאום הטקס והובלת החופה או הטקס האישי."),
        "transportation": ("הסעות", "רכב לזוג, שאטלים לאורחים, מוניות וסידורי חניה."),
        "planner": ("מפיק/ת או מנהל/ת אירוע", "תיאום ספקים, לו״ז, תשלומים וטיפול בבעיות ביום האירוע."),
        "seating_system": ("מערכת הושבה", "ניהול רשימת אורחים, שולחנות, RSVP ואישורי הגעה."),
        "attractions": ("אטרקציות לאורחים", "מגנטים, תא צילום, צייר לייב, עשן, קונפטי וזוהרים."),
        "lighting": ("תאורה וסאונד", "תאורת במה, רחבה, מסכים, מקרנים ואפקטים מיוחדים."),
        "cake": ("עוגה / שולחן קינוחים", "עוגת חתונה, מתוקים מותאמים ונשנושים מאוחרים."),
        "accommodation": ("לינה", "חדרים לזוג, משפחה או אורחים שמגיעים מרחוק."),
        "guest_gifts": ("מתנות לאורחים", "מזכרות קטנות, פריטים ממותגים, נרות ומתנות אישיות."),
        "kids_entertainment": ("הפעלות לילדים", "בייביסיטר, שולחן ילדים, משחקים ופינת פעילות."),
        "security": ("אבטחה / עזרה ראשונה", "בהתאם לגודל המקום והדרישות."),
        "cleaning": ("ניקיון / שירותים", "בדרך כלל דרך המקום, אבל חשוב לוודא מראש."),
        "after_party": ("אפטר פארטי", "בר נפרד, מועדון, אוכל, הסעות והארכת מוזיקה."),
        "nails": ("ציפורניים", "מניקור, פדיקור ובחירת צבע ניסיון."),
        "spa": ("ספא / טיפוח עור", "טיפול פנים, שעווה, לייזר, שיזוף או עיסוי."),
        "fitness": ("כושר / תזונה", "תוכנית הכנה אופציונלית לפני החתונה."),
        "tailor": ("תופר/ת / תיקונים", "תיקוני שמלה וחליפה סמוך לתאריך."),
        "jewelry": ("תכשיטים ואקססוריז", "עגילים, שרשרת, חפתים ואביזרי שיער."),
        "grooming": ("טיפוח חתן / ספר", "תספורת, זקן, טיפוח עור ופגישת הכנה."),
    },
}


CITY_DISPLAY_HE = {
    "Acre": "עכו", "Akko": "עכו", "Afula": "עפולה", "Arad": "ערד", "Ariel": "אריאל",
    "Ashdod": "אשדוד", "Ashkelon": "אשקלון", "Bat Yam": "בת ים", "Beer Sheva": "באר שבע",
    "Beit Shean": "בית שאן", "Beit Shemesh": "בית שמש", "Bnei Brak": "בני ברק",
    "Dimona": "דימונה", "Eilat": "אילת", "Gedera": "גדרה", "Givatayim": "גבעתיים",
    "Hadera": "חדרה", "Haifa": "חיפה", "Herzliya": "הרצליה", "Hod HaSharon": "הוד השרון",
    "Holon": "חולון", "Jerusalem": "ירושלים", "Kfar Saba": "כפר סבא", "Kiryat Ata": "קריית אתא",
    "Kiryat Bialik": "קריית ביאליק", "Kiryat Gat": "קריית גת", "Kiryat Malachi": "קריית מלאכי",
    "Kiryat Motzkin": "קריית מוצקין", "Kiryat Ono": "קריית אונו", "Kiryat Shmona": "קריית שמונה",
    "Kiryat Yam": "קריית ים", "Lod": "לוד", "Ma'alot-Tarshiha": "מעלות תרשיחא",
    "Mitzpe Ramon": "מצפה רמון", "Modi'in": "מודיעין", "Modiin": "מודיעין",
    "Nahariya": "נהריה", "Nazareth": "נצרת", "Nes Ziona": "נס ציונה", "Nesher": "נשר",
    "Netanya": "נתניה", "Netivot": "נתיבות", "Or Akiva": "אור עקיבא", "Or Yehuda": "אור יהודה",
    "Petah Tikva": "פתח תקווה", "Ra'anana": "רעננה", "Ramat Gan": "רמת גן",
    "Ramat HaSharon": "רמת השרון", "Ramla": "רמלה", "Rehovot": "רחובות",
    "Rishon LeZion": "ראשון לציון", "Rosh HaAyin": "ראש העין", "Safed": "צפת",
    "Sderot": "שדרות", "Tel Aviv": "תל אביב", "Tiberias": "טבריה", "Tirat Carmel": "טירת כרמל",
    "Yavne": "יבנה", "Yehud": "יהוד", "Yokneam": "יקנעם",
}


CITY_COORDS = {
    "Acre": (32.9281, 35.0827), "Akko": (32.9281, 35.0827),
    "Afula": (32.6091, 35.2892), "Arad": (31.2588, 35.2128),
    "Ariel": (32.1065, 35.1845), "Ashdod": (31.8044, 34.6553),
    "Ashkelon": (31.6688, 34.5743), "Bat Yam": (32.0167, 34.7500),
    "Beer Sheva": (31.2529, 34.7915), "Beit Shean": (32.4973, 35.4963),
    "Beit Shemesh": (31.7514, 34.9885), "Bnei Brak": (32.0807, 34.8338),
    "Dimona": (31.0708, 35.0327), "Eilat": (29.5577, 34.9519),
    "Gedera": (31.8146, 34.7796), "Givatayim": (32.0723, 34.8125),
    "Hadera": (32.4340, 34.9196), "Haifa": (32.7940, 34.9896),
    "Herzliya": (32.1624, 34.8447), "Hod HaSharon": (32.1508, 34.8883),
    "Holon": (32.0158, 34.7874), "Jerusalem": (31.7683, 35.2137),
    "Kfar Saba": (32.1782, 34.9076), "Kiryat Ata": (32.8072, 35.1050),
    "Kiryat Bialik": (32.8321, 35.0877), "Kiryat Gat": (31.6090, 34.7642),
    "Kiryat Malachi": (31.7300, 34.7460), "Kiryat Motzkin": (32.8371, 35.0776),
    "Kiryat Ono": (32.0646, 34.8554), "Kiryat Shmona": (33.2073, 35.5721),
    "Kiryat Yam": (32.8497, 35.0696), "Lod": (31.9510, 34.8881),
    "Ma'alot-Tarshiha": (33.0167, 35.2667), "Mitzpe Ramon": (30.6094, 34.8011),
    "Modi'in": (31.8980, 35.0104), "Modiin": (31.8980, 35.0104),
    "Nahariya": (33.0059, 35.0941), "Nazareth": (32.6996, 35.3035),
    "Nes Ziona": (31.9293, 34.7987), "Nesher": (32.7650, 35.0500),
    "Netanya": (32.3215, 34.8532), "Netivot": (31.4230, 34.5891),
    "Or Akiva": (32.5067, 34.9206), "Or Yehuda": (32.0311, 34.8458),
    "Petah Tikva": (32.0840, 34.8878), "Ra'anana": (32.1848, 34.8713),
    "Ramat Gan": (32.0684, 34.8248), "Ramat HaSharon": (32.1461, 34.8394),
    "Ramla": (31.9279, 34.8623), "Rehovot": (31.8948, 34.8113),
    "Rishon LeZion": (31.9730, 34.7925), "Rosh HaAyin": (32.0956, 34.9566),
    "Safed": (32.9646, 35.4960), "Sderot": (31.5250, 34.5969),
    "Tel Aviv": (32.0853, 34.7818), "Tiberias": (32.7959, 35.5309),
    "Tirat Carmel": (32.7617, 34.9719), "Yavne": (31.8781, 34.7394),
    "Yehud": (32.0332, 34.8891), "Yokneam": (32.6599, 35.1107),
}

CITY_OPTIONS = [
    "Acre", "Afula", "Arad", "Ariel", "Ashdod", "Ashkelon", "Bat Yam", "Beer Sheva",
    "Beit Shean", "Beit Shemesh", "Bnei Brak", "Dimona", "Eilat", "Gedera", "Givatayim",
    "Hadera", "Haifa", "Herzliya", "Hod HaSharon", "Holon", "Jerusalem", "Kfar Saba",
    "Kiryat Ata", "Kiryat Bialik", "Kiryat Gat", "Kiryat Malachi", "Kiryat Motzkin",
    "Kiryat Ono", "Kiryat Shmona", "Kiryat Yam", "Lod", "Ma'alot-Tarshiha",
    "Mitzpe Ramon", "Modi'in", "Nahariya", "Nazareth", "Nes Ziona", "Nesher",
    "Netanya", "Netivot", "Or Akiva", "Or Yehuda", "Petah Tikva", "Ra'anana",
    "Ramat Gan", "Ramat HaSharon", "Ramla", "Rehovot", "Rishon LeZion", "Rosh HaAyin",
    "Safed", "Sderot", "Tel Aviv", "Tiberias", "Tirat Carmel", "Yavne", "Yehud", "Yokneam",
]


def _language_for(user):
    return DEFAULT_LANGUAGE


def _t(lang, key):
    return TRANSLATIONS[DEFAULT_LANGUAGE].get(key, key)


def _display(lang, kind, value):
    if value is None:
        return ""
    return DISPLAY_TRANSLATIONS[DEFAULT_LANGUAGE].get(kind, {}).get(value, value)


def _supplier_text(lang, supplier, field="name"):
    if not supplier:
        return ""
    if lang == "he":
        item = SUPPLIER_DISPLAY["he"].get(supplier.get("code"))
        if item:
            return item[0] if field == "name" else item[1]
    return supplier.get(field, "")


def _city_label(lang, city):
    if not city:
        return ""
    return CITY_DISPLAY_HE.get(city, city)


def _date_label(lang, value):
    if not value:
        return ""
    try:
        dt = datetime.strptime(str(value)[:10], "%Y-%m-%d")
        return dt.strftime("%d.%m.%Y")
    except (ValueError, TypeError):
        return value


def _city_distance_km(a, b):
    if not a or not b:
        return None
    ca = CITY_COORDS.get(str(a).strip())
    cb = CITY_COORDS.get(str(b).strip())
    if not ca or not cb:
        return None
    lat1, lon1 = map(math.radians, ca)
    lat2, lon2 = map(math.radians, cb)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return round(6371 * 2 * math.atan2(math.sqrt(h), math.sqrt(1 - h)), 1)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        lang = _language_for(current_user())
        if "user_id" not in session:
            flash(_t(lang, "login_required"), "error")
            return redirect(url_for("index"))
        # Guard against stale sessions (e.g. after a DB re-seed)
        if not query("SELECT 1 FROM users WHERE user_id = ?", (session["user_id"],), one=True):
            session.clear()
            flash(_t(lang, "session_expired"), "error")
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
    user = current_user()
    lang = _language_for(user)
    w = current_wedding()
    liked_count = 0
    if w:
        row = query(
            "SELECT COUNT(*) AS cnt FROM favorite_vendors WHERE wedding_id=?",
            (w["wedding_id"],), one=True,
        )
        liked_count = row["cnt"] if row else 0
    return {
        "user": user,
        "wedding": w,
        "now": datetime.utcnow(),
        "liked_count": liked_count,
        "lang": lang,
        "text_dir": "rtl" if lang == "he" else "ltr",
        "t": lambda key: _t(lang, key),
        "td": lambda kind, value: _display(lang, kind, value),
        "supplier_label": lambda supplier, field="name": _supplier_text(lang, supplier, field),
        "city_label": lambda city: _city_label(lang, city),
        "date_label": lambda value: _date_label(lang, value),
        "city_options": CITY_OPTIONS,
    }


# ---------------------------------------------------------------------------
# Welcome / Auth (combined landing)
# ---------------------------------------------------------------------------

@app.route("/", methods=["GET", "POST"])
def index():
    """Combined login + register welcome screen."""
    if "user_id" in session and request.method == "GET":
        return redirect(url_for("home"))

    mode = request.args.get("mode", "login")  # 'login' or 'register'

    if request.method == "POST":
        action = request.form.get("action", "login")

        if action == "register":
            lang = _language_for(None)
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
                flash(_t(lang, "missing_register_fields"), "error")
                return redirect(url_for("index", mode="register"))

            if role in ("Bride", "Groom") and not (partner_name and partner_email and partner_phone):
                flash(_t(lang, "missing_partner_fields"), "error")
                return redirect(url_for("index", mode="register"))

            if query("SELECT user_id FROM users WHERE email = ?", (email,), one=True):
                flash(_t(lang, "email_registered"), "error")
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
            session["language"] = DEFAULT_LANGUAGE
            flash(_t(DEFAULT_LANGUAGE, "welcome_setup"), "success")
            return redirect(url_for("onboarding"))

        # login
        lang = _language_for(None)
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = query("SELECT * FROM users WHERE email = ?", (email,), one=True)
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["user_id"]
            flash(_t(_language_for(user), "welcome_back_name").format(name=user["full_name"].split()[0]), "success")
            return redirect(url_for("home"))
        flash(_t(lang, "invalid_login"), "error")
        return redirect(url_for("index", mode="login"))

    return render_template(
        "index.html",
        mode=mode,
        oauth_google_enabled=_oauth_is_configured("google"),
        oauth_facebook_enabled=_oauth_is_configured("facebook"),
    )


# Aliases so old links keep working
@app.route("/login")
def login():
    return redirect(url_for("index", mode="login"))


@app.route("/register")
def register():
    return redirect(url_for("index", mode="register"))


@app.route("/logout")
def logout():
    lang = _language_for(current_user())
    session.clear()
    flash(_t(lang, "logged_out"), "success")
    return redirect(url_for("index"))


# ---------------------------------------------------------------------------
# Social / OAuth sign-in
# ---------------------------------------------------------------------------

_OAUTH_PROVIDERS = {"google", "facebook"}


def _oauth_is_configured(provider):
    if provider == "google":
        if not (GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET):
            return False
    elif provider == "facebook":
        if not (FACEBOOK_CLIENT_ID and FACEBOOK_CLIENT_SECRET):
            return False
    else:
        return False
    return oauth.create_client(provider) is not None


def _oauth_redirect_uri(provider):
    callback_path = url_for("auth_callback", provider=provider)
    if VOWLY_PUBLIC_BASE_URL:
        return f"{VOWLY_PUBLIC_BASE_URL}{callback_path}"
    return url_for("auth_callback", provider=provider, _external=True)


@app.route("/auth/<provider>")
def auth_provider(provider):
    lang = _language_for(None)
    if provider not in _OAUTH_PROVIDERS or not _oauth_is_configured(provider):
        flash(_t(lang, "oauth_not_configured"), "error")
        return redirect(url_for("index"))
    try:
        client = oauth.create_client(provider)
    except Exception:
        flash(_t(lang, "oauth_not_configured"), "error")
        return redirect(url_for("index"))
    if client is None:
        flash(_t(lang, "oauth_not_configured"), "error")
        return redirect(url_for("index"))
    redirect_uri = _oauth_redirect_uri(provider)
    try:
        return client.authorize_redirect(redirect_uri)
    except Exception:
        app.logger.exception("OAuth authorize redirect failed for provider '%s'", provider)
        flash(_t(lang, "oauth_failed"), "error")
        return redirect(url_for("index"))


@app.route("/auth/<provider>/callback")
def auth_callback(provider):
    lang = _language_for(None)
    if provider not in _OAUTH_PROVIDERS or not _oauth_is_configured(provider):
        flash(_t(lang, "oauth_not_configured"), "error")
        return redirect(url_for("index"))
    try:
        client = oauth.create_client(provider)
        if client is None:
            flash(_t(lang, "oauth_not_configured"), "error")
            return redirect(url_for("index"))
        token  = client.authorize_access_token()
    except Exception:
        app.logger.exception("OAuth callback failed for provider '%s'", provider)
        flash(_t(lang, "oauth_failed"), "error")
        return redirect(url_for("index"))

    if provider == "google":
        info  = token.get("userinfo") or client.userinfo(token=token)
        email = (info.get("email") or "").strip().lower()
        name  = info.get("name") or email
    else:  # facebook
        resp  = client.get("me?fields=id,name,email", token=token)
        data  = resp.json()
        email = (data.get("email") or "").strip().lower()
        name  = data.get("name") or email

    if not email:
        flash(_t(lang, "oauth_no_email"), "error")
        return redirect(url_for("index"))

    user = query("SELECT * FROM users WHERE email = ?", (email,), one=True)
    if user:
        session["user_id"] = user["user_id"]
        flash(_t(_language_for(user), "welcome_back_name").format(
            name=user["full_name"].split()[0]), "success")
        return redirect(url_for("home"))

    # New user — create account and go to onboarding
    uid = execute(
        "INSERT INTO users (full_name, email, password_hash) VALUES (?, ?, ?)",
        (name, email, ""),
    )
    session["user_id"] = uid
    session["language"] = DEFAULT_LANGUAGE
    flash(_t(DEFAULT_LANGUAGE, "welcome_setup"), "success")
    return redirect(url_for("onboarding"))


@app.route("/profile")
@login_required
def profile():
    return redirect(url_for("settings"))


@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    user = current_user()
    lang = _language_for(user)
    if request.method == "POST":
        distance = request.form.get("distance_km", type=int) or 50
        distance = max(5, min(distance, 300))
        execute(
            "UPDATE users SET language=?, distance_km=? WHERE user_id=?",
            (DEFAULT_LANGUAGE, distance, session["user_id"]),
        )
        session["language"] = DEFAULT_LANGUAGE
        flash(_t(lang, "settings_saved"), "success")
        return redirect(url_for("settings"))
    distance_km = user["distance_km"] if user and "distance_km" in user.keys() and user["distance_km"] else 50
    return render_template("settings.html", distance_km=distance_km)


# ---------------------------------------------------------------------------
# Wedding profile
# ---------------------------------------------------------------------------

@app.route("/wedding-profile", methods=["GET", "POST"])
@login_required
def wedding_profile():
    lang = _language_for(current_user())
    w = current_wedding()
    if request.method == "POST":
        partner        = request.form.get("partner_name", "").strip()
        wdate          = request.form.get("wedding_date", "").strip() or None
        guests         = request.form.get("estimated_guests", "").strip() or None
        budget         = request.form.get("budget", "").strip() or None
        city           = request.form.get("city", "").strip()
        venue_pref     = request.form.get("venue_type_preference", "").strip()
        price_per_guest = request.form.get("price_per_guest", "").strip() or None
        ceremony_route = request.form.get("ceremony_route", "").strip() or None
        if w:
            execute(
                """UPDATE wedding_profiles
                   SET partner_name=?, wedding_date=?, estimated_guests=?, budget=?,
                       city=?, venue_type_preference=?, price_per_guest=?, ceremony_route=?
                   WHERE wedding_id=?""",
                (partner, wdate, guests, budget, city, venue_pref,
                 price_per_guest, ceremony_route, w["wedding_id"]),
            )
            flash(_t(lang, "profile_updated"), "success")
        else:
            execute(
                """INSERT INTO wedding_profiles
                   (user_id, partner_name, wedding_date, estimated_guests, budget,
                    city, venue_type_preference, price_per_guest, ceremony_route)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (session["user_id"], partner, wdate, guests, budget, city, venue_pref,
                 price_per_guest, ceremony_route),
            )
            flash(_t(lang, "profile_created"), "success")
        return redirect(url_for("home"))
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
    supplier is set to 'In progress'. Then we redirect to Home.
    """
    user = current_user()
    role = (user["role"] if user else None) or ""
    suppliers = visible_suppliers_for_role(role)

    if request.method == "POST":
        w = _ensure_wedding()

        # Step 1 — wedding basics (all optional; only overwrite what was given)
        wdate  = request.form.get("wedding_date", "").strip() or None
        city   = request.form.get("city", "").strip() or None
        guests = request.form.get("estimated_guests", "").strip() or None
        budget = request.form.get("budget", "").strip() or None
        if wdate or city or guests or budget:
            execute(
                """UPDATE wedding_profiles
                      SET wedding_date     = COALESCE(?, wedding_date),
                          city             = COALESCE(?, city),
                          estimated_guests = COALESCE(?, estimated_guests),
                          budget           = COALESCE(?, budget)
                    WHERE wedding_id = ?""",
                (wdate, city, guests, budget, w["wedding_id"]),
            )

        # Step 2 — suppliers to start with
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
            flash(_t(_language_for(user), "picked_suppliers").format(count=len(picked)), "success")
        return redirect(url_for("home"))

    grouped = group_by_category(suppliers)
    state   = _supplier_state_map(current_wedding()["wedding_id"]) if current_wedding() else {}
    return render_template(
        "onboarding.html",
        grouped_suppliers=grouped,
        state=state,
        role=role,
        w=current_wedding(),
    )


def _planning_context(user, w):
    """Compute the supplier checklist + progress data shared by Home and Plan."""
    role = (user["role"] if user else None) or ""

    suppliers = visible_suppliers_for_role(role)
    state     = _supplier_state_map(w["wedding_id"])
    decorated = _decorate_suppliers(suppliers, state)
    grouped   = group_by_category(decorated)

    # Map supplier code -> vendor_categories.category_id (for the Discover link)
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

    # Top "next up" suggestions: not started, ordered by group importance
    group_weight = {g: i for i, g in enumerate(GROUPS)}
    next_up = sorted(
        [s for s in decorated if s["status"] == "Not started"],
        key=lambda s: (group_weight.get(s["category"], 99), s["name"]),
    )[:4]

    partner_name = (w["partner_name"] if w and "partner_name" in w.keys() else None) \
                   or (user["partner_name"] if user else None)

    return {
        "grouped": grouped,
        "category_progress": category_progress,
        "overall": overall,
        "role": role,
        "code_to_category_id": code_to_category_id,
        "days_until_wedding": days_until_wedding,
        "wedding_date_display": wedding_date_display,
        "next_up": next_up,
        "partner_name": partner_name,
    }


def _next_best_action(user, w, decorated, days_until_wedding):
    """Return the single highest-priority next action dict, or None if all done."""
    lang = _language_for(user)
    wedding_id = w["wedding_id"] if w else None

    # 1. No wedding date
    if days_until_wedding is None:
        return {"title": _t(lang, "nba_set_date"), "subtitle": _t(lang, "nba_set_date_sub"),
                "cta_label": _t(lang, "add_wedding_date"), "route": url_for("wedding_profile"),
                "phase": "basics", "level": 1}

    # 11. Wedding day
    if days_until_wedding == 0:
        return {"title": _t(lang, "nba_wedding_day"), "subtitle": _t(lang, "nba_wedding_day_sub"),
                "cta_label": _t(lang, "see_plan"), "route": url_for("plan"),
                "phase": "wedding_day", "level": 11}

    # 2. No guest count
    if not (w and w["estimated_guests"]):
        return {"title": _t(lang, "nba_set_guests"), "subtitle": _t(lang, "nba_set_guests_sub"),
                "cta_label": _t(lang, "edit"), "route": url_for("wedding_profile"),
                "phase": "basics", "level": 2}

    # 3. No budget
    if not (w and w["budget"]):
        return {"title": _t(lang, "nba_set_budget"), "subtitle": _t(lang, "nba_set_budget_sub"),
                "cta_label": _t(lang, "edit"), "route": url_for("wedding_profile"),
                "phase": "basics", "level": 3}

    # Venue status
    venue_sup = next((s for s in decorated if s["code"] == "venue"), None)
    venue_booked = venue_sup and venue_sup["status"] == "Booked"
    venue_started = venue_sup and venue_sup["status"] in ("In progress", "Booked")

    # 4. No venue started
    if not venue_started:
        venue_cat = query("SELECT category_id FROM vendor_categories WHERE category_name='Venue'", one=True)
        route = url_for("discover", category_id=venue_cat["category_id"]) if venue_cat else url_for("discover")
        return {"title": _t(lang, "nba_find_venue"), "subtitle": _t(lang, "nba_find_venue_sub"),
                "cta_label": _t(lang, "start_swiping"), "route": route,
                "phase": "venue", "level": 4}

    # 5. Venue booked, find highest-priority missing core vendor
    if venue_booked:
        core_priority = ["photographer", "videographer", "dj", "makeup", "hair_stylist",
                         "bride_dress", "groom_suit", "florist"]
        for code in core_priority:
            sup = next((s for s in decorated if s["code"] == code), None)
            if sup and sup["status"] == "Not started":
                cat_name = SUPPLIER_TO_VENDOR_CATEGORY.get(code)
                cat_row = query("SELECT category_id FROM vendor_categories WHERE category_name=?",
                                (cat_name,), one=True) if cat_name else None
                route = url_for("discover", category_id=cat_row["category_id"]) if cat_row else url_for("discover")
                sup_label = _supplier_text(lang, sup, "name")
                return {"title": _t(lang, "nba_core_vendor").format(name=sup_label),
                        "subtitle": _t(lang, "nba_core_vendor_sub").format(name=sup_label),
                        "cta_label": _t(lang, "start_swiping"), "route": route,
                        "phase": "core_vendors", "level": 5}

    # 6. Ceremony route unknown
    ceremony_route = w["ceremony_route"] if w and "ceremony_route" in w.keys() else None
    if not ceremony_route:
        return {"title": _t(lang, "nba_ceremony_route"), "subtitle": _t(lang, "nba_ceremony_route_sub"),
                "cta_label": _t(lang, "edit"), "route": url_for("wedding_profile"),
                "phase": "ceremony", "level": 6}

    # 7. Rabbinate and no legal tasks started
    if ceremony_route == "rabbinate":
        rabbinate_items = query(
            "SELECT COUNT(*) AS c FROM checklist_items WHERE wedding_id=?", (wedding_id,), one=True
        )
        if not rabbinate_items or rabbinate_items["c"] == 0:
            return {"title": _t(lang, "nba_rabbinate_docs"), "subtitle": _t(lang, "nba_rabbinate_docs_sub"),
                    "cta_label": _t(lang, "plan"), "route": url_for("plan"),
                    "phase": "ceremony", "level": 7}

    # 8. Guest list empty
    guest_count_row = query("SELECT COUNT(*) AS c FROM guests WHERE wedding_id=?", (wedding_id,), one=True)
    guest_count = guest_count_row["c"] if guest_count_row else 0
    if guest_count == 0:
        return {"title": _t(lang, "nba_guest_list"), "subtitle": _t(lang, "nba_guest_list_sub"),
                "cta_label": _t(lang, "add_guest"), "route": url_for("guests"),
                "phase": "guests", "level": 8}

    # 9. RSVP follow-up (if within 90 days and many unanswered)
    if days_until_wedding <= 90:
        unanswered = query(
            "SELECT COUNT(*) AS c FROM guests WHERE wedding_id=? AND rsvp_status IN ('unknown','invited','needs_follow_up')",
            (wedding_id,), one=True
        )
        unanswered_count = unanswered["c"] if unanswered else 0
        if unanswered_count > 5:
            return {"title": _t(lang, "nba_rsvp_followup"),
                    "subtitle": _t(lang, "nba_rsvp_followup_sub").format(count=unanswered_count),
                    "cta_label": _t(lang, "see_guests"), "route": url_for("guests"),
                    "phase": "guests", "level": 9}

    # 10. Wedding month (≤ 30 days)
    if days_until_wedding <= 30:
        return {"title": _t(lang, "nba_wedding_month").format(days=days_until_wedding),
                "subtitle": _t(lang, "nba_wedding_month_sub"),
                "cta_label": _t(lang, "see_plan"), "route": url_for("plan"),
                "phase": "wedding_month", "level": 10}

    return None


@app.route("/home")
@login_required
def home():
    """Dashboard: countdown, progress, next actions, recent likes."""
    user = current_user()
    w = _ensure_wedding()
    ctx = _planning_context(user, w)

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
            LIMIT 12""",
        (w["wedding_id"],),
    )
    next_appointment = query(
        """SELECT a.*, v.business_name FROM appointments a
           JOIN vendors v ON v.vendor_id = a.vendor_id
          WHERE a.wedding_id = ? AND a.status = 'Scheduled'
            AND date(a.appointment_date) >= date('now')
          ORDER BY a.appointment_date LIMIT 1""",
        (w["wedding_id"],), one=True,
    )
    appt_row = query(
        """SELECT COUNT(*) AS c FROM appointments
            WHERE wedding_id = ? AND status = 'Scheduled'
              AND date(appointment_date) >= date('now')""",
        (w["wedding_id"],), one=True,
    )
    appt_count = appt_row["c"] if appt_row else 0

    # Flatten the decorated checklist once so the dashboard can look suppliers
    # up by code (timeline, vendor tiles) and surface the most actionable ones.
    flat = [s for items in ctx["grouped"].values() for s in items]
    sup_by_code = {s["code"]: s for s in flat}
    status_rank = {"In progress": 0, "Not started": 1}
    upcoming_tasks = sorted(
        [s for s in flat if s["status"] in status_rank],
        key=lambda s: (status_rank[s["status"]], s["name"]),
    )[:5]

    # Guest stats
    guest_stats = query(
        """SELECT COUNT(*) AS total,
                  SUM(CASE WHEN rsvp_status='coming' THEN 1 ELSE 0 END) AS coming,
                  SUM(CASE WHEN rsvp_status IN ('unknown','invited','needs_follow_up') THEN 1 ELSE 0 END) AS unanswered
             FROM guests WHERE wedding_id=?""",
        (w["wedding_id"],), one=True
    )

    # Budget stats
    budget_stats = query(
        """SELECT SUM(estimated_amount) AS estimated,
                  SUM(actual_amount) AS actual,
                  SUM(paid_amount) AS paid
             FROM wedding_budget WHERE wedding_id=?""",
        (w["wedding_id"],), one=True
    )

    # Wedding month mode
    wedding_month_mode = ctx["days_until_wedding"] is not None and ctx["days_until_wedding"] <= 30

    # NBA
    nba = _next_best_action(user, w, flat, ctx["days_until_wedding"])

    return render_template(
        "home.html",
        liked_vendors=liked_vendors,
        next_appointment=next_appointment,
        appt_count=appt_count,
        sup_by_code=sup_by_code,
        upcoming_tasks=upcoming_tasks,
        guest_stats=guest_stats,
        budget_stats=budget_stats,
        wedding_month_mode=wedding_month_mode,
        nba=nba,
        **ctx,
    )


@app.route("/plan")
@login_required
def plan():
    """Full supplier checklist, grouped and filterable."""
    user = current_user()
    w = _ensure_wedding()
    ctx = _planning_context(user, w)
    return render_template("plan.html", statuses=STATUSES, groups=GROUPS, **ctx)


# ---------------------------------------------------------------------------
# Guests
# ---------------------------------------------------------------------------

@app.route("/guests", methods=["GET", "POST"])
@login_required
def guests():
    lang = _language_for(current_user())
    w = _ensure_wedding()
    if request.method == "POST":
        full_name  = request.form.get("full_name", "").strip()
        phone      = request.form.get("phone", "").strip()
        side       = request.form.get("side", "").strip()
        group_name = request.form.get("group_name", "").strip()
        rsvp       = request.form.get("rsvp_status", "unknown")
        meal_notes = request.form.get("meal_notes", "").strip()
        table_num  = request.form.get("table_number", "").strip()
        notes      = request.form.get("notes", "").strip()
        if not full_name:
            flash(_t(lang, "missing_register_fields"), "error")
            return redirect(url_for("guests"))
        execute(
            """INSERT INTO guests (wedding_id, full_name, phone, side, group_name,
               rsvp_status, meal_notes, table_number, notes)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (w["wedding_id"], full_name, phone or None, side or None, group_name or None,
             rsvp, meal_notes or None, table_num or None, notes or None),
        )
        flash(_t(lang, "guest_added"), "success")
        return redirect(url_for("guests"))
    rows = query(
        "SELECT * FROM guests WHERE wedding_id=? ORDER BY side, full_name",
        (w["wedding_id"],),
    )
    stats = query(
        """SELECT COUNT(*) AS total,
                  SUM(CASE WHEN rsvp_status='coming' THEN 1 ELSE 0 END) AS coming,
                  SUM(CASE WHEN rsvp_status='not_coming' THEN 1 ELSE 0 END) AS not_coming,
                  SUM(CASE WHEN rsvp_status IN ('unknown','invited','needs_follow_up') THEN 1 ELSE 0 END) AS unanswered
             FROM guests WHERE wedding_id=?""",
        (w["wedding_id"],), one=True
    )
    return render_template("guests.html", rows=rows, stats=stats)


@app.route("/guests/<int:gid>/update", methods=["POST"])
@login_required
def guests_update(gid):
    lang = _language_for(current_user())
    w = current_wedding()
    rsvp = request.form.get("rsvp_status", "unknown")
    table_num = request.form.get("table_number", "").strip() or None
    meal_notes = request.form.get("meal_notes", "").strip() or None
    invitation_sent = 1 if request.form.get("invitation_sent") else 0
    execute(
        "UPDATE guests SET rsvp_status=?, table_number=?, meal_notes=?, invitation_sent=? WHERE guest_id=? AND wedding_id=?",
        (rsvp, table_num, meal_notes, invitation_sent, gid, w["wedding_id"] if w else 0),
    )
    flash(_t(lang, "guest_updated"), "success")
    return redirect(url_for("guests"))


@app.route("/guests/<int:gid>/delete", methods=["POST"])
@login_required
def guests_delete(gid):
    lang = _language_for(current_user())
    w = current_wedding()
    execute("DELETE FROM guests WHERE guest_id=? AND wedding_id=?",
            (gid, w["wedding_id"] if w else 0))
    flash(_t(lang, "guest_deleted"), "success")
    return redirect(url_for("guests"))


# ---------------------------------------------------------------------------
# Budget
# ---------------------------------------------------------------------------

BUDGET_CATEGORIES = [
    "Venue / food", "DJ", "Photography", "Dress", "Suit", "Makeup and hair",
    "Rings", "Rabbi / ceremony", "Design / flowers", "Invitations",
    "Alcohol upgrades", "Extras / surprises", "Honeymoon", "Emergency buffer",
]

BUDGET_CATEGORIES_HE = [
    "אולם / אוכל", "די-ג׳יי", "צילום", "שמלה", "חליפה", "איפור ושיער",
    "טבעות", "רב / טקס", "עיצוב ופרחים", "הזמנות",
    "שדרוגי אלכוהול", "אקסטרות / הפתעות", "ירח דבש", "חיץ חירום",
]


@app.route("/budget", methods=["GET", "POST"])
@login_required
def budget():
    user = current_user()
    lang = _language_for(user)
    w = _ensure_wedding()
    if request.method == "POST":
        action = request.form.get("action", "add")
        if action == "update_price_per_guest":
            ppg = request.form.get("price_per_guest", "").strip()
            try:
                ppg_val = float(ppg) if ppg else None
            except ValueError:
                ppg_val = None
            execute("UPDATE wedding_profiles SET price_per_guest=? WHERE wedding_id=?",
                    (ppg_val, w["wedding_id"]))
            flash(_t(lang, "settings_saved"), "success")
            return redirect(url_for("budget"))
        # add budget item
        cat_label = request.form.get("category_label", "").strip()
        est = request.form.get("estimated_amount", "").strip()
        actual = request.form.get("actual_amount", "").strip()
        paid = request.form.get("paid_amount", "").strip()
        due = request.form.get("due_date", "").strip() or None
        pstatus = request.form.get("payment_status", "Not paid")
        notes = request.form.get("notes", "").strip() or None
        if not (cat_label and est):
            flash(_t(lang, "budget_required_fields"), "error")
            return redirect(url_for("budget"))
        try:
            est_val = float(est)
            actual_val = float(actual) if actual else 0
            paid_val = float(paid) if paid else 0
        except ValueError:
            flash(_t(lang, "budget_required_fields"), "error")
            return redirect(url_for("budget"))
        execute(
            """INSERT INTO wedding_budget (wedding_id, category_label, estimated_amount,
               actual_amount, paid_amount, due_date, payment_status, notes)
               VALUES (?,?,?,?,?,?,?,?)""",
            (w["wedding_id"], cat_label, est_val, actual_val, paid_val, due, pstatus, notes),
        )
        flash(_t(lang, "budget_item_added"), "success")
        return redirect(url_for("budget"))

    rows = query(
        "SELECT * FROM wedding_budget WHERE wedding_id=? ORDER BY created_at",
        (w["wedding_id"],)
    )
    totals = query(
        """SELECT SUM(estimated_amount) AS estimated,
                  SUM(actual_amount) AS actual,
                  SUM(paid_amount) AS paid
             FROM wedding_budget WHERE wedding_id=?""",
        (w["wedding_id"],), one=True
    )
    next_due = query(
        """SELECT * FROM wedding_budget WHERE wedding_id=? AND due_date IS NOT NULL
           AND payment_status != 'Paid in full'
           ORDER BY due_date LIMIT 1""",
        (w["wedding_id"],), one=True
    )
    cats = BUDGET_CATEGORIES_HE if lang == "he" else BUDGET_CATEGORIES
    return render_template("budget.html", rows=rows, totals=totals, next_due=next_due,
                           budget_categories=cats, w=w)


@app.route("/budget/<int:bid>/update", methods=["POST"])
@login_required
def budget_update(bid):
    lang = _language_for(current_user())
    w = current_wedding()
    actual = request.form.get("actual_amount", "0")
    paid = request.form.get("paid_amount", "0")
    pstatus = request.form.get("payment_status", "Not paid")
    due = request.form.get("due_date", "").strip() or None
    notes = request.form.get("notes", "").strip() or None
    try:
        actual_val = float(actual)
        paid_val = float(paid)
    except ValueError:
        actual_val = paid_val = 0
    execute(
        "UPDATE wedding_budget SET actual_amount=?, paid_amount=?, payment_status=?, due_date=?, notes=? WHERE budget_id=? AND wedding_id=?",
        (actual_val, paid_val, pstatus, due, notes, bid, w["wedding_id"] if w else 0),
    )
    flash(_t(lang, "budget_item_updated"), "success")
    return redirect(url_for("budget"))


@app.route("/budget/<int:bid>/delete", methods=["POST"])
@login_required
def budget_delete(bid):
    lang = _language_for(current_user())
    w = current_wedding()
    execute("DELETE FROM wedding_budget WHERE budget_id=? AND wedding_id=?",
            (bid, w["wedding_id"] if w else 0))
    flash(_t(lang, "budget_item_deleted"), "success")
    return redirect(url_for("budget"))


@app.route("/checklist")
@login_required
def checklist():
    return redirect(url_for("plan"))


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
    return redirect(url_for("home") + f"#sup-{code}")


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
    sql += " ORDER BY v.rating_average DESC, v.business_name LIMIT 120"

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
# Discover (swipe hub)
# ---------------------------------------------------------------------------

GOOGLE_PLACES_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
GOOGLE_PLACES_PHOTO_URL = "https://places.googleapis.com/v1/{photo_name}/media"
GOOGLE_PLACES_FIELD_MASK = ",".join([
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.internationalPhoneNumber",
    "places.websiteUri",
    "places.rating",
    "places.priceLevel",
    "places.photos",
])
GOOGLE_PRICE_MAP = {
    "PRICE_LEVEL_INEXPENSIVE": (3_000, 8_000),
    "PRICE_LEVEL_MODERATE": (8_000, 20_000),
    "PRICE_LEVEL_EXPENSIVE": (20_000, 50_000),
    "PRICE_LEVEL_VERY_EXPENSIVE": (50_000, 120_000),
}


def _slug_for_contact(value):
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower().replace("&", "and"))


def _google_place_name(place):
    display = place.get("displayName") or {}
    return (display.get("text") or "").strip()


def _google_city_from_address(address):
    for part in reversed([p.strip() for p in (address or "").split(",")]):
        if part and not part.lower().startswith("israel") and not part.startswith("ישראל"):
            return part
    return ""


def _google_place_photo_url(place):
    photos = place.get("photos") or []
    if not photos:
        return ""
    photo_name = photos[0].get("name", "")
    if not photo_name:
        return ""
    return (
        GOOGLE_PLACES_PHOTO_URL.format(photo_name=quote(photo_name, safe="/"))
        + f"?maxWidthPx=800&key={GOOGLE_PLACES_API_KEY}"
    )


def _google_price_range(place):
    return GOOGLE_PRICE_MAP.get(place.get("priceLevel"), (5_000, 15_000))


def _normalize_google_vendor(place, category_name, city_hint=""):
    name = _google_place_name(place)
    address = place.get("formattedAddress") or city_hint
    city = _google_city_from_address(address) or city_hint or "Israel"
    price_min, price_max = _google_price_range(place)
    slug = _slug_for_contact(name)
    return {
        "google_place_id": place.get("id", ""),
        "business_name": name,
        "category_name": category_name,
        "city": city,
        "address": address,
        "phone": place.get("internationalPhoneNumber") or "",
        "email": f"hello@{slug}.co.il" if slug else "",
        "website": place.get("websiteUri") or "",
        "instagram_url": f"https://instagram.com/{slug}" if slug else "",
        "description": (
            f"{name} is a real {category_name.lower()} provider listed on "
            f"Google Places in {city}."
        ),
        "price_min": price_min,
        "price_max": price_max,
        "rating_average": float(place.get("rating") or 0.0),
        "photo_url": _google_place_photo_url(place),
    }


def _vendor_payload(vendor, category_name, photo_url="", review_count=0):
    photo = photo_url or f"https://picsum.photos/seed/{vendor['vendor_id']}/800/600"
    return {
        "vendorId": vendor["vendor_id"],
        "categoryId": vendor["category_id"],
        "categoryName": _display(_language_for(current_user()), "category", category_name),
        "name": vendor["business_name"],
        "city": _city_label(_language_for(current_user()), vendor["city"]),
        "rating": f"{vendor['rating_average']:.1f}" if vendor["rating_average"] else "",
        "photo": photo,
        "url": url_for("vendor_detail", vendor_id=vendor["vendor_id"]),
        "desc": vendor["description"] or "",
        "price": (
            f"₪{vendor['price_min']:.0f} - ₪{vendor['price_max']:.0f}"
            if vendor["price_min"] and vendor["price_max"] else ""
        ),
        "address": vendor["address"] or "",
        "phone": vendor["phone"] or "",
        "email": vendor["email"] or "",
        "website": vendor["website"] or "",
        "instagram": vendor["instagram_url"] or "",
        "reviewCount": int(review_count or 0),
    }


@app.route("/api/google-vendors/search")
@login_required
def google_vendor_search():
    if not GOOGLE_PLACES_API_KEY:
        return jsonify({"results": [], "error": "missing_google_places_key"}), 503

    term = request.args.get("q", "").strip()
    category_id = request.args.get("category_id", type=int)
    if len(term) < 2 or not category_id:
        return jsonify({"results": []})

    cat = query("SELECT category_name FROM vendor_categories WHERE category_id=?", (category_id,), one=True)
    if not cat:
        abort(404)

    user = current_user()
    city_hint = (user["city"] if user and "city" in user.keys() else "") or "Israel"
    text_query = f"{term} {cat['category_name']} wedding supplier in {city_hint}, Israel"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_PLACES_API_KEY,
        "X-Goog-FieldMask": GOOGLE_PLACES_FIELD_MASK,
    }
    body = {
        "textQuery": text_query,
        "languageCode": _language_for(user),
        "regionCode": "IL",
        "pageSize": 6,
    }

    try:
        response = requests.post(GOOGLE_PLACES_SEARCH_URL, headers=headers, json=body, timeout=8)
        response.raise_for_status()
    except requests.RequestException:
        return jsonify({"results": [], "error": "google_search_failed"}), 502

    normalized = []
    for place in response.json().get("places") or []:
        item = _normalize_google_vendor(place, cat["category_name"], city_hint)
        if item["google_place_id"] and item["business_name"]:
            normalized.append(item)

    session["google_vendor_search"] = {
        item["google_place_id"]: item for item in normalized
    }
    session.modified = True

    return jsonify({
        "results": [
            {
                "placeId": item["google_place_id"],
                "name": item["business_name"],
                "category": _display(_language_for(user), "category", cat["category_name"]),
                "city": _city_label(_language_for(user), item["city"]),
                "address": item["address"],
                "rating": f"{item['rating_average']:.1f}" if item["rating_average"] else "",
                "photo": item["photo_url"],
            }
            for item in normalized
        ]
    })


@app.route("/api/google-vendors/select", methods=["POST"])
@login_required
def google_vendor_select():
    payload = request.get_json(silent=True) or {}
    place_id = (payload.get("place_id") or "").strip()
    category_id = int(payload.get("category_id") or 0)
    cached = (session.get("google_vendor_search") or {}).get(place_id)
    if not cached or not category_id:
        abort(400)

    cat = query("SELECT category_name FROM vendor_categories WHERE category_id=?", (category_id,), one=True)
    if not cat:
        abort(404)

    existing = query(
        """SELECT v.*, COALESCE(COUNT(vr.review_id), 0) AS review_count
             FROM vendors v
             LEFT JOIN vendor_reviews vr ON vr.vendor_id = v.vendor_id
            WHERE v.category_id = ? AND v.business_name = ? AND COALESCE(v.address, '') = ?
            GROUP BY v.vendor_id""",
        (category_id, cached["business_name"], cached["address"] or ""),
        one=True,
    )

    if existing:
        vendor = existing
    else:
        vendor_id = execute(
            """INSERT INTO vendors
               (business_name, category_id, city, address, phone, email, website,
                instagram_url, description, price_min, price_max, rating_average, is_active)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,1)""",
            (
                cached["business_name"], category_id, cached["city"], cached["address"],
                cached["phone"], cached["email"], cached["website"], cached["instagram_url"],
                cached["description"], cached["price_min"], cached["price_max"],
                cached["rating_average"],
            ),
        )
        if cached.get("photo_url"):
            execute(
                "INSERT INTO vendor_photos (vendor_id, photo_url, caption) VALUES (?,?,?)",
                (vendor_id, cached["photo_url"], cached["business_name"]),
            )
        vendor = query(
            "SELECT v.*, 0 AS review_count FROM vendors v WHERE v.vendor_id=?",
            (vendor_id,), one=True,
        )

    photo = query(
        "SELECT photo_url FROM vendor_photos WHERE vendor_id=? ORDER BY uploaded_at LIMIT 1",
        (vendor["vendor_id"],), one=True,
    )
    return jsonify({
        "vendor": _vendor_payload(
            vendor,
            cat["category_name"],
            photo["photo_url"] if photo else cached.get("photo_url", ""),
            vendor["review_count"] if "review_count" in vendor.keys() else 0,
        )
    })


def _build_deck(w, user, category_id, search=""):
    """Return (vendors, photo_map) for the swipe deck of one category:
    unswiped, active vendors, nearest-first within the user's distance."""
    user_city = ((user["city"] if user else "") or "").strip()
    max_distance = user["distance_km"] if user and "distance_km" in user.keys() and user["distance_km"] else 50

    search_clause = ""
    search_params = ()
    if search:
        search_clause = " AND (v.business_name LIKE ? OR v.description LIKE ?)"
        search_params = (f"%{search}%", f"%{search}%")

    sql = """SELECT v.*, COALESCE(COUNT(vr.review_id), 0) AS review_count
             FROM vendors v
             LEFT JOIN vendor_reviews vr ON vr.vendor_id = v.vendor_id
             WHERE v.category_id = ? AND v.is_active = 1
               AND v.vendor_id NOT IN (SELECT vendor_id FROM vendor_swipes WHERE wedding_id = ?)
               {search_clause}
             GROUP BY v.vendor_id
             ORDER BY v.rating_average DESC
             LIMIT 80""".format(search_clause=search_clause)
    vendors = query(sql, (category_id, w["wedding_id"], *search_params))

    if user_city:
        nearby, unknown = [], []
        for vendor in vendors:
            dist = _city_distance_km(user_city, vendor["city"])
            if dist is None:
                unknown.append(vendor)
            elif dist <= max_distance:
                nearby.append((dist, vendor))
        nearby.sort(key=lambda item: (item[0], -(item[1]["rating_average"] or 0)))
        vendors = [vendor for _dist, vendor in nearby] + unknown
    vendors = vendors[:8]

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
    return vendors, photo_map


@app.route("/discover")
@login_required
def discover():
    """Central matching hub: category chips on top, swipe deck below."""
    user = current_user()
    w = _ensure_wedding()
    search = request.args.get("q", "").strip()

    categories = query(
        """SELECT vc.category_id, vc.category_name,
                  COALESCE(SUM(CASE WHEN v.is_active = 1 AND v.vendor_id NOT IN
                       (SELECT vendor_id FROM vendor_swipes WHERE wedding_id = ?)
                       THEN 1 ELSE 0 END), 0) AS remaining
             FROM vendor_categories vc
             LEFT JOIN vendors v ON v.category_id = vc.category_id
            GROUP BY vc.category_id, vc.category_name
           HAVING COUNT(v.vendor_id) > 0
            ORDER BY vc.category_id""",
        (w["wedding_id"],),
    )

    cat_code_map = {name: code for code, name in SUPPLIER_TO_VENDOR_CATEGORY.items()}

    if not categories:
        return render_template("discover.html", categories=[], category=None,
                               vendors=[], photo_map={}, search=search,
                               cat_code_map=cat_code_map)

    requested = request.args.get("category_id", type=int)
    by_id = {c["category_id"]: c for c in categories}
    if requested and requested in by_id:
        active = by_id[requested]
    else:
        active = next((c for c in categories if c["remaining"] > 0), categories[0])

    vendors, photo_map = _build_deck(w, user, active["category_id"], search)

    return render_template("discover.html",
                           categories=categories, category=active,
                           vendors=vendors, photo_map=photo_map,
                           search=search, cat_code_map=cat_code_map)


@app.route("/swipe")
@login_required
def swipe_pick_category():
    return redirect(url_for("discover"))


@app.route("/swipe/<int:category_id>")
@login_required
def swipe(category_id):
    # Legacy URL: matching now lives in the Discover hub.
    args = {"category_id": category_id}
    q = request.args.get("q", "").strip()
    if q:
        args["q"] = q
    return redirect(url_for("discover", **args))


@app.route("/swipe/<category_ref>")
@login_required
def swipe_by_ref(category_ref):
    # Compatibility for older links that used supplier codes such as /swipe/venue.
    ref = (category_ref or "").strip()
    category_id = None

    if ref in SUPPLIER_TO_VENDOR_CATEGORY:
        row = query(
            "SELECT category_id FROM vendor_categories WHERE category_name = ?",
            (SUPPLIER_TO_VENDOR_CATEGORY[ref],),
            one=True,
        )
        category_id = row["category_id"] if row else None

    if category_id is None:
        row = query(
            "SELECT category_id FROM vendor_categories WHERE lower(category_name) = lower(?)",
            (ref.replace("-", " "),),
            one=True,
        )
        category_id = row["category_id"] if row else None

    args = {}
    if category_id:
        args["category_id"] = category_id
    q = request.args.get("q", "").strip()
    if q:
        args["q"] = q
    return redirect(url_for("discover", **args))


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
    selected_ids = {
        r["vendor_id"] for r in query(
            "SELECT vendor_id FROM selected_vendors WHERE wedding_id=?",
            (w["wedding_id"],),
        )
    }
    grouped = {}
    for r in rows:
        grouped.setdefault(r["category_name"], []).append(r)
    return render_template("favorites.html", grouped=grouped, selected_ids=selected_ids)


@app.route("/favorites/add/<int:vendor_id>", methods=["POST"])
@login_required
def favorites_add(vendor_id):
    lang = _language_for(current_user())
    w = current_wedding()
    if not w: return redirect(url_for("wedding_profile"))
    db = get_db()
    db.execute(
        "INSERT OR IGNORE INTO favorite_vendors (wedding_id, vendor_id) VALUES (?,?)",
        (w["wedding_id"], vendor_id),
    )
    db.commit()
    flash(_t(lang, "favorite_added"), "success")
    return redirect(request.referrer or url_for("vendor_detail", vendor_id=vendor_id))


@app.route("/favorites/remove/<int:vendor_id>", methods=["POST"])
@login_required
def favorites_remove(vendor_id):
    lang = _language_for(current_user())
    w = current_wedding()
    if not w: return redirect(url_for("wedding_profile"))
    execute(
        "DELETE FROM favorite_vendors WHERE wedding_id=? AND vendor_id=?",
        (w["wedding_id"], vendor_id),
    )
    flash(_t(lang, "favorite_removed"), "success")
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
    lang = _language_for(current_user())
    w = current_wedding()
    if not w: return redirect(url_for("wedding_profile"))
    v = query("SELECT category_id FROM vendors WHERE vendor_id=?", (vendor_id,), one=True)
    if not v: abort(404)
    price_per_meal = request.form.get("price_per_meal") or None
    guest_count    = request.form.get("guest_count") or None
    execute(
        """INSERT INTO selected_vendors (wedding_id, vendor_id, category_id, status, agreed_price, guest_count)
           VALUES (?,?,?, 'Considering', ?, ?)""",
        (w["wedding_id"], vendor_id, v["category_id"], price_per_meal, guest_count),
    )
    flash(_t(lang, "shortlist_added"), "success")
    return redirect(url_for("selected_vendors"))


@app.route("/selected-vendors/<int:sid>/update", methods=["POST"])
@login_required
def selected_vendors_update(sid):
    lang = _language_for(current_user())
    status      = request.form.get("status", "Considering")
    price       = request.form.get("agreed_price") or None
    notes       = request.form.get("notes", "")
    guest_count = request.form.get("guest_count") or None
    if status not in ("Considering","Contacted","Meeting Scheduled","Booked","Rejected"):
        abort(400)
    execute(
        "UPDATE selected_vendors SET status=?, agreed_price=?, notes=?, guest_count=? WHERE selected_vendor_id=?",
        (status, price, notes, guest_count, sid),
    )
    flash(_t(lang, "selection_updated"), "success")
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
    lang = _language_for(current_user())
    w = current_wedding()
    if not w: return redirect(url_for("wedding_profile"))
    if request.method == "POST":
        vendor_id = request.form.get("vendor_id", type=int)
        adate     = request.form.get("appointment_date")
        location  = request.form.get("location", "")
        notes     = request.form.get("notes", "")
        if not (vendor_id and adate):
            flash(_t(lang, "appointment_required"), "error")
        else:
            execute(
                """INSERT INTO appointments (wedding_id, vendor_id, appointment_date, location, notes)
                   VALUES (?,?,?,?,?)""",
                (w["wedding_id"], vendor_id, adate, location, notes),
            )
            flash(_t(lang, "appointment_scheduled"), "success")
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
    lang = _language_for(current_user())
    w = current_wedding()
    if request.method == "POST":
        vendor_id = request.form.get("vendor_id", type=int)
        rating    = request.form.get("rating", type=int)
        text      = request.form.get("review_text", "").strip()
        if not (vendor_id and rating and 1 <= rating <= 5):
            flash(_t(lang, "review_required"), "error")
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
            flash(_t(lang, "review_posted"), "success")
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
    return render_template("error.html", code=404, message=_t(_language_for(current_user()), "page_not_found")), 404

@app.errorhandler(500)
def server_error(_e):
    return render_template("error.html", code=500, message=_t(_language_for(current_user()), "server_error")), 500


if __name__ == "__main__":
    init_db()
    app.run(debug=os.getenv("FLASK_DEBUG", "0") == "1")

