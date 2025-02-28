import os
from PyQt5 import QtWidgets, QtGui, QtCore
from typing import Dict, List, Optional
import json

from ..models import ServiceConfig

class AddServiceDialog(QtWidgets.QDialog):
    """Dialog for adding or editing a service."""
    
    def __init__(self, parent=None, existing_config: Optional[ServiceConfig] = None):
        super().__init__(parent)
        self.setWindowTitle('Add Service' if not existing_config else 'Edit Service')
        self.setFixedSize(700, 800)
        self.existing_config = existing_config
        self.init_ui()
        
        if existing_config:
            self.load_service_config(existing_config)
            # If editing an existing service, disable the service name field
            self.service_name_input.setEnabled(False)
        
    def init_ui(self):
        """Initialize the dialog UI."""
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
        """Initialize the Application tab."""
        layout = QtWidgets.QFormLayout()
        self.app_tab.setLayout(layout)
        
        self.service_name_input = QtWidgets.QLineEdit()
        self.service_name_input.setPlaceholderText('Required (Alphanumeric, _, -, .)')
        self.service_name_input.setToolTip('Enter a unique service name. Allowed characters: A-Z, a-z, 0-9, _, -, .')
        
        self.executable_path_input = QtWidgets.QLineEdit()
        self.executable_path_input.setPlaceholderText('Required')
        
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
        
        self.arguments_input = QtWidgets.QLineEdit()
        
        layout.addRow('Service Name (*):', self.service_name_input)
        layout.addRow('Executable Path (*):', exec_layout)
        layout.addRow('Application Directory:', app_dir_layout)
        layout.addRow('Arguments:', self.arguments_input)
        
    def init_details_tab(self):
        """Initialize the Details tab."""
        layout = QtWidgets.QFormLayout()
        self.details_tab.setLayout(layout)
        
        self.display_name_input = QtWidgets.QLineEdit()
        self.display_name_input.setPlaceholderText('Optional')
        
        self.description_input = QtWidgets.QTextEdit()
        self.description_input.setPlaceholderText('Optional')
        self.description_input.setMaximumHeight(100)
        
        self.startup_type_combo = QtWidgets.QComboBox()
        self.startup_type_combo.addItems([
            'SERVICE_AUTO_START',
            'SERVICE_DELAYED_AUTO_START',
            'SERVICE_DEMAND_START',
            'SERVICE_DISABLED'
        ])
        self.startup_type_combo.setToolTip('Select the startup type for the service.')
        
        # Service type
        self.service_type_combo = QtWidgets.QComboBox()
        self.service_type_combo.addItems([
            'SERVICE_WIN32_OWN_PROCESS',
            'SERVICE_INTERACTIVE_PROCESS'
        ])
        self.service_type_combo.setToolTip('Select the service type.')
        
        layout.addRow('Display Name:', self.display_name_input)
        layout.addRow('Description:', self.description_input)
        layout.addRow('Startup Type:', self.startup_type_combo)
        layout.addRow('Service Type:', self.service_type_combo)
        
    def init_logon_tab(self):
        """Initialize the Logon tab."""
        layout = QtWidgets.QFormLayout()
        self.logon_tab.setLayout(layout)
        
        # Account type radio buttons
        self.account_type_group = QtWidgets.QGroupBox("Account Type")
        account_layout = QtWidgets.QVBoxLayout()
        
        self.system_radio = QtWidgets.QRadioButton("LocalSystem")
        self.service_radio = QtWidgets.QRadioButton("LocalService")
        self.network_radio = QtWidgets.QRadioButton("NetworkService")
        self.user_radio = QtWidgets.QRadioButton("User Account")
        
        self.system_radio.setChecked(True)
        
        account_layout.addWidget(self.system_radio)
        account_layout.addWidget(self.service_radio)
        account_layout.addWidget(self.network_radio)
        account_layout.addWidget(self.user_radio)
        
        self.account_type_group.setLayout(account_layout)
        
        # User account inputs
        self.user_group = QtWidgets.QGroupBox("User Account Details")
        user_layout = QtWidgets.QFormLayout()
        
        self.username_input = QtWidgets.QLineEdit()
        self.username_input.setPlaceholderText('DOMAIN\\Username')
        self.username_input.setEnabled(False)
        
        self.password_input = QtWidgets.QLineEdit()
        self.password_input.setEchoMode(QtWidgets.QLineEdit.Password)
        self.password_input.setEnabled(False)
        
        user_layout.addRow('Username:', self.username_input)
        user_layout.addRow('Password:', self.password_input)
        
        self.user_group.setLayout(user_layout)
        
        # Connect radio buttons
        self.system_radio.toggled.connect(self.toggle_user_inputs)
        self.service_radio.toggled.connect(self.toggle_user_inputs)
        self.network_radio.toggled.connect(self.toggle_user_inputs)
        self.user_radio.toggled.connect(self.toggle_user_inputs)
        
        layout.addWidget(self.account_type_group)
        layout.addWidget(self.user_group)
        
    def toggle_user_inputs(self, checked):
        """Enable or disable user inputs based on selected account type."""
        if self.user_radio.isChecked():
            self.username_input.setEnabled(True)
            self.password_input.setEnabled(True)
        else:
            self.username_input.setEnabled(False)
            self.password_input.setEnabled(False)
        
    def init_dependencies_tab(self):
        """Initialize the Dependencies tab."""
        layout = QtWidgets.QVBoxLayout()
        self.dependencies_tab.setLayout(layout)
        
        # List of available services
        services_group = QtWidgets.QGroupBox("Available Services")
        services_layout = QtWidgets.QVBoxLayout()
        
        self.services_filter = QtWidgets.QLineEdit()
        self.services_filter.setPlaceholderText("Filter services...")
        self.services_filter.textChanged.connect(self.filter_services)
        
        self.services_list = QtWidgets.QListWidget()
        
        services_layout.addWidget(self.services_filter)
        services_layout.addWidget(self.services_list)
        
        services_group.setLayout(services_layout)
        
        # List of dependencies
        dependencies_group = QtWidgets.QGroupBox("Dependencies")
        dependencies_layout = QtWidgets.QVBoxLayout()
        
        self.dependencies_list = QtWidgets.QListWidget()
        
        # Buttons
        buttons_layout = QtWidgets.QHBoxLayout()
        
        self.add_dep_button = QtWidgets.QPushButton("Add >>")
        self.remove_dep_button = QtWidgets.QPushButton("Remove")
        
        self.add_dep_button.clicked.connect(self.add_dependency)
        self.remove_dep_button.clicked.connect(self.remove_dependency)
        
        buttons_layout.addWidget(self.add_dep_button)
        buttons_layout.addWidget(self.remove_dep_button)
        
        dependencies_layout.addWidget(self.dependencies_list)
        dependencies_layout.addLayout(buttons_layout)
        
        dependencies_group.setLayout(dependencies_layout)
        
        # Add to main layout
        main_layout = QtWidgets.QHBoxLayout()
        main_layout.addWidget(services_group)
        main_layout.addWidget(dependencies_group)
        
        layout.addLayout(main_layout)
        
        # Populate services list
        self.populate_services_list()
        
    def populate_services_list(self):
        """Populate the list of available services."""
        try:
            # This is a simplified implementation
            # In a real application, you would get this from the OS
            import subprocess
            output = subprocess.check_output(['sc', 'query', 'state=', 'all'], text=True)
            
            services = []
            for line in output.split('\n'):
                if line.strip().startswith('SERVICE_NAME:'):
                    services.append(line.strip().split(':', 1)[1].strip())
            
            # Add to list widget
            self.services_list.clear()
            self.services_list.addItems(services)
        except Exception as e:
            print(f"Error getting services: {str(e)}")
        
    def filter_services(self, text):
        """Filter the services list based on text input."""
        for i in range(self.services_list.count()):
            item = self.services_list.item(i)
            item.setHidden(text.lower() not in item.text().lower())
        
    def add_dependency(self):
        """Add a dependency to the dependencies list."""
        selected_items = self.services_list.selectedItems()
        for item in selected_items:
            # Check if already in dependencies
            exists = False
            for i in range(self.dependencies_list.count()):
                if self.dependencies_list.item(i).text() == item.text():
                    exists = True
                    break
            
            if not exists:
                self.dependencies_list.addItem(item.text())
        
    def remove_dependency(self):
        """Remove a dependency from the dependencies list."""
        selected_items = self.dependencies_list.selectedItems()
        for item in selected_items:
            self.dependencies_list.takeItem(self.dependencies_list.row(item))
        
    def init_process_tab(self):
        """Initialize the Process tab."""
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
        
        # CPU affinity
        affinity_group = QtWidgets.QGroupBox("CPU Affinity")
        affinity_layout = QtWidgets.QGridLayout()
        
        self.affinity_checkboxes = []
        
        # Get the number of CPU cores
        import multiprocessing
        cpu_count = multiprocessing.cpu_count()
        
        # Create checkboxes for each CPU
        for i in range(min(cpu_count, 32)):  # Limit to 32 checkboxes
            checkbox = QtWidgets.QCheckBox(f"CPU {i}")
            checkbox.setChecked(True)
            self.affinity_checkboxes.append(checkbox)
            
            row = i // 8
            col = i % 8
            affinity_layout.addWidget(checkbox, row, col)
        
        affinity_group.setLayout(affinity_layout)
        
        layout.addRow('Process Priority:', self.priority_combo)
        layout.addRow(affinity_group)
        
    def init_io_tab(self):
        """Initialize the I/O tab."""
        layout = QtWidgets.QFormLayout()
        self.io_tab.setLayout(layout)
        
        # Stdout path
        self.stdout_path_input = QtWidgets.QLineEdit()
        stdout_browse_button = QtWidgets.QPushButton('Browse')
        stdout_browse_button.clicked.connect(self.browse_stdout)
        
        stdout_layout = QtWidgets.QHBoxLayout()
        stdout_layout.addWidget(self.stdout_path_input)
        stdout_layout.addWidget(stdout_browse_button)
        
        # Stderr path
        self.stderr_path_input = QtWidgets.QLineEdit()
        stderr_browse_button = QtWidgets.QPushButton('Browse')
        stderr_browse_button.clicked.connect(self.browse_stderr)
        
        stderr_layout = QtWidgets.QHBoxLayout()
        stderr_layout.addWidget(self.stderr_path_input)
        stderr_layout.addWidget(stderr_browse_button)
        
        layout.addRow('Redirect stdout to file:', stdout_layout)
        layout.addRow('Redirect stderr to file:', stderr_layout)
        
    def init_env_tab(self):
        """Initialize the Environment tab."""
        layout = QtWidgets.QVBoxLayout()
        self.env_tab.setLayout(layout)
        
        # Environment variables table
        self.env_table = QtWidgets.QTableWidget()
        self.env_table.setColumnCount(2)
        self.env_table.setHorizontalHeaderLabels(['Variable', 'Value'])
        self.env_table.horizontalHeader().setStretchLastSection(True)
        self.env_table.verticalHeader().setVisible(False)
        
        # Buttons
        buttons_layout = QtWidgets.QHBoxLayout()
        
        self.add_env_button = QtWidgets.QPushButton("Add")
        self.edit_env_button = QtWidgets.QPushButton("Edit")
        self.remove_env_button = QtWidgets.QPushButton("Remove")
        
        self.add_env_button.clicked.connect(self.add_env_variable)
        self.edit_env_button.clicked.connect(self.edit_env_variable)
        self.remove_env_button.clicked.connect(self.remove_env_variable)
        
        buttons_layout.addWidget(self.add_env_button)
        buttons_layout.addWidget(self.edit_env_button)
        buttons_layout.addWidget(self.remove_env_button)
        buttons_layout.addStretch(1)
        
        layout.addWidget(self.env_table)
        layout.addLayout(buttons_layout)
        
    def add_env_variable(self):
        """Add an environment variable."""
        dialog = EnvVariableDialog(self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            var_name, var_value = dialog.get_variable()
            
            # Add to table
            row = self.env_table.rowCount()
            self.env_table.insertRow(row)
            self.env_table.setItem(row, 0, QtWidgets.QTableWidgetItem(var_name))
            self.env_table.setItem(row, 1, QtWidgets.QTableWidgetItem(var_value))
        
    def edit_env_variable(self):
        """Edit an environment variable."""
        selected_rows = self.env_table.selectedItems()
        if not selected_rows:
            return
            
        row = selected_rows[0].row()
        var_name = self.env_table.item(row, 0).text()
        var_value = self.env_table.item(row, 1).text()
        
        dialog = EnvVariableDialog(self, var_name, var_value)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            new_name, new_value = dialog.get_variable()
            
            # Update table
            self.env_table.setItem(row, 0, QtWidgets.QTableWidgetItem(new_name))
            self.env_table.setItem(row, 1, QtWidgets.QTableWidgetItem(new_value))
        
    def remove_env_variable(self):
        """Remove an environment variable."""
        selected_rows = self.env_table.selectedItems()
        if not selected_rows:
            return
            
        row = selected_rows[0].row()
        self.env_table.removeRow(row)
        
    def init_shutdown_tab(self):
        """Initialize the Shutdown tab."""
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
        
    def toggle_console_delay(self, state):
        """Enable or disable console delay input."""
        self.console_delay_input.setEnabled(state == QtCore.Qt.Checked)
        
    def toggle_window_delay(self, state):
        """Enable or disable window delay input."""
        self.window_delay_input.setEnabled(state == QtCore.Qt.Checked)
        
    def toggle_threads_delay(self, state):
        """Enable or disable threads delay input."""
        self.threads_delay_input.setEnabled(state == QtCore.Qt.Checked)
        
    def init_exit_tab(self):
        """Initialize the Exit tab."""
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
        """Initialize the Rotation tab."""
        layout = QtWidgets.QFormLayout()
        self.rotation_tab.setLayout(layout)
        
        self.rotate_files_checkbox = QtWidgets.QCheckBox('Enable Log Rotation')
        self.rotate_files_checkbox.setChecked(False)
        self.rotate_files_checkbox.stateChanged.connect(self.toggle_rotation_settings)
        
        self.rotate_online_checkbox = QtWidgets.QCheckBox('Rotate Logs Online')
        self.rotate_online_checkbox.setChecked(False)
        self.rotate_online_checkbox.setEnabled(False)
        
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
        
    def toggle_rotation_settings(self, state):
        """Enable or disable rotation settings."""
        enabled = state == QtCore.Qt.Checked
        self.rotate_online_checkbox.setEnabled(enabled)
        self.rotate_seconds_input.setEnabled(enabled)
        self.rotate_bytes_low_input.setEnabled(enabled)
        
    def init_hooks_tab(self):
        """Initialize the Hooks tab."""
        layout = QtWidgets.QFormLayout()
        self.hooks_tab.setLayout(layout)
        
        self.hook_share_output_handles_checkbox = QtWidgets.QCheckBox('Share Output Handles with Hooks')
        self.hook_share_output_handles_checkbox.setChecked(False)
        
        # Hook event and action
        self.hook_event_combo = QtWidgets.QComboBox()
        self.hook_event_combo.addItems(['Start_Pre', 'Start_Post', 'Stop_Pre', 'Exit_Post', 'Power_Change', 'Power_Resume'])
        
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
        self.hooks_list.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.hooks_list.customContextMenuRequested.connect(self.show_hooks_context_menu)
        
        layout.addRow(self.hook_share_output_handles_checkbox)
        layout.addRow('Hook Event:', self.hook_event_combo)
        layout.addRow('Hook Action:', self.hook_action_combo)
        layout.addRow('Hook Command:', hook_cmd_layout)
        layout.addRow(self.add_hook_button)
        layout.addRow('Existing Hooks:', self.hooks_list)
        
    def browse_executable(self):
        """Browse for executable file."""
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, 'Select Executable', '', 'Executable Files (*.exe *.bat *.cmd);;All Files (*)'
        )
        if path:
            self.executable_path_input.setText(path)
            
    def browse_app_directory(self):
        """Browse for application directory."""
        directory = QtWidgets.QFileDialog.getExistingDirectory(
            self, 'Select Application Directory'
        )
        if directory:
            self.app_directory_input.setText(directory)
            
    def browse_stdout(self):
        """Browse for stdout file."""
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Select Output File', '', 'Log Files (*.log *.txt);;All Files (*)'
        )
        if path:
            self.stdout_path_input.setText(path)
            
    def browse_stderr(self):
        """Browse for stderr file."""
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Select Error File', '', 'Log Files (*.log *.txt);;All Files (*)'
        )
        if path:
            self.stderr_path_input.setText(path)
            
    def browse_hook_command(self):
        """Browse for hook command file."""
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, 'Select Hook Command', '', 'Executable Files (*.exe *.bat *.cmd);;All Files (*)'
        )
        if path:
            self.hook_command_input.setText(path)
            
    def add_hook(self):
        """Add a hook to the hooks list."""
        event = self.hook_event_combo.currentText()
        action = self.hook_action_combo.currentText()
        command = self.hook_command_input.text().strip()
        
        if not command:
            QtWidgets.QMessageBox.warning(
                self, 'Input Error', 'Hook command is required.'
            )
            return
            
        hook_entry = f"{event} - {action}: {command}"
        self.hooks_list.addItem(hook_entry)
        self.hook_command_input.clear()
        
    def show_hooks_context_menu(self, position):
        """Show the context menu for the hooks list."""
        menu = QtWidgets.QMenu()
        remove_action = menu.addAction("Remove")
        
        action = menu.exec_(self.hooks_list.mapToGlobal(position))
        
        if action == remove_action:
            selected_items = self.hooks_list.selectedItems()
            for item in selected_items:
                self.hooks_list.takeItem(self.hooks_list.row(item))
                
    def load_service_config(self, config: ServiceConfig):
        """Load service configuration into the dialog."""
        # Application tab
        self.service_name_input.setText(config.service_name)
        self.executable_path_input.setText(config.application_path)
        self.app_directory_input.setText(config.app_directory)
        self.arguments_input.setText(config.arguments)
        
        # Details tab
        self.display_name_input.setText(config.display_name)
        self.description_input.setText(config.description)
        
        index = self.startup_type_combo.findText(config.start)
        if index != -1:
            self.startup_type_combo.setCurrentIndex(index)
            
        index = self.service_type_combo.findText(config.type)
        if index != -1:
            self.service_type_combo.setCurrentIndex(index)
            
        # Logon tab
        if config.object_name == 'LocalSystem':
            self.system_radio.setChecked(True)
        elif config.object_name == 'LocalService':
            self.service_radio.setChecked(True)
        elif config.object_name == 'NetworkService':
            self.network_radio.setChecked(True)
        else:
            self.user_radio.setChecked(True)
            self.username_input.setText(config.object_name)
            
        # Dependencies tab
        self.dependencies_list.clear()
        for dependency in config.dependencies:
            self.dependencies_list.addItem(dependency)
            
        # Process tab
        index = self.priority_combo.findText(config.process_priority)
        if index != -1:
            self.priority_combo.setCurrentIndex(index)
            
        # I/O tab
        self.stdout_path_input.setText(config.stdout_path)
        self.stderr_path_input.setText(config.stderr_path)
        
        # Environment tab
        self.env_table.setRowCount(0)
        for key, value in config.env_variables.items():
            row = self.env_table.rowCount()
            self.env_table.insertRow(row)
            self.env_table.setItem(row, 0, QtWidgets.QTableWidgetItem(key))
            self.env_table.setItem(row, 1, QtWidgets.QTableWidgetItem(value))
            
        # Shutdown tab
        self.method_console_checkbox.setChecked(config.kill_console_delay > 0)
        self.console_delay_input.setValue(config.kill_console_delay)
        
        self.method_window_checkbox.setChecked(config.kill_window_delay > 0)
        self.window_delay_input.setValue(config.kill_window_delay)
        
        self.method_threads_checkbox.setChecked(config.kill_threads_delay > 0)
        self.threads_delay_input.setValue(config.kill_threads_delay)
        
        self.kill_process_tree_checkbox.setChecked(config.kill_process_tree)
        
        # Exit tab
        self.throttle_delay_input.setValue(config.throttle_delay)
        
        index = self.exit_action_combo.findText(config.app_exit)
        if index != -1:
            self.exit_action_combo.setCurrentIndex(index)
            
        self.restart_delay_input.setValue(config.restart_delay)
        
        # Rotation tab
        self.rotate_files_checkbox.setChecked(config.rotate_files)
        self.rotate_online_checkbox.setChecked(config.rotate_online)
        self.rotate_seconds_input.setValue(config.rotate_seconds)
        self.rotate_bytes_low_input.setValue(config.rotate_bytes_low)
        
        # Hooks tab
        self.hook_share_output_handles_checkbox.setChecked(config.hook_share_output_handles)
        
        self.hooks_list.clear()
        for event, action in config.hooks.items():
            hook_entry = f"{event} - {action}"
            self.hooks_list.addItem(hook_entry)
            
    def get_service_config(self) -> Optional[ServiceConfig]:
        """Get the service configuration from the dialog."""
        try:
            # Basic validation
            service_name = self.service_name_input.text().strip()
            executable_path = self.executable_path_input.text().strip()
            
            if not service_name:
                QtWidgets.QMessageBox.warning(
                    self, 'Input Error', 'Service Name is required.'
                )
                return None
                
            if not executable_path and not self.existing_config:
                QtWidgets.QMessageBox.warning(
                    self, 'Input Error', 'Executable Path is required.'
                )
                return None
                
            # Build the config dictionary
            config_dict = {
                'service_name': service_name,
                'application_path': executable_path,
                'arguments': self.arguments_input.text().strip(),
                'app_directory': self.app_directory_input.text().strip(),
                'display_name': self.display_name_input.text().strip(),
                'description': self.description_input.toPlainText().strip(),
                'start': self.startup_type_combo.currentText(),
                'type': self.service_type_combo.currentText(),
                'process_priority': self.priority_combo.currentText(),
                'stdout_path': self.stdout_path_input.text().strip(),
                'stderr_path': self.stderr_path_input.text().strip(),
            }
            
            # Object name (logon account)
            if self.system_radio.isChecked():
                config_dict['object_name'] = 'LocalSystem'
            elif self.service_radio.isChecked():
                config_dict['object_name'] = 'LocalService'
            elif self.network_radio.isChecked():
                config_dict['object_name'] = 'NetworkService'
            else:
                config_dict['object_name'] = self.username_input.text().strip()
                
            # Dependencies
            dependencies = []
            for i in range(self.dependencies_list.count()):
                dependencies.append(self.dependencies_list.item(i).text())
            config_dict['dependencies'] = dependencies
            
            # Environment variables
            env_variables = {}
            for i in range(self.env_table.rowCount()):
                key = self.env_table.item(i, 0).text()
                value = self.env_table.item(i, 1).text()
                env_variables[key] = value
            config_dict['env_variables'] = env_variables
            
            # Shutdown settings
            config_dict['kill_console_delay'] = self.console_delay_input.value() if self.method_console_checkbox.isChecked() else 0
            config_dict['kill_window_delay'] = self.window_delay_input.value() if self.method_window_checkbox.isChecked() else 0
            config_dict['kill_threads_delay'] = self.threads_delay_input.value() if self.method_threads_checkbox.isChecked() else 0
            config_dict['kill_process_tree'] = self.kill_process_tree_checkbox.isChecked()
            
            # Exit settings
            config_dict['throttle_delay'] = self.throttle_delay_input.value()
            config_dict['app_exit'] = self.exit_action_combo.currentText()
            config_dict['restart_delay'] = self.restart_delay_input.value()
            
            # Rotation settings
            config_dict['rotate_files'] = self.rotate_files_checkbox.isChecked()
            config_dict['rotate_online'] = self.rotate_online_checkbox.isChecked()
            config_dict['rotate_seconds'] = self.rotate_seconds_input.value()
            config_dict['rotate_bytes_low'] = self.rotate_bytes_low_input.value()
            
            # Hooks settings
            config_dict['hook_share_output_handles'] = self.hook_share_output_handles_checkbox.isChecked()
            
            hooks = {}
            for i in range(self.hooks_list.count()):
                hook_entry = self.hooks_list.item(i).text()
                if ' - ' in hook_entry and ': ' in hook_entry:
                    event_action, command = hook_entry.split(': ', 1)
                    event, action = event_action.split(' - ', 1)
                    hooks[event] = command
            config_dict['hooks'] = hooks
            
            # Create and return the config object
            return ServiceConfig(**config_dict)
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self, 'Error', f'Failed to create service configuration: {str(e)}'
            )
            return None
            
    def accept(self):
        """Accept the dialog."""
        # Skip validation if the user clicked Cancel
        config = self.get_service_config()
        if config:
            super().accept()
        # Otherwise, keep the dialog open
            
