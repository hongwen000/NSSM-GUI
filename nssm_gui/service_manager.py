import os
import subprocess
import json
import logging
from typing import List, Dict, Optional, Union, Tuple
import asyncio
import shlex
from concurrent.futures import ThreadPoolExecutor

from .models import ServiceConfig, ServiceInfo

# Create a thread pool for running commands asynchronously
executor = ThreadPoolExecutor(max_workers=4)

class NSSmManager:
    """
    Class for managing NSSM services.
    """
    def __init__(self, nssm_path: str):
        self.nssm_path = nssm_path
        self.logger = logging.getLogger("nssm_gui.service_manager")

    async def get_services(self) -> List[ServiceInfo]:
        """
        Get a list of all NSSM services.
        
        Returns:
            List[ServiceInfo]: List of service information objects
        """
        try:
            power_shell_cmd = [
                'powershell',
                '-NoProfile',
                '-Command',
                "Get-CimInstance -ClassName Win32_Service | Where-Object { $_.PathName -and ($_.PathName.Contains('nssm')) } | "
                "Select-Object -Property Name, DisplayName, State, Status, ProcessId, PathName | ConvertTo-Json"
            ]
            
            # Run the command asynchronously using the thread pool
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                # Create a new event loop if not already running
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
            result = await loop.run_in_executor(
                executor,
                lambda: subprocess.run(
                    power_shell_cmd,
                    capture_output=True,
                    text=True,
                    check=True
                )
            )
            
            output = result.stdout.strip()
            if not output:
                return []

            services_data = json.loads(output)
            
            # Handle both single service and multiple services
            if isinstance(services_data, dict):
                services_data = [services_data]
            
            # Convert to ServiceInfo objects
            services = []
            for svc in services_data:
                service_info = ServiceInfo(
                    name=svc.get('Name', ''),
                    display_name=svc.get('DisplayName', ''),
                    state=svc.get('State', 'Unknown'),
                    status=svc.get('Status', 'Unknown'),
                    pid=svc.get('ProcessId'),
                    is_nssm=True,
                    path=svc.get('PathName', '')
                )
                services.append(service_info)
                
            return services
            
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.strip() if e.stderr else "Unknown Error"
            self.logger.error(f"Error getting services: {error_msg}")
            raise RuntimeError(f"Failed to get services: {error_msg}")
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing JSON: {str(e)}")
            raise RuntimeError(f"Failed to parse service data: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            raise RuntimeError(f"Unexpected error: {str(e)}")

    async def run_nssm_command(self, args: List[str]) -> str:
        """
        Run an NSSM command asynchronously.
        
        Args:
            args: List of command arguments
            
        Returns:
            str: Command output
            
        Raises:
            RuntimeError: If the command fails
        """
        cmd = [self.nssm_path] + args
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                executor,
                lambda: subprocess.run(cmd, capture_output=True, check=False)
            )
            
            # Try to decode output with utf-8 first, then fallback to system encoding
            try:
                stdout = result.stdout.decode('utf-8', errors='replace')
                stderr = result.stderr.decode('utf-8', errors='replace')
            except UnicodeDecodeError:
                import locale
                encoding = locale.getpreferredencoding()
                stdout = result.stdout.decode(encoding, errors='replace')
                stderr = result.stderr.decode(encoding, errors='replace')
            
            if result.returncode != 0:
                error_msg = stderr if stderr else "Unknown error"
                self.logger.error(f"NSSM command failed: {error_msg}")
                raise RuntimeError(f"NSSM command failed: {error_msg}")
                
            return stdout
        except Exception as e:
            self.logger.error(f"Error running NSSM command: {str(e)}")
            raise RuntimeError(f"Error running NSSM command: {str(e)}")
            
    async def get_service_config(self, service_name: str) -> Optional[ServiceConfig]:
        """
        Get the configuration of a service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Optional[ServiceConfig]: Service configuration or None if not found
        """
        try:
            output = await self.run_nssm_command(['dump', service_name])
            config_data = self._parse_nssm_dump(output)
            return ServiceConfig(**config_data) if config_data else None
        except Exception as e:
            self.logger.error(f"Error getting service config: {str(e)}")
            return None
    
    def _parse_nssm_dump(self, dump_output: str) -> dict:
        """Parse NSSM dump output into a dictionary."""
        import shlex
        config = {}
        lines = dump_output.strip().split('\n')
        for line in lines:
            if not line.strip():
                continue
                
            try:
                lexer = shlex.shlex(line, posix=False)
                lexer.whitespace_split = True
                lexer.commenters = ''
                parts = list(lexer)
                
                if len(parts) >= 4:
                    command = parts[1]
                    service_name = parts[2]
                    
                    if 'service_name' not in config:
                        config['service_name'] = service_name
                        
                    if command == 'install':
                        config['application_path'] = parts[3]
                        if len(parts) > 4:
                            config['arguments'] = ' '.join(parts[4:])
                    elif command == 'set' and len(parts) >= 5:
                        setting = parts[3]
                        value = ' '.join(parts[4:])
                        
                        # Map settings to config fields
                        self._map_setting_to_config(config, setting, value)
            except Exception as e:
                self.logger.warning(f"Error parsing line '{line}': {str(e)}")
                continue
                
        return config
        
    def _map_setting_to_config(self, config: dict, setting: str, value: str):
        """Map NSSM settings to ServiceConfig fields."""
        # This is a helper method for _parse_nssm_dump
        setting_mapping = {
            'AppParameters': ('arguments', lambda v: v.strip('"')),
            'AppDirectory': ('app_directory', lambda v: v.strip('"')),
            'AppExit': ('app_exit', lambda v: v.strip('"').lstrip('Default ')),
            'DisplayName': ('display_name', lambda v: v.strip('"')),
            'Description': ('description', lambda v: v.strip('"')),
            'ObjectName': ('object_name', lambda v: v.strip('"')),
            'Start': ('start', lambda v: v.strip()),
            'Type': ('type', lambda v: v.strip()),
            'AppPriority': ('process_priority', lambda v: v.strip()),
            'AppStdout': ('stdout_path', lambda v: v.strip('"')),
            'AppStderr': ('stderr_path', lambda v: v.strip('"')),
        }
        
        # Handle special cases
        if setting in setting_mapping:
            field_name, transform_func = setting_mapping[setting]
            config[field_name] = transform_func(value)
        elif setting == 'DependOnService':
            dep = value.strip('"')
            config.setdefault('dependencies', []).append(dep)
        elif setting == 'AppEnvironmentExtra':
            env_var = value.strip('"')
            if '=' in env_var:
                key, val = env_var.split('=', 1)
                config.setdefault('env_variables', {})[key] = val
        elif setting == 'KillConsoleDelay':
            try:
                config['kill_console_delay'] = int(value)
            except ValueError:
                pass
        elif setting == 'KillWindowDelay':
            try:
                config['kill_window_delay'] = int(value)
            except ValueError:
                pass
        elif setting == 'KillThreadsDelay':
            try:
                config['kill_threads_delay'] = int(value)
            except ValueError:
                pass
        elif setting == 'KillProcessTree':
            config['kill_process_tree'] = value.strip() == '1'
        elif setting == 'ThrottleDelay':
            try:
                config['throttle_delay'] = int(value)
            except ValueError:
                pass
        elif setting == 'RestartDelay':
            try:
                config['restart_delay'] = int(value)
            except ValueError:
                pass
        elif setting == 'RotateFiles':
            config['rotate_files'] = value.strip() == '1'
        elif setting == 'RotateOnline':
            config['rotate_online'] = value.strip() == '1'
        elif setting == 'RotateSeconds':
            try:
                config['rotate_seconds'] = int(value)
            except ValueError:
                pass
        elif setting == 'RotateBytesLow':
            try:
                config['rotate_bytes_low'] = int(value)
            except ValueError:
                pass
        elif setting == 'HookShareOutputHandles':
            config['hook_share_output_handles'] = value.strip() == '1'
        elif setting.startswith('Hook_'):
            hook_event = setting[len('Hook_'):]
            config.setdefault('hooks', {})[hook_event] = value.strip('"')
    
    async def configure_service(self, config: ServiceConfig, edit: bool = False) -> bool:
        """
        Configure a service using the provided configuration.
        
        Args:
            config: Service configuration
            edit: Whether this is an edit operation or a new service
            
        Returns:
            bool: Whether the operation was successful
        """
        service_name = config.service_name
        
        try:
            # Install service if it's a new service
            if not edit:
                await self.run_nssm_command(['install', service_name, config.application_path])
            elif config.application_path:
                await self.run_nssm_command(['set', service_name, 'Application', config.application_path])
                
            # Configure each setting
            settings_commands = self._build_config_commands(service_name, config)
            
            # Run all the commands
            for cmd in settings_commands:
                if isinstance(cmd[0], list):  # Handle nested command lists
                    for subcmd in cmd:
                        await self.run_nssm_command(subcmd)
                else:
                    await self.run_nssm_command(cmd)
                    
            return True
        except Exception as e:
            self.logger.error(f"Error configuring service: {str(e)}")
            raise RuntimeError(f"Failed to configure service: {str(e)}")
            
    def _build_config_commands(self, service_name: str, config: ServiceConfig) -> List[List[str]]:
        """Build NSSM commands from the configuration."""
        commands = []
        
        # Basic settings
        if config.arguments:
            commands.append(['set', service_name, 'AppParameters', config.arguments])
        if config.app_directory:
            commands.append(['set', service_name, 'AppDirectory', config.app_directory])
        if config.app_exit:
            commands.append(['set', service_name, 'AppExit', 'Default', config.app_exit])
        if config.display_name:
            commands.append(['set', service_name, 'DisplayName', config.display_name])
        if config.description:
            commands.append(['set', service_name, 'Description', config.description])
        if config.object_name:
            commands.append(['set', service_name, 'ObjectName', config.object_name])
        if config.start:
            commands.append(['set', service_name, 'Start', config.start])
        if config.type:
            commands.append(['set', service_name, 'Type', config.type])
        if config.process_priority:
            commands.append(['set', service_name, 'AppPriority', config.process_priority])
        if config.stdout_path:
            commands.append(['set', service_name, 'AppStdout', config.stdout_path])
        if config.stderr_path:
            commands.append(['set', service_name, 'AppStderr', config.stderr_path])
            
        # Dependencies
        dep_commands = []
        for dep in config.dependencies:
            dep_commands.append(['set', service_name, 'DependOnService', '+', dep])
        if dep_commands:
            commands.append(dep_commands)
            
        # Environment variables
        env_commands = []
        for key, value in config.env_variables.items():
            env_commands.append(['set', service_name, 'AppEnvironmentExtra', f'{key}={value}'])
        if env_commands:
            commands.append(env_commands)
            
        # Shutdown configurations
        commands.append(['set', service_name, 'KillConsoleDelay', str(config.kill_console_delay)])
        commands.append(['set', service_name, 'KillWindowDelay', str(config.kill_window_delay)])
        commands.append(['set', service_name, 'KillThreadsDelay', str(config.kill_threads_delay)])
        commands.append(['set', service_name, 'KillProcessTree', '1' if config.kill_process_tree else '0'])
        
        # Exit configurations
        commands.append(['set', service_name, 'ThrottleDelay', str(config.throttle_delay)])
        commands.append(['set', service_name, 'RestartDelay', str(config.restart_delay)])
        
        # Rotation configurations
        commands.append(['set', service_name, 'RotateFiles', '1' if config.rotate_files else '0'])
        commands.append(['set', service_name, 'RotateOnline', '1' if config.rotate_online else '0'])
        commands.append(['set', service_name, 'RotateSeconds', str(config.rotate_seconds)])
        commands.append(['set', service_name, 'RotateBytesLow', str(config.rotate_bytes_low)])
        
        # Hooks configurations
        commands.append(['set', service_name, 'HookShareOutputHandles', '1' if config.hook_share_output_handles else '0'])
        
        hook_commands = []
        for event, action in config.hooks.items():
            hook_commands.append(['set', service_name, f'Hook_{event}', action])
        if hook_commands:
            commands.append(hook_commands)
            
        return commands
        
    async def remove_service(self, service_name: str) -> bool:
        """
        Remove a service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            bool: Whether the operation was successful
        """
        try:
            # First stop the service
            try:
                await self.run_nssm_command(['stop', service_name])
            except Exception:
                # Ignore errors when stopping the service
                pass
                
            # Remove the service
            await self.run_nssm_command(['remove', service_name, 'confirm'])
            return True
        except Exception as e:
            self.logger.error(f"Error removing service: {str(e)}")
            return False
            
    async def start_service(self, service_name: str) -> bool:
        """Start a service."""
        try:
            await self.run_nssm_command(['start', service_name])
            return True
        except Exception as e:
            self.logger.error(f"Error starting service: {str(e)}")
            return False
            
    async def stop_service(self, service_name: str) -> bool:
        """Stop a service."""
        try:
            await self.run_nssm_command(['stop', service_name])
            return True
        except Exception as e:
            self.logger.error(f"Error stopping service: {str(e)}")
            return False
            
    async def restart_service(self, service_name: str) -> bool:
        """Restart a service."""
        try:
            await self.stop_service(service_name)
            await self.start_service(service_name)
            return True
        except Exception as e:
            self.logger.error(f"Error restarting service: {str(e)}")
            return False
            
    async def get_service_status(self, service_name: str) -> str:
        """Get the status of a service."""
        try:
            command = ['sc', 'query', service_name]
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                executor,
                lambda: subprocess.run(command, capture_output=True, text=True, check=False)
            )
            
            if result.returncode != 0:
                return "Unknown"
                
            for line in result.stdout.split('\n'):
                if 'STATE' in line:
                    parts = line.strip().split(':')
                    if len(parts) > 1:
                        state_parts = parts[1].strip().split()
                        if len(state_parts) > 0:
                            return state_parts[0]
            return "Unknown"
        except Exception as e:
            self.logger.error(f"Error getting service status: {str(e)}")
            return "Error"
            
    async def get_service_logs(self, service_name: str, log_type: str = 'stdout') -> str:
        """
        Get the service logs.
        
        Args:
            service_name: Name of the service
            log_type: 'stdout' or 'stderr'
            
        Returns:
            str: Log content
        """
        try:
            config = await self.get_service_config(service_name)
            if not config:
                return "Could not retrieve service configuration."
                
            log_path = config.stdout_path if log_type == 'stdout' else config.stderr_path
            if not log_path:
                return f"No {log_type} log path configured."
                
            if not os.path.exists(log_path):
                return f"Log file {log_path} does not exist."
                
            # Read the log file
            with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
                
            return content
        except Exception as e:
            self.logger.error(f"Error getting service logs: {str(e)}")
            return f"Error getting service logs: {str(e)}"