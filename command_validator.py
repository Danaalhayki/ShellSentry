import os
import re
import shlex
from logger import setup_logger
from config import Config

logger = setup_logger()

class CommandValidator:
    """Validates generated Bash commands using whitelist and blacklist"""
    
    def __init__(self):
        # Whitelist of allowed commands
        self.whitelist = [
            'netstat', 'ss', 'ping', 'ifconfig', 'ip', 'hostname',
            'df', 'du', 'free', 'top', 'htop', 'ps', 'uptime',
            'who', 'w', 'last', 'uname', 'ls', 'cat', 'grep',
            'head', 'tail', 'wc', 'sort', 'uniq', 'find',
            'date', 'uptime', 'dmesg', 'journalctl', 'systemctl',
            'service', 'systemd-analyze', 'lsof', 'tcpdump',
            'curl', 'wget', 'dig', 'nslookup', 'host', 'traceroute',
            'route', 'arp', 'iptables', 'firewall-cmd', 'ufw',
            'mount', 'umount', 'blkid', 'lsblk', 'fdisk', 'parted',
            'lscpu', 'lspci', 'lsusb', 'dmidecode', 'sensors',
            'iostat', 'vmstat', 'sar', 'mpstat', 'pidstat',
            'strace', 'ltrace', 'tcpdump', 'wireshark', 'tcpflow',
            'nc', 'netcat', 'telnet', 'ssh', 'scp', 'rsync',
            'tar', 'gzip', 'gunzip', 'zip', 'unzip',
            'echo', 'printf', 'test', '[', '[[',
            'awk', 'sed', 'cut', 'tr', 'xargs',
            'which', 'whereis', 'locate', 'updatedb',
            'chmod', 'chown', 'chgrp', 'lsattr', 'chattr',
            'stat', 'file', 'md5sum', 'sha1sum', 'sha256sum',
            'diff', 'cmp', 'comm', 'join', 'paste',
            'env', 'export', 'set', 'unset', 'alias', 'unalias',
            'history', 'type', 'command', 'hash',
            'read', 'readonly', 'declare', 'local',
            'true', 'false', ':', 'exit', 'return',
            'cd', 'pwd', 'pushd', 'popd', 'dirs',
            'mkdir', 'rmdir', 'touch', 'ln', 'cp', 'mv',
            'rm',  # Allowed but with restrictions
            'kill', 'killall', 'pkill',  # Allowed but with restrictions
            'nohup', 'screen', 'tmux', 'bg', 'fg', 'jobs',
            'wait', 'sleep', 'timeout', 'watch',
            'seq', 'yes', 'factor', 'bc', 'dc',
            'basename', 'dirname', 'realpath', 'readlink',
            'id', 'groups', 'whoami', 'logname',
            'passwd',  # Allowed but with restrictions
            'su', 'sudo',  # Allowed but with restrictions
            'visudo', 'vipw', 'vigr',
            'crontab', 'at', 'batch', 'atq', 'atrm',
            'nice', 'renice', 'ionice',
            'ulimit', 'prlimit',
            'stty', 'tty', 'tput', 'reset',
            'clear', 'reset',
            'man', 'info', 'help', 'apropos', 'whatis',
            'less', 'more', 'most',
            'vim', 'vi', 'nano', 'emacs', 'ed',
            'git', 'svn', 'hg', 'bzr',
            'make', 'gcc', 'g++', 'cc', 'c++',
            'python', 'python2', 'python3', 'perl', 'ruby',
            'node', 'npm', 'yarn',
            'docker', 'docker-compose', 'podman',
            'kubectl', 'helm',
            'ansible', 'ansible-playbook',
            'puppet', 'chef', 'salt',
            'systemd', 'systemctl', 'journalctl',
            'logrotate', 'rsyslog', 'syslog-ng',
            'fail2ban', 'tripwire', 'aide',
            'clamav', 'rkhunter', 'chkrootkit',
            'nmap', 'masscan', 'zmap',
            'metasploit', 'nmap', 'masscan',
            'tcpdump', 'wireshark', 'tshark',
            'strace', 'ltrace', 'gdb',
            'valgrind', 'perf',
            'tcpflow', 'tcpick', 'ngrep',
            'ettercap', 'arpspoof', 'dsniff',
            'hydra', 'medusa', 'ncrack',
            'sqlmap', 'nikto', 'wapiti',
            'burpsuite', 'owasp-zap',
            'aircrack-ng', 'reaver', 'hashcat',
            'john', 'hashcat', 'rainbowcrack',
            'autopsy', 'sleuthkit', 'volatility',
            'wireshark', 'tshark', 'dumpcap',
            'tcpdump', 'tcpflow', 'tcpick',
            'ngrep', 'dsniff', 'ettercap',
            'nmap', 'masscan', 'zmap',
            'unicornscan', 'amap',
            'ike-scan', 'ikeforce',
            'sqlmap', 'sqlninja',
            'nikto', 'wapiti', 'skipfish',
            'dirb', 'dirbuster', 'gobuster',
            'wfuzz', 'ffuf',
            'subfinder', 'amass', 'sublist3r',
            'theHarvester', 'recon-ng',
            'shodan', 'censys',
            'maltego', 'spiderfoot',
            'metasploit', 'armitage',
            'cobaltstrike', 'empire',
            'powershell-empire',
            'veil', 'shellter',
            'msfvenom', 'unicorn',
            'weevely', 'webshells',
            'beef', 'xsser',
            'commix', 'xsstrike',
            'dnsrecon', 'dnsenum',
            'fierce', 'dnsmap',
            'dnswalk', 'dnsrecon',
            'theHarvester', 'recon-ng',
            'shodan', 'censys',
            'maltego', 'spiderfoot',
            'metasploit', 'armitage',
            'cobaltstrike', 'empire',
            'powershell-empire',
            'veil', 'shellter',
            'msfvenom', 'unicorn',
            'weevely', 'webshells',
            'beef', 'xsser',
            'commix', 'xsstrike',
            'dnsrecon', 'dnsenum',
            'fierce', 'dnsmap',
            'dnswalk', 'dnsrecon',
        ]
        
        # Blacklist of forbidden commands/patterns
        self.blacklist_patterns = [
            r'rm\s+-rf\s+/',           # rm -rf /
            r'rm\s+-rf\s+/\s*',        # rm -rf / with trailing
            r'rm\s+-rf\s+/[^/]',       # rm -rf /something
            r'format\s+\w+',           # format commands
            r'mkfs\s+',                # mkfs commands
            r'fdisk\s+/dev/[hs]d[a-z]', # fdisk on disk
            r'dd\s+if=',               # dd commands
            r'>\s*/dev/[hs]d[a-z]',    # redirecting to disk
            r'>\s*/dev/sd[a-z]',       # redirecting to disk
            r'>\s*/dev/hd[a-z]',       # redirecting to disk
            r':\s*\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;',  # fork bomb
            r'\|\s*bash\s*$',          # piping to bash at end
            r'\|\s*sh\s*$',            # piping to sh at end
            r';\s*rm\s+-rf',           # command chaining with rm -rf
            r'&&\s*rm\s+-rf',          # conditional with rm -rf
            r'\|\s*rm\s+-rf',          # piping to rm -rf
            r'sudo\s+rm\s+-rf\s+/',    # sudo rm -rf /
            r'su\s+-c\s+["\']rm\s+-rf', # su -c "rm -rf"
            r'chmod\s+777\s+/',        # chmod 777 /
            r'chown\s+-R\s+root\s+/',  # chown -R root /
            r'passwd\s+root',          # changing root password
            r'sudo\s+passwd',          # sudo passwd
            r'shutdown\s+-h\s+now',    # shutdown now
            r'reboot\s+now',           # reboot now
            r'halt',                   # halt
            r'poweroff',               # poweroff
            r'init\s+0',               # init 0
            r'init\s+6',               # init 6
            r'telinit\s+0',            # telinit 0
            r'telinit\s+6',            # telinit 6
        ]
        
        # Commands that require special validation
        self.restricted_commands = {
            'rm': self._validate_rm,
            'kill': self._validate_kill,
            'killall': self._validate_kill,
            'pkill': self._validate_kill,
            'passwd': self._validate_passwd,
            'su': self._validate_su,
            'sudo': self._validate_sudo,
        }
    
    def validate(self, command):
        """
        Validate a Bash command
        
        Args:
            command: The Bash command to validate
            
        Returns:
            dict: {'valid': bool, 'reason': str}
        """
        if not command or len(command.strip()) == 0:
            return {'valid': False, 'reason': 'Empty command'}
        
        # Remove comments
        command = re.sub(r'#.*$', '', command, flags=re.MULTILINE)
        command = command.strip()
        
        # Remove surrounding quotes if present
        if (command.startswith('"') and command.endswith('"')) or (command.startswith("'") and command.endswith("'")):
            command = command[1:-1].strip()
        
        if not command:
            return {'valid': False, 'reason': 'Command is only comments'}
        
        # Check blacklist patterns
        for pattern in self.blacklist_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                logger.warning(f"Blacklist pattern matched: {pattern}")
                return {'valid': False, 'reason': f'Forbidden pattern detected: {pattern}'}
        
        # Parse command to get the base command
        try:
            # Split by ;, &&, ||, |, & to check each part
            parts = re.split(r'[;&|]|\|\||&&', command)
            
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                
                # Extract the first word (command)
                first_word = part.split()[0] if part.split() else ''
                
                # Remove any path prefixes
                base_command = os.path.basename(first_word)
                
                # Check if command is in whitelist
                if base_command not in self.whitelist:
                    # Check if it's a builtin or common command
                    if not self._is_safe_builtin(base_command):
                        logger.warning(f"Command not in whitelist: {base_command}")
                        return {
                            'valid': False,
                            'reason': f'Command not allowed: {base_command}'
                        }
                
                # Check restricted commands
                if base_command in self.restricted_commands:
                    validation_func = self.restricted_commands[base_command]
                    result = validation_func(part)
                    if not result['valid']:
                        return result
        
        except Exception as e:
            logger.error(f"Error parsing command: {str(e)}")
            return {'valid': False, 'reason': f'Error parsing command: {str(e)}'}
        
        return {'valid': True}
    
    def _is_safe_builtin(self, command):
        """Check if command is a safe shell builtin"""
        safe_builtins = [
            'echo', 'printf', 'test', '[', '[[', 'true', 'false', ':',
            'cd', 'pwd', 'pushd', 'popd', 'dirs',
            'read', 'readonly', 'declare', 'local', 'export', 'set', 'unset',
            'alias', 'unalias', 'type', 'command', 'hash',
            'exit', 'return', 'break', 'continue',
            'wait', 'jobs', 'fg', 'bg',
            'history', 'fc',
        ]
        return command in safe_builtins
    
    def _validate_rm(self, command_part):
        """Validate rm command"""
        # Don't allow rm -rf on root or system directories
        if re.search(r'rm\s+-rf\s+/(\s|$)', command_part):
            return {'valid': False, 'reason': 'rm -rf / is forbidden'}
        if re.search(r'rm\s+-rf\s+/etc', command_part):
            return {'valid': False, 'reason': 'rm -rf /etc is forbidden'}
        if re.search(r'rm\s+-rf\s+/usr', command_part):
            return {'valid': False, 'reason': 'rm -rf /usr is forbidden'}
        if re.search(r'rm\s+-rf\s+/var', command_part):
            return {'valid': False, 'reason': 'rm -rf /var is forbidden'}
        if re.search(r'rm\s+-rf\s+/boot', command_part):
            return {'valid': False, 'reason': 'rm -rf /boot is forbidden'}
        return {'valid': True}
    
    def _validate_kill(self, command_part):
        """Validate kill commands"""
        # Don't allow killing critical processes
        if re.search(r'kill\s+-9\s+1', command_part):  # init process
            return {'valid': False, 'reason': 'Killing init process is forbidden'}
        return {'valid': True}
    
    def _validate_passwd(self, command_part):
        """Validate passwd command"""
        # Only allow changing own password, not root
        if re.search(r'passwd\s+root', command_part):
            return {'valid': False, 'reason': 'Changing root password is forbidden'}
        return {'valid': True}
    
    def _validate_su(self, command_part):
        """Validate su command"""
        # Check if root execution is allowed
        if not Config.ALLOW_ROOT_EXECUTION:
            if re.search(r'su\s+-', command_part) or re.search(r'su\s+root', command_part):
                return {'valid': False, 'reason': 'Root execution is not allowed'}
        return {'valid': True}
    
    def _validate_sudo(self, command_part):
        """Validate sudo command"""
        # Check if root execution is allowed
        if not Config.ALLOW_ROOT_EXECUTION:
            return {'valid': False, 'reason': 'Sudo execution is not allowed'}
        return {'valid': True}

