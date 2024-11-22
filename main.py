import sys
import os
import subprocess
import requests
import zipfile
from io import BytesIO
from PyQt5 import QtWidgets, QtGui, QtCore
import locale
import logging

from pydantic import BaseModel, validator

from pydantic import BaseModel, Field, field_validator, ValidationError
from typing import Optional, List, Dict
import os
import re
import ctypes

# Configure logging
logging.basicConfig(filename='nssm_gui.log', level=logging.ERROR,
                    format='%(asctime)s:%(levelname)s:%(message)s')


class ServiceConfig(BaseModel):
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
        if not os.path.isfile(v):
            raise ValueError(f"Application path '{v}' does not exist or is not a file.")

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

    @field_validator('dependencies')
    def validate_dependencies(cls, v):
        return v

    @field_validator('env_variables')
    def validate_env_variables(cls, v):
        for key in v:
            if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', key):
                raise ValueError(f"Environment variable name '{key}' is invalid.")
        return v

    @field_validator('app_exit')
    def validate_app_exit(cls, v):
        valid_actions = ['Restart', 'Ignore', 'Exit', 'Suicide']
        # Handle cases like 'Default Restart'
        if ' ' in v:
            parts = v.split()
            if len(parts) == 2 and parts[0] == 'Default' and parts[1] in valid_actions:
                return v
        if v not in valid_actions:
            raise ValueError(f"AppExit must be one of {valid_actions}, optionally prefixed with 'Default '.")
        return v

    @field_validator('type')
    def validate_type(cls, v):
        valid_types = ['SERVICE_WIN32_OWN_PROCESS', 'SERVICE_INTERACTIVE_PROCESS']
        if v not in valid_types:
            raise ValueError(f"Type must be one of {valid_types}.")
        return v


NSSM_URL = 'https://nssm.cc/ci/nssm-2.24-103-gdee49fc.zip'
CACHE_DIR = os.path.join(os.getenv('APPDATA'), 'nssm-gui')
NSSM_EXE_PATH = os.path.join(CACHE_DIR, 'nssm.exe')

def download_nssm():
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)
    response = requests.get(NSSM_URL)
    with zipfile.ZipFile(BytesIO(response.content)) as z:
        for file in z.namelist():
            if file.endswith('win64/nssm.exe'):
                with z.open(file) as source, open(NSSM_EXE_PATH, 'wb') as target:
                    target.write(source.read())
                break

if not os.path.exists(NSSM_EXE_PATH):
    download_nssm()


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


