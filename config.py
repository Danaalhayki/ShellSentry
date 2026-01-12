import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Application configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///shellsentry.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # LLM Configuration
    LLM_API_TYPE = os.environ.get('LLM_API_TYPE', 'openai')
    LLM_API_KEY = os.environ.get('LLM_API_KEY', '')
    LLM_API_BASE_URL = os.environ.get('LLM_API_BASE_URL', 'https://api.openai.com/v1')
    LLM_MODEL = os.environ.get('LLM_MODEL', 'gpt-3.5-turbo')
    
    # SSH Configuration
    SSH_USER = os.environ.get('SSH_USER', '')
    SSH_KEY_PATH = os.environ.get('SSH_KEY_PATH', '~/.ssh/id_rsa')
    SSH_AGENT_SOCKET = os.environ.get('SSH_AGENT_SOCKET', '')
    
    # Remote Servers
    REMOTE_SERVERS = [s.strip() for s in os.environ.get('REMOTE_SERVERS', '').split(',') if s.strip()]
    
    # Security Settings
    ALLOW_ROOT_EXECUTION = os.environ.get('ALLOW_ROOT_EXECUTION', 'false').lower() == 'true'
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

