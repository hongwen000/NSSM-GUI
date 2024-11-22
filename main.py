import sys
import os
import subprocess
import requests
import zipfile
from io import BytesIO
from PyQt5 import QtWidgets, QtGui, QtCore
import locale
import logging

# Configure logging
logging.basicConfig(filename='nssm_gui.log', level=logging.ERROR)
from pydantic import BaseModel, validator

from pydantic import BaseModel, Field, field_validator, ValidationError
import os
import re

class ServiceConfig(BaseModel):
    service_name: str = Field(..., min_length=1, max_length=256)
    application_path: str
    arguments: str = ''
    app_directory: str = ''
    app_exit: str = 'Restart'
    display_name: str = ''
    description: str = ''
    object_name: str = 'LocalSystem'
    start: str = 'SERVICE_AUTO_START'
    type: str = 'SERVICE_WIN32_OWN_PROCESS'
    dependencies: list[str] = []
    process_priority: str = 'NORMAL_PRIORITY_CLASS'
    stdout_path: str = ''
    env_variables: dict[str, str] = {}

    @field_validator('service_name')
    def validate_service_name(cls, v):
        # Service names must not contain illegal characters
        if not re.match(r'^[A-Za-z0-9_\-\.]+$', v):
            raise ValueError("Service name contains illegal characters.")
        return v

    @field_validator('application_path')
    def validate_application_path(cls, v):
        if not os.path.isfile(v):
            raise ValueError(f"Application path '{v}' does not exist or is not a file.")

        return v

    @field_validator('app_directory')
    def validate_app_directory(cls, v):
        if v and not os.path.isdir(v):
            raise ValueError(f"App directory '{v}' does not exist or is not a directory.")
        return v

    @field_validator('stdout_path')
    def validate_stdout_path(cls, v):
        if v:
            directory = os.path.dirname(v)
            if directory and not os.path.isdir(directory):
                raise ValueError(f"The directory for stdout path '{v}' does not exist.")
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
        # Optionally, validate domain accounts
        if '\\' in v:
            domain, user = v.split('\\', 1)
            if not domain or not user:
                raise ValueError("Invalid object name format. Expected 'DOMAIN\\UserName'.")
            return v
        else:
            raise ValueError(f"Invalid object name '{v}'. Use 'LocalSystem', 'LocalService', 'NetworkService', or 'DOMAIN\\UserName'.")
        return v

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