class NSSMGUI(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('NSSM-GUI')
        self.setGeometry(100, 100, 1000, 800)
        self.initUI()
        self.load_services()

    def initUI(self):
        # Central widget
        self.central_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.central_widget)

        # Layouts
        self.main_layout = QtWidgets.QVBoxLayout()
        self.button_layout = QtWidgets.QHBoxLayout()

        # Service Table
        self.service_table = QtWidgets.QTableWidget()
        self.service_table.setColumnCount(2)
        self.service_table.setHorizontalHeaderLabels(['Service Name', 'Status'])
        self.service_table.horizontalHeader().setStretchLastSection(True)
        self.service_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.service_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.main_layout.addWidget(self.service_table)

        # Buttons
        self.add_button = QtWidgets.QPushButton('Add Service')
        self.edit_button = QtWidgets.QPushButton('Edit Service')
        self.delete_button = QtWidgets.QPushButton('Delete Service')
        self.start_button = QtWidgets.QPushButton('Start Service')
        self.stop_button = QtWidgets.QPushButton('Stop Service')
        self.enable_button = QtWidgets.QPushButton('Enable Service')
        self.disable_button = QtWidgets.QPushButton('Disable Service')

        self.button_layout.addWidget(self.add_button)
        self.button_layout.addWidget(self.edit_button)
        self.button_layout.addWidget(self.delete_button)
        self.button_layout.addWidget(self.start_button)
        self.button_layout.addWidget(self.stop_button)
        self.button_layout.addWidget(self.enable_button)
        self.button_layout.addWidget(self.disable_button)

        self.main_layout.addLayout(self.button_layout)
        self.central_widget.setLayout(self.main_layout)

        # Connect signals
        self.add_button.clicked.connect(self.add_service)
        self.edit_button.clicked.connect(self.edit_service)
        self.delete_button.clicked.connect(self.delete_service)
        self.start_button.clicked.connect(self.start_service)
        self.stop_button.clicked.connect(self.stop_service)
        self.enable_button.clicked.connect(self.enable_service)
        self.disable_button.clicked.connect(self.disable_service)

    def run_nssm_command(self, args):
        cmd = [NSSM_EXE_PATH] + args
        try:
            # Capture output as bytes
            result = subprocess.run(cmd, capture_output=True, check=False)
            # Determine the encoding used by nssm.exe
            # Assuming UTF-8; adjust if nssm.exe uses a different encoding
            encoding = 'utf-8'

            # Decode stdout and stderr
            stdout = result.stdout.decode(encoding, errors='replace')
            stderr = result.stderr.decode(encoding, errors='replace')

            if stderr:
                # Handle error output
                QtWidgets.QMessageBox.critical(self, 'NSSM Error', stderr)
            return stdout
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, 'Error', f"Failed to run NSSM command: {str(e)}")
            logging.error("Error in run_nssm_command", exc_info=True)
            return ''


    def load_services(self):
        # Clear existing rows
        self.service_table.setRowCount(0)
        # Get the system encoding
        try:
            # Get list of services using NSSM naming convention
            # Use the system's preferred encoding
            sys_encoding = locale.getpreferredencoding()
            output = subprocess.check_output(['sc', 'query', 'type=', 'service', 'state=', 'all'], text=True, encoding=sys_encoding)
            service_names = []
            for line in output.split('\n'):
                if 'SERVICE_NAME:' in line:
                    name = line.strip().split(':')[1].strip()
                    if self.is_nssm_service(name):
                        service_names.append(name)
            # Populate the table
            for service in service_names:
                row_position = self.service_table.rowCount()
                self.service_table.insertRow(row_position)
                self.service_table.setItem(row_position, 0, QtWidgets.QTableWidgetItem(service))
                status = self.get_service_status(service)
                self.service_table.setItem(row_position, 1, QtWidgets.QTableWidgetItem(status))
        except subprocess.CalledProcessError as e:
            QtWidgets.QMessageBox.critical(self, 'Error', f"Failed to load services:\n{e.stderr}")

    def is_nssm_service(self, service_name):
        # Implement a method to check if a service is managed by NSSM
        try:
            output = subprocess.check_output(['sc', 'qc', service_name])
            for line in output.decode(encoding='utf-8', errors='replace').split('\n'):
                if 'BINARY_PATH_NAME' in line and 'nssm.exe' in line.lower():
                    return True
        except subprocess.CalledProcessError:
            pass
        return False

    def get_service_status(self, service_name):
        output = subprocess.check_output(['sc', 'query', service_name])
        for line in output.decode(encoding='utf-8', errors='replace').split('\n'):
            if 'STATE' in line:
                return line.strip().split(':')[1].split('  ')[1]
        return 'Unknown'

    def add_service(self):
        dialog = AddServiceDialog(self, existing_config=ServiceConfig())
        if dialog.exec_():
            service_config = dialog.get_service_config()
            if service_config:
                self.configure_service(service_config)
                self.load_services()

    def edit_service(self):
        current_row = self.service_table.currentRow()
        if current_row >= 0:
            service_name = self.service_table.item(current_row, 0).text()
            # Get current configuration using nssm dump
            service_config = self.get_service_config(service_name)
            if service_config:
                dialog = AddServiceDialog(self, service_name=service_name, existing_config=service_config)
                if dialog.exec_():
                    updated_config = dialog.get_service_config()
                    if updated_config:
                        self.configure_service(updated_config, edit=True, old_config=service_config)
                        self.load_services()
            else:
                QtWidgets.QMessageBox.warning(self, 'Error', f'Could not retrieve configuration for service {service_name}')

    # def configure_service(self, config: ServiceConfig, edit: bool = False, current_config: Optional[ServiceConfig] = None):
    #     service_name = config.service_name
    #     if not service_name:
    #         QtWidgets.QMessageBox.warning(self, 'Configuration Error', 'Service Name is required.')
    #         return
    #     if not config.application_path and not edit:
    #         QtWidgets.QMessageBox.warning(self, 'Configuration Error', 'Executable Path is required.')
    #         return

    #     # Build the command to set various configurations
    #     settings_commands = []
    #     args = []
    #     if edit:
    #         if config.application_path:
    #             settings_commands.append(['set', service_name, 'Application', config.application_path])
    #     else:
    #         args = ['install', service_name, config.application_path]

    #     if config.arguments:
    #         settings_commands.append(['set', service_name, 'AppParameters', config.arguments])

    #     if config.app_directory:
    #         settings_commands.append(['set', service_name, 'AppDirectory', config.app_directory])

    #     if config.app_exit:
    #         settings_commands.append(['set', service_name, 'AppExit', 'Default', config.app_exit])

    #     if config.display_name:
    #         settings_commands.append(['set', service_name, 'DisplayName', config.display_name])

    #     if config.description:
    #         settings_commands.append(['set', service_name, 'Description', config.description])

    #     if config.object_name:
    #         settings_commands.append(['set', service_name, 'ObjectName', config.object_name])

    #     if config.start:
    #         settings_commands.append(['set', service_name, 'Start', config.start])

    #     if config.type:
    #         settings_commands.append(['set', service_name, 'Type', config.type])

    #     if config.dependencies:
    #         for dep in config.dependencies:
    #             settings_commands.append(['set', service_name, 'DependOnService', '+', dep])

    #     if config.process_priority:
    #         settings_commands.append(['set', service_name, 'AppPriority', config.process_priority])

    #     if config.stdout_path:
    #         settings_commands.append(['set', service_name, 'AppStdout', config.stdout_path])
        
    #     if config.stderr_path:
    #         settings_commands.append(['set', service_name, 'AppStderr', config.stderr_path])

    #     if config.env_variables:
    #         for key, value in config.env_variables.items():
    #             settings_commands.append(['set', service_name, 'AppEnvironmentExtra', f'{key}={value}'])

    #     # Shutdown configurations
    #     settings_commands.append(['set', service_name, 'KillConsoleDelay', str(config.kill_console_delay)])
    #     settings_commands.append(['set', service_name, 'KillWindowDelay', str(config.kill_window_delay)])
    #     settings_commands.append(['set', service_name, 'KillThreadsDelay', str(config.kill_threads_delay)])
    #     settings_commands.append(['set', service_name, 'KillProcessTree', '1' if config.kill_process_tree else '0'])

    #     # Exit configurations
    #     settings_commands.append(['set', service_name, 'ThrottleDelay', str(config.throttle_delay)])
    #     settings_commands.append(['set', service_name, 'RestartDelay', str(config.restart_delay)])

    #     # Rotation configurations
    #     settings_commands.append(['set', service_name, 'RotateFiles', '1' if config.rotate_files else '0'])
    #     settings_commands.append(['set', service_name, 'RotateOnline', '1' if config.rotate_online else '0'])
    #     settings_commands.append(['set', service_name, 'RotateSeconds', str(config.rotate_seconds)])
    #     settings_commands.append(['set', service_name, 'RotateBytesLow', str(config.rotate_bytes_low)])

    #     # Hooks configurations
    #     settings_commands.append(['set', service_name, 'HookShareOutputHandles', '1' if config.hook_share_output_handles else '0'])
    #     for event, action in config.hooks.items():
    #         settings_commands.append(['set', service_name, f'Hook_{event}', action])

    #     # Run the commands
    #     if len(args):
    #         self.run_nssm_command(args)
    #     for cmd in settings_commands:
    #         self.run_nssm_command(cmd)

    #     QtWidgets.QMessageBox.information(self, 'Success', f"Service '{service_name}' has been {'edited' if edit else 'added'} successfully.")

    def configure_service(self, config: ServiceConfig, edit: bool = False, old_config: Optional[ServiceConfig] = None):
        service_name = config.service_name
        if not service_name:
            QtWidgets.QMessageBox.warning(self, 'Configuration Error', 'Service Name is required.')
            return
        if not config.application_path and not edit:
            QtWidgets.QMessageBox.warning(self, 'Configuration Error', 'Executable Path is required.')
            return

        # Determine the default config
        default_config = ServiceConfig()

        # Convert configs to dictionaries for easy comparison
        config_dict = config.model_dump()
        default_config_dict = default_config.model_dump()
        old_config_dict = old_config.model_dump() if old_config else {}

        settings_commands = []

        # Iterate through each field in ServiceConfig
        for field, new_value in config_dict.items():
            # Skip service_name as it's used for identification
            if field == 'service_name':
                continue

            # Determine if the field exists in old_config
            if old_config and field in old_config_dict:
                old_value = old_config_dict[field]
                if new_value != old_value:
                    # Field exists in old_config and has changed
                    settings_commands.append(self.build_set_command(service_name, field, new_value))
            else:
                # Field does not exist in old_config
                default_value = default_config_dict.get(field)
                if new_value != default_value:
                    # Field is different from default
                    settings_commands.append(self.build_set_command(service_name, field, new_value))

        # Build the command to install or edit the service
        if edit:
            # if config.application_path:
            #     settings_commands.append(['set', service_name, 'Application', config.application_path])
            pass
        else:
            args = ['install', service_name, config.application_path]
            self.run_nssm_command(args)

        # Run the settings commands
        for cmd in settings_commands:
            self.run_nssm_command(cmd)

        if not edit or (edit and settings_commands):
            QtWidgets.QMessageBox.information(self, 'Success', f"Service '{service_name}' has been {'edited' if edit else 'added'} successfully.")
        else:
            QtWidgets.QMessageBox.information(self, 'Success', f"No changes for service '{service_name}'.")

    def build_set_command(self, service_name: str, field: str, value):
        """
        Helper method to build NSSM set commands based on the field type.
        """
        # Mapping fields to NSSM parameters
        field_mapping = {
            'arguments': ['set', service_name, 'AppParameters', value],
            'app_directory': ['set', service_name, 'AppDirectory', value],
            'app_exit': ['set', service_name, 'AppExit', 'Default', value],
            'display_name': ['set', service_name, 'DisplayName', value],
            'description': ['set', service_name, 'Description', value],
            'object_name': ['set', service_name, 'ObjectName', value],
            'start': ['set', service_name, 'Start', value],
            'type': ['set', service_name, 'Type', value],
            'process_priority': ['set', service_name, 'AppPriority', value],
            'stdout_path': ['set', service_name, 'AppStdout', value],
            'stderr_path': ['set', service_name, 'AppStderr', value],
            'kill_console_delay': ['set', service_name, 'KillConsoleDelay', str(value)],
            'kill_window_delay': ['set', service_name, 'KillWindowDelay', str(value)],
            'kill_threads_delay': ['set', service_name, 'KillThreadsDelay', str(value)],
            'kill_process_tree': ['set', service_name, 'KillProcessTree', '1' if value else '0'],
            'throttle_delay': ['set', service_name, 'ThrottleDelay', str(value)],
            'restart_delay': ['set', service_name, 'RestartDelay', str(value)],
            'rotate_files': ['set', service_name, 'RotateFiles', '1' if value else '0'],
            'rotate_online': ['set', service_name, 'RotateOnline', '1' if value else '0'],
            'rotate_seconds': ['set', service_name, 'RotateSeconds', str(value)],
            'rotate_bytes_low': ['set', service_name, 'RotateBytesLow', str(value)],
            'hook_share_output_handles': ['set', service_name, 'HookShareOutputHandles', '1' if value else '0'],
        }

        if field in field_mapping:
            return field_mapping[field]
        elif field == 'dependencies':
            # Handle dependencies separately as they are a list
            commands = []
            for dep in value:
                commands.append(['set', service_name, 'DependOnService', '+', dep])
            return commands  # This will be a list of lists
        elif field == 'env_variables':
            # Handle environment variables separately as they are a dict
            commands = []
            for key, val in value.items():
                commands.append(['set', service_name, 'AppEnvironmentExtra', f'{key}={val}'])
            return commands  # This will be a list of lists
        elif field == 'hooks':
            # Handle hooks separately as they are a dict
            commands = []
            for event, action in value.items():
                commands.append(['set', service_name, f'Hook_{event}', action])
            return commands  # This will be a list of lists
        else:
            # For any other fields, attempt a generic set
            return ['set', service_name, field, str(value)]

    

    def delete_service(self):
        current_row = self.service_table.currentRow()
        if current_row >= 0:
            service_name = self.service_table.item(current_row, 0).text()
            reply = QtWidgets.QMessageBox.question(self, 'Confirm Delete',
                                                   f'Are you sure you want to delete the service "{service_name}"?',
                                                   QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                                                   QtWidgets.QMessageBox.No)
            if reply == QtWidgets.QMessageBox.Yes:
                output = self.run_nssm_command(['remove', service_name, 'confirm'])
                if output:
                    QtWidgets.QMessageBox.information(self, 'Success', f"Service '{service_name}' has been deleted successfully.")
                    self.load_services()

    def start_service(self):
        current_row = self.service_table.currentRow()
        if current_row >= 0:
            service_name = self.service_table.item(current_row, 0).text()
            output = self.run_nssm_command(['start', service_name])
            if output:
                QtWidgets.QMessageBox.information(self, 'Success', f"Service '{service_name}' started successfully.")
                self.load_services()

    def stop_service(self):
        current_row = self.service_table.currentRow()
        if current_row >= 0:
            service_name = self.service_table.item(current_row, 0).text()
            output = self.run_nssm_command(['stop', service_name])
            if output:
                QtWidgets.QMessageBox.information(self, 'Success', f"Service '{service_name}' stopped successfully.")
                self.load_services()

    def enable_service(self):
        current_row = self.service_table.currentRow()
        if current_row >= 0:
            service_name = self.service_table.item(current_row, 0).text()
            try:
                subprocess.run(['sc', 'config', service_name, 'start=', 'auto'], check=True)
                QtWidgets.QMessageBox.information(self, 'Success', f"Service '{service_name}' enabled successfully.")
                self.load_services()
            except subprocess.CalledProcessError as e:
                QtWidgets.QMessageBox.critical(self, 'Error', f"Failed to enable service '{service_name}':\n{e}")

    def disable_service(self):
        current_row = self.service_table.currentRow()
        if current_row >= 0:
            service_name = self.service_table.item(current_row, 0).text()
            try:
                subprocess.run(['sc', 'config', service_name, 'start=', 'disabled'], check=True)
                QtWidgets.QMessageBox.information(self, 'Success', f"Service '{service_name}' disabled successfully.")
                self.load_services()
            except subprocess.CalledProcessError as e:
                QtWidgets.QMessageBox.critical(self, 'Error', f"Failed to disable service '{service_name}':\n{e}")

    def get_service_config(self, service_name: str) -> Optional[ServiceConfig]:
        # Use nssm dump to get the current configuration
        output = self.run_nssm_command(['dump', service_name])
        if not output:
            return None  # Error already shown
        config_data = self.parse_nssm_dump(output)
        if config_data:
            try:
                return ServiceConfig(**config_data)
            except ValidationError as e:
                # Display validation errors to the user
                error_messages = '\n'.join([f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()])
                QtWidgets.QMessageBox.warning(self, 'Validation Error', f"Failed to parse service configuration:\n{error_messages}")
        return None

    def parse_nssm_dump(self, dump_output: str) -> dict:
        import shlex  # Import shlex for proper command-line parsing
        config = {}
        lines = dump_output.strip().split('\n')
        for line in lines:
            if not line.strip():
                continue  # Skip empty lines
            # Use shlex with posix=False to handle Windows paths correctly
            lexer = shlex.shlex(line, posix=False)
            lexer.whitespace_split = True
            lexer.commenters = ''
            try:
                parts = list(lexer)
            except ValueError as e:
                QtWidgets.QMessageBox.warning(self, 'Parsing Error', f"Failed to parse line:\n{line}\nError: {str(e)}")
                continue

            # Ensure we have at least 4 parts: nssm.exe, command, service_name, setting/value
            if len(parts) >= 4:
                # The command is the second part
                command = parts[1]
                service_name = parts[2]
                if 'service_name' not in config:
                    config['service_name'] = service_name
                if command == 'install':
                    # The application path is the fourth part
                    config['application_path'] = parts[3]
                    if len(parts) > 4:
                        # If there are additional arguments
                        config['arguments'] = ' '.join(parts[4:])
                elif command == 'set' and len(parts) >= 5:
                    setting = parts[3]
                    value = ' '.join(parts[4:])
                    # Handle specific settings
                    if setting == 'AppParameters':
                        config['arguments'] = value.strip('"')
                    elif setting == 'AppDirectory':
                        config['app_directory'] = value.strip('"')
                    elif setting == 'AppExit':
                        config['app_exit'] = value.strip('"').lstrip('Default ')
                    elif setting == 'DisplayName':
                        config['display_name'] = value.strip('"')
                    elif setting == 'Description':
                        config['description'] = value.strip('"')
                    elif setting == 'ObjectName':
                        config['object_name'] = value.strip('"')
                    elif setting == 'Start':
                        config['start'] = value.strip()
                    elif setting == 'Type':
                        config['type'] = value.strip()
                    elif setting == 'DependOnService':
                        dep = value.strip('"')
                        config.setdefault('dependencies', []).append(dep)
                    elif setting == 'AppPriority':
                        config['process_priority'] = value.strip()
                    elif setting == 'AppStdout':
                        config['stdout_path'] = value.strip('"')
                    elif setting == 'AppStderr':
                        config['stderr_path'] = value.strip('"')
                    elif setting == 'AppEnvironmentExtra':
                        env_var = value.strip('"')
                        if '=' in env_var:
                            key, val = env_var.split('=', 1)
                            config.setdefault('env_variables', {})[key] = val
                    # Shutdown settings
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
                    # Exit settings
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
                    # Rotation settings
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
                    # Hooks settings
                    elif setting.startswith('Hook_'):
                        hook_event = setting[len('Hook_'):].split('_')[0]
                        hook_action = setting[len('Hook_'):].split('_')[1] if '_' in setting[len('Hook_'):] else ' '.join(setting[len('Hook_'):].split('_')[1:])
                        config.setdefault('hooks', {})[hook_event] = value.strip('"')
        return config


class AddServiceDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, service_name: Optional[str] = None, existing_config: Optional[ServiceConfig] = None):
        super(AddServiceDialog, self).__init__(parent)
        self.setWindowTitle('Add Service' if not service_name else 'Edit Service')
        self.setFixedSize(700, 800)
        self.service_name = service_name
        self.existing_config = existing_config
        self.initUI()
        if existing_config:
            self.load_service_config(existing_config)

    def initUI(self):
        self.layout = QtWidgets.QVBoxLayout(self)

        # Tabs
        self.tabs = QtWidgets.QTabWidget()
        self.layout.addWidget(self.tabs)

        # Application Tab
        self.app_tab = QtWidgets.QWidget()
        self.tabs.addTab(self.app_tab, 'Application')
        self.init_app_tab()

        # Details Tab
        self.details_tab = QtWidgets.QWidget()
        self.tabs.addTab(self.details_tab, 'Details')
        self.init_details_tab()

        # Logon Tab
        self.logon_tab = QtWidgets.QWidget()
        self.tabs.addTab(self.logon_tab, 'Logon')
        self.init_logon_tab()

        # Dependencies Tab
        self.dependencies_tab = QtWidgets.QWidget()
        self.tabs.addTab(self.dependencies_tab, 'Dependencies')
        self.init_dependencies_tab()

        # Process Tab
        self.process_tab = QtWidgets.QWidget()
        self.tabs.addTab(self.process_tab, 'Process')
        self.init_process_tab()

        # I/O Tab
        self.io_tab = QtWidgets.QWidget()
        self.tabs.addTab(self.io_tab, 'I/O')
        self.init_io_tab()

        # Environment Tab
        self.env_tab = QtWidgets.QWidget()
        self.tabs.addTab(self.env_tab, 'Environment')
        self.init_env_tab()

        # Shutdown Tab
        self.shutdown_tab = QtWidgets.QWidget()
        self.tabs.addTab(self.shutdown_tab, 'Shutdown')
        self.init_shutdown_tab()

        # Exit Tab
        self.exit_tab = QtWidgets.QWidget()
        self.tabs.addTab(self.exit_tab, 'Exit')
        self.init_exit_tab()

        # Rotation Tab
        self.rotation_tab = QtWidgets.QWidget()
        self.tabs.addTab(self.rotation_tab, 'Rotation')
        self.init_rotation_tab()

        # Hooks Tab
        self.hooks_tab = QtWidgets.QWidget()
        self.tabs.addTab(self.hooks_tab, 'Hooks')
        self.init_hooks_tab()

        # Buttons
        self.button_box = QtWidgets.QDialogButtonBox()
        self.button_box.setStandardButtons(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

    def init_app_tab(self):
        layout = QtWidgets.QFormLayout()
        self.app_tab.setLayout(layout)

        self.service_name_input = QtWidgets.QLineEdit()
        self.service_name_input.setPlaceholderText('Required (Alphanumeric, _, -, .)')
        self.service_name_input.setToolTip('Enter a unique service name. Allowed characters: A-Z, a-z, 0-9, _, -, .')
        self.executable_path_input = QtWidgets.QLineEdit()
        self.service_name_input.setPlaceholderText('Required')
        self.executable_path_input.setPlaceholderText('Required')
        self.arguments_input = QtWidgets.QLineEdit()
        browse_button = QtWidgets.QPushButton('Browse')
        browse_button.clicked.connect(self.browse_executable)

        exec_layout = QtWidgets.QHBoxLayout()
        exec_layout.addWidget(self.executable_path_input)
        exec_layout.addWidget(browse_button)

        # App directory input
        self.app_directory_input = QtWidgets.QLineEdit()
        self.app_directory_input.setPlaceholderText('Optional')
        browse_dir_button = QtWidgets.QPushButton('Browse')
        browse_dir_button.clicked.connect(self.browse_app_directory)

        app_dir_layout = QtWidgets.QHBoxLayout()
        app_dir_layout.addWidget(self.app_directory_input)
        app_dir_layout.addWidget(browse_dir_button)
        layout.addRow('Service Name (*):', self.service_name_input)
        layout.addRow('Executable Path (*):', exec_layout)
        layout.addRow('Application Directory:', app_dir_layout)
        layout.addRow('Arguments:', self.arguments_input)

        if self.service_name:
            self.service_name_input.setText(self.service_name)
            self.service_name_input.setEnabled(False)

    def init_details_tab(self):
        layout = QtWidgets.QFormLayout()
        self.details_tab.setLayout(layout)

        self.display_name_input = QtWidgets.QLineEdit()
        self.display_name_input.setPlaceholderText('Optional')
        self.description_input = QtWidgets.QLineEdit()
        self.description_input.setPlaceholderText('Optional')
        self.startup_type_combo = QtWidgets.QComboBox()
        self.startup_type_combo.addItems(['SERVICE_AUTO_START', 'SERVICE_DELAYED_AUTO_START', 'SERVICE_DEMAND_START', 'SERVICE_DISABLED'])
        self.startup_type_combo.setToolTip('Select the startup type for the service.')

        layout.addRow('Display Name:', self.display_name_input)
        layout.addRow('Description:', self.description_input)
        layout.addRow('Startup Type:', self.startup_type_combo)

    def init_logon_tab(self):
        layout = QtWidgets.QFormLayout()
        self.logon_tab.setLayout(layout)

        self.object_name_input = QtWidgets.QLineEdit()
        self.object_name_input.setPlaceholderText('LocalSystem / LocalService / NetworkService or DOMAIN\\UserName')
        self.object_name_input.setToolTip('Specify the account under which the service runs.')

        layout.addRow('Object Name:', self.object_name_input)

    def init_dependencies_tab(self):
        layout = QtWidgets.QFormLayout()
        self.dependencies_tab.setLayout(layout)

        self.dependencies_input = QtWidgets.QPlainTextEdit()
        self.dependencies_input.setPlaceholderText('Enter one service name per line.')

        layout.addRow('Dependencies (one per line):', self.dependencies_input)

    def init_process_tab(self):
        layout = QtWidgets.QFormLayout()
        self.process_tab.setLayout(layout)

        self.priority_combo = QtWidgets.QComboBox()
        self.priority_combo.addItems([
            'REALTIME_PRIORITY_CLASS',
            'HIGH_PRIORITY_CLASS',
            'ABOVE_NORMAL_PRIORITY_CLASS',
            'NORMAL_PRIORITY_CLASS',
            'BELOW_NORMAL_PRIORITY_CLASS',
            'IDLE_PRIORITY_CLASS'
        ])
        self.priority_combo.setToolTip('Set the priority class for the service process.')

        layout.addRow('Process Priority:', self.priority_combo)

    def init_io_tab(self):
        layout = QtWidgets.QFormLayout()
        self.io_tab.setLayout(layout)

        self.stdout_path_input = QtWidgets.QLineEdit()
        stdout_browse_button = QtWidgets.QPushButton('Browse')
        stdout_browse_button.clicked.connect(self.browse_stdout)

        stdout_layout = QtWidgets.QHBoxLayout()
        stdout_layout.addWidget(self.stdout_path_input)
        stdout_layout.addWidget(stdout_browse_button)

        self.stderr_path_input = QtWidgets.QLineEdit()
        stderr_browse_button = QtWidgets.QPushButton('Browse')
        stderr_browse_button.clicked.connect(self.browse_stderr)
        
        stderr_layout = QtWidgets.QHBoxLayout()
        stderr_layout.addWidget(self.stderr_path_input)
        stderr_layout.addWidget(stderr_browse_button)

        layout.addRow('Redirect stdout to file:', stdout_layout)
        layout.addRow('Redirect stderr to file:', stderr_layout)

    def init_env_tab(self):
        layout = QtWidgets.QFormLayout()
        self.env_tab.setLayout(layout)

        self.env_input = QtWidgets.QPlainTextEdit()
        self.env_input.setPlaceholderText('KEY=VALUE pairs, one per line.')

        layout.addRow('Environment Variables (KEY=VALUE):', self.env_input)

    def init_shutdown_tab(self):
        layout = QtWidgets.QFormLayout()
        self.shutdown_tab.setLayout(layout)

        # Shutdown methods checkboxes
        self.method_console_checkbox = QtWidgets.QCheckBox('Kill Console')
        self.method_console_checkbox.setChecked(True)
        self.method_console_checkbox.stateChanged.connect(self.toggle_console_delay)

        self.method_window_checkbox = QtWidgets.QCheckBox('Kill Window')
        self.method_window_checkbox.setChecked(True)
        self.method_window_checkbox.stateChanged.connect(self.toggle_window_delay)

        self.method_threads_checkbox = QtWidgets.QCheckBox('Kill Threads')
        self.method_threads_checkbox.setChecked(True)
        self.method_threads_checkbox.stateChanged.connect(self.toggle_threads_delay)

        self.method_terminate_checkbox = QtWidgets.QCheckBox('Terminate Process')
        self.method_terminate_checkbox.setChecked(True)

        # Delay inputs
        self.console_delay_input = QtWidgets.QSpinBox()
        self.console_delay_input.setRange(0, 600)
        self.console_delay_input.setSuffix(' seconds')
        self.console_delay_input.setValue(0)

        self.window_delay_input = QtWidgets.QSpinBox()
        self.window_delay_input.setRange(0, 600)
        self.window_delay_input.setSuffix(' seconds')
        self.window_delay_input.setValue(0)

        self.threads_delay_input = QtWidgets.QSpinBox()
        self.threads_delay_input.setRange(0, 600)
        self.threads_delay_input.setSuffix(' seconds')
        self.threads_delay_input.setValue(0)

        self.kill_process_tree_checkbox = QtWidgets.QCheckBox('Kill Process Tree')
        self.kill_process_tree_checkbox.setChecked(False)

        # Layout arrangement
        layout.addRow(self.method_console_checkbox, self.console_delay_input)
        layout.addRow(self.method_window_checkbox, self.window_delay_input)
        layout.addRow(self.method_threads_checkbox, self.threads_delay_input)
        layout.addRow(self.method_terminate_checkbox, self.kill_process_tree_checkbox)

    def init_exit_tab(self):
        layout = QtWidgets.QFormLayout()
        self.exit_tab.setLayout(layout)

        self.throttle_delay_input = QtWidgets.QSpinBox()
        self.throttle_delay_input.setRange(0, 3600)
        self.throttle_delay_input.setSuffix(' seconds')
        self.throttle_delay_input.setValue(0)

        self.exit_action_combo = QtWidgets.QComboBox()
        self.exit_action_combo.addItems(['Restart', 'Ignore', 'Exit', 'Suicide'])
        self.exit_action_combo.setToolTip('Select the action to perform on application exit.')

        self.restart_delay_input = QtWidgets.QSpinBox()
        self.restart_delay_input.setRange(0, 3600)
        self.restart_delay_input.setSuffix(' seconds')
        self.restart_delay_input.setValue(0)

        layout.addRow('Throttle Delay:', self.throttle_delay_input)
        layout.addRow('Exit Action:', self.exit_action_combo)
        layout.addRow('Restart Delay:', self.restart_delay_input)

    def init_rotation_tab(self):
        layout = QtWidgets.QFormLayout()
        self.rotation_tab.setLayout(layout)

        self.rotate_files_checkbox = QtWidgets.QCheckBox('Enable Log Rotation')
        self.rotate_files_checkbox.setChecked(False)
        self.rotate_files_checkbox.stateChanged.connect(self.toggle_rotation_settings)

        self.rotate_online_checkbox = QtWidgets.QCheckBox('Rotate Logs Online')
        self.rotate_online_checkbox.setChecked(False)

        self.rotate_seconds_input = QtWidgets.QSpinBox()
        self.rotate_seconds_input.setRange(0, 86400)
        self.rotate_seconds_input.setSuffix(' seconds')
        self.rotate_seconds_input.setValue(0)
        self.rotate_seconds_input.setEnabled(False)

        self.rotate_bytes_low_input = QtWidgets.QSpinBox()
        self.rotate_bytes_low_input.setRange(0, 1000000)
        self.rotate_bytes_low_input.setSuffix(' KB')
        self.rotate_bytes_low_input.setValue(0)
        self.rotate_bytes_low_input.setEnabled(False)

        layout.addRow(self.rotate_files_checkbox)
        layout.addRow(self.rotate_online_checkbox)
        layout.addRow('Rotate Every:', self.rotate_seconds_input)
        layout.addRow('Rotate When Size Exceeds:', self.rotate_bytes_low_input)

    def init_hooks_tab(self):
        layout = QtWidgets.QFormLayout()
        self.hooks_tab.setLayout(layout)

        self.hook_share_output_handles_checkbox = QtWidgets.QCheckBox('Share Output Handles with Hooks')
        self.hook_share_output_handles_checkbox.setChecked(False)

        # Hook event and action
        self.hook_event_combo = QtWidgets.QComboBox()
        self.hook_event_combo.addItems(['Start Pre', 'Start Post', 'Stop Pre', 'Exit Post', 'Power Change', 'Power Resume'])
        self.hook_action_combo = QtWidgets.QComboBox()
        self.hook_action_combo.addItems(['Execute', 'Log'])

        self.hook_command_input = QtWidgets.QLineEdit()
        browse_hook_button = QtWidgets.QPushButton('Browse')
        browse_hook_button.clicked.connect(self.browse_hook_command)

        hook_cmd_layout = QtWidgets.QHBoxLayout()
        hook_cmd_layout.addWidget(self.hook_command_input)
        hook_cmd_layout.addWidget(browse_hook_button)

        # Add hook button
        self.add_hook_button = QtWidgets.QPushButton('Add Hook')
        self.add_hook_button.clicked.connect(self.add_hook)

        # Hooks list
        self.hooks_list = QtWidgets.QListWidget()

        layout.addRow(self.hook_share_output_handles_checkbox)
        layout.addRow('Hook Event:', self.hook_event_combo)
        layout.addRow('Hook Action:', self.hook_action_combo)
        layout.addRow('Hook Command:', hook_cmd_layout)
        layout.addRow(self.add_hook_button)
        layout.addRow('Existing Hooks:', self.hooks_list)

    def browse_executable(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Select Executable')
        if path:
            self.executable_path_input.setText(path)

    def browse_app_directory(self):
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select Application Directory')
        if directory:
            self.app_directory_input.setText(directory)
    def browse_stdout(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Select Output File')
        if path:
            self.stdout_path_input.setText(path)
    
    def browse_stderr(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Select Error File')
        if path:
            self.stderr_path_input.setText(path)

    def browse_hook_command(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Select Hook Command', filter='Executable Files (*.exe *.bat *.cmd *.com);;All Files (*)')
        if path:
            self.hook_command_input.setText(path)

    def toggle_console_delay(self, state):
        self.console_delay_input.setEnabled(state == QtCore.Qt.Checked)

    def toggle_window_delay(self, state):
        self.window_delay_input.setEnabled(state == QtCore.Qt.Checked)

    def toggle_threads_delay(self, state):
        self.threads_delay_input.setEnabled(state == QtCore.Qt.Checked)

    def toggle_rotation_settings(self, state):
        enabled = state == QtCore.Qt.Checked
        self.rotate_online_checkbox.setEnabled(enabled)
        self.rotate_seconds_input.setEnabled(enabled)
        self.rotate_bytes_low_input.setEnabled(enabled)

    def add_hook(self):
        event_action = self.hook_event_combo.currentText()
        command = self.hook_command_input.text().strip()
        if not command:
            QtWidgets.QMessageBox.warning(self, 'Input Error', 'Hook command is required.')
            return
        if ' ' in event_action:
            event, action = event_action.split(' ', 1)
        else:
            event, action = event_action, ''
        hook_entry = f"{event} - {action}: {command}"
        self.hooks_list.addItem(hook_entry)
        self.hook_command_input.clear()

    def load_service_config(self, config: ServiceConfig):
        self.service_name_input.setText(config.service_name)
        self.executable_path_input.setText(config.application_path)
        self.app_directory_input.setText(config.app_directory)
        self.arguments_input.setText(config.arguments)
        self.display_name_input.setText(config.display_name)
        self.description_input.setText(config.description)
        index = self.startup_type_combo.findText(config.start)
        if index != -1:
            self.startup_type_combo.setCurrentIndex(index)
        self.object_name_input.setText(config.object_name)
        self.dependencies_input.setPlainText('\n'.join(config.dependencies))
        index = self.priority_combo.findText(config.process_priority)
        if index != -1:
            self.priority_combo.setCurrentIndex(index)
        self.stdout_path_input.setText(config.stdout_path)
        self.stderr_path_input.setText(config.stderr_path)
        env_text = '\n'.join([f'{k}={v}' for k, v in config.env_variables.items()])
        self.env_input.setPlainText(env_text)

        # Shutdown configurations
        self.method_console_checkbox.setChecked(config.kill_console_delay > 0)
        self.console_delay_input.setValue(config.kill_console_delay)
        self.console_delay_input.setEnabled(config.kill_console_delay > 0)

        self.method_window_checkbox.setChecked(config.kill_window_delay > 0)
        self.window_delay_input.setValue(config.kill_window_delay)
        self.window_delay_input.setEnabled(config.kill_window_delay > 0)

        self.method_threads_checkbox.setChecked(config.kill_threads_delay > 0)
        self.threads_delay_input.setValue(config.kill_threads_delay)
        self.threads_delay_input.setEnabled(config.kill_threads_delay > 0)

        self.method_terminate_checkbox.setChecked(True)  # Assuming terminate is always enabled
        self.kill_process_tree_checkbox.setChecked(config.kill_process_tree)

        # Exit configurations
        self.throttle_delay_input.setValue(config.throttle_delay)
        index = self.exit_action_combo.findText(config.app_exit)
        if index != -1:
            self.exit_action_combo.setCurrentIndex(index)
        self.restart_delay_input.setValue(config.restart_delay)

        # Rotation configurations
        self.rotate_files_checkbox.setChecked(config.rotate_files)
        self.rotate_online_checkbox.setChecked(config.rotate_online)
        self.rotate_seconds_input.setValue(config.rotate_seconds)
        self.rotate_bytes_low_input.setValue(config.rotate_bytes_low)
        self.rotate_online_checkbox.setEnabled(config.rotate_files)
        self.rotate_seconds_input.setEnabled(config.rotate_files)
        self.rotate_bytes_low_input.setEnabled(config.rotate_files)

        # Hooks configurations
        self.hook_share_output_handles_checkbox.setChecked(config.hook_share_output_handles)
        for event, action in config.hooks.items():
            hook_entry = f"{event} - {action}: {config.hooks[event]}"
            self.hooks_list.addItem(hook_entry)

    def get_service_config(self) -> Optional[ServiceConfig]:
        config = {}
        config['service_name'] = self.service_name_input.text().strip()
        config['application_path'] = self.executable_path_input.text().strip()
        config['app_directory'] = self.app_directory_input.text().strip()
        config['arguments'] = self.arguments_input.text().strip()
        config['display_name'] = self.display_name_input.text().strip()
        config['description'] = self.description_input.text().strip()
        config['start'] = self.startup_type_combo.currentText()
        config['object_name'] = self.object_name_input.text().strip()
        dependencies = self.dependencies_input.toPlainText()
        if dependencies:
            config['dependencies'] = [dep.strip() for dep in dependencies.strip().split('\n') if dep.strip()]
        config['process_priority'] = self.priority_combo.currentText()
        config['stdout_path'] = self.stdout_path_input.text().strip()
        config['stderr_path'] = self.stderr_path_input.text().strip()
        env_vars = self.env_input.toPlainText()
        if env_vars:
            env_dict = {}
            for line in env_vars.strip().split('\n'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    env_dict[key.strip()] = value.strip()
            config['env_variables'] = env_dict

        # Shutdown configurations
        config['kill_console_delay'] = self.console_delay_input.value() if self.method_console_checkbox.isChecked() else 0
        config['kill_window_delay'] = self.window_delay_input.value() if self.method_window_checkbox.isChecked() else 0
        config['kill_threads_delay'] = self.threads_delay_input.value() if self.method_threads_checkbox.isChecked() else 0
        config['kill_process_tree'] = self.kill_process_tree_checkbox.isChecked()

        # Exit configurations
        config['throttle_delay'] = self.throttle_delay_input.value()
        config['app_exit'] = self.exit_action_combo.currentText()
        config['restart_delay'] = self.restart_delay_input.value()

        # Rotation configurations
        config['rotate_files'] = self.rotate_files_checkbox.isChecked()
        config['rotate_online'] = self.rotate_online_checkbox.isChecked() if config['rotate_files'] else False
        config['rotate_seconds'] = self.rotate_seconds_input.value() if config['rotate_files'] else 0
        config['rotate_bytes_low'] = self.rotate_bytes_low_input.value() if config['rotate_files'] else 0

        # Hooks configurations
        config['hook_share_output_handles'] = self.hook_share_output_handles_checkbox.isChecked()
        hooks = {}
        for index in range(self.hooks_list.count()):
            item = self.hooks_list.item(index).text()
            if ': ' in item:
                event_action, command = item.split(': ', 1)
                if ' - ' in event_action:
                    event, action = event_action.split(' - ', 1)
                    hooks[event] = f"{action}: {command}"
        config['hooks'] = hooks

        try:
            service_config = ServiceConfig(**config)
            # Additional checks for required fields when adding a new service
            if not self.existing_config:
                missing_fields = []
                if not service_config.service_name:
                    missing_fields.append('Service Name')
                if not service_config.application_path:
                    missing_fields.append('Executable Path')
                if missing_fields:
                    raise ValidationError([{
                        'loc': (field,),
                        'msg': 'This field is required.',
                        'type': 'value_error'
                    } for field in missing_fields], model=ServiceConfig)
            return service_config
        except ValidationError as e:
            # Display validation errors to the user
            error_messages = '\n'.join([f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()])
            QtWidgets.QMessageBox.warning(self, 'Validation Error', f"Failed to create service configuration:\n{error_messages}")
            return None
        except Exception as e:
            # Catch any other exceptions that might occur
            QtWidgets.QMessageBox.critical(self, 'Error', f"An unexpected error occurred: {str(e)}")
            logging.error("Error in get_service_config", exc_info=True)
            return None

    def accept(self):
        if not self.service_name_input.text():
            QtWidgets.QMessageBox.warning(self, 'Input Error', 'Service Name is required.')
            return
        if not self.executable_path_input.text():
            QtWidgets.QMessageBox.warning(self, 'Input Error', 'Executable Path is required.')
            return
        # Proceed to get the service configuration
        super().accept()



def main():
    app = QtWidgets.QApplication(sys.argv)
    gui = NSSMGUI()
    gui.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
