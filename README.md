# ShellSentry (LLM-to-Bash)

Web application that turns **natural language** into **Bash** commands using an **OpenAI-compatible LLM**, validates them in layers, and runs them on **remote Linux hosts** over **SSH** (Paramiko). Built for **educational and controlled** environments.

---

## What it does

1. User signs in and describes a task in plain English (optionally lists target hosts).
2. The server validates the text, probes hosts (OS, services, listening ports), optionally **retrieves** similar command examples (**RAG**), and asks the LLM for one command to run **per host**.
3. Generated commands pass **whitelist / blacklist** checks and optional **read-only** policy.
4. Commands execute over SSH; results return as JSON plus plain-language summary and a formatted report; an optional second LLM call can explain the report for non-experts.

---

## Features

- **Authentication** — Register, login, logout; password hashing and policy (`src/auth.py`).
- **LLM integration** — OpenAI-compatible `chat/completions` via `requests` (`src/llm_client.py`); retries for timeouts and rate limits.
- **RAG grounding** — `sentence-transformers` + **FAISS** over a small curated command knowledge base (`src/rag_pipeline.py`). If the index fails to load, retrieval is skipped safely.
- **Host context** — Before generation, SSH probes: `uname`, systemd unit sample, `ss` listeners (`src/ssh_executor.py`).
- **Multi-layer security** — User input rules (`src/security.py`), command validation including **read-only mode** (`src/command_validator.py`).
- **Remote execution** — Keys, password, optional SSH agent, optional per-server credentials (`SERVER_CREDENTIALS`).
- **Audit trail** — `ExecutionLog` in the database; file + console logging (`src/logger.py`).
- **Dashboard** — Jinja templates + `static/js/dashboard.js` calling `POST /api/execute`.

---

## Architecture (data flow)

```
User (browser)
    → Flask (auth, dashboard)
    → SecurityLayer (user text)
    → SSHExecutor.probe_host_context (per host)
    → RagPipeline.retrieve (optional)
    → LLMClient.generate_command
    → CommandValidator.validate + normalize_for_execution
    → SSHExecutor.execute_on_servers
    → result_formatter + optional LLMClient.summarize_execution_report
    → JSON + UI
```

---

## Prerequisites

- Python 3.8+
- LLM API key for an OpenAI-compatible endpoint (defaults in `env.example` point at Groq; override as needed).
- SSH access to target Linux hosts (key and/or password as configured).
- RAG stack: `sentence-transformers` and `faiss-cpu` (listed in `requirements.txt`).

---

## Quick start

1. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment** — Copy `env.example` to `.env` and set at minimum:

   - `SECRET_KEY`
   - `LLM_API_KEY`, `LLM_API_BASE_URL`, `LLM_MODEL`
   - `SSH_USER` (and `SSH_PASSWORD` or key path)
   - `REMOTE_SERVERS` (comma-separated hostnames or IPs)

3. **Run the app**

   ```bash
   python run.py
   ```

   Default dev URL: `http://localhost:5001`

4. **First user** — Use **Register** to create an account (there is no guaranteed default admin user in code; change any printed dev credentials if you add them manually).

5. **Optional** — Run `python test_llm.py` to verify LLM connectivity.

---

## Configuration (summary)

| Variable | Purpose |
|----------|---------|
| `SECRET_KEY` | Flask session signing |
| `DATABASE_URL` | SQLAlchemy URL (default SQLite `shellsentry.db`) |
| `LLM_API_KEY`, `LLM_API_BASE_URL`, `LLM_MODEL`, `LLM_API_TYPE` | LLM endpoint |
| `SSH_USER`, `SSH_PASSWORD`, `SSH_KEY_PATH`, `SSH_AGENT_SOCKET` | Default SSH auth |
| `SERVER_CREDENTIALS` | Per-host `IP:username:password` entries (comma-separated) |
| `REMOTE_SERVERS` | Default target hosts when the UI leaves servers empty |
| `ALLOW_ROOT_EXECUTION` | Allow `sudo` / root-style paths in validation (`false` by default) |
| `READ_ONLY_EXECUTION` | Strict non-mutating command policy (`true` by default) |
| `LOG_LEVEL` | Logging verbosity |

Full detail: `env.example` and `src/config.py`.

---

## Project structure

```
ShellSentry/
├── README.md
├── run.py                      # Dev server entry (port 5001)
├── test_llm.py                 # LLM connectivity check
├── requirements.txt
├── env.example
├── src/
│   ├── __init__.py
│   ├── app.py                  # Routes, execute pipeline, error handlers
│   ├── config.py
│   ├── models.py               # User, ExecutionLog
│   ├── auth.py
│   ├── security.py             # User input validation
│   ├── llm_client.py
│   ├── rag_pipeline.py
│   ├── command_validator.py
│   ├── ssh_executor.py
│   ├── result_formatter.py
│   └── logger.py
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   └── errors/error.html
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── dashboard.js
└── MdFiles/
    ├── projectDescription.md              # Product/architecture narrative
    └── SHELLSENTRY_SYSTEM_DOCUMENTATION.md # Deep technical reference
```

---

## HTTP API (authenticated unless noted)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/execute` | Main NL → command → SSH pipeline (JSON body: `command`, optional `servers`) |
| `GET` | `/api/servers` | Configured `REMOTE_SERVERS` list |
| `GET` | `/api/health` | Health + whether LLM/SSH/servers appear configured (no auth) |

Pages: `/`, `/login`, `/register`, `/dashboard`, `/logout`.

---

## Documentation

- **[MdFiles/projectDescription.md](MdFiles/projectDescription.md)** — Problem statement, goals, and high-level architecture (from project brief).
- **[MdFiles/SHELLSENTRY_SYSTEM_DOCUMENTATION.md](MdFiles/SHELLSENTRY_SYSTEM_DOCUMENTATION.md)** — Features, techniques, stack, module map, and step-by-step `execute` flow.

---

## Security notes

Designed for **labs and controlled use**, not as-is for open production.

- Prefer **least-privilege** SSH users, strong keys, and **HTTPS** when exposed beyond localhost.
- **Read-only mode** is on by default; review `src/command_validator.py` if you change policy.
- Review **execution logs** and rotate credentials; keep dependencies updated.

---

## Limitations

- Command quality depends on the **LLM**; validation cannot cover every edge case.
- Large **whitelist**; tighten for stricter sites if needed.
- UI is **functional**, not a design showcase.

---

## Future ideas

Role-based access control, dry-run/simulation mode, richer audit UI, SIEM hooks, additional scripting targets—see `projectDescription.md` for a longer list.

---

## License

Educational / project use unless you attach another license.

---

## Contributing

Contributions welcome; please keep security-related behavior explicit in PR descriptions and run through the validation paths you touch.