class EnvVariableDialog(QtWidgets.QDialog):
    """Dialog for adding or editing an environment variable."""
    
    def __init__(self, parent=None, var_name="", var_value=""):
        super().__init__(parent)
        self.setWindowTitle('Environment Variable')
        self.init_ui()
        
        # Set initial values if provided
        if var_name:
            self.name_input.setText(var_name)
            self.value_input.setText(var_value)
        
    def init_ui(self):
        """Initialize the dialog UI."""
        layout = QtWidgets.QFormLayout(self)
        
        self.name_input = QtWidgets.QLineEdit()
        self.name_input.setPlaceholderText('Variable name')
        
        self.value_input = QtWidgets.QLineEdit()
        self.value_input.setPlaceholderText('Variable value')
        
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        layout.addRow('Name:', self.name_input)
        layout.addRow('Value:', self.value_input)
        layout.addWidget(button_box)
        
    def get_variable(self) -> tuple:
        """Get the variable name and value."""
        return self.name_input.text().strip(), self.value_input.text().strip()
        
    def accept(self):
        """Accept the dialog."""
        name = self.name_input.text().strip()
        if not name:
            QtWidgets.QMessageBox.warning(
                self, 'Input Error', 'Variable name is required.'
            )
            return
            
        # Validate variable name (letters, numbers, and underscores)
        if not all(c.isalnum() or c == '_' for c in name):
            QtWidgets.QMessageBox.warning(
                self, 'Input Error', 'Variable name can only contain letters, numbers, and underscores.'
            )
            return
            
        super().accept()
        

