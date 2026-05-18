import sys
import os

# Add backend dir to path so imports resolve when run from Vercel
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

# Import the FastAPI ASGI app exported from backend/main.py
from main import app

# Export `app` (ASGI application) so the Vercel Python builder serves FastAPI directly
