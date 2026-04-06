import os
import re
import shlex
from .logger import setup_logger
from .config import Config

logger = setup_logger()

class CommandValidator:
    """Validates generated Bash commands using whitelist and blacklist"""
    
    def __init__(self):
        # Whitelist of allowed commands
        self.whitelist = [
            'netstat', 'ss', 'ping', 'ifconfig', 'ip', 'hostname',
            'hostnamectl', 'timedatectl', 'udevadm', 'getfacl', 'getenforce',
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
        
        # Shebang patterns to strip before execution (so shell does not try to run them as commands)
        self._shebang_patterns = [
            re.compile(r'^\s*#!\s*\S+.*$', re.MULTILINE),
            re.compile(r'^\s*!/bin/(ba)?sh\s*.*$', re.MULTILINE),
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

        # When READ_ONLY_EXECUTION is on, only these bases (plus read-only-safe builtins) may run.
        self.readonly_allowlist = frozenset({
            'netstat', 'ss', 'ping', 'ifconfig', 'ip', 'hostname', 'df', 'du', 'free', 'top', 'htop',
            'ps', 'uptime', 'who', 'w', 'last', 'lastb', 'uname', 'ls', 'cat', 'grep', 'egrep', 'fgrep',
            'head', 'tail', 'wc', 'sort', 'uniq', 'find', 'date', 'dmesg', 'journalctl', 'systemctl',
            'lsof', 'dig', 'nslookup', 'host', 'traceroute', 'tracepath', 'route', 'arp', 'mtr',
            'mount', 'lsblk', 'blkid', 'lscpu', 'lspci', 'lsusb', 'dmidecode', 'sensors', 'lshw',
            'iostat', 'vmstat', 'sar', 'mpstat', 'pidstat', 'strace', 'ltrace', 'tcpdump', 'tshark',
            'which', 'whereis', 'locate', 'stat', 'file', 'md5sum', 'sha1sum', 'sha256sum', 'diff',
            'cmp', 'comm', 'id', 'groups', 'whoami', 'logname', 'env', 'printenv', 'getconf', 'getent',
            'man', 'info', 'help', 'apropos', 'whatis', 'less', 'more', 'most',
            'awk', 'sed', 'cut', 'tr', 'basename', 'dirname', 'realpath', 'readlink',
            'echo', 'printf', 'seq', 'yes', 'factor', 'bc', 'dc',
            'type', 'command', 'hash',
            'nmap', 'nmcli', 'ethtool', 'iwconfig', 'iw', 'ss', 'systemd-analyze', 'systemd-detect-virt',
            'hostnamectl', 'timedatectl', 'udevadm', 'lsattr', 'getfacl', 'getenforce', 'iptables',
            'pwd', 'pwdx', 'pgrep', 'pstree',
        })

        self.readonly_safe_builtins = frozenset({
            'echo', 'printf', 'test', '[', '[[', 'true', 'false', ':',
            'cd', 'pwd', 'pushd', 'popd', 'dirs',
            'read', 'readonly', 'declare', 'local', 'export', 'set', 'unset',
            'alias', 'unalias', 'type', 'command', 'hash',
            'exit', 'return', 'break', 'continue',
            'wait', 'jobs', 'fg', 'bg',
            'history', 'fc',
        })

    def _strip_inline_backticks(self, text):
        """Remove Markdown inline-code backticks so `ping` is validated as ping, not `ping."""
        if not text:
            return text
        t = text.strip()
        while t.startswith('`'):
            t = t[1:].lstrip()
        while t.endswith('`'):
            t = t[:-1].rstrip()
        return t

    def _read_only_has_forbidden_redirect(self, cmd):
        """Disallow > / >> to real files (allow only /dev/null and &1/&2 style merges)."""
        if not cmd:
            return False
        if re.search(r'>>\s+(?!/dev/null)\S', cmd):
            return True
        for m in re.finditer(r'(?:^|[;\s|&])(\d*)>\s+(\S+)', cmd):
            target = m.group(2)
            if target.startswith('/dev/null'):
                continue
            if target.startswith('&'):
                continue
            return True
        return False

    def _read_only_global(self, command):
        """Whole-command checks for read-only mode (privilege, pipes to shell, file writes)."""
        c = command
        if self._read_only_has_forbidden_redirect(c):
            logger.warning("Read-only: forbidden shell redirect")
            return {'valid': False, 'reason': 'Read-only mode: redirecting output to a file is not allowed'}

        if re.search(r'\bsudo\b', c, re.IGNORECASE):
            return {'valid': False, 'reason': 'Read-only mode: sudo is not allowed'}
        if re.search(r'\bsu\s+(?:-|root\b)', c, re.IGNORECASE):
            return {'valid': False, 'reason': 'Read-only mode: su is not allowed'}

        if re.search(r'(?:^|[;\s|&])(?:bash|sh)\s+(?:-c|-s)\s', c):
            return {'valid': False, 'reason': 'Read-only mode: invoking shell with -c/-s is not allowed'}

        if re.search(r'\|\s*(?:bash|sh)\b', c):
            return {'valid': False, 'reason': 'Read-only mode: piping to a shell is not allowed'}

        if re.search(r'sed\s+(?:-i\S*|--in-place)', c, re.IGNORECASE):
            return {'valid': False, 'reason': 'Read-only mode: sed in-place editing is not allowed'}

        if re.search(r'(?:curl|wget)\s+.*(?:\s-o\s|\s--output(?:=|\s)|\s-O\b)', c, re.IGNORECASE):
            return {'valid': False, 'reason': 'Read-only mode: curl/wget saving to a file is not allowed'}

        if re.search(r'(?:tcpdump|tshark)\s+.*(?:\s-w\s|\s--write)', c, re.IGNORECASE):
            return {'valid': False, 'reason': 'Read-only mode: writing packet capture to a file is not allowed'}

        if re.search(r'\$\([^)]*\b(?:\b(?:rm|dd|mkdir|chmod|chown|mkfs|wget|curl|tee)\b|systemctl\s+start|iptables\s+-[AF])\b[^)]*\)', c, re.IGNORECASE):
            return {'valid': False, 'reason': 'Read-only mode: command substitution contains a state-changing command'}

        return {'valid': True}

    def _read_only_check_part(self, part, base_command):
        """Per pipeline segment: allow only inspection-style commands when read-only mode is on."""
        if base_command in self.readonly_safe_builtins:
            return {'valid': True}
        if base_command not in self.readonly_allowlist:
            logger.warning(f"Read-only: base command not allowed: {base_command}")
            return {'valid': False, 'reason': f'Read-only mode: state-changing or disallowed command: {base_command}'}

        p = part.strip()
        if base_command == 'journalctl':
            if re.search(
                r'journalctl\s+(?:--vacuum|--flush|--rotate|--relinquish|--update-catalog|--setup-keys)\b',
                p,
                re.IGNORECASE,
            ):
                return {'valid': False, 'reason': 'Read-only mode: journalctl may only read logs, not vacuum or rotate'}

        if base_command == 'systemctl':
            if re.search(
                r'systemctl\s+(?:start|stop|restart|reload|try-restart|reload-or-restart|'
                r'enable|disable|mask|unmask|daemon-reload|daemon-reexec|isolate|edit|set-property|kill|reset-failed)',
                p,
                re.IGNORECASE,
            ):
                return {'valid': False, 'reason': 'Read-only mode: systemctl may only query status (not start/stop/enable/etc.)'}

        if base_command == 'find':
            if re.search(r'(?:^|\s)(?:-delete|-exec|-execdir|-ok|-okdir|--exec)\b', p, re.IGNORECASE):
                return {'valid': False, 'reason': 'Read-only mode: find may not delete or execute subcommands'}

        if base_command == 'ip':
            if re.search(r'\bip\s+(?:link|addr|route|neigh|rule|netns|maddr|tunnel|tuntap|xfrm)\s+(?:set|add|del|flush|replace|change)\b', p, re.IGNORECASE):
                return {'valid': False, 'reason': 'Read-only mode: ip may not change network configuration'}

        if base_command == 'iptables':
            # Allow -L, -S, -C (check), -n, -v, -x, -t, etc.; forbid mutations (-A, -D, -I, -N, -P, -F, -Z, ...).
            # Match case-sensitively so -n (numeric) is not confused with -N (new chain).
            if re.search(
                r'iptables\s+(?:-[ADEFIJNPQRXZ]\b|--append|--delete|--insert|--replace|--flush|--zero|--delete-chain|--policy|--rename-chain|--new-chain|--modprobe|--load|--save)',
                p,
            ):
                return {'valid': False, 'reason': 'Read-only mode: iptables may only be listed (e.g. -L, -S), not modified'}

        if base_command == 'mount':
            s = p.strip()
            if s == 'mount' or re.match(r'^mount\s+(?:-l|--list)\b', s):
                return {'valid': True}
            return {'valid': False, 'reason': 'Read-only mode: only `mount` or `mount -l` are allowed (listing mounts)'}

        if base_command in ('tcpdump', 'tshark'):
            if re.search(r'(?:\s-w\s|\s--write)', p, re.IGNORECASE):
                return {'valid': False, 'reason': 'Read-only mode: packet capture to a file is not allowed'}

        if base_command == 'hostnamectl':
            if re.search(
                r'hostnamectl\s+(?:set-hostname|set-icon-name|set-chassis|set-deployment|set-location|commit)\b',
                p,
                re.IGNORECASE,
            ):
                return {'valid': False, 'reason': 'Read-only mode: hostnamectl may only show status, not change configuration'}

        if base_command == 'timedatectl':
            if re.search(
                r'timedatectl\s+(?:set-time|set-timezone|set-local-rtc|set-ntp)\b',
                p,
                re.IGNORECASE,
            ):
                return {'valid': False, 'reason': 'Read-only mode: timedatectl may only show status, not change time or timezone'}

        if base_command == 'udevadm':
            if re.search(r'udevadm\s+(?:trigger|control|reload)\b', p, re.IGNORECASE):
                return {'valid': False, 'reason': 'Read-only mode: udevadm trigger/control/reload is not allowed'}

        return {'valid': True}

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
        
        # Remove shebang line(s) at the start (e.g. #!/bin/bash or !/bin/bash) so they are not validated as commands
        command = self._strip_shebang(command)
        command = self._strip_inline_backticks(command)
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

        if Config.READ_ONLY_EXECUTION:
            ro_global = self._read_only_global(command)
            if not ro_global['valid']:
                return ro_global
        
        # Parse command to get the base command
        try:
            control_keywords = self._get_shell_control_keywords()
            # Split by ;, &&, ||, |, & to check each part
            parts = re.split(r'[;&|]|\|\||&&', command)
            
            for part in parts:
                part = self._strip_inline_backticks(part.strip())
                if not part:
                    continue
                
                tokens = part.split()
                first_word = tokens[0] if tokens else ''
                first_word = self._strip_inline_backticks(first_word)
                base_command = os.path.basename(first_word)
                
                # Skip variable assignments (e.g. MACHINES=("m1" "m2") or FOO=bar)
                if first_word and '=' in first_word and not first_word.startswith('-'):
                    continue
                
                # If part starts with a control-structure keyword (for, do, done, etc.)
                if base_command in control_keywords:
                    # 'do' and 'then' are followed by the actual command to run
                    if base_command in ('do', 'then', 'else', 'elif') and len(tokens) > 1:
                        base_command = os.path.basename(tokens[1])
                    else:
                        # No executable in this part (e.g. "for ...", "done")
                        continue
                
                # Check if command is in whitelist
                if base_command not in self.whitelist:
                    # Check if it's a builtin or common command
                    if not self._is_safe_builtin(base_command):
                        logger.warning(f"Command not in whitelist: {base_command}")
                        return {
                            'valid': False,
                            'reason': f'Command not allowed: {base_command}'
                        }

                if Config.READ_ONLY_EXECUTION:
                    ro_part = self._read_only_check_part(part, base_command)
                    if not ro_part['valid']:
                        return ro_part
                
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
    
    def _strip_shebang(self, command):
        """Remove shebang line(s) from the start of a command/script."""
        if not command or not command.strip():
            return command
        result = command
        for pattern in self._shebang_patterns:
            result = pattern.sub('', result)
        return result.strip()

    def normalize_for_execution(self, command):
        """
        Return a command with shebang lines removed and surrounding quotes stripped,
        suitable for passing to the shell. Prevents the remote from trying to run
        a single token like "ps aux" (command not found) instead of ps with args.
        """
        if not command or not command.strip():
            return command
        command = self._strip_shebang(command)
        command = self._strip_inline_backticks(command.strip())
        # Strip one level of surrounding quotes so "ps aux" -> ps aux (remote runs ps with arg aux)
        c = command.strip()
        if len(c) >= 2 and ((c[0] == '"' and c[-1] == '"') or (c[0] == "'" and c[-1] == "'")):
            command = c[1:-1]
        return command

    def _get_shell_control_keywords(self):
        """Shell control-structure keywords (allowed in compound commands)."""
        return {
            'for', 'do', 'done', 'while', 'until',
            'if', 'then', 'else', 'elif', 'fi',
            'case', 'esac', 'in',  # 'in' for for/case
        }

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

