import re
from .models import db, User

# Password policy: min 8 chars, uppercase, lowercase, number
# Blacklisted special chars (shell injection / dangerous): ; | & $ ` \ < > ( ) { } [ ] ! \n \t
PASSWORD_BLACKLIST_CHARS = r'[;|&$`\\<>(){}[\]!\s]'
PASSWORD_MIN_LENGTH = 8


def validate_password(password):
    """
    Validate password against policy.
    Returns: (success: bool, error_message: str)
    """
    if not password or len(password) < PASSWORD_MIN_LENGTH:
        return False, f'Password must be at least {PASSWORD_MIN_LENGTH} characters long.'
    if not re.search(r'[A-Z]', password):
        return False, 'Password must contain at least one uppercase letter.'
    if not re.search(r'[a-z]', password):
        return False, 'Password must contain at least one lowercase letter.'
    if not re.search(r'\d', password):
        return False, 'Password must contain at least one number.'
    if re.search(PASSWORD_BLACKLIST_CHARS, password):
        return False, 'Password contains forbidden characters (e.g. ; | & $ ` \\ < > ( ) { } [ ] ! or spaces).'
    return True, ''


def register_user(username, email, password):
    """
    Register a new user.
    Returns: (success: bool, error_message: str)
    """
    if User.query.filter_by(username=username).first():
        return False, 'Username is already in use.'
    if User.query.filter_by(email=email).first():
        return False, 'Email is already registered to another account.'
    valid, msg = validate_password(password)
    if not valid:
        return False, msg
    user = User(username=username, email=email)
    user.set_password(password)
    try:
        db.session.add(user)
        db.session.commit()
        return True, ''
    except Exception:
        db.session.rollback()
        return False, 'Registration failed. Please try again.'


def authenticate_user(username, password):
    """Authenticate a user"""
    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        return user
    return None

