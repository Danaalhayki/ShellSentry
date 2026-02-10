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
    
    def generate_command(self, natural_language_input):
        """
        Generate Bash command from natural language input
        
        Args:
            natural_language_input: User's natural language request
            
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

Examples:
- "Show active connections" -> "netstat -nlutp"
- "Check disk usage" -> "df -h"
- "Check if 192.168.1.1 is alive" -> "ping -c 4 192.168.1.1"
- "Show network interfaces" -> "ifconfig -a"

Now convert this request to a Bash command:"""
        
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

