"""Vowly configuration."""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
INSTANCE_DIR.mkdir(exist_ok=True)

DATABASE_PATH = str(INSTANCE_DIR / "vowly.db")
SECRET_KEY = os.environ.get("VOWLY_SECRET", "vowly-dev-secret-change-me")
FOURSQUARE_KEY = os.environ.get("FOURSQUARE_KEY", "")
GOOGLE_PLACES_API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY", "")
VOWLY_PUBLIC_BASE_URL = os.environ.get("VOWLY_PUBLIC_BASE_URL", "").rstrip("/")

# OAuth — set these in .env before enabling social login
GOOGLE_CLIENT_ID     = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
FACEBOOK_CLIENT_ID     = os.environ.get("FACEBOOK_CLIENT_ID", "")
FACEBOOK_CLIENT_SECRET = os.environ.get("FACEBOOK_CLIENT_SECRET", "")
