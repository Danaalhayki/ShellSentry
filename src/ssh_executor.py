import paramiko
import os
import socket
from .logger import setup_logger
from .config import Config
from .models import db, ExecutionLog

logger = setup_logger()

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
    
    def execute_on_servers(self, command, servers, username, user_id=None, original_request=''):
        """
        Execute command on one or more remote servers
        
        Args:
            command: Bash command to execute
            servers: List of server hostnames/IPs
            username: Username of the user executing the command
            user_id: User ID for logging
            original_request: Original natural language request
            
        Returns:
            dict: Results from each server
        """
        if not servers:
            return {'error': 'No servers specified'}
        
        results = {}
        
        for server in servers:
            try:
                result = self._execute_on_server(server, command)
                results[server] = result
            except Exception as e:
                logger.error(f"Error executing on {server}: {str(e)}", exc_info=True)
                results[server] = {
                    'success': False,
                    'error': str(e),
                    'stdout': '',
                    'stderr': '',
                    'exit_code': -1
                }
        
        # Log execution
        self._log_execution(username, user_id, original_request, command, servers, results)
        
        return results
    
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
            # Create SSH client
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Connect to server with retry logic
            connect_kwargs = {
                'hostname': server,
                'username': self.ssh_user or 'root',
                'timeout': 30,  # Increased timeout
                'look_for_keys': False,  # Disable auto-detection to avoid DSA keys
                'allow_agent': False     # Disable agent to avoid DSA keys
            }
            
            # Use SSH key if available
            if self.ssh_key_path and os.path.exists(self.ssh_key_path):
                # Explicitly load RSA key to avoid DSA key issues
                try:
                    from paramiko import RSAKey, Ed25519Key
                    import io
                    with open(self.ssh_key_path, 'r') as f:
                        key_content = f.read()
                        # Only try RSA or Ed25519 keys, explicitly skip DSA
                        if 'BEGIN RSA PRIVATE KEY' in key_content or 'BEGIN OPENSSH PRIVATE KEY' in key_content:
                            # Try RSA first
                            try:
                                key = RSAKey.from_private_key(io.StringIO(key_content))
                                connect_kwargs['pkey'] = key
                                logger.info(f"Using RSA SSH key: {self.ssh_key_path}")
                            except Exception as e1:
                                # Try Ed25519
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
                # Use SSH agent
                connect_kwargs['allow_agent'] = True
            elif self.ssh_password:
                # Use password authentication
                connect_kwargs['password'] = self.ssh_password
                logger.info(f"Using password authentication for {server}")
            else:
                # Try password authentication (not recommended)
                logger.warning(f"No SSH key found, attempting password auth for {server}")
            
            # Retry connection logic
            max_retries = 2
            for attempt in range(max_retries):
                try:
                    ssh.connect(**connect_kwargs)
                    break  # Success, exit retry loop
                except (paramiko.SSHException, Exception) as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"SSH connection attempt {attempt + 1}/{max_retries} failed for {server}: {str(e)}, retrying...")
                        import time
                        time.sleep(1)
                        continue
                    else:
                        raise
            
            # Execute command with increased timeout
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

