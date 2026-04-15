"""
API Routes Package
Contains all API route modules for the FinChat application
"""

from .chat_routes import router as chat_router
from .docs_routes import router as docs_router
from .settings_routes import router as settings_router

__all__ = ["chat_router", "docs_router", "settings_router"]