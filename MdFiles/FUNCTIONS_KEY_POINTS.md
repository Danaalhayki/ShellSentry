# ShellSentry - Functions Key Points (Quick Reference)

## 🎯 Main Workflow Function

### `execute_command()` - `app.py`
**THE CORE FUNCTION** - Orchestrates entire execution pipeline
- **Input**: Natural language request from user
- **Process**: 5-step security pipeline
  1. Input validation (Security Layer)
  2. LLM processing (generate Bash command)
  3. Command validation (whitelist/blacklist)
  4. Remote execution (SSH)
  5. Result logging
- **Output**: JSON with results from all servers
- **Key Point**: This is where everything comes together

---

## 🔒 Security Functions

### `validate_input()` - `security.py`
**FIRST LINE OF DEFENSE**
- **Purpose**: Block malicious input before it reaches LLM
- **Checks**: 
  - Prohibited keywords ("rm -rf", "format", etc.)
  - Dangerous patterns (regex)
  - Prompt injection attempts
  - Input length (max 1000 chars)
- **Returns**: `{'valid': bool, 'reason': str}`
- **Key Point**: Prevents users from tricking the system

### `validate()` - `command_validator.py`
**SECOND LINE OF DEFENSE**
- **Purpose**: Validate LLM-generated commands
- **Checks**:
  - Whitelist (~200+ allowed commands)
  - Blacklist patterns (forbidden operations)
  - Special validation for dangerous commands (rm, kill, sudo)
- **Returns**: `{'valid': bool, 'reason': str}`
- **Key Point**: Even if LLM generates bad code, this blocks it

---

## 🤖 AI/LLM Functions

### `generate_command()` - `llm_client.py`
**NATURAL LANGUAGE → BASH CONVERSION**
- **Purpose**: Convert user's English request to Bash command
- **Process**:
  - Sends request to LLM API (OpenAI-compatible)
  - Uses system prompt with safety instructions
  - Extracts and cleans Bash command from response
- **Features**: Retry logic (3 attempts), timeout handling
- **Returns**: `{'success': bool, 'command': str, 'error': str}`
- **Key Point**: This is the "brain" that understands user intent

---

## 🌐 Remote Execution Functions

### `execute_on_servers()` - `ssh_executor.py`
**MULTI-SERVER EXECUTION**
- **Purpose**: Execute command on multiple remote servers
- **Process**:
  - Loops through each server
  - Calls `_execute_on_server()` for each
  - Collects all results
  - Logs to database
- **Returns**: Dictionary mapping server → execution results
- **Key Point**: Handles parallel execution across multiple machines

### `_execute_on_server()` - `ssh_executor.py`
**SINGLE SERVER EXECUTION**
- **Purpose**: Execute command on one remote server via SSH
- **Process**:
  1. Create SSH client (Paramiko)
  2. Authenticate (key/password/agent)
  3. Execute command (with timeout)
  4. Collect stdout, stderr, exit code
  5. Close connection
- **Features**: Retry logic, error handling, multi-line script support
- **Returns**: `{'success': bool, 'stdout': str, 'stderr': str, 'exit_code': int}`
- **Key Point**: This is where commands actually run on remote machines

---

## 👤 Authentication Functions

### `authenticate_user()` - `auth.py`
**USER LOGIN VERIFICATION**
- **Purpose**: Verify username and password
- **Process**:
  - Find user in database
  - Check password hash (secure comparison)
- **Returns**: User object if valid, None if invalid
- **Key Point**: Secure password verification using Werkzeug hashing

### `register_user()` - `auth.py`
**NEW USER CREATION**
- **Purpose**: Create new user account
- **Process**:
  - Check username/email uniqueness
  - Hash password securely
  - Save to database
- **Returns**: True if successful, False if username/email exists
- **Key Point**: Prevents duplicate accounts

---

## 📊 Database Functions

### `set_password()` - `models.py` (User class)
**SECURE PASSWORD STORAGE**
- **Purpose**: Hash and store password
- **Method**: Uses Werkzeug's `generate_password_hash()`
- **Key Point**: Passwords never stored in plain text

