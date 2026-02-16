# ShellSentry - Complete Functions and Methods Documentation

This document provides a comprehensive explanation of all functions and methods used in the ShellSentry project, organized by module. This is designed to help you explain your program to your professor.

---

## Table of Contents

1. [Main Application (`src/app.py`)](#1-main-application-srcapppy)
2. [Authentication Module (`src/auth.py`)](#2-authentication-module-srcauthpy)
3. [Security Layer (`src/security.py`)](#3-security-layer-srcsecuritypy)
4. [LLM Client (`src/llm_client.py`)](#4-llm-client-srcllm_clientpy)
5. [Command Validator (`src/command_validator.py`)](#5-command-validator-srccommand_validatorpy)
6. [SSH Executor (`src/ssh_executor.py`)](#6-ssh-executor-srcssh_executorpy)
7. [Database Models (`src/models.py`)](#7-database-models-srcmodelspy)
8. [Configuration (`src/config.py`)](#8-configuration-srcconfigpy)
9. [Logger (`src/logger.py`)](#9-logger-srcloggerpy)
10. [Frontend JavaScript (`static/js/dashboard.js`)](#10-frontend-javascript-staticjsdashboardjs)
11. [Entry Point (`run.py`)](#11-entry-point-runpy)

---

## 1. Main Application (`src/app.py`)

The main Flask application that orchestrates all components and handles HTTP requests.

### **Class/Module Initialization**

**Components Initialized:**
- `security_layer`: Instance of `SecurityLayer` for input validation
- `llm_client`: Instance of `LLMClient` for LLM API communication
- `command_validator`: Instance of `CommandValidator` for command validation
- `ssh_executor`: Instance of `SSHExecutor` for remote execution
- `logger`: Application logger for tracking events

### **Functions:**

#### `load_user(user_id)`
- **Purpose**: Flask-Login callback to load a user from the database
- **Parameters**: 
  - `user_id` (int): The user's ID from the session
- **Returns**: `User` object or `None`
- **Usage**: Called automatically by Flask-Login when checking authentication

#### `create_tables()`
- **Purpose**: Initialize the database schema and create default admin user
- **Parameters**: None
- **Returns**: None
- **Behavior**:
  - Creates all database tables using SQLAlchemy
  - Creates a default admin user (username: `admin`, password: `admin123`) if it doesn't exist
  - Logs the creation of the default admin user

### **Route Handlers:**

#### `index()` - Route: `/`
- **Purpose**: Root endpoint that redirects users
- **Behavior**: 
  - If authenticated → redirects to dashboard
  - If not authenticated → redirects to login page
- **Returns**: HTTP redirect response

#### `login()` - Route: `/login` (GET, POST)
- **Purpose**: Handle user login
- **GET Request**: Displays the login form
- **POST Request**: 
  - Extracts `username` and `password` from form
  - Calls `authenticate_user()` to verify credentials
  - If successful: logs the user in and redirects to dashboard
  - If failed: shows error message and stays on login page
- **Returns**: Rendered template or redirect

#### `register()` - Route: `/register` (GET, POST)
- **Purpose**: Handle new user registration
- **GET Request**: Displays the registration form
- **POST Request**:
  - Extracts `username`, `email`, and `password` from form
  - Calls `register_user()` to create account
  - If successful: shows success message and redirects to login
  - If failed: shows error message (usually username already exists)
- **Returns**: Rendered template or redirect

#### `logout()` - Route: `/logout`
- **Purpose**: Handle user logout
- **Authentication**: Requires login (`@login_required`)
- **Behavior**: 
  - Logs the logout event
  - Calls Flask-Login's `logout_user()`
  - Redirects to login page
- **Returns**: HTTP redirect response

#### `dashboard()` - Route: `/dashboard`
- **Purpose**: Display the main dashboard interface
- **Authentication**: Requires login (`@login_required`)
- **Behavior**: Renders the dashboard template with the current username
- **Returns**: Rendered HTML template

#### `execute_command()` - Route: `/api/execute` (POST)
- **Purpose**: Main API endpoint for executing natural language commands
- **Authentication**: Requires login (`@login_required`)
- **Request Body** (JSON):
  - `command` (string): Natural language request
  - `servers` (array, optional): List of target servers
- **Workflow**:
  1. **Input Validation**: Uses `security_layer.validate_input()` to check for malicious content
  2. **LLM Processing**: Calls `llm_client.generate_command()` to convert natural language to Bash
  3. **Command Validation**: Uses `command_validator.validate()` to ensure command is safe
  4. **Command Normalization**: Strips shebang and quotes using `command_validator.normalize_for_execution()`
  5. **Remote Execution**: Calls `ssh_executor.execute_on_servers()` to run command on remote machines
  6. **Logging**: Logs the execution event
- **Returns**: JSON response with:
  - `success`: Boolean indicating overall success
  - `original_request`: The user's natural language input
  - `generated_command`: The Bash command generated by LLM
  - `results`: Dictionary of results from each server
- **Error Handling**: Returns appropriate HTTP status codes (400, 500) with error messages

#### `get_servers()` - Route: `/api/servers` (GET)
- **Purpose**: Get list of available remote servers
- **Authentication**: Requires login (`@login_required`)
- **Returns**: JSON response with `servers` array from configuration

#### `health_check()` - Route: `/api/health` (GET)
- **Purpose**: Health check endpoint to verify system configuration
- **Authentication**: None (public endpoint)
- **Returns**: JSON response with:
  - `status`: "healthy"
  - `llm_configured`: Boolean indicating if LLM API key is set
  - `ssh_configured`: Boolean indicating if SSH user is configured
  - `servers_configured`: Boolean indicating if servers are configured

---

## 2. Authentication Module (`src/auth.py`)

Handles user registration and authentication logic.

### **Functions:**

#### `register_user(username, email, password)`
- **Purpose**: Register a new user in the database
- **Parameters**:
  - `username` (string): Unique username
  - `email` (string): Unique email address
  - `password` (string): Plain text password (will be hashed)
- **Returns**: 
  - `True` if registration successful
  - `False` if username/email already exists or database error occurs
- **Behavior**:
  - Checks if username already exists → returns `False`
  - Checks if email already exists → returns `False`
  - Creates new `User` object
  - Hashes password using `user.set_password()`
  - Saves to database
  - Handles exceptions with rollback

#### `authenticate_user(username, password)`
- **Purpose**: Verify user credentials and return user object
- **Parameters**:
  - `username` (string): Username to authenticate
  - `password` (string): Plain text password to verify
- **Returns**: 
  - `User` object if credentials are valid
  - `None` if username doesn't exist or password is incorrect
- **Behavior**:
  - Queries database for user by username
  - If user exists, verifies password using `user.check_password()`
  - Returns user object if password matches

---

## 3. Security Layer (`src/security.py`)

Provides input validation and prompt sanitization to prevent malicious requests.

### **Class: `SecurityLayer`**

#### `__init__(self)`
- **Purpose**: Initialize security layer with prohibited keywords and patterns
- **Initializes**:
  - `prohibited_keywords`: List of dangerous keywords (e.g., "rm -rf", "format", "delete all")
  - `dangerous_patterns`: Regex patterns for dangerous command patterns
  - `injection_patterns`: Regex patterns to detect prompt injection attacks

#### `validate_input(self, user_input)`
- **Purpose**: Validate user input for malicious content before sending to LLM
- **Parameters**:
  - `user_input` (string): The natural language input from user
- **Returns**: Dictionary with:
  - `valid` (bool): Whether input passed validation
  - `reason` (string): Reason for failure (if invalid)
  - `sanitized_input` (string): Cleaned input (if valid)
- **Validation Checks**:
  1. **Empty Check**: Rejects empty or whitespace-only input
  2. **Length Check**: Rejects input longer than 1000 characters
  3. **Keyword Check**: Scans for prohibited keywords (case-insensitive)
  4. **Pattern Check**: Uses regex to detect dangerous command patterns
  5. **Injection Check**: Detects prompt injection attempts (e.g., "ignore previous instructions")
  6. **Sanitization**: Removes control characters (non-printable characters)
- **Logging**: Logs warnings when malicious patterns are detected

#### `sanitize_prompt(self, user_input)`
- **Purpose**: Additional sanitization specifically for LLM prompts
- **Parameters**:
  - `user_input` (string): Input to sanitize
- **Returns**: Sanitized string (max 500 characters)
- **Behavior**:
  - Removes dangerous characters: `<>{}[]\`
  - Truncates to 500 characters maximum

---

## 4. LLM Client (`src/llm_client.py`)

Handles communication with the Large Language Model API to convert natural language to Bash commands.

### **Class: `LLMClient`**

#### `__init__(self)`
- **Purpose**: Initialize LLM client with configuration
- **Loads from Config**:
  - `api_key`: API key for authentication
  - `api_base`: Base URL for API endpoint
  - `model`: Model name to use (e.g., "llama-3.1-8b-instant")
  - `api_type`: Type of API ("openai" or compatible)

#### `generate_command(self, natural_language_input)`
- **Purpose**: Convert natural language request into Bash command using LLM
- **Parameters**:
  - `natural_language_input` (string): User's natural language request
- **Returns**: Dictionary with:
  - `success` (bool): Whether API call succeeded
  - `command` (string): Generated Bash command (if successful)
  - `error` (string): Error message (if failed)
- **Behavior**:
  1. Checks if API key is configured
  2. Creates system prompt with instructions for the LLM
  3. Calls appropriate API method based on `api_type`
  4. Processes response to extract command
  5. Cleans up command (removes markdown code blocks, shell prompts)
- **System Prompt**: Instructs LLM to:
  - Generate ONLY Bash commands (no explanations)
  - Use safe commands only
  - Support multi-server operations
  - Avoid sudo unless requested
  - Return "ERROR" if request is unclear/unsafe

#### `_call_openai_api(self, system_prompt, user_prompt)`
- **Purpose**: Make HTTP request to OpenAI-compatible API
- **Parameters**:
  - `system_prompt` (string): System instructions for LLM
  - `user_prompt` (string): User's natural language request
- **Returns**: Same format as `generate_command()`
- **Features**:
  - **Retry Logic**: Attempts up to 3 times on timeout/connection errors
  - **Exponential Backoff**: Waits longer between retries (1s, 2s, 3s)
  - **Timeout**: 60-second timeout for API requests
  - **Error Handling**: Provides detailed error messages
- **Request Format**:
  - Uses `/chat/completions` endpoint
  - Sends messages array with system and user roles
  - Temperature: 0.3 (low for consistent output)
  - Max tokens: 500

#### `_call_openai_compatible_api(self, system_prompt, user_prompt)`
- **Purpose**: Wrapper for OpenAI-compatible APIs (currently same as OpenAI)
- **Parameters**: Same as `_call_openai_api()`
- **Returns**: Same format
- **Note**: Can be customized for different API providers if needed

---

## 5. Command Validator (`src/command_validator.py`)

Validates LLM-generated Bash commands using whitelist and blacklist mechanisms.

### **Class: `CommandValidator`**

#### `__init__(self)`
- **Purpose**: Initialize validator with security rules
- **Initializes**:
  - `whitelist`: List of ~200+ allowed commands (netstat, ping, df, etc.)
  - `blacklist_patterns`: Regex patterns for forbidden operations (e.g., `rm -rf /`)
  - `_shebang_patterns`: Patterns to identify and strip shebang lines
  - `restricted_commands`: Dictionary mapping commands to special validation functions

#### `validate(self, command)`
- **Purpose**: Main validation function for Bash commands
- **Parameters**:
  - `command` (string): The Bash command/script to validate
- **Returns**: Dictionary with:
  - `valid` (bool): Whether command is safe
  - `reason` (string): Reason for rejection (if invalid)
- **Validation Process**:
  1. **Empty Check**: Rejects empty commands
  2. **Comment Removal**: Strips comments from command
  3. **Shebang Removal**: Removes shebang lines (e.g., `#!/bin/bash`)
  4. **Quote Stripping**: Removes surrounding quotes if present
  5. **Blacklist Check**: Scans for forbidden patterns (e.g., `rm -rf /`)
  6. **Command Parsing**: Splits command by `;`, `&&`, `||`, `|` to check each part
  7. **Whitelist Check**: Verifies each command is in the whitelist
  8. **Builtin Check**: Allows safe shell builtins (echo, test, etc.)
  9. **Restricted Command Check**: Applies special validation for dangerous commands (rm, kill, sudo, etc.)
- **Logging**: Logs warnings when commands are rejected

#### `normalize_for_execution(self, command)`
- **Purpose**: Prepare command for execution by removing shebang and quotes
- **Parameters**:
  - `command` (string): Command to normalize
- **Returns**: Normalized command string
- **Behavior**:
  - Strips shebang lines
  - Removes one level of surrounding quotes
  - Ensures command can be executed by shell without syntax errors

#### `_strip_shebang(self, command)`
- **Purpose**: Remove shebang lines from command
- **Parameters**:
  - `command` (string): Command with potential shebang
- **Returns**: Command without shebang lines
- **Patterns**: Matches `#!/bin/bash`, `#!/bin/sh`, `!/bin/bash`, etc.

#### `_get_shell_control_keywords(self)`
- **Purpose**: Get list of shell control structure keywords
- **Returns**: Set of keywords: `for`, `do`, `done`, `while`, `if`, `then`, `else`, `elif`, `fi`, `case`, `esac`, `in`
- **Usage**: Used to skip control structures during command parsing

#### `_is_safe_builtin(self, command)`
- **Purpose**: Check if command is a safe shell builtin
- **Parameters**:
  - `command` (string): Command name to check
- **Returns**: Boolean
- **Safe Builtins**: echo, printf, test, cd, pwd, read, export, alias, etc. (non-destructive operations)

#### `_validate_rm(self, command_part)`
- **Purpose**: Special validation for `rm` (remove) command
- **Parameters**:
  - `command_part` (string): The part of command containing `rm`
- **Returns**: Dictionary with `valid` and `reason`
- **Restrictions**: Blocks `rm -rf` on:
  - Root directory (`/`)
  - System directories (`/etc`, `/usr`, `/var`, `/boot`)

#### `_validate_kill(self, command_part)`
- **Purpose**: Special validation for `kill`, `killall`, `pkill` commands
- **Parameters**:
  - `command_part` (string): The part of command containing kill command
- **Returns**: Dictionary with `valid` and `reason`
- **Restrictions**: Blocks killing process ID 1 (init process)

#### `_validate_passwd(self, command_part)`
- **Purpose**: Special validation for `passwd` command
- **Parameters**:
  - `command_part` (string): The part of command containing `passwd`
- **Returns**: Dictionary with `valid` and `reason`
- **Restrictions**: Blocks changing root password

#### `_validate_su(self, command_part)`
- **Purpose**: Special validation for `su` (switch user) command
- **Parameters**:
  - `command_part` (string): The part of command containing `su`
- **Returns**: Dictionary with `valid` and `reason`
- **Restrictions**: Blocks root execution if `Config.ALLOW_ROOT_EXECUTION` is `False`

#### `_validate_sudo(self, command_part)`
- **Purpose**: Special validation for `sudo` command
- **Parameters**:
  - `command_part` (string): The part of command containing `sudo`
- **Returns**: Dictionary with `valid` and `reason`
- **Restrictions**: Blocks sudo execution if `Config.ALLOW_ROOT_EXECUTION` is `False`

---

## 6. SSH Executor (`src/ssh_executor.py`)

Handles secure remote command execution using SSH (Paramiko library).

### **Class: `SSHExecutor`**

#### `__init__(self)`
- **Purpose**: Initialize SSH executor with authentication configuration
- **Loads from Config**:
  - `SSH_USER`: Username (can be in format "user@host" or just "user")
  - `SSH_PASSWORD`: Password for authentication (if using password auth)
  - `SSH_KEY_PATH`: Path to SSH private key file
  - `SSH_AGENT_SOCKET`: Path to SSH agent socket (if using agent)
- **Behavior**: Parses `SSH_USER` to extract username if it contains `@`

#### `execute_on_servers(self, command, servers, username, user_id=None, original_request='')`
- **Purpose**: Execute command on multiple remote servers
- **Parameters**:
  - `command` (string): Bash command to execute
  - `servers` (list): List of server hostnames/IPs
  - `username` (string): Username of the user executing (for logging)
  - `user_id` (int, optional): User ID for database logging
  - `original_request` (string, optional): Original natural language request
- **Returns**: Dictionary mapping server names to execution results
- **Behavior**:
  - Iterates through each server
  - Calls `_execute_on_server()` for each
  - Collects results
  - Logs execution to database using `_log_execution()`
- **Error Handling**: Catches exceptions per server and returns error result

#### `_execute_on_server(self, server, command)`
- **Purpose**: Execute command on a single remote server
- **Parameters**:
  - `server` (string): Server hostname or IP address
  - `command` (string): Bash command to execute
- **Returns**: Dictionary with:
  - `success` (bool): Whether command executed successfully
  - `stdout` (string): Standard output from command
  - `stderr` (string): Standard error from command
  - `exit_code` (int): Command exit code (0 = success)
  - `error` (string): Error message (if connection/execution failed)
- **Process**:
  1. **SSH Client Creation**: Creates Paramiko SSHClient
  2. **Host Key Policy**: Sets `AutoAddPolicy` (accepts unknown host keys)
  3. **Authentication**: Tries in order:
     - SSH key file (RSA or Ed25519, explicitly avoids DSA)
     - SSH agent socket
     - Password authentication
  4. **Connection**: Connects with 30-second timeout, retries up to 2 times
  5. **Command Execution**: 
     - For multi-line scripts: Wraps in heredoc to avoid quoting issues
     - Executes with 60-second timeout
  6. **Output Collection**: Reads stdout, stderr, and exit code
  7. **Cleanup**: Closes SSH connection
- **Error Handling**: Handles:
  - Authentication failures
  - SSH exceptions (timeout, DNS resolution, network unreachable)
  - Socket timeouts
  - Generic exceptions

#### `_log_execution(self, username, user_id, original_request, command, servers, results)`
- **Purpose**: Log command execution to database for audit trail
- **Parameters**:
  - `username` (string): Username who executed command
  - `user_id` (int): User ID
  - `original_request` (string): Original natural language request
  - `command` (string): Generated Bash command
  - `servers` (list): List of target servers
  - `results` (dict): Execution results from each server
- **Returns**: None
- **Behavior**:
  - Determines overall status: `success`, `failed`, or `partial`
  - Creates `ExecutionLog` database entry with:
    - User information
    - Original request and generated command
    - Target servers (JSON string)
    - Execution status
    - Results (JSON string)
    - Timestamp
  - Commits to database
- **Error Handling**: Logs errors but doesn't fail execution

---

## 7. Database Models (`src/models.py`)

Defines database schema using SQLAlchemy ORM.

### **Class: `User` (extends `UserMixin`, `db.Model`)**

Represents a user account in the system.

**Database Columns:**
- `id` (Integer, Primary Key): Unique user ID
- `username` (String, Unique, Not Null): Username
- `email` (String, Unique, Not Null): Email address
- `password_hash` (String, Not Null): Hashed password (not plain text)
- `created_at` (DateTime): Account creation timestamp
- `is_admin` (Boolean, Default: False): Admin flag

**Relationships:**
- `executions`: One-to-many relationship with `ExecutionLog` (backref)

#### `set_password(self, password)`
- **Purpose**: Hash and store password securely
- **Parameters**:
  - `password` (string): Plain text password
- **Returns**: None
- **Behavior**: Uses Werkzeug's `generate_password_hash()` to create secure hash

#### `check_password(self, password)`
- **Purpose**: Verify if provided password matches stored hash
- **Parameters**:
  - `password` (string): Plain text password to verify
- **Returns**: Boolean (True if password matches)
- **Behavior**: Uses Werkzeug's `check_password_hash()` for secure comparison

#### `__repr__(self)`
- **Purpose**: String representation for debugging
- **Returns**: String like `"<User admin>"`

### **Class: `ExecutionLog` (extends `db.Model`)**

Stores audit log of all command executions.

**Database Columns:**
- `id` (Integer, Primary Key): Unique log entry ID
- `user_id` (Integer, Foreign Key): Reference to User who executed
- `username` (String, Not Null): Username (denormalized for quick access)
- `original_request` (Text, Not Null): Original natural language request
- `generated_command` (Text, Not Null): Bash command generated by LLM
- `target_servers` (Text, Not Null): JSON string of server list
- `execution_status` (String, Not Null): "success", "failed", or "partial"
- `execution_results` (Text): JSON string of results from each server
- `timestamp` (DateTime): Execution timestamp

**Relationships:**
- `user`: Many-to-one relationship with `User`

#### `__repr__(self)`
- **Purpose**: String representation for debugging
- **Returns**: String like `"<ExecutionLog 1 by admin>"`

---

## 8. Configuration (`src/config.py`)

Centralized configuration management using environment variables.

### **Class: `Config`**

All configuration values are loaded from environment variables (via `.env` file) with fallback defaults.

**Configuration Variables:**

- **Flask Configuration:**
  - `SECRET_KEY`: Secret key for session encryption (default: 'dev-secret-key-change-in-production')
  - `SQLALCHEMY_DATABASE_URI`: Database connection string (default: 'sqlite:///shellsentry.db')
  - `SQLALCHEMY_TRACK_MODIFICATIONS`: Disabled for performance

- **LLM Configuration:**
  - `LLM_API_TYPE`: Type of API ("openai" or compatible, default: "openai")
  - `LLM_API_KEY`: API key for LLM service (required)
  - `LLM_API_BASE_URL`: Base URL for API (default: Groq endpoint)
  - `LLM_MODEL`: Model name to use (default: "llama-3.1-8b-instant")

- **SSH Configuration:**
  - `SSH_USER`: SSH username (can be "user@host" format)
  - `SSH_PASSWORD`: SSH password (if using password auth)
  - `SSH_KEY_PATH`: Path to SSH private key (default: "~/.ssh/id_rsa")
  - `SSH_AGENT_SOCKET`: Path to SSH agent socket (optional)

- **Remote Servers:**
  - `REMOTE_SERVERS`: Comma-separated list of server hostnames/IPs

- **Security Settings:**
  - `ALLOW_ROOT_EXECUTION`: Allow sudo/root execution (default: false)
  - `LOG_LEVEL`: Logging level (default: "INFO")

**Note**: Uses `python-dotenv` to load variables from `.env` file.

---

## 9. Logger (`src/logger.py`)

Sets up application-wide logging.

### **Function: `setup_logger(name='ShellSentry', log_file='shellsentry.log')`**

- **Purpose**: Configure and return application logger
- **Parameters**:
  - `name` (string): Logger name (default: "ShellSentry")
  - `log_file` (string): Path to log file (default: "shellsentry.log")
- **Returns**: `logging.Logger` object
- **Configuration**:
  - **Log Level**: Set from `Config.LOG_LEVEL` (default: INFO)
  - **Console Handler**: Outputs to console (INFO level)
  - **File Handler**: Outputs to file (DEBUG level for detailed logs)
  - **Format**: `"%(asctime)s - %(name)s - %(levelname)s - %(message)s"`
- **Behavior**:
  - Prevents duplicate handlers (returns existing logger if already configured)
  - Handles file handler creation errors gracefully

---

## 10. Frontend JavaScript (`static/js/dashboard.js`)

Client-side JavaScript for the dashboard interface.

### **Functions:**

#### `fillExample(command)`
- **Purpose**: Fill the command input field with an example command
- **Parameters**:
  - `command` (string): Example command text
- **Returns**: None
- **Behavior**: Sets input value and focuses the input field

#### `displayResults(data)`
- **Purpose**: Display execution results in the UI
- **Parameters**:
  - `data` (object): Response data from `/api/execute` endpoint
- **Returns**: None
- **Behavior**:
  - Shows generated Bash command
  - Shows original request
  - Displays results for each server:
    - Server name
    - Success/failure status
    - Standard output
    - Standard error
    - Exit code
  - Handles error responses
- **HTML Generation**: Creates result cards with proper styling

#### `escapeHtml(text)`
- **Purpose**: Escape HTML special characters to prevent XSS attacks
- **Parameters**:
  - `text` (string): Text to escape
- **Returns**: Escaped HTML string
- **Security**: Critical for preventing cross-site scripting attacks

### **Event Listeners:**

#### Form Submission Handler
- **Event**: Form submit on `#commandForm`
- **Behavior**:
  1. Prevents default form submission
  2. Validates input (checks if command is provided)
  3. Parses server list (comma-separated)
  4. Disables button and shows loading spinner
  5. Makes POST request to `/api/execute` with:
     - 2-minute timeout
     - JSON body with command and servers
  6. On success: Calls `displayResults()` and scrolls to results
  7. On error: Shows error message with troubleshooting tips
  8. Re-enables button after completion
- **Error Handling**: Provides user-friendly error messages for:
  - Timeout errors
  - Network errors
  - API errors

---

## 11. Entry Point (`run.py`)

Simple script to run the Flask application.

### **Main Execution Block**

- **Purpose**: Start the Flask development server
- **Behavior**:
  - Prints welcome message with project name
  - Displays default admin credentials
  - Shows warning about changing default password
  - Displays server URL (http://localhost:5001)
  - Starts Flask app with:
    - Debug mode enabled
    - Host: 0.0.0.0 (accessible from network)
    - Port: 5001

---

## Summary of Security Flow

1. **User Input** → `SecurityLayer.validate_input()` → Blocks malicious patterns
2. **LLM Generation** → `LLMClient.generate_command()` → Converts to Bash
3. **Command Validation** → `CommandValidator.validate()` → Whitelist/blacklist check
4. **Remote Execution** → `SSHExecutor.execute_on_server()` → Secure SSH execution
5. **Audit Logging** → `SSHExecutor._log_execution()` → Database logging

---

## Key Design Patterns

1. **Separation of Concerns**: Each module has a single responsibility
2. **Defense in Depth**: Multiple validation layers (input → LLM → command → execution)
3. **Fail-Safe Defaults**: Commands are blocked unless explicitly allowed
4. **Audit Trail**: All executions are logged to database
5. **Error Handling**: Comprehensive error handling at each layer
6. **Retry Logic**: Network operations have retry mechanisms

---

This documentation covers all functions and methods in your ShellSentry project. Use this as a reference when explaining your program to your professor!


