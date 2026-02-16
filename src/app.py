from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from .models import db, User
from .auth import register_user, authenticate_user
from .security import SecurityLayer
from .llm_client import LLMClient
from .command_validator import CommandValidator
from .ssh_executor import SSHExecutor
from .logger import setup_logger
import os

# Get the project root directory (parent of src)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__, 
            template_folder=os.path.join(project_root, 'templates'),
            static_folder=os.path.join(project_root, 'static'))
app.config.from_object('src.config.Config')

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize components
security_layer = SecurityLayer()
llm_client = LLMClient()
command_validator = CommandValidator()
ssh_executor = SSHExecutor()
logger = setup_logger()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def create_tables():
    """Create database tables"""
    with app.app_context():
        db.create_all()
        # Create default admin user if it doesn't exist
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', email='admin@shellsentry.local')
            admin.set_password('admin123')  # Change in production!
            db.session.add(admin)
            db.session.commit()
            logger.info("Default admin user created (username: admin, password: admin123)")

# Initialize database on startup
create_tables()

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
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if register_user(username, email, password):
            flash('Registration successful. Please login.', 'success')
            logger.info(f"New user registered: {username}")
            return redirect(url_for('login'))
        else:
            flash('Registration failed. Username may already exist.', 'error')
    
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

@app.route('/api/execute', methods=['POST'])
@login_required
def execute_command():
    """Main API endpoint for command execution"""
    try:
        data = request.json
        natural_language = data.get('command', '').strip()
        target_servers = data.get('servers', [])
        
        if not natural_language:
            return jsonify({'error': 'Command is required'}), 400
        
        # Step 1: Input Validation
        validation_result = security_layer.validate_input(natural_language)
        if not validation_result['valid']:
            logger.warning(f"Input validation failed for user {current_user.username}: {validation_result['reason']}")
            return jsonify({
                'error': 'Input validation failed',
                'reason': validation_result['reason']
            }), 400
        
        # Step 2: LLM Processing
        logger.info(f"User {current_user.username} requested: {natural_language}")
        llm_response = llm_client.generate_command(natural_language)
        
        if not llm_response['success']:
            return jsonify({
                'error': 'Failed to generate command',
                'details': llm_response.get('error', 'Unknown error')
            }), 500
        
        generated_command = llm_response['command']
        logger.info(f"Generated command: {generated_command}")
        
        # Step 3: Command Validation
        validation_result = command_validator.validate(generated_command)
        if not validation_result['valid']:
            logger.warning(f"Command validation failed: {validation_result['reason']}")
            return jsonify({
                'error': 'Command validation failed',
                'reason': validation_result['reason'],
                'generated_command': generated_command
            }), 400
        
        # Normalize command for execution (strip shebang so shell does not try to run !/bin/bash etc.)
        command_to_run = command_validator.normalize_for_execution(generated_command)
        
        # Step 4: Remote Execution
        if not target_servers:
            target_servers = app.config['REMOTE_SERVERS']
        
        if not target_servers:
            return jsonify({
                'error': 'No target servers configured',
                'details': 'Please configure REMOTE_SERVERS in .env or specify servers in the request'
            }), 400
        
        execution_results = ssh_executor.execute_on_servers(
            command_to_run,
            target_servers,
            current_user.username,
            current_user.id,
            natural_language
        )
        
        # Step 5: Log execution
        logger.info(f"Command executed by {current_user.username} on {len(target_servers)} server(s)")
        
        return jsonify({
            'success': True,
            'original_request': natural_language,
            'generated_command': command_to_run,
            'results': execution_results
        })
        
    except Exception as e:
        logger.error(f"Error in execute_command: {str(e)}", exc_info=True)
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@app.route('/api/servers', methods=['GET'])
@login_required
def get_servers():
    """Get list of available servers"""
    servers = app.config['REMOTE_SERVERS']
    return jsonify({'servers': servers})

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'llm_configured': bool(app.config['LLM_API_KEY']),
        'ssh_configured': bool(app.config['SSH_USER']),
        'servers_configured': len(app.config['REMOTE_SERVERS']) > 0
    })
 
# Note:
# - Use `python run.py` for local development.
# - `app` is intentionally importable for WSGI servers and tooling.

