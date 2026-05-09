from flask import render_template
from jinja2 import TemplateNotFound

from ..services import logger


def register_error_handlers(app):
    @app.errorhandler(TemplateNotFound)
    def template_not_found_error(error):
        """Show custom 500 page when a template is missing (e.g. renamed/deleted)."""
        logger.error(f"Template not found: {error}")
        try:
            return render_template(
                'errors/error.html',
                error_code=500,
                error_title='Internal Server Error',
                error_message="A required page could not be loaded. Please try again or contact support."
            ), 500
        except TemplateNotFound:
            return (
                '<h1>500 Internal Server Error</h1>'
                '<p>A required page could not be loaded.</p>'
            ), 500

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template(
            'errors/error.html',
            error_code=404,
            error_title='Page Not Found',
            error_message="The page you're looking for doesn't exist or was moved. Check the URL or head back to safety."
        ), 404

    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template(
            'errors/error.html',
            error_code=403,
            error_title='Access Forbidden',
            error_message="You don't have permission to access this resource. If you believe this is an error, contact your administrator."
        ), 403

    @app.errorhandler(400)
    def bad_request_error(error):
        return render_template(
            'errors/error.html',
            error_code=400,
            error_title='Bad Request',
            error_message="The request was invalid or malformed. Please check your input and try again."
        ), 400

    @app.errorhandler(405)
    def method_not_allowed_error(error):
        return render_template(
            'errors/error.html',
            error_code=405,
            error_title='Method Not Allowed',
            error_message="This HTTP method is not allowed for the requested resource."
        ), 405

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {str(error)}", exc_info=True)
        return render_template(
            'errors/error.html',
            error_code=500,
            error_title='Internal Server Error',
            error_message="Something went wrong on our end. We've been notified and are looking into it. Please try again later."
        ), 500
