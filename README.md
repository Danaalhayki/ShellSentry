# ShellSentry - LLM-to-Bash

A secure web-based system that translates natural language requests into Linux Bash commands using Large Language Models (LLMs) and executes them securely on remote machines.

## Features

- 🔐 **User Authentication**: Secure login and registration system
- 🤖 **LLM Integration**: Converts natural language to Bash commands using OpenAI/LLaMA APIs
- 🧠 **RAG Grounding Layer**: Retrieves trusted Bash examples from a vector index before LLM generation
- 🛡️ **Multi-Layer Security**: 
  - Input validation and prompt sanitization
  - Command whitelist/blacklist validation
  - Protection against malicious commands
- 🔌 **SSH Remote Execution**: Secure command execution on remote Linux servers
- 📊 **Result Display**: Clear visualization of execution results
- 📝 **Audit Logging**: Complete logging of all user actions and executions

## Architecture

```
User → Web Interface → Security Layer → LLM API → Command Validator → SSH Executor → Remote Servers
```

## Prerequisites

- Python 3.8+
- SSH access to remote Linux servers (key-based or password authentication)
- LLM API key or local LLM (OpenAI-compatible API; see [LLM_SETUP.md](MdFiles/LLM_SETUP.md))

## Quick Start

For detailed setup instructions, see [QUICKSTART.md](MdFiles/QUICKSTART.md).

**Basic Setup:**
1. Install dependencies: `pip install -r requirements.txt`
2. Copy `env.example` to `.env` and configure it
3. Set up LLM (see [LLM_SETUP.md](MdFiles/LLM_SETUP.md))
4. Configure SSH access (key or password)
5. Run: `python run.py`

**Default Admin Credentials:**
- Username: `admin`
- Password: `admin123`
- **⚠️ IMPORTANT**: Change the default password immediately after first login!

The application will be available at `http://localhost:5001`

## Usage

1. **Login** to the system using your credentials
2. **Enter a natural language command** in the dashboard, for example:
   - "Show active connections on the server"
   - "Check if 192.168.56.1 is alive"
   - "Show disk storage usage on all machines"
   - "Display network interfaces"
3. **Optionally specify target servers** (leave empty to use all configured servers)
4. **Click "Execute Command"** and view the results

## Security Features

### Input Validation
- Detects prohibited keywords (rm -rf, format, etc.)
- Blocks dangerous patterns (command injection, fork bombs)
- Prevents prompt injection attacks

### Command Validation
- Whitelist of allowed commands
- Blacklist of forbidden patterns
- Special validation for restricted commands (rm, kill, sudo, etc.)
- Prevents execution of destructive commands

### SSH Security
- Key-based or password authentication (Paramiko)
- Optional SSH agent via `SSH_AGENT_SOCKET`
- Secure connection handling

## Documentation

- **[QUICKSTART.md](MdFiles/QUICKSTART.md)** - Quick start guide with step-by-step setup
- **[LLM_SETUP.md](MdFiles/LLM_SETUP.md)** - Comprehensive guide for setting up LLM (local or cloud)
- **[projectDescription.md](MdFiles/projectDescription.md)** - Detailed project description and architecture
- **[RAG_SETUP.md](MdFiles/RAG_SETUP.md)** - Retrieval-Augmented Generation pipeline details

## Configuration

See [QUICKSTART.md](MdFiles/QUICKSTART.md) for detailed configuration instructions.

**Key Environment Variables:**
- `SECRET_KEY` - Flask secret key (generate with: `python -c "import secrets; print(secrets.token_hex(32))"`)
- `DATABASE_URL` - Database URL (default: `sqlite:///shellsentry.db`)
- `LLM_API_KEY` - LLM API key (see [LLM_SETUP.md](MdFiles/LLM_SETUP.md))
- `LLM_API_BASE_URL` - API endpoint URL
- `LLM_MODEL` - Model name
- `SSH_USER` - SSH username for remote servers
- `SSH_PASSWORD` - SSH password (optional; use key auth if not set)
- `SSH_KEY_PATH` - Path to SSH private key (default: `~/.ssh/id_rsa`)
- `REMOTE_SERVERS` - Comma-separated list of server hostnames/IPs
- `ALLOW_ROOT_EXECUTION` - Allow sudo/root commands (default: `false`)

## Project Structure

```
ShellSentry/
├── run.py                 # Application runner (run this: python run.py)
├── test_llm.py            # LLM connection diagnostic tool
├── requirements.txt       # Python dependencies
├── env.example            # Environment variable template
├── src/                   # Application package
│   ├── app.py             # Main Flask application
│   ├── config.py          # Configuration (from .env)
│   ├── models.py          # Database models
│   ├── auth.py            # Authentication functions
│   ├── security.py        # Security layer (input validation)
│   ├── llm_client.py      # LLM API client (OpenAI-compatible)
│   ├── command_validator.py  # Command validation (whitelist/blacklist)
│   ├── ssh_executor.py    # SSH remote execution (Paramiko)
│   └── logger.py          # Logging setup
├── templates/             # HTML templates
│   ├── base.html
│   ├── login.html
│   ├── register.html
│   └── dashboard.html
├── static/                # Static files
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── dashboard.js
└── MdFiles/               # Documentation
    ├── QUICKSTART.md
    ├── LLM_SETUP.md
    └── projectDescription.md
```

## Supported Commands

The system supports a wide range of safe system administration commands:

- **Network**: `netstat`, `ss`, `ping`, `ifconfig`, `ip`, `tcpdump`
- **System**: `ps`, `top`, `htop`, `uptime`, `df`, `du`, `free`
- **Monitoring**: `dmesg`, `journalctl`, `systemctl`, `lsof`
- **File Operations**: `ls`, `cat`, `grep`, `find`, `head`, `tail`
- **Network Tools**: `curl`, `wget`, `dig`, `nslookup`, `traceroute`
- And many more (see `src/command_validator.py` for full whitelist)

## Limitations

- Depends on LLM accuracy for command generation
- Not intended for unrestricted production environments
- Complex commands may require additional validation rules
- Frontend design is functional but not the primary focus

## Security Considerations

⚠️ **This system is designed for educational and controlled environments only.**

- Always change default credentials
- Use strong SSH keys
- Regularly review execution logs
- Monitor for suspicious activity
- Keep dependencies updated
- Use HTTPS in production
- Implement additional security measures as needed

## Future Enhancements

- Role-based access control (RBAC)
- Command execution simulation mode
- Audit dashboard for security monitoring
- Support for additional scripting languages
- Integration with SIEM or monitoring tools

## License

This project is for educational purposes.

## Contributing

Contributions are welcome! Please ensure all security checks pass before submitting.

## Support

For issues and questions, please open an issue on the repository.

