import os

from flask import Flask
from flask_login import LoginManager

from .models import db, User
from .routes import register_api_routes, register_error_handlers, register_page_routes

# Get the project root directory (parent of src)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = Flask(
    __name__,
    template_folder=os.path.join(project_root, 'templates'),
    static_folder=os.path.join(project_root, 'static'),
)
app.config.from_object('src.config.Config')

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def create_tables():
    """Create database tables"""
    with app.app_context():
        db.create_all()


create_tables()

register_page_routes(app)
register_api_routes(app)
register_error_handlers(app)


# Note:
# - Use `python run.py` for local development.
# - `app` is intentionally importable for WSGI servers and tooling.
