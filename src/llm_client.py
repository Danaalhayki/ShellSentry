import json
import re
import time
import requests
from typing import Optional
from .logger import setup_logger
from .config import Config

logger = setup_logger()


def _extract_json_object(text: str) -> Optional[dict]:
    """Parse first JSON object from model output (allows ```json fences)."""
    if not text or not str(text).strip():
        return None
    raw = str(text).strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{[\s\S]*\}", raw)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    return None


def _retry_after_seconds(response) -> Optional[int]:
    """Parse Retry-After header (seconds) if present and sane."""
    raw = (response.headers or {}).get("Retry-After")
    if not raw:
        return None
    try:
        sec = int(float(str(raw).strip().split()[0]))
        if 0 < sec <= 300:
            return sec
    except (ValueError, TypeError, IndexError):
        pass
    return None


class LLMClient:
    """Client for interacting with LLM API (OpenAI/LLaMA)"""
    
    def __init__(self):
        self.api_key = Config.LLM_API_KEY
        self.api_base = Config.LLM_API_BASE_URL
        self.model = Config.LLM_MODEL
        self.api_type = Config.LLM_API_TYPE
    
    def classify_execution_route(self, user_text: str):
        """
        Ask the LLM to classify the request into ShellSentry routes.
        Returns dict: success, route, script_name, cron_expression, date_scope,
        calendar_day, execution_style, error.

        Backend still enforces policy; regex fallback runs if this fails.
        """
        if not self.api_key:
            return {
                "success": False,
                "route": None,
                "error": "LLM API key not configured",
            }

        system_prompt = """You classify user requests for ShellSentry, a tool that runs Bash on remote Linux servers over SSH.

Return ONE JSON object only (no markdown, no prose). Keys:
- "route": one of:
  - "cron_list" — user wants to VIEW ShellSentry-managed cron lines only (safe list).
  - "cron_schedule" — user wants to SCHEDULE or UPDATE a recurring job for an EXISTING saved script file (*.sh) in their home archive using cron syntax or macros (@daily, etc.).
  - "cron_forbidden" — user wants to DELETE, CLEAR, WIPE, or REMOVE crontab/cron entries (destructive). Never allow these through.
  - "archive_list" — user wants to LIST saved ShellSentry archive scripts (optionally today/yesterday/specific day).
  - "archive_rerun" — user wants to RUN AGAIN an existing saved *.sh from the archive.
  - "archive_explain" — user wants an EXPLANATION of what a saved *.sh script does.
  - "archive_forbidden" — user wants to DELETE, EDIT, APPEND, RENAME, MOVE, or OTHERWISE MODIFY archived scripts or replace crontab lines outside managed scheduling. Block these.
  - "normal_command" — ordinary one-line or simple inspection command (disk, network, processes, etc.) — not cron/archive workflow.
  - "script_command" — user needs a multi-line Bash script or non-trivial script block generated and run (still subject to server validation).
  - "unclear" — cannot tell; the app will use keyword fallback.

Optional keys (use null if unknown):
- "script_name": basename like "ShellSentry_2026-01-01_12-00-00_123456789.sh" if mentioned or inferable.
- "cron_expression": 5-field cron or allowed macro (@daily, @hourly, …) if scheduling.
- "date_scope": "all" | "today" | "yesterday" | "day" (for archive_list).
- "calendar_day": "YYYY-MM-DD" when listing scripts for one calendar day.

Rules you MUST follow when choosing route:
1) Cron: Only "cron_list" or "cron_schedule" are allowed for cron topics. Any destructive crontab edit intent → "cron_forbidden".
2) Scheduling must reference an existing archived script name (*.sh). Do not invent filenames.
3) Saved scripts: ONLY list, rerun, explain are allowed workflows. Any delete/modify/archive tampering → "archive_forbidden".
4) Typos and informal language: infer intent (e.g. "chrontab", "corn job") toward the correct route when obvious.
5) If the user mixes topics, prefer the SAFEST primary intent (if destructive cron → cron_forbidden).
6) Input that is ONLY a bare filename (e.g. dana.txt, notes.log) with no verbs like list/show/run/schedule → "unclear", NOT archive_list.

Output valid JSON only."""

        user_prompt = f"User request:\n{user_text.strip()}"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 350,
        }

        try:
            response = requests.post(
                f"{self.api_base}/chat/completions",
                headers=headers,
                json=payload,
                timeout=45,
            )
            if response.status_code != 200:
                err = response.text[:300]
                try:
                    err = response.json().get("error", {}).get("message", err)
                except Exception:
                    pass
                return {"success": False, "route": None, "error": err}

            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()
            parsed = _extract_json_object(content)
            if not parsed or not isinstance(parsed, dict):
                return {
                    "success": False,
                    "route": None,
                    "error": "Classifier did not return valid JSON",
                }

            route = parsed.get("route")
            if isinstance(route, str):
                route = route.strip().lower()

            return {
                "success": True,
                "route": route or "unclear",
                "script_name": parsed.get("script_name"),
                "cron_expression": parsed.get("cron_expression"),
                "date_scope": parsed.get("date_scope"),
                "calendar_day": parsed.get("calendar_day"),
                "execution_style": parsed.get("execution_style"),
                "error": "",
            }
        except Exception as e:
            logger.error(f"classify_execution_route: {e}", exc_info=True)
            return {"success": False, "route": None, "error": str(e)}

    def _format_remote_host_context(self, host_context):
        """Turn per-host probe (OS, running services, listeners) into text for the LLM."""
        if not host_context:
            return None
        blocks = []
        for host in sorted(host_context.keys()):
            info = host_context[host]
            if info.get('error') and not info.get('uname_line') and not info.get('running_services'):
                blocks.append(f"### {host}\n(could not connect or probe — {info['error']})")
                continue
            parts = [f"### {host}"]
            if info.get('uname_line'):
                parts.append(f"OS (uname -a): {info['uname_line']}")
            elif info.get('error'):
                parts.append(f"OS: unavailable ({info['error']})")
            else:
                parts.append("OS: unavailable")
            if info.get('running_services'):
                parts.append(
                    "Running systemd service units (sample):\n"
                    + info['running_services']
                )
            if info.get('listening_tcp'):
                parts.append(
                    "Listening TCP (ss -tlnp; like nmap listener view):\n"
                    + info['listening_tcp']
                )
            if info.get('listening_udp'):
                parts.append(
                    "Listening UDP (ss -ulnp):\n"
                    + info['listening_udp']
                )
            blocks.append("\n".join(parts))
        if not blocks:
            return None
        return (
            "Remote host snapshot gathered over SSH before generating the command "
            "(OS, running services, listening ports). Use this to pick correct tools, paths, "
            "and flags; align suggestions with what is actually running when relevant.\n\n"
            + "\n\n".join(blocks)
        )

    def generate_command(
        self,
        natural_language_input,
        remote_host_context=None,
        rag_context_text: str = "",
        execution_style: str = "auto",
    ):
        """
        Generate Bash command from natural language input
        
        Args:
            natural_language_input: User's natural language request
            remote_host_context: Optional dict host -> probe result from SSHExecutor.probe_host_context
            rag_context_text: Optional retrieved command examples from RAG layer
            
        Returns:
            dict: {'success': bool, 'command': str, 'error': str}
        """
        if not self.api_key:
            logger.error("LLM API key not configured")
            return {
                'success': False,
                'error': 'LLM API key not configured'
            }

        style = (execution_style or "auto").strip().lower()
        if style not in ("auto", "single", "multi"):
            style = "auto"

        style_hint = ""
        if style == "single":
            style_hint = (
                "\nOutput preference: prefer a SINGLE LINE shell command when possible.\n"
            )
        elif style == "multi":
            style_hint = (
                "\nOutput preference: the user needs a SMALL MULTI-LINE Bash script "
                "(use \\n between lines). Keep it minimal and safe; no interactive prompts.\n"
            )

        # Create system prompt
        system_prompt = f"""You are a secure Bash command generator for ShellSentry. You convert natural language into commands/scripts that run on REMOTE Linux hosts over SSH.

Context the app handles elsewhere (do NOT try to fulfill these as shell commands):
- Listing/scheduling managed cron for saved archive scripts, crontab edits, or saved-script list/rerun/explain — those use dedicated app flows. If the user text still reached you, treat it as a normal command ONLY when they clearly ask for immediate execution output (e.g. "show disk usage now").

{style_hint}
Rules:
1. Generate ONLY the Bash command/script, no explanations
2. Use safe commands only (no rm -rf, format, etc.)
3. Multi-server work is done by the app: the user picks servers in the UI. You output ONE command that will be run on each target (e.g. `df -h`), never `ssh`, `scp`, `hosts.txt`, or `for` loops to fan out to hosts
4. Do not include sudo unless explicitly requested
5. Output should be executable Bash code only
6. If the request is unclear or unsafe, return "ERROR: Request unclear or potentially unsafe"
7. When remote host context is provided (OS, running services, listening ports), prefer command-line flags, paths, and tools that match that environment; if a service (e.g. nginx, sshd) is visible in the snapshot, prefer inspecting that stack when the user asks about services or ports
8. Output raw shell only: never wrap the command in backticks (`) or markdown.
9. The app already runs your command on the target host via SSH. Never use `ssh`, `scp`, or `rsync` in the command (read-only mode blocks them). The only exception is if the user explicitly needs to jump from the remote to another host.
10. If trusted grounding examples are provided, prefer commands and patterns from them unless there is a strong reason not to.

Examples:
- "Show active connections" -> "netstat -nlutp"
- "Check disk usage" -> "df -h"
- "Check if 192.168.1.1 is alive" -> "ping -c 4 192.168.1.1"
- "Show network interfaces" -> "ifconfig -a"

Now convert this request to a Bash command:"""
        
        prompt_blocks = []
        ctx_block = self._format_remote_host_context(remote_host_context)
        if ctx_block:
            prompt_blocks.append(ctx_block)
        if rag_context_text:
            prompt_blocks.append(rag_context_text.strip())
        prompt_blocks.append(f"User request:\n{natural_language_input}")
        user_prompt = "\n\n".join(prompt_blocks).strip()
        
        try:
            if self.api_type == 'openai' or 'openai' in self.api_base.lower():
                return self._call_openai_api(system_prompt, user_prompt)
            else:
                # Try OpenAI-compatible API
                return self._call_openai_compatible_api(system_prompt, user_prompt)
        except Exception as e:
            logger.error(f"Error calling LLM API: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f'API call failed: {str(e)}'
            }
    
    def _call_openai_api(self, system_prompt, user_prompt):
        """Call OpenAI API with retry logic"""
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': self.model,
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt}
            ],
            'temperature': 0.3,
            'max_tokens': 500
        }
        
        # Retries: transient network issues + HTTP 429 (TPM / rate limit; wait for window to free)
        max_retries = 5
        retry_delay = 1  # seconds, for network backoff

        for attempt in range(max_retries):
            try:
                response = requests.post(
                    f'{self.api_base}/chat/completions',
                    headers=headers,
                    json=payload,
                    timeout=60  # Increased timeout
                )
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"LLM API timeout (attempt {attempt + 1}/{max_retries}), retrying..."
                    )
                    time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                    continue
                else:
                    logger.error("LLM API timeout after all retries")
                    return {
                        'success': False,
                        'error': 'Request timeout: LLM API did not respond in time'
                    }
            except requests.exceptions.ConnectionError as e:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"LLM API connection error (attempt {attempt + 1}/{max_retries}): {str(e)}, retrying..."
                    )
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                else:
                    logger.error(f"LLM API connection error after all retries: {str(e)}")
                    return {
                        'success': False,
                        'error': f'Connection error: {str(e)}'
                    }
            except requests.exceptions.RequestException as e:
                logger.error(f"LLM API request error: {str(e)}")
                return {
                    'success': False,
                    'error': f'Request error: {str(e)}'
                }

            if response.status_code == 200:
                data = response.json()
                command = data['choices'][0]['message']['content'].strip()

                # Clean up the command (remove markdown code blocks if present)
                command = command.replace('```bash', '').replace('```', '').strip()
                command = command.replace('```sh', '').strip()

                # Remove leading $ or # prompts
                command = re.sub(r'^[\$#]\s*', '', command)

                # Strip Markdown inline backticks (`ping ...`) so validation sees "ping", not "`ping"
                command = command.strip()
                while command.startswith('`'):
                    command = command[1:].lstrip()
                while command.endswith('`'):
                    command = command[:-1].rstrip()
                command = command.strip()

                return {
                    'success': True,
                    'command': command
                }

            if response.status_code == 429 and attempt < max_retries - 1:
                ra = _retry_after_seconds(response)
                wait = ra if ra is not None else min(5 * (2**attempt), 60)
                logger.warning(
                    "LLM API rate limited (429), waiting %s s (attempt %s/%s)",
                    wait,
                    attempt + 1,
                    max_retries,
                )
                time.sleep(wait)
                continue

            error_text = response.text
            try:
                error_json = response.json()
                error_text = error_json.get('error', {}).get('message', error_text)
            except Exception:
                pass
            logger.error(
                f"OpenAI API error: {response.status_code} - {error_text[:300]}"
            )
            if response.status_code == 429:
                extra = " Wait a bit or raise your API tier; each request also sends host context, which uses many tokens."
                err = f"API returned status 429: {error_text[:200]}.{extra}"
            else:
                err = f"API returned status {response.status_code}: {error_text[:200]}"
            return {
                'success': False,
                'error': err
            }
    
    def _call_openai_compatible_api(self, system_prompt, user_prompt):
        """Call OpenAI-compatible API (for LLaMA servers)"""
        # Similar to OpenAI but may need adjustments
        return self._call_openai_api(system_prompt, user_prompt)

    def summarize_execution_report(
        self,
        user_question: str,
        command_run: str,
        report_text: str,
        max_report_chars: int = 14000,
    ):
        """
        Ask the LLM to explain the formatted execution report in plain language
        for non-technical readers.
        """
        if not self.api_key:
            return {"success": False, "summary": "", "error": "LLM API key not configured"}

        rt = (report_text or "").strip()
        if len(rt) > max_report_chars:
            rt = rt[: max_report_chars - 80] + "\n\n[… report shortened for the assistant …]"

        system_prompt = """You are a clear, friendly assistant helping someone who is NOT a Linux or IT expert.

You will see:
- What the user asked for in everyday language
- The command that was run on remote computer(s)
- A technical report with command output, exit codes, and errors

Your job:
1. Explain what the report means in simple, readable language (short paragraphs; bullets are OK).
2. Say what happened on each computer when there are several — in plain words.
3. Call out the important facts (numbers, names, errors) without copying the whole raw log.
4. If something failed, say what went wrong in everyday terms.
5. Do not invent information that is not supported by the report. If the report is empty or unclear, say so.
6. Do not use Markdown headings with # symbols. You may use **bold** sparingly for key facts if helpful.
7. Never wrap the whole answer in a code block."""

        user_prompt = f"""What the user asked (their words):
{user_question.strip()}

Command that ran on the remote machine(s):
{command_run.strip()}

--- BEGIN REPORT ---
{rt}
--- END REPORT ---

Write the explanation now, in plain language."""

        try:
            if self.api_type == "openai" or "openai" in self.api_base.lower():
                return self._summarize_openai(system_prompt, user_prompt)
            return self._summarize_openai(system_prompt, user_prompt)
        except Exception as e:
            logger.error(f"LLM summarize_execution_report: {str(e)}", exc_info=True)
            return {"success": False, "summary": "", "error": str(e)}

    def _summarize_openai(self, system_prompt: str, user_prompt: str):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.35,
            "max_tokens": 1000,
        }
        max_retries = 4
        response = None
        for attempt in range(max_retries):
            response = requests.post(
                f"{self.api_base}/chat/completions",
                headers=headers,
                json=payload,
                timeout=90,
            )
            if response.status_code == 200:
                data = response.json()
                text = data["choices"][0]["message"]["content"].strip()
                text = text.replace("```markdown", "").replace("```", "").strip()
                return {"success": True, "summary": text, "error": ""}
            if response.status_code == 429 and attempt < max_retries - 1:
                ra = _retry_after_seconds(response)
                wait = ra if ra is not None else min(5 * (2**attempt), 60)
                logger.warning(
                    "summarize_execution_report: rate limited (429), waiting %s s", wait
                )
                time.sleep(wait)
                continue
            break
        if response is None:
            return {"success": False, "summary": "", "error": "No response from API"}
        err = response.text[:400]
        try:
            err = response.json().get("error", {}).get("message", err)
        except Exception:
            pass
        logger.error(
            f"summarize_execution_report API error: {response.status_code} {err}"
        )
        return {"success": False, "summary": "", "error": f"API error: {err}"}

    def explain_script(self, script_name: str, script_content: str):
        """Explain a saved shell script in plain language."""
        if not self.api_key:
            return {"success": False, "explanation": "", "error": "LLM API key not configured"}

        script_text = (script_content or "").strip()
        if not script_text:
            return {"success": False, "explanation": "", "error": "Script content is empty"}
        if len(script_text) > 10000:
            script_text = script_text[:9900] + "\n\n# ... truncated ..."

        system_prompt = """You explain Bash scripts for non-expert users.

Rules:
1. Explain what the script does step-by-step in simple words.
2. Mention any potentially sensitive/risky parts (file writes, deletes, network changes, privilege use).
3. Keep it concise and practical.
4. Do not invent behavior not present in the script.
5. Do not wrap your answer in code blocks."""

        user_prompt = f"""Script name:
{script_name}

Script content:
{script_text}

Explain this script now."""

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.2,
                "max_tokens": 500,
            }
            response = requests.post(
                f"{self.api_base}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60,
            )
            if response.status_code != 200:
                err = response.text[:400]
                try:
                    err = response.json().get("error", {}).get("message", err)
                except Exception:
                    pass
                return {"success": False, "explanation": "", "error": f"API error: {err}"}

            data = response.json()
            text = data["choices"][0]["message"]["content"].strip()
            text = text.replace("```markdown", "").replace("```", "").strip()
            return {"success": True, "explanation": text, "error": ""}
        except Exception as e:
            logger.error(f"explain_script error: {str(e)}", exc_info=True)
            return {"success": False, "explanation": "", "error": str(e)}

