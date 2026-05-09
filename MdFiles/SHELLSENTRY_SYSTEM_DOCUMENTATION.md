# ShellSentry (LLM-to-Bash) — System Documentation (Updated)

This document reflects the current implemented behavior of the ShellSentry codebase, including script archiving, re-execution, script explanation, and managed Safe Cron scheduling.

---

## 1. System Summary

ShellSentry is an authenticated Flask application that converts natural language into validated Bash commands and executes them on remote Linux hosts over SSH.

Main security architecture:

1. User authentication.
2. Input-level safety validation.
3. Intent routing for safe built-in actions (archive/cron modes).
4. Host-aware LLM command generation with optional RAG grounding.
5. Command policy validation (whitelist + blacklist + read-only guardrails).
6. Parallel SSH execution with audit logging.
7. User-friendly and technical result reporting.

---

## 2. Repository Structure

```text
ShellSentry/
├── run.py
├── requirements.txt
├── env.example
├── src/
│   ├── app.py
│   ├── config.py
│   ├── models.py
│   ├── auth.py
│   ├── security.py
│   ├── llm_client.py
│   ├── rag_pipeline.py
│   ├── command_validator.py
│   ├── ssh_executor.py
│   ├── result_formatter.py
│   ├── logger.py
│   └── __init__.py
├── templates/
├── static/
│   └── js/dashboard.js
└── MdFiles/
    ├── projectDescription.md
    └── SHELLSENTRY_SYSTEM_DOCUMENTATION.md
```

---

## 3. Major Modules and Responsibilities

### `src/app.py`
- Flask routes and overall orchestration.
- Main endpoint: `POST /api/execute`.
- Intent detectors:
  - `_detect_archive_intent()` for list/re-run/explain saved scripts.
  - `_detect_safe_cron_intent()` for managed cron operations.
  - `_extract_cron_expression()` and `_is_safe_cron_expr()` for cron parsing/validation.

### `src/security.py`
- `SecurityLayer.validate_input()` checks user text for unsafe patterns.

### `src/llm_client.py`
- `generate_command()` for NL->Bash generation.
- `summarize_execution_report()` for plain-language report explanation.
- `explain_script()` for plain-language explanation of saved script content.
- Host-context formatting and HTTP retry/rate-limit handling.

### `src/command_validator.py`
- Command policy engine:
  - whitelist/blacklist checks,
  - restricted command handling,
  - read-only enforcement,
  - execution normalization.

### `src/ssh_executor.py`
- Parallel SSH execution and host probing.
- Handles script archive lifecycle and Safe Cron operations:
  - `list_saved_scripts()`
  - `execute_saved_script()`
  - `get_servers_having_script()`
  - `get_saved_script_content()`
  - `find_saved_script_content_across_servers()`
  - `list_managed_cron_entries()`
  - `schedule_saved_script_cron()`

### `src/result_formatter.py`
- Creates user-facing summary and formatted technical report.

### `src/models.py`
- DB models including `ExecutionLog` for auditing.

---

## 4. API Endpoints

### `POST /api/execute` (authenticated)
Primary orchestration endpoint. Accepts:
- `command`: natural language request (required)
- `servers`: optional array of server hostnames/IPs

Returns:
- `success`
- `original_request`
- `generated_command`
- `results` (per-server output)
- `natural_language_summary`
- `formatted_report`
- optional: `remote_host_context`, `rag_retrieval`, `ai_report_explanation`, `script_explanation`, `missing_script_servers`

### `GET /api/servers` (authenticated)
Returns configured default server list.

### `GET /api/health` (public)
Returns health and basic config flags (`llm_configured`, `ssh_configured`, `servers_configured`).

---

## 5. End-to-End Execution Flow (`/api/execute`)

1. Validate authenticated session (`@login_required`).
2. Parse and validate payload (`command`, optional `servers`).
3. Apply `SecurityLayer.validate_input()`.
4. If no servers supplied, fallback to `REMOTE_SERVERS`.
5. Check Safe Cron intent (`_detect_safe_cron_intent`):
   - `list` -> `ssh_executor.list_managed_cron_entries()`
   - `schedule` -> `ssh_executor.schedule_saved_script_cron()`
   - destructive removal intent -> blocked
6. Check Script Archive intent (`_detect_archive_intent`):
   - `list` -> `ssh_executor.list_saved_scripts()`
   - `rerun` -> existence check + content validation + `execute_saved_script()`
   - `explain` -> fetch content + `llm_client.explain_script()`
7. Standard NL->Bash flow:
   - Probe host context: `ssh_executor.probe_host_context()`
   - Retrieve RAG examples: `rag_pipeline.retrieve()`
   - Generate command: `llm_client.generate_command()`
   - Validate: `command_validator.validate()`
   - Normalize: `command_validator.normalize_for_execution()`
   - Execute: `ssh_executor.execute_on_servers()`
8. Format response via `format_execution_payload()`.
9. Optional AI explanation of report via `summarize_execution_report()`.