### `check_password()` - `models.py` (User class)
**PASSWORD VERIFICATION**
- **Purpose**: Verify password against stored hash
- **Method**: Uses Werkzeug's `check_password_hash()`
- **Key Point**: Secure comparison without exposing hash

### `_log_execution()` - `ssh_executor.py`
**AUDIT TRAIL CREATION**
- **Purpose**: Log all command executions to database
- **Stores**: User, command, servers, results, timestamp, status
- **Key Point**: Complete audit trail for security monitoring

---

## 🛠️ Utility Functions

### `normalize_for_execution()` - `command_validator.py`
**COMMAND PREPARATION**
- **Purpose**: Clean command before execution
- **Process**: Removes shebang lines, strips quotes
- **Key Point**: Ensures commands execute correctly in shell

### `_strip_shebang()` - `command_validator.py`
**SHEBANG REMOVAL**
- **Purpose**: Remove `#!/bin/bash` lines from commands
- **Key Point**: Prevents shell from trying to execute shebang as command

### `setup_logger()` - `logger.py`
**LOGGING CONFIGURATION**
- **Purpose**: Set up application-wide logging
- **Output**: Console (INFO) + File (DEBUG)
- **Key Point**: Centralized logging for debugging and monitoring

---

## 🎨 Frontend Functions

### `displayResults()` - `dashboard.js`
**UI RESULT DISPLAY**
- **Purpose**: Show execution results to user
- **Process**: Generates HTML cards for each server's results
- **Key Point**: User-friendly presentation of command outputs

### `escapeHtml()` - `dashboard.js`
**XSS PREVENTION**
- **Purpose**: Escape HTML special characters
- **Key Point**: Critical security function to prevent cross-site scripting

---

## 📋 Quick Function Reference Table

| Function | Module | Purpose | Key Feature |
|----------|--------|---------|-------------|
| `execute_command()` | app.py | Main workflow | Orchestrates 5-step pipeline |
| `validate_input()` | security.py | Input security | Blocks malicious patterns |
| `validate()` | command_validator.py | Command security | Whitelist/blacklist check |
| `generate_command()` | llm_client.py | AI conversion | Natural language → Bash |
| `execute_on_servers()` | ssh_executor.py | Multi-server exec | Parallel execution |
| `_execute_on_server()` | ssh_executor.py | Single server exec | SSH command execution |
| `authenticate_user()` | auth.py | Login | Password verification |
| `register_user()` | auth.py | Registration | Account creation |
| `_log_execution()` | ssh_executor.py | Audit logging | Database logging |

---

## 🔑 Critical Security Functions (Must Understand)

1. **`validate_input()`** - First defense (blocks bad input)
2. **`validate()`** - Second defense (blocks bad commands)
3. **`_execute_on_server()`** - Execution point (where commands run)
4. **`_log_execution()`** - Audit trail (accountability)

---

## 💡 Key Design Patterns

1. **Defense in Depth**: Multiple validation layers
2. **Fail-Safe Defaults**: Commands blocked unless explicitly allowed
3. **Separation of Concerns**: Each function has single responsibility
4. **Error Handling**: Comprehensive try-catch blocks
5. **Retry Logic**: Network operations retry on failure

---

## 🎯 For Your Meeting - Top 5 Functions to Explain

1. **`execute_command()`** - Show the complete workflow
2. **`validate()`** - Explain security validation
3. **`generate_command()`** - Demonstrate AI integration
4. **`_execute_on_server()`** - Show remote execution
5. **`_log_execution()`** - Highlight audit trail

---

## 📝 Function Flow Diagram

```
User Input
    ↓
validate_input() [Security Layer]
    ↓
generate_command() [LLM Client]
    ↓
validate() [Command Validator]
    ↓
normalize_for_execution() [Command Validator]
    ↓
execute_on_servers() [SSH Executor]
    ↓
_execute_on_server() [SSH Executor] × N servers
    ↓
_log_execution() [SSH Executor]
    ↓
displayResults() [Frontend]
```

---

Use this as a quick reference during your meeting!


