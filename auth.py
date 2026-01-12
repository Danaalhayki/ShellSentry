from models import db, User

def register_user(username, email, password):
    """Register a new user"""
    if User.query.filter_by(username=username).first():
        return False
    
    if User.query.filter_by(email=email).first():
        return False
    
    user = User(username=username, email=email)
    user.set_password(password)
    
    try:
        db.session.add(user)
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        return False

def authenticate_user(username, password):
    """Authenticate a user"""
    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        return user
    return None

