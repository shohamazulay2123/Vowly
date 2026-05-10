"""WSGI entry point for PythonAnywhere (and other WSGI servers)."""
import sys
import os

# Add the project directory to sys.path
sys.path.insert(0, os.path.dirname(__file__))

from database import init_db
init_db()

from app import app as application  # noqa: F401
