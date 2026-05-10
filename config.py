"""Vowly configuration."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
INSTANCE_DIR.mkdir(exist_ok=True)

DATABASE_PATH = str(INSTANCE_DIR / "vowly.db")
SECRET_KEY = os.environ.get("VOWLY_SECRET", "vowly-dev-secret-change-me")
FOURSQUARE_KEY = os.environ.get("FOURSQUARE_KEY", "")
