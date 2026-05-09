from flask import render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user

from ..auth import register_user, authenticate_user
from ..services import logger


def register_page_routes(app):
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return render_template('index.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')

            user = authenticate_user(username, password)
            if user:
                login_user(user)
                logger.info(f"User {username} logged in")
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid username or password', 'error')
                logger.warning(f"Failed login attempt for username: {username}")

        return render_template('login.html')

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip()
            password = request.form.get('password')
            password_confirm = request.form.get('password_confirm')

            if password != password_confirm:
                flash('Passwords do not match. Please verify your password confirmation.', 'error')
            else:
                success, msg = register_user(username, email, password)
                if success:
                    flash('Registration successful. Please login.', 'success')
                    logger.info(f"New user registered: {username}")
                    return redirect(url_for('login'))
                else:
                    flash(msg, 'error')

        return render_template('register.html')

    @app.route('/logout')
    @login_required
    def logout():
        username = current_user.username
        logout_user()
        logger.info(f"User {username} logged out")
        return redirect(url_for('login'))

    @app.route('/dashboard')
    @login_required
    def dashboard():
        return render_template('dashboard.html', username=current_user.username)
