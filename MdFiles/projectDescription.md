# ShellSentry (LLM-to-Bash)
## Updated Project Description

ShellSentry is a secure web application that translates natural language requests into Bash commands and executes them on remote Linux servers through SSH. It is designed for cybersecurity-focused educational use, where usability and safety must be balanced.

The system combines authentication, input sanitization, host-aware LLM generation, command policy validation, and audited remote execution. It now also includes a managed script archive workflow, script re-execution, script explanation, and safe managed cron scheduling for saved scripts.

---

## 1) Motivation and Problem

System administrators and cybersecurity teams often run repetitive Linux commands across multiple servers. This creates two major problems:

1. Usability risk: users need strong CLI expertise to execute tasks quickly and correctly.
2. Security risk: mistakes, unsafe commands, or abuse can impact critical infrastructure.

LLMs reduce the usability barrier, but directly running LLM output introduces new threats such as prompt abuse, dangerous command generation, privilege misuse, and inconsistent multi-host behavior.

ShellSentry addresses this gap with defense-in-depth controls around natural-language-driven automation.

---

## 2) Core Objectives

- Convert plain-English requests into executable Bash commands.
- Enforce safety before and after LLM generation.
- Execute on one or many remote hosts with SSH.
- Return clear outputs for technical and non-technical users.
- Keep auditable logs for accountability.
- Support safer operational reuse with archived script execution and controlled scheduling.

---

## 3) End-to-End Workflow (As Implemented)

1. **Authentication**
   - User logs in through the web interface.
   - Session-protected API requires authenticated access.

2. **Natural Language Request**
   - User submits a task and optional target server list.
   - If servers are omitted, configured defaults are used.

3. **Input Security Validation**
   - `SecurityLayer` checks unsafe patterns, suspicious phrasing, and policy violations.

4. **Intent Routing (Built-in Safe Modes)**
   - Safe Cron intent: list managed cron entries or schedule an archived script.
   - Script Archive intent: list saved scripts, re-run a saved script, explain a saved script.
   - Dangerous cron removal requests are blocked by policy.

5. **Host Context Probe (Pre-LLM)**
   - SSH probe collects OS info, running services, and listening ports per host.
   - The system uses per-server identity/context (target host name plus detected OS/service state) to tailor command generation for each machine environment.
   - This improves command relevance and lowers hallucination risk.

6. **RAG Grounding**
   - Retrieval pipeline adds trusted command examples to the LLM prompt when available.

7. **LLM Generation**
   - OpenAI-compatible API generates one command/script for per-host execution.
   - Output is cleaned from markdown wrappers/backticks/prompts.

8. **Command Validation**
   - Whitelist, blacklist, and read-only policy checks enforce command safety.
   - Command is normalized before execution.

9. **Remote Execution and Script Archiving**
   - Commands execute via Paramiko SSH in parallel across servers.
   - Multi-line scripts are saved to `$HOME/ShellSentryScripts` (configurable), then executed.

10. **Result Formatting and AI Explanation**
    - Returns raw output + human-friendly summary.
    - Optional second LLM call explains technical report in plain language.

11. **Audit Logging**
    - Every execution path records metadata/results in `ExecutionLog`.

---

## 4) Key Implemented Features

### A) Secure NL-to-Bash Execution
- Natural language task input.
- Host-aware command generation.
- Multi-server parallel SSH execution.
- Structured JSON responses with summaries and technical report.

### B) Script Archive Lifecycle
- Multi-line scripts are automatically saved remotely with timestamped names:
  - `ShellSentry_YYYY-MM-DD_HH-MM-SS_nanoseconds.sh`
- Saved under:
  - `$HOME/<SCRIPT_ARCHIVE_DIR_NAME>` (default: `ShellSentryScripts`)
- Built-in operations through natural language:
  - list saved scripts (all/today/yesterday)
  - re-execute saved script
  - explain saved script content using LLM

### C) Safe Re-execution of Saved Scripts
- Script filename format is strictly validated (`*.sh` safe basename only).
- Script existence is checked per selected server.
- Script content is re-validated against current security policy before re-run.
- This prevents executing archived scripts that become non-compliant or tampered.

### D) Safe Cron Mode (Managed Scheduling)
- Detects cron-related user intent.
- Allows:
  - list only ShellSentry-managed cron entries
  - schedule/update a managed cron entry for a saved script
- Blocks:
  - destructive cron actions (clear/remove/wipe crontab)
- Adds managed tag marker:
  - `# ShellSentryManaged:<script_name>` (prefix configurable)

### E) Reliability and UX Hardening
- Fast pre-flight SSH reachability check (port 22).
- Parallel server operations to avoid one host blocking others.
- Retry/backoff for LLM API timeouts and rate limits (HTTP 429).
- Friendly natural-language error summaries.
- Optional AI explanation panel for report/script output.

---

## 5) Security Model

ShellSentry applies multiple defensive layers:

1. User authentication and protected endpoints.
2. Input sanitization and intent-level checks.
3. LLM prompt constraints + cleaned output.
4. Command whitelist/blacklist and restricted patterns.
5. Read-only mode (enabled by default).
6. Script re-validation before archive re-execution.
7. Managed-only cron scheduling boundaries.
8. Execution logging to database and file/console logs.

---

## 6) Technology Stack

- **Backend:** Python, Flask, Flask-Login, Flask-SQLAlchemy
- **LLM integration:** OpenAI-compatible `chat/completions` API via `requests`
- **SSH execution:** Paramiko
- **Retrieval:** `sentence-transformers` + `faiss-cpu`
- **Frontend:** Jinja templates + HTML/CSS + Vanilla JavaScript
- **Targets:** Linux remote servers

---

## 7) High-Level Architecture

```text
User (Dashboard)
   -> Flask API (/api/execute)
   -> Security validation + intent detection
   -> (A) Safe Cron / Script-Archive built-in action
      OR
   -> (B) Host probe -> RAG retrieval -> LLM generate -> command validation
   -> SSH parallel executor (Paramiko)
   -> Result formatter + optional LLM explanation
   -> JSON response + UI rendering + DB audit log
```

---

## 8) Scope and Current Limitations

- Intended for educational/lab/controlled environments.
- Security policies reduce risk but cannot eliminate all LLM-related edge cases.
- Command whitelist is broad and may need narrowing for strict deployments.
- Not a full production hardening package (RBAC/secrets/SIEM/deployment controls should be added externally).
- Validation environment was expanded by adding a Kali Linux server as an additional target to confirm multi-server execution behavior across different Linux distributions.

---

## 9) Realistic Future Enhancements

- Role-based access control and command policy per role.
- Dry-run/simulation mode before real execution.
- Stronger script integrity (e.g., hashing/signature checks).
- Rich audit dashboard and SIEM integration.
- Extended support for additional automation targets and script types.

---

## 10) Conclusion

ShellSentry demonstrates a practical and security-aware approach to AI-assisted system administration. Beyond NL-to-command translation, the implemented architecture now covers host-aware generation, script archival/reuse, safe managed cron scheduling, policy-gated re-execution, and auditable multi-host execution.

