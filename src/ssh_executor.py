import paramiko
import os
import socket
import re
import concurrent.futures
from .logger import setup_logger
from .config import Config
from .models import db, ExecutionLog

logger = setup_logger()

# Fast pre-flight reachability check timeout (seconds). Keeps UI responsive when
# a server is offline by failing in ~5s instead of waiting for the OS-level TCP
# connect timeout (~21s on Windows) inside paramiko.
PORT_REACHABILITY_TIMEOUT = 5

# Cap concurrent SSH workers so a large server list does not exhaust file handles
# or hammer the local network stack.
MAX_PARALLEL_SSH_WORKERS = 16

class SSHExecutor:
    """Handles SSH-based remote command execution"""
    
    def __init__(self):
        # Parse SSH_USER - can be in format "username@hostname" or just "username"
        ssh_user_raw = Config.SSH_USER or ''
        if '@' in ssh_user_raw:
            self.ssh_user = ssh_user_raw.split('@')[0]
        else:
            self.ssh_user = ssh_user_raw
        self.ssh_password = Config.SSH_PASSWORD
        self.ssh_key_path = os.path.expanduser(Config.SSH_KEY_PATH)
        self.ssh_agent_socket = Config.SSH_AGENT_SOCKET
        self.server_credentials = Config.SERVER_CREDENTIALS
        self.script_archive_dir_name = Config.SCRIPT_ARCHIVE_DIR_NAME
        self.script_archive_max_list = Config.SCRIPT_ARCHIVE_MAX_LIST
        self.safe_cron_tag_prefix = Config.SAFE_CRON_TAG_PREFIX

    @staticmethod
    def _is_port_reachable(server, port=22, timeout=PORT_REACHABILITY_TIMEOUT):
        """
        Quick TCP reachability check to short-circuit slow paramiko timeouts on
        servers that are powered off, blocked by firewall, or otherwise not
        listening on the SSH port. Returns True if a TCP connection can be
        established within `timeout` seconds.
        """
        try:
            with socket.create_connection((server, port), timeout=timeout):
                return True
        except (socket.timeout, OSError):
            return False

    def _run_in_parallel(self, servers, worker_fn):
        """
        Run `worker_fn(server)` for each server concurrently and return a dict
        keyed by server in the original input order. A failure on one server
        never blocks results from the others.
        """
        if not servers:
            return {}

        results = {}
        max_workers = max(1, min(len(servers), MAX_PARALLEL_SSH_WORKERS))

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_server = {executor.submit(worker_fn, s): s for s in servers}
            for future in concurrent.futures.as_completed(future_to_server):
                server = future_to_server[future]
                try:
                    results[server] = future.result()
                except Exception as e:
                    logger.error(f"Worker failure for {server}: {str(e)}", exc_info=True)
                    results[server] = {
                        'success': False,
                        'error': f'Internal worker error: {str(e)}',
                        'stdout': '',
                        'stderr': str(e),
                        'exit_code': -1,
                    }

        return {s: results[s] for s in servers if s in results}
    
    def execute_on_servers(self, command, servers, username, user_id=None, original_request=''):
        """
        Execute command on one or more remote servers in parallel.

        Reachable servers return real output even when other servers in the same
        batch time out or are offline. Each server's outcome is independent.

        Args:
            command: Bash command to execute
            servers: List of server hostnames/IPs
            username: Username of the user executing the command
            user_id: User ID for logging
            original_request: Original natural language request

        Returns:
            dict: Results from each server, keyed by server (preserves input order).
        """
        if not servers:
            return {'error': 'No servers specified'}

        def _worker(server):
            try:
                return self._execute_on_server(server, command)
            except Exception as e:
                logger.error(f"Error executing on {server}: {str(e)}", exc_info=True)
                return {
                    'success': False,
                    'error': str(e),
                    'stdout': '',
                    'stderr': '',
                    'exit_code': -1,
                }

        results = self._run_in_parallel(servers, _worker)

        self._log_execution(username, user_id, original_request, command, servers, results)
        return results

    def _exec_remote_text(self, ssh, command, timeout=25):
        """Run one non-interactive command; return (exit_code, stdout, stderr)."""
        stdin, stdout, stderr = ssh.exec_command(command, timeout=timeout)
        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode('utf-8', errors='replace').strip()
        err = stderr.read().decode('utf-8', errors='replace').strip()
        return exit_code, out, err

    def probe_host_context(self, servers):
        """
        Per host over one SSH session: OS (uname -a), running systemd services (summary),
        and listening TCP/UDP sockets (ss), similar in spirit to nmap "service" hints.
        Does not write ExecutionLog entries. Output is truncated on the remote via head.

        Probes are run in parallel across servers so a single offline host does
        not delay context collection for the others.
        """
        if not servers:
            return {}

        def _worker(server):
            ssh, connect_error = self._open_ssh(server)
            if connect_error is not None:
                return connect_error
            try:
                u_exit, u_out, u_err = self._exec_remote_text(ssh, 'uname -a', timeout=15)
                svc_cmd = (
                    "systemctl list-units --type=service --state=running --no-pager "
                    "2>/dev/null | head -n 50"
                )
                _s_exit, s_out, s_err = self._exec_remote_text(ssh, svc_cmd, timeout=25)
                _t_exit, t_out, t_err = self._exec_remote_text(
                    ssh, "ss -tlnp 2>/dev/null | head -n 40", timeout=20
                )
                _ud_exit, ud_out, ud_err = self._exec_remote_text(
                    ssh, "ss -ulnp 2>/dev/null | head -n 25", timeout=20
                )

                uname_line = u_out or None
                return {
                    'success': u_exit == 0,
                    'uname_line': uname_line,
                    'uname_stderr': u_err or None,
                    'running_services': s_out if s_out else None,
                    'running_services_stderr': s_err if s_err else None,
                    'listening_tcp': t_out if t_out else None,
                    'listening_tcp_stderr': t_err if t_err else None,
                    'listening_udp': ud_out if ud_out else None,
                    'listening_udp_stderr': ud_err if ud_err else None,
                    'error': None
                    if u_exit == 0
                    else (u_err or f'uname exited with {u_exit}'),
                }
            except Exception as e:
                logger.warning(f"Host context probe failed on {server}: {str(e)}")
                return {
                    'success': False,
                    'uname_line': None,
                    'running_services': None,
                    'listening_tcp': None,
                    'listening_udp': None,
                    'stderr': str(e),
                    'error': str(e),
                }
            finally:
                try:
                    ssh.close()
                except Exception:
                    pass

        return self._run_in_parallel(servers, _worker)

    def probe_os_uname(self, servers):
        """
        Backward-compatible alias: full host context (OS + services + listeners).
        Prefer probe_host_context in new code.
        """
        return self.probe_host_context(servers)

    def _open_ssh(self, server):
        """
        Open an SSH connection to server using the same credential rules as execution.
        Returns (ssh_client, None) on success, or (None, error_dict) on failure.

        A short TCP-level reachability probe runs first so that a powered-off or
        firewalled server fails in ~5 seconds instead of waiting for the OS-level
        TCP connect timeout (~21s on Windows) inside paramiko. This keeps batch
        operations responsive when only some servers are reachable.
        """
        if not self._is_port_reachable(server, port=22, timeout=PORT_REACHABILITY_TIMEOUT):
            logger.warning(
                f"Pre-flight check: SSH port 22 is not reachable on {server} "
                f"(timeout {PORT_REACHABILITY_TIMEOUT}s) — skipping connection attempt"
            )
            return None, {
                'success': False,
                'uname_line': None,
                'stderr': (
                    f'Server {server} is unreachable on port 22 within '
                    f'{PORT_REACHABILITY_TIMEOUT}s. The host may be offline, '
                    f'a firewall may be blocking SSH, or the SSH service is not running.'
                ),
                'exit_code': -1,
                'error': f'Connection timeout: {server} is unreachable',
            }

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            server_username = self.ssh_user or 'root'
            server_password = self.ssh_password
            has_server_specific_creds = False

            if server in self.server_credentials:
                server_username = self.server_credentials[server]['username']
                server_password = self.server_credentials[server]['password']
                has_server_specific_creds = True
                logger.info(f"Using server-specific credentials for {server}: user={server_username}")

            connect_kwargs = {
                'hostname': server,
                'username': server_username,
                'timeout': 15,
                'banner_timeout': 15,
                'auth_timeout': 15,
                'look_for_keys': False,
                'allow_agent': False
            }

            if has_server_specific_creds and server_password:
                connect_kwargs['password'] = server_password
                logger.info(f"Using password authentication for {server}")
            elif self.ssh_key_path and os.path.exists(self.ssh_key_path):
                try:
                    from paramiko import RSAKey, Ed25519Key
                    import io
                    with open(self.ssh_key_path, 'r') as f:
                        key_content = f.read()
                        if 'BEGIN RSA PRIVATE KEY' in key_content or 'BEGIN OPENSSH PRIVATE KEY' in key_content:
                            try:
                                key = RSAKey.from_private_key(io.StringIO(key_content))
                                connect_kwargs['pkey'] = key
                                logger.info(f"Using RSA SSH key: {self.ssh_key_path}")
                            except Exception as e1:
                                try:
                                    key = Ed25519Key.from_private_key(io.StringIO(key_content))
                                    connect_kwargs['pkey'] = key
                                    logger.info(f"Using Ed25519 SSH key: {self.ssh_key_path}")
                                except Exception as e2:
                                    logger.error(f"Could not load key as RSA or Ed25519: {str(e2)}")
                                    raise e1
                        else:
                            raise ValueError("Key format not recognized (not RSA or Ed25519)")
                except Exception as e:
                    logger.error(f"Could not load SSH key: {str(e)}")
                    raise
            elif self.ssh_agent_socket:
                connect_kwargs['allow_agent'] = True
            elif server_password:
                connect_kwargs['password'] = server_password
                logger.info(f"Using password authentication for {server}")
            else:
                logger.warning(f"No SSH key or password found for {server}")

            # Pre-flight TCP check above already proved the port is reachable,
            # so a single connect attempt is sufficient. This avoids stacking
            # paramiko timeouts on top of an already-confirmed reachable host.
            ssh.connect(**connect_kwargs)
            return ssh, None
        except paramiko.AuthenticationException:
            logger.error(f"Authentication failed for {server}")
            ssh.close()
            return None, {
                'success': False,
                'uname_line': None,
                'stderr': 'SSH authentication failed',
                'exit_code': -1,
                'error': 'Authentication failed'
            }
        except paramiko.SSHException as e:
            error_msg = str(e)
            logger.error(f"SSH error for {server}: {error_msg}")
            if 'timeout' in error_msg.lower():
                error_msg = f'Connection timeout: Server {server} did not respond'
            elif 'name resolution' in error_msg.lower() or 'could not resolve' in error_msg.lower():
                error_msg = f'DNS resolution failed: Could not resolve {server}'
            elif 'no route to host' in error_msg.lower():
                error_msg = f'Network unreachable: Cannot reach {server}'
            elif 'unable to connect to port 22' in error_msg.lower() or 'port 22' in error_msg.lower():
                error_msg = (
                    f'Cannot connect to SSH port 22 on {server}. Possible causes: SSH service not running, '
                    f'firewall blocking port 22, or server is down.'
                )
            ssh.close()
            return None, {
                'success': False,
                'uname_line': None,
                'stderr': error_msg,
                'exit_code': -1,
                'error': f'SSH error: {error_msg}'
            }
        except socket.timeout:
            logger.error(f"Connection timeout for {server}")
            ssh.close()
            return None, {
                'success': False,
                'uname_line': None,
                'stderr': 'Connection timeout',
                'exit_code': -1,
                'error': f'Connection timeout: Server {server} did not respond in time'
            }
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Unexpected error for {server}: {error_msg}", exc_info=True)
            if 'unable to connect to port 22' in error_msg.lower() or 'port 22' in error_msg.lower():
                error_msg = (
                    f'Cannot connect to SSH port 22 on {server}. Possible causes: SSH service not running, '
                    f'firewall blocking port 22, or server is down.'
                )
            ssh.close()
            return None, {
                'success': False,
                'uname_line': None,
                'stderr': error_msg,
                'exit_code': -1,
                'error': f'Unexpected error: {error_msg}'
            }

    def _execute_on_server(self, server, command):
        """
        Execute command on a single server
        
        Args:
            server: Server hostname/IP
            command: Bash command to execute
            
        Returns:
            dict: Execution result
        """
        ssh = None
        try:
            ssh, connect_error = self._open_ssh(server)
            if connect_error is not None:
                return {
                    'success': False,
                    'error': connect_error.get('error', 'SSH connection failed'),
                    'stdout': '',
                    'stderr': connect_error.get('stderr', ''),
                    'exit_code': connect_error.get('exit_code', -1)
                }
            
            # Execute command with increased timeout.
            # For multi-line scripts, persist a copy on the remote host for auditing/reuse,
            # then execute that saved file.
            if '\n' in command:
                wrapper_marker = 'SHELLSENTRY_WRAPPER_EOF'
                script_marker = 'SHELLSENTRY_SCRIPT_EOF'
                command = (
                    f"SHELLSENTRY_SCRIPT_DIR=\"$HOME/{self.script_archive_dir_name}\"\n"
                    f"mkdir -p \"$SHELLSENTRY_SCRIPT_DIR\"\n"
                    f"SHELLSENTRY_SCRIPT_PATH=\"$SHELLSENTRY_SCRIPT_DIR/ShellSentry_$(date +%Y-%m-%d_%H-%M-%S_%N).sh\"\n"
                    f"cat > \"$SHELLSENTRY_SCRIPT_PATH\" << '{script_marker}'\n"
                    f"{command}\n"
                    f"{script_marker}\n"
                    f"chmod 700 \"$SHELLSENTRY_SCRIPT_PATH\"\n"
                    f"bash \"$SHELLSENTRY_SCRIPT_PATH\"\n"
                    f"echo \"[ShellSentry] Script saved to: $SHELLSENTRY_SCRIPT_PATH\"\n"
                )
                command = f"bash -s << '{wrapper_marker}'\n{command}\n{wrapper_marker}"
            stdin, stdout, stderr = ssh.exec_command(command, timeout=60)
            
            # Wait for command to complete
            exit_code = stdout.channel.recv_exit_status()
            
            # Read output
            stdout_text = stdout.read().decode('utf-8', errors='replace')
            stderr_text = stderr.read().decode('utf-8', errors='replace')
            
            return {
                'success': exit_code == 0,
                'stdout': stdout_text,
                'stderr': stderr_text,
                'exit_code': exit_code
            }
            
        except paramiko.AuthenticationException:
            logger.error(f"Authentication failed for {server}")
            return {
                'success': False,
                'error': 'Authentication failed',
                'stdout': '',
                'stderr': 'SSH authentication failed',
                'exit_code': -1
            }
        except paramiko.SSHException as e:
            error_msg = str(e)
            logger.error(f"SSH error for {server}: {error_msg}")
            # Provide more helpful error messages
            if 'timeout' in error_msg.lower():
                error_msg = f'Connection timeout: Server {server} did not respond'
            elif 'name resolution' in error_msg.lower() or 'could not resolve' in error_msg.lower():
                error_msg = f'DNS resolution failed: Could not resolve {server}'
            elif 'no route to host' in error_msg.lower():
                error_msg = f'Network unreachable: Cannot reach {server}'
            elif 'unable to connect to port 22' in error_msg.lower() or 'port 22' in error_msg.lower():
                error_msg = f'Cannot connect to SSH port 22 on {server}. Possible causes: SSH service not running, firewall blocking port 22, or server is down.'
            return {
                'success': False,
                'error': f'SSH error: {error_msg}',
                'stdout': '',
                'stderr': error_msg,
                'exit_code': -1
            }
        except socket.timeout:
            logger.error(f"Connection timeout for {server}")
            return {
                'success': False,
                'error': f'Connection timeout: Server {server} did not respond in time',
                'stdout': '',
                'stderr': 'Connection timeout',
                'exit_code': -1
            }
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Unexpected error for {server}: {error_msg}", exc_info=True)
            # Check for connection errors
            if 'unable to connect to port 22' in error_msg.lower() or 'port 22' in error_msg.lower():
                error_msg = f'Cannot connect to SSH port 22 on {server}. Possible causes: SSH service not running, firewall blocking port 22, or server is down.'
            return {
                'success': False,
                'error': f'Unexpected error: {error_msg}',
                'stdout': '',
                'stderr': error_msg,
                'exit_code': -1
            }
        finally:
            if ssh:
                ssh.close()

    def _valid_script_filename(self, script_name):
        """Allow only safe basename-like script names."""
        if not script_name:
            return False
        return re.fullmatch(r'[A-Za-z0-9._-]+\.sh', script_name) is not None

    def list_saved_scripts(self, servers, username, user_id=None, original_request='', date_scope='all'):
        """
        List saved ShellSentry scripts from the fixed archive folder on each server.
        date_scope: all|today|yesterday
        """
        if not servers:
            return {'error': 'No servers specified'}

        date_scope = (date_scope or 'all').strip().lower()
        if date_scope not in ('all', 'today', 'yesterday'):
            date_scope = 'all'

        find_filter = ''
        if date_scope == 'today':
            find_filter = '-daystart -mtime 0'
        elif date_scope == 'yesterday':
            find_filter = '-daystart -mtime 1'

        archive_dir = f"$HOME/{self.script_archive_dir_name}"
        list_cmd = (
            f"ARCHIVE_DIR=\"{archive_dir}\"; "
            "if [ ! -d \"$ARCHIVE_DIR\" ]; then "
            "echo \"(archive directory not found)\"; exit 0; "
            "fi; "
            f"find \"$ARCHIVE_DIR\" -maxdepth 1 -type f -name 'ShellSentry_*.sh' {find_filter} "
            "-printf '%TY-%Tm-%Td %TH:%TM:%TS | %f\\n' 2>/dev/null | "
            "sort -r | "
            f"head -n {int(self.script_archive_max_list)}"
        )
        return self.execute_on_servers(list_cmd, servers, username, user_id, original_request)

    def execute_saved_script(self, servers, script_name, username, user_id=None, original_request=''):
        """Execute an existing saved script by filename on selected servers."""
        if not servers:
            return {'error': 'No servers specified'}
        if not self._valid_script_filename(script_name):
            return {
                'error': 'Invalid script name format',
                'details': 'Script name must look like ShellSentry_YYYY-MM-DD_HH-MM-SS_xxx.sh'
            }

        archive_dir = f"$HOME/{self.script_archive_dir_name}"
        run_cmd = (
            f"ARCHIVE_DIR=\"{archive_dir}\"; "
            f"SCRIPT_PATH=\"$ARCHIVE_DIR/{script_name}\"; "
            "if [ ! -f \"$SCRIPT_PATH\" ]; then "
            "echo \"Script not found: $SCRIPT_PATH\" 1>&2; exit 2; "
            "fi; "
            "bash \"$SCRIPT_PATH\""
        )
        return self.execute_on_servers(run_cmd, servers, username, user_id, original_request)

    def get_servers_having_script(self, servers, script_name):
        """Return two lists: servers_with_script, servers_missing_script.

        Runs the existence check in parallel so unreachable servers do not
        block the lookup on healthy hosts.
        """
        if not servers:
            return [], []
        if not self._valid_script_filename(script_name):
            return [], list(servers)

        archive_dir = f"$HOME/{self.script_archive_dir_name}"
        check_cmd = (
            f"ARCHIVE_DIR=\"{archive_dir}\"; "
            f"SCRIPT_PATH=\"$ARCHIVE_DIR/{script_name}\"; "
            "[ -f \"$SCRIPT_PATH\" ]"
        )

        def _worker(server):
            ssh, connect_error = self._open_ssh(server)
            if connect_error is not None:
                return False
            try:
                exit_code, _, _ = self._exec_remote_text(ssh, check_cmd, timeout=15)
                return exit_code == 0
            except Exception:
                return False
            finally:
                try:
                    ssh.close()
                except Exception:
                    pass

        check_results = self._run_in_parallel(servers, _worker)
        have = [s for s in servers if check_results.get(s) is True]
        missing = [s for s in servers if check_results.get(s) is not True]
        return have, missing

    def get_saved_script_content(self, server, script_name):
        """Read one saved script content from a single server for explanation."""
        if not self._valid_script_filename(script_name):
            return {'success': False, 'error': 'Invalid script name format', 'content': ''}

        ssh, connect_error = self._open_ssh(server)
        if connect_error is not None:
            return {'success': False, 'error': connect_error.get('error', 'SSH connection failed'), 'content': ''}

        try:
            archive_dir = f"$HOME/{self.script_archive_dir_name}"
            read_cmd = (
                f"ARCHIVE_DIR=\"{archive_dir}\"; "
                f"SCRIPT_PATH=\"$ARCHIVE_DIR/{script_name}\"; "
                "if [ ! -f \"$SCRIPT_PATH\" ]; then "
                "echo \"Script not found: $SCRIPT_PATH\" 1>&2; exit 2; "
                "fi; "
                "cat \"$SCRIPT_PATH\""
            )
            exit_code, out, err = self._exec_remote_text(ssh, read_cmd, timeout=25)
            if exit_code != 0:
                return {'success': False, 'error': err or f'Failed to read script (exit {exit_code})', 'content': ''}
            return {'success': True, 'error': '', 'content': out}
        except Exception as e:
            return {'success': False, 'error': str(e), 'content': ''}
        finally:
            ssh.close()

    def find_saved_script_content_across_servers(self, servers, script_name):
        """
        Search servers in order and return the first server that has the script content.
        """
        if not servers:
            return {
                'success': False,
                'error': 'No servers specified',
                'server': None,
                'content': '',
                'checked_servers': [],
            }
        if not self._valid_script_filename(script_name):
            return {
                'success': False,
                'error': 'Invalid script name format',
                'server': None,
                'content': '',
                'checked_servers': list(servers),
            }

        checked = []
        errors = []
        for server in servers:
            checked.append(server)
            data = self.get_saved_script_content(server, script_name)
            if data.get('success'):
                return {
                    'success': True,
                    'error': '',
                    'server': server,
                    'content': data.get('content', ''),
                    'checked_servers': checked,
                }
            errors.append(f"{server}: {data.get('error', 'not found')}")

        return {
            'success': False,
            'error': (
                f"Script '{script_name}' was not found on selected servers. "
                f"Checked: {', '.join(checked)}. Details: {' | '.join(errors)}"
            ),
            'server': None,
            'content': '',
            'checked_servers': checked,
        }

    def list_managed_cron_entries(self, servers, username, user_id=None, original_request=''):
        """List only ShellSentry-managed crontab entries."""
        if not servers:
            return {'error': 'No servers specified'}
        cmd = (
            "(crontab -l 2>/dev/null || true) | "
            f"grep '{self.safe_cron_tag_prefix}:' || "
            "echo '(no managed cron entries)'"
        )
        return self.execute_on_servers(cmd, servers, username, user_id, original_request)

    def schedule_saved_script_cron(self, servers, script_name, cron_expr, username, user_id=None, original_request=''):
        """
        Add/update a managed cron entry for one saved script.
        Only affects this script's managed line.
        """
        if not servers:
            return {'error': 'No servers specified'}
        if not self._valid_script_filename(script_name):
            return {'error': 'Invalid script name format'}

        tag = f"{self.safe_cron_tag_prefix}:{script_name}"
        archive_dir = f"$HOME/{self.script_archive_dir_name}"
        cmd = (
            f"ARCHIVE_DIR=\"{archive_dir}\"; "
            f"SCRIPT_PATH=\"$ARCHIVE_DIR/{script_name}\"; "
            "if [ ! -f \"$SCRIPT_PATH\" ]; then "
            "echo \"Script not found: $SCRIPT_PATH\" 1>&2; exit 2; "
            "fi; "
            "TMP_CRON_FILE=$(mktemp); "
            "(crontab -l 2>/dev/null || true) | grep -v "
            f"'# {tag}$' > \"$TMP_CRON_FILE\"; "
            f"CRON_LINE='{cron_expr} bash \"$HOME/{self.script_archive_dir_name}/{script_name}\" # {tag}'; "
            "echo \"$CRON_LINE\" >> \"$TMP_CRON_FILE\"; "
            "crontab \"$TMP_CRON_FILE\"; "
            "rm -f \"$TMP_CRON_FILE\"; "
            "echo \"Scheduled managed cron: $CRON_LINE\""
        )
        return self.execute_on_servers(cmd, servers, username, user_id, original_request)
    
    def _log_execution(self, username, user_id, original_request, command, servers, results):
        """Log command execution to database"""
        try:
            import json
            from datetime import datetime
            
            # Determine overall status
            all_success = all(r.get('success', False) for r in results.values())
            all_failed = all(not r.get('success', False) for r in results.values())
            
            if all_success:
                status = 'success'
            elif all_failed:
                status = 'failed'
            else:
                status = 'partial'
            
            # Create log entry
            log_entry = ExecutionLog(
                user_id=user_id or 0,
                username=username,
                original_request=original_request,
                generated_command=command,
                target_servers=json.dumps(servers),
                execution_status=status,
                execution_results=json.dumps(results),
                timestamp=datetime.utcnow()
            )
            
            db.session.add(log_entry)
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Error logging execution: {str(e)}", exc_info=True)

