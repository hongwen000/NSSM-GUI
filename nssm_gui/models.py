from pydantic import BaseModel, Field, field_validator, ValidationError
from typing import Optional, List, Dict
import re
import os

class ServiceConfig(BaseModel):
    """
    Pydantic model representing NSSM service configuration.
    """
    service_name: Optional[str] = Field('', min_length=1, max_length=256)
    application_path: Optional[str] = ''
    arguments: str = ''
    app_directory: Optional[str] = ''
    app_exit: str = 'Restart'
    display_name: str = ''
    description: str = ''
    object_name: str = 'LocalSystem'
    start: str = 'SERVICE_AUTO_START'
    type: str = 'SERVICE_WIN32_OWN_PROCESS'
    dependencies: List[str] = []
    process_priority: str = 'NORMAL_PRIORITY_CLASS'
    stdout_path: Optional[str] = ''
    stderr_path: Optional[str] = ''
    env_variables: Dict[str, str] = {}
    
    # Shutdown configurations
    kill_console_delay: int = 0
    kill_window_delay: int = 0
    kill_threads_delay: int = 0
    kill_process_tree: bool = False
    
    # Exit configurations
    throttle_delay: int = 0
    restart_delay: int = 0
    
    # Rotation configurations
    rotate_files: bool = False
    rotate_online: bool = False
    rotate_seconds: int = 0
    rotate_bytes_low: int = 0
    
    # Hooks configurations
    hook_share_output_handles: bool = False
    hooks: Dict[str, str] = {}
    
    @field_validator('service_name')
    def validate_service_name(cls, v):
        if not v:
            return v  # Allow empty string for default constructor
        # Service names must not contain illegal characters
        if not re.match(r'^[A-Za-z0-9_\-\.]+$', v):
            raise ValueError("Service name contains illegal characters.")
        return v

    @field_validator('application_path')
    def validate_application_path(cls, v):
        if not v:
            return v  # Allow empty string for default constructor
        return v

    @field_validator('app_directory')
    def validate_app_directory(cls, v):
        if not v:
            return v  # Allow empty string
        if not os.path.isdir(v):
            raise ValueError(f"App directory '{v}' does not exist or is not a directory.")
        return v

    @field_validator('stdout_path')
    def validate_stdout_path(cls, v):
        if not v:
            return v
        directory = os.path.dirname(v)
        if directory and not os.path.isdir(directory):
            raise ValueError(f"The directory for stdout path '{v}' does not exist.")
        return v

    @field_validator('stderr_path')
    def validate_stderr_path(cls, v):
        if not v:
            return v
        directory = os.path.dirname(v)
        if directory and not os.path.isdir(directory):
            raise ValueError(f"The directory for stderr path '{v}' does not exist.")
        return v

    @field_validator('start')
    def validate_start(cls, v):
        valid_values = ['SERVICE_AUTO_START', 'SERVICE_DELAYED_AUTO_START', 'SERVICE_DEMAND_START', 'SERVICE_DISABLED']
        if v not in valid_values:
            raise ValueError(f"Start must be one of {valid_values}.")
        return v

    @field_validator('process_priority')
    def validate_priority(cls, v):
        valid_priorities = [
            'REALTIME_PRIORITY_CLASS',
            'HIGH_PRIORITY_CLASS',
            'ABOVE_NORMAL_PRIORITY_CLASS',
            'NORMAL_PRIORITY_CLASS',
            'BELOW_NORMAL_PRIORITY_CLASS',
            'IDLE_PRIORITY_CLASS'
        ]
        if v not in valid_priorities:
            raise ValueError(f"Process priority must be one of {valid_priorities}.")
        return v

    @field_validator('object_name')
    def validate_object_name(cls, v):
        valid_accounts = ['LocalSystem', 'LocalService', 'NetworkService']
        if v in valid_accounts:
            return v
        # Validate domain accounts
        if '\\' in v:
            domain, user = v.split('\\', 1)
            if not domain or not user:
                raise ValueError("Invalid object name format. Expected 'DOMAIN\\UserName'.")
            return v
        else:
            raise ValueError(f"Invalid object name '{v}'. Use 'LocalSystem', 'LocalService', 'NetworkService', or 'DOMAIN\\UserName'.")

class ServiceInfo(BaseModel):
    """
    Model representing basic service information.
    """
    name: str
    display_name: str = ""
    state: str = "Unknown"
    status: str = "Unknown"
    pid: Optional[int] = None
    is_nssm: bool = False
    path: str = ""
    
    @property
    def is_running(self) -> bool:
        return self.state.lower() == "running"