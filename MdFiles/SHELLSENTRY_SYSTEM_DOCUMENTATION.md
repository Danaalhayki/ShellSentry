# ShellSentry (LLM-to-Bash) — System Documentation

This document describes the **ShellSentry** codebase: features, techniques, technologies, code layout, and end-to-end request flow. It is written for **technical reporting** and deep onboarding.

---

## 1. Project overview

**ShellSentry** is a web application that:

1. Authenticates users.
2. Accepts a **natural language** task description and optional **target hostnames/IPs**.
3. **Validates** the user’s text for unsafe patterns and prompt-injection style phrases.
4. **Probes** remote Linux hosts over SSH to collect lightweight **host context** (OS, running services, listening ports).
5. Optionally **retrieves** similar command examples via a **RAG (retrieval)** layer to ground the LLM.
6. Calls an **OpenAI-compatible** LLM to produce a **Bash command or short script** (one command to run per target).
7. **Validates** the generated command (whitelist, blacklist, optional **read-only** policy).
8. **Executes** the command on one or more servers via **Paramiko (SSH)**, with logging to the database.
9. Returns a **plain-language summary**, a **formatted technical report**, and an optional **LLM-generated explanation** of the run.

The high-level product goal matches `projectDescription.md`: *natural language → validated Bash → secure remote execution*, with the implementation adding **RAG**, **host-aware prompting**, and **stricter read-only execution** than the static doc alone implies.

---

## 2. Features (as implemented in code)

| Area | Feature |
|------|--------|
| **Auth** | Register, login, logout; passwords hashed (Werkzeug); password policy (length, mixed case, digit; blocks shell-dangerous characters). |
| **Dashboard** | Authenticated page to submit NL requests and optional server list. |
| **API** | `POST /api/execute` — main pipeline; `GET /api/servers` — configured server list; `GET /api/health` — health and config flags. |
| **User input security** | Keyword blocklist, regex “dangerous” patterns, prompt-injection style patterns, length limit, control-character strip. |
| **Host context** | Before LLM: per-host SSH session runs `uname -a`, `systemctl list-units` (sample), `ss -tlnp` / `ss -ulnp` (sample), truncated with `head`. |
| **RAG** | Optional retrieval from a static knowledge base; **sentence-transformers** embedding + **FAISS** similarity search; top-k examples appended to the LLM user prompt. |
| **LLM** | `generate_command`: system rules (no `ssh` fan-out, prefer grounding examples, use host context); retries on timeout, connection errors, HTTP 429. |
| **Output cleanup** | Strips markdown fences, shell prompts, backticks from model output. |
| **Command validation** | Whitelist of command bases; blacklist regexes; special handlers for `rm`, `kill*`, `passwd`, `su`, `sudo`; optional **read-only** mode with extra rules (no sudo, no file redirects except safe cases, no mutating `systemctl` / `journalctl` vacuum, etc.). |
| **Execution** | SSH per host; multiline commands sent via **bash heredoc**; stdout/stderr/exit code; per-server and overall status. |
| **Auditing** | `ExecutionLog` rows: user, original request, generated command, targets, JSON results, timestamp; file + console logging. |
| **UX** | `result_formatter` builds non-technical summary + monospace report; second LLM call can **summarize** the report in plain language. |
| **Errors** | Branded Jinja2 error pages for 400/403/404/405/500; API returns `natural_language_summary` for failures. |

---

## 3. Techniques and design patterns

- **Defense in depth**: user-text checks → LLM (constrained by prompt) → **command** whitelist/blacklist → optional read-only policy → SSH.
- **Grounding (RAG)**: retrieve similar *trusted* (hand-authored) `description → command` pairs to reduce wild hallucinations; cached queries (LRU) to limit embedding work.
- **Context-aware generation**: host snapshot text steers tool/path choices (e.g., services visible on the host).
- **Idempotent / single-shot remote command**: LLM is instructed to output **one** command for the app to run on each target, not a loop over hosts (the app handles multi-host).
- **Safe multiline execution**: `bash -s << 'SHELLSENTRY_EOF'` avoids quoting bugs on scripts.
- **Read-only default**: `READ_ONLY_EXECUTION` (default `true`) blocks state-changing patterns even if whitelisted in the broad list.
- **API UX**: structured JSON for UI; human-readable `natural_language_summary` and `format_error_summary` for errors.
- **Resilience**: LLM HTTP retries, SSH connect retries, graceful RAG failure (empty retrieval if index fails to build).

---

## 4. Technologies and dependencies

| Layer | Technology |
|-------|------------|
| **Runtime** | Python 3.8+ (typical) |
| **Web framework** | Flask 3, Jinja2 templates |
| **Session / auth** | Flask-Login |
| **Persistence** | Flask-SQLAlchemy; default SQLite via `DATABASE_URL` |
| **Passwords** | Werkzeug `generate_password_hash` / `check_password_hash` |
| **Config** | `python-dotenv` → `src.config.Config` |
| **LLM** | HTTPS `requests` to OpenAI-compatible `.../chat/completions` (OpenAI, Groq, Ollama-compatible, etc.) |
| **SSH** | Paramiko (RSA/Ed25519 keys, password, optional `SSH_AGENT_SOCKET`, per-server `SERVER_CREDENTIALS`) |
| **RAG** | `sentence-transformers` (e.g. `all-MiniLM-L6-v2`), `faiss-cpu` |
| **Frontend** | Server-rendered HTML + vanilla JS (`static/js/dashboard.js`), CSS under `static/css/` |

