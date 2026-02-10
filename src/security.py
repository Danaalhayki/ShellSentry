import re
from .logger import setup_logger

logger = setup_logger()

class SecurityLayer:
    """Security layer for input validation and prompt sanitization"""
    
    def __init__(self):
        # Prohibited keywords that indicate malicious intent
        self.prohibited_keywords = [
            'rm -rf', 'format', 'delete all', 'wipe', 'destroy',
            'drop database', 'truncate', 'kill all', 'shutdown',
            'reboot', 'halt', 'poweroff', 'dd if=', 'mkfs',
            'fdisk', 'parted', 'wipefs', 'clear', 'reset',
            'password', 'passwd', 'chmod 777', 'chown root',
            'sudo su', 'su -', 'sudo -i', 'sudo passwd'
        ]
        
        # Dangerous patterns
        self.dangerous_patterns = [
            r'rm\s+-rf\s+/',  # rm -rf /
            r'format\s+\w+',  # format commands
            r'dd\s+if=',      # dd commands
            r'>\s*/dev/',     # redirecting to /dev
            r'\|\s*bash',     # piping to bash
            r'\|\s*sh\s',     # piping to sh
            r';\s*rm\s',      # command chaining with rm
            r'&&\s*rm\s',     # conditional execution with rm
        ]
        
        # Prompt injection patterns
        self.injection_patterns = [
            r'ignore\s+previous\s+instructions',
            r'forget\s+all\s+previous',
            r'new\s+instructions',
            r'system\s+prompt',
            r'you\s+are\s+now',
            r'act\s+as\s+if',
        ]
    
    def validate_input(self, user_input):
        """
        Validate user input for malicious content
        
        Returns:
            dict: {'valid': bool, 'reason': str}
        """
        if not user_input or len(user_input.strip()) == 0:
            return {'valid': False, 'reason': 'Empty input'}
        
        # Check length
        if len(user_input) > 1000:
            return {'valid': False, 'reason': 'Input too long (max 1000 characters)'}
        
        input_lower = user_input.lower()
        
        # Check for prohibited keywords
        for keyword in self.prohibited_keywords:
            if keyword in input_lower:
                logger.warning(f"Prohibited keyword detected: {keyword}")
                return {'valid': False, 'reason': f'Prohibited keyword detected: {keyword}'}
        
        # Check for dangerous patterns
        for pattern in self.dangerous_patterns:
            if re.search(pattern, input_lower, re.IGNORECASE):
                logger.warning(f"Dangerous pattern detected: {pattern}")
                return {'valid': False, 'reason': f'Dangerous pattern detected'}
        
        # Check for prompt injection
        for pattern in self.injection_patterns:
            if re.search(pattern, input_lower, re.IGNORECASE):
                logger.warning(f"Prompt injection pattern detected: {pattern}")
                return {'valid': False, 'reason': 'Potential prompt injection detected'}
        
        # Sanitize input (remove control characters)
        sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', user_input)
        if sanitized != user_input:
            logger.warning("Control characters removed from input")
        
        return {'valid': True, 'sanitized_input': sanitized}
    
    def sanitize_prompt(self, user_input):
        """Sanitize input for LLM prompt"""
        # Remove any remaining dangerous characters
        sanitized = re.sub(r'[<>{}[\]\\]', '', user_input)
        # Limit length
        sanitized = sanitized[:500]
        return sanitized