class LogViewerDialog(QtWidgets.QDialog):
    """Dialog for viewing service logs."""
    
    def __init__(self, parent=None, service_name="", stdout_logs="", stderr_logs="", 
                 stdout_path="", stderr_path=""):
        super().__init__(parent)
        self.setWindowTitle(f'Logs for {service_name}')
        self.setGeometry(100, 100, 800, 600)
        
        self.service_name = service_name
        self.stdout_logs = stdout_logs
        self.stderr_logs = stderr_logs
        self.stdout_path = stdout_path
        self.stderr_path = stderr_path
        
        self.init_ui()
        
    def init_ui(self):
        """Initialize the dialog UI."""
        layout = QtWidgets.QVBoxLayout(self)
        
        # Tabs for stdout and stderr
        self.tabs = QtWidgets.QTabWidget()
        
        # Stdout tab
        self.stdout_tab = QtWidgets.QWidget()
        stdout_layout = QtWidgets.QVBoxLayout(self.stdout_tab)
        
        self.stdout_text = QtWidgets.QPlainTextEdit()
        self.stdout_text.setReadOnly(True)
        self.stdout_text.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        self.stdout_text.setPlainText(self.stdout_logs)
        
        stdout_path_label = QtWidgets.QLabel(f"Log file: {self.stdout_path}")
        
        stdout_layout.addWidget(stdout_path_label)
        stdout_layout.addWidget(self.stdout_text)
        
        # Stderr tab
        self.stderr_tab = QtWidgets.QWidget()
        stderr_layout = QtWidgets.QVBoxLayout(self.stderr_tab)
        
        self.stderr_text = QtWidgets.QPlainTextEdit()
        self.stderr_text.setReadOnly(True)
        self.stderr_text.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        self.stderr_text.setPlainText(self.stderr_logs)
        
        stderr_path_label = QtWidgets.QLabel(f"Log file: {self.stderr_path}")
        
        stderr_layout.addWidget(stderr_path_label)
        stderr_layout.addWidget(self.stderr_text)
        
        # Add tabs
        self.tabs.addTab(self.stdout_tab, "Standard Output")
        self.tabs.addTab(self.stderr_tab, "Standard Error")
        
        # Buttons
        button_layout = QtWidgets.QHBoxLayout()
        
        self.refresh_button = QtWidgets.QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_logs)
        
        self.clear_button = QtWidgets.QPushButton("Clear Logs")
        self.clear_button.clicked.connect(self.clear_logs)
        
        self.save_button = QtWidgets.QPushButton("Save As...")
        self.save_button.clicked.connect(self.save_logs)
        
        self.close_button = QtWidgets.QPushButton("Close")
        self.close_button.clicked.connect(self.accept)
        
        button_layout.addWidget(self.refresh_button)
        button_layout.addWidget(self.clear_button)
        button_layout.addWidget(self.save_button)
        button_layout.addStretch(1)
        button_layout.addWidget(self.close_button)
        
        layout.addWidget(self.tabs)
        layout.addLayout(button_layout)
        
    def refresh_logs(self):
        """Refresh the logs."""
        # This would need to fetch the logs again from the service
        QtWidgets.QMessageBox.information(
            self, "Refresh", "This would refresh the logs. Implement this functionality."
        )
        
    def clear_logs(self):
        """Clear the logs."""
        current_tab = self.tabs.currentIndex()
        
        if current_tab == 0:  # stdout
            if not self.stdout_path:
                QtWidgets.QMessageBox.warning(
                    self, "Warning", "No stdout log file configured."
                )
                return
                
            reply = QtWidgets.QMessageBox.question(
                self, "Confirm Clear",
                f"Are you sure you want to clear the stdout log file?\n{self.stdout_path}",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No
            )
            
            if reply == QtWidgets.QMessageBox.Yes:
                try:
                    with open(self.stdout_path, 'w') as f:
                        pass
                    self.stdout_text.clear()
                    QtWidgets.QMessageBox.information(
                        self, "Success", "Stdout log file cleared."
                    )
                except Exception as e:
                    QtWidgets.QMessageBox.critical(
                        self, "Error", f"Failed to clear stdout log file: {str(e)}"
                    )
        else:  # stderr
            if not self.stderr_path:
                QtWidgets.QMessageBox.warning(
                    self, "Warning", "No stderr log file configured."
                )
                return
                
            reply = QtWidgets.QMessageBox.question(
                self, "Confirm Clear",
                f"Are you sure you want to clear the stderr log file?\n{self.stderr_path}",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No
            )
            
            if reply == QtWidgets.QMessageBox.Yes:
                try:
                    with open(self.stderr_path, 'w') as f:
                        pass
                    self.stderr_text.clear()
                    QtWidgets.QMessageBox.information(
                        self, "Success", "Stderr log file cleared."
                    )
                except Exception as e:
                    QtWidgets.QMessageBox.critical(
                        self, "Error", f"Failed to clear stderr log file: {str(e)}"
                    )
                    
    def save_logs(self):
        """Save the logs to a file."""
        current_tab = self.tabs.currentIndex()
        
        if current_tab == 0:  # stdout
            log_text = self.stdout_text.toPlainText()
            file_type = "stdout"
        else:  # stderr
            log_text = self.stderr_text.toPlainText()
            file_type = "stderr"
            
        if not log_text:
            QtWidgets.QMessageBox.warning(
                self, "Warning", f"No {file_type} logs to save."
            )
            return
            
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, f"Save {file_type.capitalize()} Logs", f"{self.service_name}_{file_type}.log",
            "Log Files (*.log *.txt);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    f.write(log_text)
                QtWidgets.QMessageBox.information(
                    self, "Success", f"{file_type.capitalize()} logs saved to {file_path}"
                )
            except Exception as e:
                QtWidgets.QMessageBox.critical(
                    self, "Error", f"Failed to save logs: {str(e)}"
                )
                