**Note:** `requirements.txt` lists `openai` but the main client path uses `requests` for chat completions. RAG is **optional at runtime** if dependencies fail: retrieval returns empty and the app continues.

---

## 5. Repository and code structure

```
ShellSentry/
├── run.py                 # Dev entry: `python run.py` (port 5001)
├── test_llm.py            # LLM connectivity helper (if present)
├── requirements.txt
├── env.example            # Environment variable template
├── src/
│   ├── app.py             # Flask routes, pipeline orchestration, error handlers
│   ├── config.py          # Config from environment
│   ├── models.py          # User, ExecutionLog
│   ├── auth.py            # register_user, authenticate_user, password policy
│   ├── security.py        # SecurityLayer: user input validation
│   ├── llm_client.py      # LLMClient: generate_command, summarize_execution_report
│   ├── rag_pipeline.py   # RagPipeline: embeddings, FAISS, retrieve, format_for_prompt
│   ├── command_validator.py  # Whitelist/blacklist, read-only rules, normalize_for_execution
│   ├── ssh_executor.py    # Paramiko: probe_host_context, execute_on_servers, logging
│   ├── result_formatter.py # Plain-language + formatted report, error summaries
│   ├── logger.py          # File + console logging
│   └── __init__.py
├── templates/             # Jinja2: index, login, register, dashboard, errors/error.html
├── static/
│   ├── css/
│   └── js/dashboard.js    # fetch /api/execute, render results
└── MdFiles/
    ├── projectDescription.md
    └── SHELLSENTRY_SYSTEM_DOCUMENTATION.md   # (this file)
```

---

## 6. End-to-end code flow (main execution path)

The central path is `POST /api/execute` in `src/app.py` → `execute_command()`.

1. **Auth**: `@login_required` ensures a logged-in user.
2. **Parse JSON**: `command` (NL text), `servers` (optional list). If `servers` is empty, use `app.config['REMOTE_SERVERS']`.
3. **Empty / config checks**: Reject empty command; reject if no targets after defaulting.
4. **SecurityLayer.validate_input(natural_language)**: blocklists, patterns, length; may return 400.
5. **SSHExecutor.probe_host_context(target_servers)**: one SSH session per host; collect OS, services, `ss` samples (or error dict per host).
6. **RagPipeline.retrieve(natural_language, top_k=3)** → **format_for_prompt** for LLM text block.
7. **LLMClient.generate_command(..., remote_host_context=host_context, rag_context_text=...)**:
   - Builds system + user messages; calls OpenAI-compatible API; cleans markdown/prompts from output.
8. **On LLM failure**: 500 with error details and friendly summary.
9. **CommandValidator.validate(generated_command)**: whitelist/blacklist/restricted/read-only; on failure 400, may include `generated_command` for debugging.
10. **CommandValidator.normalize_for_execution**: strip shebangs/quotes/backticks for actual shell.
11. **SSHExecutor.execute_on_servers(command, servers, user, user_id, original_request)**:
    - Per host: connect, `exec_command`, collect stdout/stderr/exit; **ExecutionLog** inserted.
12. **format_execution_payload**: natural language summary + monospace report.
13. **LLMClient.summarize_execution_report** (optional second call): plain-language “AI report explanation” for non-experts.
14. **JSON response**: `success`, `original_request`, `remote_host_context`, `generated_command`, `rag_retrieval`, `results`, `natural_language_summary`, `formatted_report`, `ai_report_explanation` (or error key).

**Supporting routes**

- `GET /` — landing or redirect to dashboard if logged in.  
- `GET/POST /login`, `/register`, `GET /logout`  
- `GET /dashboard` — main UI  
- `GET /api/servers` — list from config  
- `GET /api/health` — `llm_configured`, `ssh_configured`, `servers_configured`  

---

## 7. Configuration (environment)

Key variables (see `env.example` and `src/config.py`):

- **Flask / DB**: `SECRET_KEY`, `DATABASE_URL`  
- **LLM**: `LLM_API_KEY`, `LLM_API_BASE_URL`, `LLM_MODEL`, `LLM_API_TYPE`  
- **SSH**: `SSH_USER`, `SSH_PASSWORD`, `SSH_KEY_PATH`, `SSH_AGENT_SOCKET`, `SERVER_CREDENTIALS` (per-host `IP:user:pass` list)  
- **Targets**: `REMOTE_SERVERS` (comma-separated)  
- **Security**: `ALLOW_ROOT_EXECUTION`, `READ_ONLY_EXECUTION`, `LOG_LEVEL`  

---

## 8. Security and limitations (honest scope)

- **Not a full production hardening guide**: use HTTPS, secrets management, network firewalls, and least-privilege SSH users in real deployments.  
- **LLM risk**: validation reduces but cannot eliminate all creative bypass attempts; read-only mode is a strong default.  
- **Whitelist breadth**: the whitelist is large; organizational policy may want to **narrow** it for stricter sites.  
- **RAG knowledge base** includes example strings with `sudo` in static entries; **read-only validation** and prompts still constrain what actually runs.  
- **Default admin**: `run.py` prints default credentials; ensure deployment creates users and rotates passwords (auto-creation in `create_tables()` is not fully implemented in the snippet—rely on registration or manual DB user creation as your deployment does).

---

*Align any assignment or deployment wording with your actual setup and `projectDescription.md` where they differ.*