---

## 6. Script Archive: Implemented Lifecycle

### Auto-save behavior
When execution command is multi-line, `ssh_executor._execute_on_server()` wraps and saves it on the remote host before running.

Default location:
- `$HOME/ShellSentryScripts` (from `SCRIPT_ARCHIVE_DIR_NAME`)

Filename pattern:
- `ShellSentry_<timestamp>.sh`

### Listing
- Natural language list requests trigger `list_saved_scripts()`.
- Supports date scopes: `all`, `today`, `yesterday`.
- Results are sorted and capped by `SCRIPT_ARCHIVE_MAX_LIST`.

### Re-execution
- Natural language rerun requests include a `*.sh` filename.
- Server-level existence is checked in parallel.
- Before running, script content is loaded and passed through `command_validator.validate()` using current policy.
- If valid, it runs with `bash "$HOME/<archive>/<script_name>"`.

### Script explanation
- Natural language explain requests load script content from selected servers.
- `llm_client.explain_script()` returns plain-language behavior and risk explanation.

---

## 7. Safe Cron Mode (Managed Cron)

Safe cron is focused on managed archived scripts only.

### Supported actions
- List managed entries:
  - `list_managed_cron_entries()`
  - Filters by configured tag prefix (`SAFE_CRON_TAG_PREFIX`)
- Schedule/update entry for one saved script:
  - `schedule_saved_script_cron()`
  - Replaces existing managed line for the same script, then appends new line.

### Blocked actions
- User requests to clear/remove/wipe cron are explicitly blocked at intent layer.

### Safety checks
- Cron expression must match:
  - valid macro (`@daily`, etc.) or
  - strict 5-field expression.
- Script name must be a safe `.sh` basename.
- Script must exist on target server(s).

---

## 8. Host Probe and Context-Aware Generation

Before normal LLM generation, ShellSentry probes each host (parallel SSH):
- `uname -a`
- running systemd services (sample)
- listening TCP/UDP sockets (`ss`, sample)
- target server identity/context is preserved per host so generated commands are adapted to each machine's environment.

`llm_client.generate_command()` incorporates this host snapshot and optional RAG context in the final prompt, improving command relevance per environment.

---

## 9. Reliability and Parallelism

Implemented resilience techniques in SSH and LLM paths:

- Fast SSH port reachability pre-check (port 22).
- Parallel per-server operations with bounded worker pool.
- Independent per-host outcomes (one failed host does not block others).
- LLM retry logic for timeout, connection issues, and HTTP 429 with backoff.
- Frontend request timeout and improved user-facing troubleshooting messages.

---

## 10. Security Controls in Practice

Defense-in-depth currently includes:

1. Authenticated endpoints and user sessions.
2. Input text validation (`SecurityLayer`).
3. Prompt constraints and output cleanup.
4. Command validation + optional read-only mode (`READ_ONLY_EXECUTION=true` default).
5. Script name/path constraints for archive/cron flows.
6. Re-validation before saved script re-execution.
7. Managed-only cron filtering and update logic.
8. Persistent audit logs (`ExecutionLog`) plus logger output.

---

## 11. Configuration Reference (`src/config.py`)

Core variables:

- App/DB:
  - `SECRET_KEY`
  - `DATABASE_URL`
- LLM:
  - `LLM_API_TYPE`
  - `LLM_API_KEY`
  - `LLM_API_BASE_URL`
  - `LLM_MODEL`
- SSH:
  - `SSH_USER`
  - `SSH_PASSWORD`
  - `SSH_KEY_PATH`
  - `SSH_AGENT_SOCKET`
  - `SERVER_CREDENTIALS`
- Targets:
  - `REMOTE_SERVERS`
- Security:
  - `ALLOW_ROOT_EXECUTION`
  - `READ_ONLY_EXECUTION`
  - `LOG_LEVEL`
- Script archive + cron:
  - `SCRIPT_ARCHIVE_DIR_NAME`
  - `SCRIPT_ARCHIVE_MAX_LIST`
  - `SAFE_CRON_MODE`
  - `SAFE_CRON_TAG_PREFIX`

---

## 12. Frontend Behavior (`static/js/dashboard.js`)

UI renders:
- Simple-language summary (`natural_language_summary`)
- Optional AI explanation of report (`ai_report_explanation`)
- Optional AI explanation of saved script (`script_explanation`)
- Expandable raw technical report (`formatted_report`)

It also surfaces API errors with actionable troubleshooting context.

---

## 13. Limitations and Deployment Notes

- Designed for educational/controlled environments, not unrestricted production.
- LLM-generated content remains probabilistic; policy checks mitigate but do not eliminate all risk.
- Broader production readiness would require stronger operational controls (RBAC, hardened secret management, TLS termination, SIEM pipelines, stricter command policy profiles, and security testing).
- Test setup includes an added Kali Linux target server to verify the platform works in multi-server scenarios across different Linux OS environments.

---

This documentation now aligns with the current implemented ShellSentry code paths and features.