class NSSMGUI(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('NSSM-GUI')
        self.setGeometry(100, 100, 900, 700)
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
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                # Handle error output
                QtWidgets.QMessageBox.critical(self, 'NSSM Error', result.stderr)
            return result.stdout
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, 'Error', f"Failed to run NSSM command: {str(e)}")
            logging.error("Error in get_service_config", exc_info=True)
            return ''


    def load_services(self):
        # Clear existing rows
        self.service_table.setRowCount(0)
        # Get the system encoding
        sys_encoding = locale.getpreferredencoding()
        # Get list of services using NSSM naming convention
        output = subprocess.check_output(['sc', 'query', 'type=', 'service', 'state=', 'all'])
        services = output.decode(encoding=sys_encoding)
        service_names = []
        for line in services.split('\n'):
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

    def is_nssm_service(self, service_name):
        # Implement a method to check if a service is managed by NSSM
        try:
            output = subprocess.check_output(['sc', 'qc', service_name])
            for line in output.decode(encoding='GBK').split('\n'):
                if 'BINARY_PATH_NAME' in line and 'nssm.exe' in line.lower():
                    return True
        except subprocess.CalledProcessError:
            pass
        return False

    def get_service_status(self, service_name):
        output = subprocess.check_output(['sc', 'query', service_name])
        for line in output.decode(encoding='GBK').split('\n'):
            if 'STATE' in line:
                return line.strip().split(':')[1].split('  ')[1]
        return 'Unknown'

    def add_service(self):
        dialog = AddServiceDialog(self)
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
                        self.configure_service(updated_config, edit=True)
                        self.load_services()

    def configure_service(self, config: ServiceConfig, edit=False):
        service_name = config.service_name
        args = []
        if edit:
            args = ['edit', service_name]
        else:
            args = ['install', service_name, config.application_path]

        # Build the command to set various configurations
        settings_commands = []

        if config.arguments:
            settings_commands.append(['set', service_name, 'AppParameters', config.arguments])

        if config.app_directory:
            settings_commands.append(['set', service_name, 'AppDirectory', config.app_directory])

        if config.app_exit:
            settings_commands.append(['set', service_name, 'AppExit', 'Default', config.app_exit])

        if config.display_name:
            settings_commands.append(['set', service_name, 'DisplayName', config.display_name])

        if config.description:
            settings_commands.append(['set', service_name, 'Description', config.description])

        if config.object_name:
            settings_commands.append(['set', service_name, 'ObjectName', config.object_name])

        if config.start:
            settings_commands.append(['set', service_name, 'Start', config.start])

        if config.type:
            settings_commands.append(['set', service_name, 'Type', config.type])

        if config.dependencies:
            for dep in config.dependencies:
                settings_commands.append(['set', service_name, 'DependOnService', '+', dep])

        if config.process_priority:
            settings_commands.append(['set', service_name, 'AppPriority', config.process_priority])

        if config.stdout_path:
            settings_commands.append(['set', service_name, 'AppStdout', config.stdout_path])

        if config.env_variables:
            for key, value in config.env_variables.items():
                settings_commands.append(['set', service_name, 'AppEnvironmentExtra', f'{key}={value}'])

        # Run the commands
        self.run_nssm_command(args)
        for cmd in settings_commands:
            self.run_nssm_command(cmd)

    def delete_service(self):
        current_row = self.service_table.currentRow()
        if current_row >= 0:
            service_name = self.service_table.item(current_row, 0).text()
            reply = QtWidgets.QMessageBox.question(self, 'Confirm Delete',
                                                   f'Are you sure you want to delete {service_name}?',
                                                   QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                                                   QtWidgets.QMessageBox.No)
            if reply == QtWidgets.QMessageBox.Yes:
                self.run_nssm_command(['remove', service_name, 'confirm'])
                self.load_services()

    def start_service(self):
        current_row = self.service_table.currentRow()
        if current_row >= 0:
            service_name = self.service_table.item(current_row, 0).text()
            self.run_nssm_command(['start', service_name])
            self.load_services()

    def stop_service(self):
        current_row = self.service_table.currentRow()
        if current_row >= 0:
            service_name = self.service_table.item(current_row, 0).text()
            self.run_nssm_command(['stop', service_name])
            self.load_services()

    def enable_service(self):
        current_row = self.service_table.currentRow()
        if current_row >= 0:
            service_name = self.service_table.item(current_row, 0).text()
            subprocess.run(['sc', 'config', service_name, 'start=', 'auto'])
            self.load_services()

    def disable_service(self):
        current_row = self.service_table.currentRow()
        if current_row >= 0:
            service_name = self.service_table.item(current_row, 0).text()
            subprocess.run(['sc', 'config', service_name, 'start=', 'disabled'])
            self.load_services()

    def get_service_config(self, service_name) -> ServiceConfig:
        # Use nssm dump to get the current configuration
        output = self.run_nssm_command(['dump', service_name])
        config_data = self.parse_nssm_dump(output)
        if config_data:
            return ServiceConfig(**config_data)
        else:
            return None

    def parse_nssm_dump(self, dump_output: str) -> dict:
        import shlex  # Import shlex for proper command-line parsing
        config = {}
        lines = dump_output.strip().split('\n')
        for line in lines:
            # Use shlex with posix=False to handle Windows paths correctly
            lexer = shlex.shlex(line, posix=False)
            lexer.whitespace_split = True
            lexer.commenters = ''
            parts = list(lexer)
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
                        config['app_exit'] = value.strip('"')
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
                    elif setting == 'AppEnvironmentExtra':
                        env_var = value.strip('"')
                        if '=' in env_var:
                            key, val = env_var.split('=', 1)
                            config.setdefault('env_variables', {})[key] = val
        return config


class AddServiceDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, service_name=None, existing_config: ServiceConfig = None):
        super(AddServiceDialog, self).__init__(parent)
        self.setWindowTitle('Add Service' if not service_name else 'Edit Service')
        self.setFixedSize(600, 500)
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
        self.executable_path_input = QtWidgets.QLineEdit()
        self.service_name_input.setPlaceholderText('Required')
        self.executable_path_input.setPlaceholderText('Required')
        self.arguments_input = QtWidgets.QLineEdit()
        browse_button = QtWidgets.QPushButton('Browse')
        browse_button.clicked.connect(self.browse_executable)

        exec_layout = QtWidgets.QHBoxLayout()
        exec_layout.addWidget(self.executable_path_input)
        exec_layout.addWidget(browse_button)

        layout.addRow('Service Name (*):', self.service_name_input)
        layout.addRow('Executable Path (*):', exec_layout)
        layout.addRow('Arguments:', self.arguments_input)

        if self.service_name:
            self.service_name_input.setText(self.service_name)
            self.service_name_input.setEnabled(False)

    def init_details_tab(self):
        layout = QtWidgets.QFormLayout()
        self.details_tab.setLayout(layout)

        self.display_name_input = QtWidgets.QLineEdit()
        self.description_input = QtWidgets.QLineEdit()
        self.startup_type_combo = QtWidgets.QComboBox()
        self.startup_type_combo.addItems(['SERVICE_AUTO_START', 'SERVICE_DELAYED_AUTO_START', 'SERVICE_DEMAND_START', 'SERVICE_DISABLED'])

        layout.addRow('Display Name:', self.display_name_input)
        layout.addRow('Description:', self.description_input)
        layout.addRow('Startup Type:', self.startup_type_combo)

    def init_logon_tab(self):
        layout = QtWidgets.QFormLayout()
        self.logon_tab.setLayout(layout)

        self.object_name_input = QtWidgets.QLineEdit()
        self.object_name_input.setToolTip('Specify the account under which the service runs. Default is LocalSystem.')

        layout.addRow('Object Name:', self.object_name_input)

    def init_dependencies_tab(self):
        layout = QtWidgets.QFormLayout()
        self.dependencies_tab.setLayout(layout)

        self.dependencies_input = QtWidgets.QPlainTextEdit()

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

        layout.addRow('Redirect stdout to file:', stdout_layout)

    def init_env_tab(self):
        layout = QtWidgets.QFormLayout()
        self.env_tab.setLayout(layout)

        self.env_input = QtWidgets.QPlainTextEdit()

        layout.addRow('Environment Variables (KEY=VALUE):', self.env_input)

    def browse_executable(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Select Executable')
        if path:
            self.executable_path_input.setText(path)

    def browse_stdout(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Select Output File')
        if path:
            self.stdout_path_input.setText(path)

    def load_service_config(self, config: ServiceConfig):
        self.service_name_input.setText(config.service_name)
        self.executable_path_input.setText(config.application_path)
        self.arguments_input.setText(config.arguments)
        self.display_name_input.setText(config.display_name)
        self.description_input.setText(config.description)
        self.startup_type_combo.setCurrentText(config.start)
        self.object_name_input.setText(config.object_name)
        self.dependencies_input.setPlainText('\n'.join(config.dependencies))
        self.priority_combo.setCurrentText(config.process_priority)
        self.stdout_path_input.setText(config.stdout_path)
        env_text = '\n'.join([f'{k}={v}' for k, v in config.env_variables.items()])
        self.env_input.setPlainText(env_text)

    def get_service_config(self) -> ServiceConfig:
        config = {}
        config['service_name'] = self.service_name_input.text()
        config['application_path'] = self.executable_path_input.text()
        config['arguments'] = self.arguments_input.text()
        config['display_name'] = self.display_name_input.text()
        config['description'] = self.description_input.text()
        config['start'] = self.startup_type_combo.currentText()
        config['object_name'] = self.object_name_input.text()
        dependencies = self.dependencies_input.toPlainText()
        if dependencies:
            config['dependencies'] = dependencies.strip().split('\n')
        config['process_priority'] = self.priority_combo.currentText()
        config['stdout_path'] = self.stdout_path_input.text()
        env_vars = self.env_input.toPlainText()
        if env_vars:
            env_dict = {}
            for line in env_vars.strip().split('\n'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    env_dict[key.strip()] = value.strip()
            config['env_variables'] = env_dict
        try:
            service_config = ServiceConfig(**config)
            return service_config
        except ValidationError as e:
            # Display validation errors to the user
            error_messages = '\n'.join([f"{err['loc'][0]}: {err['msg']}" for err in e.errors()])
            QtWidgets.QMessageBox.warning(self, 'Validation Error', error_messages)
            return None
        except Exception as e:
            # Catch any other exceptions that might occur
            QtWidgets.QMessageBox.critical(self, 'Error', f"An unexpected error occurred: {str(e)}")
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
