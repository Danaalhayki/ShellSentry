# ShellSentry - LLM-to-Bash

A secure web-based system that translates natural language requests into Linux Bash commands using Large Language Models (LLMs) and executes them securely on remote machines.

## Features

- 🔐 **User Authentication**: Secure login and registration system
- 🤖 **LLM Integration**: Converts natural language to Bash commands using OpenAI/LLaMA APIs
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
- SSH access to remote Linux servers
- LLM API key (OpenAI or compatible API)
- SSH key for remote server authentication

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ShellSentry
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and configure:
   - `SECRET_KEY`: Flask secret key (generate a strong random key)
   - `LLM_API_KEY`: Your OpenAI or compatible API key
   - `LLM_API_BASE_URL`: API endpoint URL
   - `LLM_MODEL`: Model name (e.g., `gpt-3.5-turbo`)
   - `SSH_USER`: SSH username for remote servers
   - `SSH_KEY_PATH`: Path to SSH private key
   - `REMOTE_SERVERS`: Comma-separated list of server hostnames/IPs

4. **Initialize the database**
   ```bash
   python app.py
   ```
   
   The application will automatically create the database and a default admin user:
   - Username: `admin`
   - Password: `admin123`
   
   **⚠️ IMPORTANT**: Change the default password immediately!

5. **Run the application**
   ```bash
   python app.py
   ```
   
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
- Key-based authentication
- SSH agent support
- Secure connection handling

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Flask secret key | Required |
| `LLM_API_KEY` | LLM API key | Required |
| `LLM_API_BASE_URL` | API base URL | `https://api.openai.com/v1` |
| `LLM_MODEL` | Model name | `gpt-3.5-turbo` |
| `SSH_USER` | SSH username | Required |
| `SSH_KEY_PATH` | SSH key path | `~/.ssh/id_rsa` |
| `REMOTE_SERVERS` | Comma-separated servers | Required |
| `ALLOW_ROOT_EXECUTION` | Allow sudo/root commands | `false` |

## Project Structure

```
ShellSentry/
├── app.py                 # Main Flask application
├── config.py              # Configuration management
├── models.py              # Database models
├── auth.py                # Authentication functions
├── security.py            # Security layer (input validation)
├── llm_client.py          # LLM API client
├── command_validator.py   # Command validation (whitelist/blacklist)
├── ssh_executor.py        # SSH remote execution
├── logger.py              # Logging setup
├── requirements.txt       # Python dependencies
├── templates/             # HTML templates
│   ├── base.html
│   ├── login.html
│   ├── register.html
│   └── dashboard.html
└── static/                # Static files
    ├── css/
    │   └── style.css
    └── js/
        └── dashboard.js
```

## Supported Commands

The system supports a wide range of safe system administration commands:

- **Network**: `netstat`, `ss`, `ping`, `ifconfig`, `ip`, `tcpdump`
- **System**: `ps`, `top`, `htop`, `uptime`, `df`, `du`, `free`
- **Monitoring**: `dmesg`, `journalctl`, `systemctl`, `lsof`
- **File Operations**: `ls`, `cat`, `grep`, `find`, `head`, `tail`
- **Network Tools**: `curl`, `wget`, `dig`, `nslookup`, `traceroute`
- And many more (see `command_validator.py` for full whitelist)

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

