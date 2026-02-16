# ShellSentry - Meeting Summary Guide

Quick reference guide for explaining your project to your professor.

---

## Project Overview

**ShellSentry** is a secure web-based system that translates natural language requests into Linux Bash commands using Large Language Models (LLMs) and executes them safely on remote servers via SSH.

---

## Core Architecture (5 Main Components)

### 1. **Security Layer** (`security.py`)
- **Purpose**: First line of defense - validates user input before it reaches the LLM
- **Key Function**: `validate_input()` - blocks malicious keywords, dangerous patterns, and prompt injection attacks
- **Why Important**: Prevents users from tricking the LLM or submitting dangerous requests

### 2. **LLM Client** (`llm_client.py`)
- **Purpose**: Communicates with AI model to convert natural language → Bash commands
- **Key Function**: `generate_command()` - sends request to LLM API and extracts Bash command
- **Features**: Retry logic, timeout handling, error recovery
- **Why Important**: This is the "brain" that understands user intent

### 3. **Command Validator** (`command_validator.py`)
- **Purpose**: Second line of defense - validates LLM-generated commands
- **Key Function**: `validate()` - checks against whitelist (allowed commands) and blacklist (forbidden patterns)
- **Security Features**:
  - Whitelist of ~200+ safe commands
  - Blacklist patterns (e.g., `rm -rf /`)
  - Special validation for dangerous commands (rm, kill, sudo)
- **Why Important**: Even if LLM generates unsafe code, validator blocks it

### 4. **SSH Executor** (`ssh_executor.py`)
- **Purpose**: Executes validated commands on remote Linux servers
- **Key Function**: `execute_on_server()` - establishes SSH connection and runs commands
- **Features**: 
  - Supports key-based and password authentication
  - Handles multi-line scripts
  - Error handling and retry logic
- **Why Important**: Secure remote execution is the core functionality

### 5. **Web Application** (`app.py`)
- **Purpose**: Orchestrates all components and handles HTTP requests
- **Key Endpoint**: `/api/execute` - main workflow:
  1. User submits natural language request
  2. Security layer validates input
  3. LLM generates Bash command
  4. Command validator checks safety
  5. SSH executor runs on remote servers
  6. Results returned to user
- **Why Important**: Provides user interface and coordinates all components

---

## Security Features (Multi-Layer Defense)

1. **Input Validation** (Security Layer)
   - Blocks prohibited keywords
   - Detects prompt injection attempts
   - Sanitizes user input

2. **Command Validation** (Command Validator)
   - Whitelist: Only allowed commands can execute
   - Blacklist: Forbidden patterns are blocked
   - Special rules for dangerous commands (rm, kill, sudo)

3. **Authentication** (Auth Module)
   - User login required
   - Password hashing (Werkzeug)
   - Session management (Flask-Login)

4. **Audit Logging** (Database Models)
   - All executions logged to database
   - Tracks: user, command, servers, results, timestamp
   - Enables accountability and forensics

5. **SSH Security** (SSH Executor)
   - Key-based authentication (preferred)
   - Password authentication (fallback)
   - Secure connection handling

---

## Data Flow Example

**User Request**: "Show active network connections"

1. **Frontend** (`dashboard.js`): User submits form → POST to `/api/execute`
2. **Security Layer**: Validates "Show active network connections" ✓ (safe)
3. **LLM Client**: Sends to API → Receives: `"netstat -nlutp"`
4. **Command Validator**: Checks `netstat` is in whitelist ✓ (allowed)
5. **SSH Executor**: Connects to remote server → Executes `netstat -nlutp`
6. **Database**: Logs execution (user, command, results)
7. **Frontend**: Displays results to user

---

## Key Functions to Highlight

### Most Important Functions:

1. **`execute_command()`** (`app.py`)
   - Main API endpoint
   - Orchestrates entire workflow
   - Handles errors and returns results

2. **`validate_input()`** (`security.py`)
   - First security check
   - Prevents malicious input

3. **`validate()`** (`command_validator.py`)
   - Second security check
   - Ensures LLM output is safe

4. **`generate_command()`** (`llm_client.py`)
   - AI integration
   - Natural language → Bash conversion

5. **`execute_on_server()`** (`ssh_executor.py`)
   - Remote execution
   - Secure SSH communication

---

## Technologies Used

- **Backend**: Python, Flask, SQLAlchemy
- **AI/LLM**: OpenAI-compatible API (Groq, OpenAI, Ollama)
- **Remote Access**: Paramiko (SSH library)
- **Security**: Werkzeug (password hashing), Flask-Login (sessions)
- **Database**: SQLite (development)
- **Frontend**: HTML, CSS, JavaScript

---

## Security Considerations (For Discussion)

1. **Defense in Depth**: Multiple validation layers
2. **Fail-Safe Defaults**: Commands blocked unless explicitly allowed
3. **Principle of Least Privilege**: Commands run as configured user (not root by default)
4. **Audit Trail**: Complete logging of all actions
5. **Input Sanitization**: Prevents injection attacks
6. **Command Validation**: Whitelist + blacklist approach

---

## Potential Questions & Answers

**Q: What if the LLM generates a dangerous command?**
A: The Command Validator checks every generated command against whitelist/blacklist before execution. Even if LLM suggests `rm -rf /`, it will be blocked.

**Q: How do you prevent prompt injection?**
A: Security Layer scans for injection patterns like "ignore previous instructions" and blocks them before reaching the LLM.

**Q: What happens if SSH connection fails?**
A: SSH Executor has retry logic (2 attempts) and returns detailed error messages (timeout, DNS failure, authentication error).

**Q: How are passwords stored?**
A: Using Werkzeug's password hashing (not plain text). Database stores hashes only.

**Q: Can users execute commands as root?**
A: Only if `ALLOW_ROOT_EXECUTION=true` in configuration. By default, it's disabled for security.

**Q: What commands are allowed?**
A: ~200+ safe commands in whitelist (monitoring, diagnostics, file operations). Destructive commands like `rm -rf /` are blocked.

---

## Project Strengths

1. ✅ **Multi-layer security** (input → LLM → command → execution)
2. ✅ **Comprehensive error handling** (retries, timeouts, user-friendly messages)
3. ✅ **Audit logging** (complete execution history)
4. ✅ **Flexible LLM integration** (supports multiple providers)
5. ✅ **User-friendly interface** (natural language input)
6. ✅ **Secure remote execution** (SSH with multiple auth methods)

---

## Areas for Future Enhancement

1. Role-based access control (RBAC)
2. Command execution simulation mode (dry-run)
3. Audit dashboard for security monitoring
4. Support for additional scripting languages
5. Integration with SIEM tools

---

## Quick Stats

- **Total Modules**: 9 Python modules
- **Main Classes**: 5 (SecurityLayer, LLMClient, CommandValidator, SSHExecutor, User)
- **API Endpoints**: 6 routes
- **Security Layers**: 3 (Input validation, Command validation, SSH security)
- **Database Models**: 2 (User, ExecutionLog)
- **Whitelisted Commands**: ~200+
- **Blacklist Patterns**: ~20+

---

Use this summary along with `FUNCTIONS_EXPLANATION.md` for your meeting!


