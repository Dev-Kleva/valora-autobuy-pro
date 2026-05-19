import sys
import os

# Add repository root to path so backend package imports resolve when run from Vercel
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT_DIR)

# Import the FastAPI ASGI app exported from backend/main.py
from backend.main import app

# Export `app` (ASGI application) so the Vercel Python builder serves FastAPI directly
