# Configuration Guide - Where to Find Each Value

## 1. SECRET_KEY ✅ (Generated for you!)

**Generated Key:** `fb50b79c58997a8b88f8a5e6bd20c347cbe39e71049bda11fcb9dc9ac69572b4`

This is a secure random key that has been generated for you. It's used by Flask for session management and security.

**Location in .env:**
```
SECRET_KEY=fb50b79c58997a8b88f8a5e6bd20c347cbe39e71049bda11fcb9dc9ac69572b4
```

---

## 2. LLM_API_KEY (You need to obtain this)

### Option A: OpenAI API (Recommended for testing)

1. **Go to:** https://platform.openai.com/
2. **Sign up** or **Log in** to your account
3. **Navigate to:** API Keys section (https://platform.openai.com/api-keys)
4. **Click:** "Create new secret key"
5. **Copy** the key (it starts with `sk-...`)
6. **Paste** it in your `.env` file

**Location in .env:**
```
LLM_API_KEY=sk-your-actual-key-here
```

**Note:** OpenAI API requires a paid account with credits. Free tier may have limited access.

### Option B: Local LLaMA/Compatible API

If you're running a local LLaMA server or using a compatible API:

1. **Set up** your local LLM server (e.g., using Ollama, llama.cpp, etc.)
2. **Get** the API endpoint URL
3. **Update** in `.env`:
   ```
   LLM_API_BASE_URL=http://localhost:11434/v1  # Example for Ollama
   LLM_API_KEY=not-needed-for-local  # May not be required
   LLM_MODEL=llama2  # Your model name
   ```

### Option C: Other Compatible APIs

- **Anthropic Claude:** https://console.anthropic.com/
- **Google Gemini:** https://makersuite.google.com/app/apikey
- **Hugging Face:** https://huggingface.co/settings/tokens
- **LocalAI:** https://localai.io/

---

## 3. SSH_USER (Your Linux/Server Username)

This is the username you use to SSH into your remote Linux servers.

**How to find it:**
- It's the username you type when connecting: `ssh username@server.com`
- Common examples: `root`, `ubuntu`, `admin`, `yourname`
- On your local machine, you can check with: `whoami` (on Linux/Mac) or `$env:USERNAME` (on Windows PowerShell)

**Location in .env:**
```
SSH_USER=your-actual-username
```

**Examples:**
```
SSH_USER=ubuntu
SSH_USER=root
SSH_USER=admin
SSH_USER=danah
```

---

## 4. REMOTE_SERVERS (List of servers to connect to)

These are the hostnames or IP addresses of the Linux servers where you want to execute commands.

**Format:** Comma-separated list (no spaces, or spaces after commas)

**Location in .env:**
```
REMOTE_SERVERS=server1.example.com,server2.example.com
```

**Examples:**

### Using Hostnames:
```
REMOTE_SERVERS=web1.example.com,web2.example.com,db.example.com
```

### Using IP Addresses:
```
REMOTE_SERVERS=192.168.1.10,192.168.1.11,192.168.1.12
```

### Mix of Both:
```
REMOTE_SERVERS=server1.com,192.168.1.10,server2.example.com
```

### Single Server:
```
REMOTE_SERVERS=myserver.example.com
```

**How to find your servers:**
- If you have VPS/Cloud servers: Check your hosting provider dashboard (AWS, DigitalOcean, Linode, etc.)
- If you have local servers: Use their IP addresses (e.g., `192.168.1.x`)
- If you have domain names: Use the hostnames
- Test connection: `ssh username@server.com` to verify

**Important:** Make sure you have SSH key-based authentication set up for these servers!

---

## Quick Setup Checklist

- [ ] ✅ SECRET_KEY - Generated (already done)
- [ ] ⬜ LLM_API_KEY - Get from OpenAI or set up local LLM
- [ ] ⬜ SSH_USER - Your SSH username
- [ ] ⬜ REMOTE_SERVERS - List your server hostnames/IPs
- [ ] ⬜ SSH_KEY_PATH - Verify your SSH key path (default: `~/.ssh/id_rsa`)

---

## Example Complete .env File

```env
# Flask Configuration
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=fb50b79c58997a8b88f8a5e6bd20c347cbe39e71049bda11fcb9dc9ac69572b4

# Database
DATABASE_URL=sqlite:///shellsentry.db

# LLM API Configuration
LLM_API_TYPE=openai
LLM_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
LLM_API_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-3.5-turbo

# SSH Configuration
SSH_USER=ubuntu
SSH_KEY_PATH=~/.ssh/id_rsa
SSH_AGENT_SOCKET=

# Remote Servers (comma-separated)
REMOTE_SERVERS=192.168.1.10,192.168.1.11

# Security Settings
ALLOW_ROOT_EXECUTION=false
LOG_LEVEL=INFO
```

---

## Need Help?

- **For OpenAI API:** Visit https://platform.openai.com/docs
- **For SSH Setup:** See QUICKSTART.md section on SSH
- **For Testing:** You can test with a single local server first

