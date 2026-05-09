"""Route registration for the Flask app."""

from .pages import register_page_routes
from .api import register_api_routes
from .errors import register_error_handlers

__all__ = ['register_page_routes', 'register_api_routes', 'register_error_handlers']
