import json
import re
import time
import requests
from .logger import setup_logger
from .config import Config

logger = setup_logger()

class LLMClient:
    """Client for interacting with LLM API (OpenAI/LLaMA)"""
    
    def __init__(self):
        self.api_key = Config.LLM_API_KEY
        self.api_base = Config.LLM_API_BASE_URL
        self.model = Config.LLM_MODEL
        self.api_type = Config.LLM_API_TYPE
    
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

    def generate_command(self, natural_language_input, remote_host_context=None):
        """
        Generate Bash command from natural language input
        
        Args:
            natural_language_input: User's natural language request
            remote_host_context: Optional dict host -> probe result from SSHExecutor.probe_host_context
            
        Returns:
            dict: {'success': bool, 'command': str, 'error': str}
        """
        if not self.api_key:
            logger.error("LLM API key not configured")
            return {
                'success': False,
                'error': 'LLM API key not configured'
            }
        
        # Create system prompt
        system_prompt = """You are a secure Bash command generator. Your task is to convert natural language requests into safe, single-line Bash commands or simple multi-line scripts.

Rules:
1. Generate ONLY the Bash command/script, no explanations
2. Use safe commands only (no rm -rf, format, etc.)
3. For multi-server operations, create a simple script
4. Do not include sudo unless explicitly requested
5. Output should be executable Bash code only
6. If the request is unclear or unsafe, return "ERROR: Request unclear or potentially unsafe"
7. When remote host context is provided (OS, running services, listening ports), prefer command-line flags, paths, and tools that match that environment; if a service (e.g. nginx, sshd) is visible in the snapshot, prefer inspecting that stack when the user asks about services or ports
8. Output raw shell only: never wrap the command in backticks (`) or markdown.
9. The app already runs your command on the target host via SSH; do not use ssh/scp to reach that host unless the user explicitly asks to SSH from the remote to another machine.

Examples:
- "Show active connections" -> "netstat -nlutp"
- "Check disk usage" -> "df -h"
- "Check if 192.168.1.1 is alive" -> "ping -c 4 192.168.1.1"
- "Show network interfaces" -> "ifconfig -a"

Now convert this request to a Bash command:"""
        
        ctx_block = self._format_remote_host_context(remote_host_context)
        if ctx_block:
            user_prompt = f"{ctx_block}\n\nUser request:\n{natural_language_input}"
        else:
            user_prompt = natural_language_input
        
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
        
        # Retry logic for network issues
        max_retries = 3
        retry_delay = 1  # seconds
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    f'{self.api_base}/chat/completions',
                    headers=headers,
                    json=payload,
                    timeout=60  # Increased timeout
                )
                break  # Success, exit retry loop
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    logger.warning(f"LLM API timeout (attempt {attempt + 1}/{max_retries}), retrying...")
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
                    logger.warning(f"LLM API connection error (attempt {attempt + 1}/{max_retries}): {str(e)}, retrying...")
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
        else:
            error_text = response.text
            try:
                error_json = response.json()
                error_text = error_json.get('error', {}).get('message', error_text)
            except:
                pass
            logger.error(f"OpenAI API error: {response.status_code} - {error_text}")
            return {
                'success': False,
                'error': f'API returned status {response.status_code}: {error_text[:200]}'
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
        response = requests.post(
            f"{self.api_base}/chat/completions",
            headers=headers,
            json=payload,
            timeout=90,
        )
        if response.status_code != 200:
            err = response.text[:400]
            try:
                err = response.json().get("error", {}).get("message", err)
            except Exception:
                pass
            logger.error(f"summarize_execution_report API error: {response.status_code} {err}")
            return {"success": False, "summary": "", "error": f"API error: {err}"}

        data = response.json()
        text = data["choices"][0]["message"]["content"].strip()
        text = text.replace("```markdown", "").replace("```", "").strip()
        return {"success": True, "summary": text, "error": ""}

