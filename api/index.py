"""
J.A.R.V.I.S. Vercel Serverless Function Entrypoint
Exposes FastAPI ASGI application to the Vercel Python runtime.
"""

import sys
import os

# Ensure the root project directory is in the Python module search path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from server import app

# Vercel's Python runtime natively detects ASGI 'app'