class PreferencesDialog(QtWidgets.QDialog):
    """Dialog for application preferences."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Preferences')
        self.setFixedSize(400, 300)
        
        self.init_ui()
        self.load_preferences()
        
    def init_ui(self):
        """Initialize the dialog UI."""
        layout = QtWidgets.QVBoxLayout(self)
        
        # General settings
        general_group = QtWidgets.QGroupBox("General")
        general_layout = QtWidgets.QFormLayout()
        
        self.auto_refresh_check = QtWidgets.QCheckBox("Auto-refresh service list")
        self.auto_refresh_check.setChecked(True)
        
        self.refresh_interval_spin = QtWidgets.QSpinBox()
        self.refresh_interval_spin.setRange(1, 60)
        self.refresh_interval_spin.setSuffix(" seconds")
        self.refresh_interval_spin.setValue(5)
        
        self.confirm_actions_check = QtWidgets.QCheckBox("Confirm before actions")
        self.confirm_actions_check.setChecked(True)
        
        self.show_details_check = QtWidgets.QCheckBox("Show details panel")
        self.show_details_check.setChecked(True)
        
        general_layout.addRow(self.auto_refresh_check)
        general_layout.addRow("Refresh interval:", self.refresh_interval_spin)
        general_layout.addRow(self.confirm_actions_check)
        general_layout.addRow(self.show_details_check)
        
        general_group.setLayout(general_layout)
        
        # Appearance settings
        appearance_group = QtWidgets.QGroupBox("Appearance")
        appearance_layout = QtWidgets.QFormLayout()
        
        self.dark_mode_check = QtWidgets.QCheckBox("Dark mode")
        self.dark_mode_check.setChecked(False)
        
        self.font_size_spin = QtWidgets.QSpinBox()
        self.font_size_spin.setRange(8, 24)
        self.font_size_spin.setValue(9)
        
        appearance_layout.addRow(self.dark_mode_check)
        appearance_layout.addRow("Font size:", self.font_size_spin)
        
        appearance_group.setLayout(appearance_layout)
        
        # Add to main layout
        layout.addWidget(general_group)
        layout.addWidget(appearance_group)
        layout.addStretch(1)
        
        # Buttons
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        layout.addWidget(button_box)
        
    def load_preferences(self):
        """Load preferences from the parent application."""
        if hasattr(self.parent(), 'preferences'):
            prefs = self.parent().preferences
            
            self.auto_refresh_check.setChecked(prefs.get('auto_refresh', True))
            self.refresh_interval_spin.setValue(prefs.get('refresh_interval', 5000) // 1000)
            self.confirm_actions_check.setChecked(prefs.get('confirm_actions', True))
            self.show_details_check.setChecked(prefs.get('show_details_panel', True))
            self.dark_mode_check.setChecked(prefs.get('dark_mode', False))
            self.font_size_spin.setValue(prefs.get('font_size', 9))
        
    def get_preferences(self) -> dict:
        """Get the preferences as a dictionary."""
        return {
            'auto_refresh': self.auto_refresh_check.isChecked(),
            'refresh_interval': self.refresh_interval_spin.value() * 1000,  # Convert to milliseconds
            'confirm_actions': self.confirm_actions_check.isChecked(),
            'show_details_panel': self.show_details_check.isChecked(),
            'dark_mode': self.dark_mode_check.isChecked(),
            'font_size': self.font_size_spin.value()
        }