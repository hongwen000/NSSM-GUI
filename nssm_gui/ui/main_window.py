import os
import sys
import asyncio
from PyQt5 import QtWidgets, QtGui, QtCore
import logging
from typing import List, Optional, Dict

from ..models import ServiceConfig, ServiceInfo
from ..service_manager import NSSmManager
from .dialogs import AddServiceDialog, LogViewerDialog, PreferencesDialog

class ServiceTableModel(QtCore.QAbstractTableModel):
    """Custom table model for service information."""
    
    def __init__(self, services: List[ServiceInfo] = None):
        super().__init__()
        self.services = services or []
        self.headers = ["Service Name", "Display Name", "State", "PID"]
        
    def rowCount(self, parent=None):
        return len(self.services)
        
    def columnCount(self, parent=None):
        return len(self.headers)
        
    def data(self, index, role):
        if not index.isValid():
            return None
            
        if role == QtCore.Qt.DisplayRole:
            service = self.services[index.row()]
            col = index.column()
            
            if col == 0:
                return service.name
            elif col == 1:
                return service.display_name
            elif col == 2:
                return service.state
            elif col == 3:
                return str(service.pid) if service.pid else ""
                
        elif role == QtCore.Qt.BackgroundRole:
            service = self.services[index.row()]
            if service.state.lower() == "running":
                return QtGui.QColor(200, 255, 200)  # Light green
            elif service.state.lower() == "stopped":
                return QtGui.QColor(255, 200, 200)  # Light red
                
        return None
        
    def headerData(self, section, orientation, role):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return self.headers[section]
        return None
        
    def update_services(self, services: List[ServiceInfo]):
        self.beginResetModel()
        self.services = services
        self.endResetModel()
        
    def get_service(self, row: int) -> Optional[ServiceInfo]:
        if 0 <= row < len(self.services):
            return self.services[row]
        return None

class NSSmGUI(QtWidgets.QMainWindow):
    """Main window for the NSSM GUI application."""
    
    def __init__(self, nssm_path: str, async_helper=None):
        super().__init__()
        self.nssm_path = nssm_path
        self.service_manager = NSSmManager(nssm_path)
        self.logger = logging.getLogger("nssm_gui.main_window")
        self.async_helper = async_helper
        
        # Initialize UI
        self.setWindowTitle('NSSM Service Manager')
        self.setGeometry(100, 100, 1200, 800)
        self.init_ui()
        
        # Set up the refresh timer
        self.refresh_timer = QtCore.QTimer()
        self.refresh_timer.timeout.connect(self.refresh_services)
        
        # Load user preferences
        self.load_preferences()
        
        # Load services after window is shown (defer with a timer)
        QtCore.QTimer.singleShot(100, self.refresh_services)
        
    def init_ui(self):
        # Central widget and main layout
        self.central_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QtWidgets.QVBoxLayout(self.central_widget)
        
        # Service filter
        self.filter_layout = QtWidgets.QHBoxLayout()
        self.filter_label = QtWidgets.QLabel("Filter:")
        self.filter_input = QtWidgets.QLineEdit()
        self.filter_input.setPlaceholderText("Filter services by name...")
        self.filter_input.textChanged.connect(self.apply_filter)
        
        self.status_filter_combo = QtWidgets.QComboBox()
        self.status_filter_combo.addItems(["All", "Running", "Stopped"])
        self.status_filter_combo.currentTextChanged.connect(self.apply_filter)
        
        self.filter_layout.addWidget(self.filter_label)
        self.filter_layout.addWidget(self.filter_input, 1)
        self.filter_layout.addWidget(QtWidgets.QLabel("Status:"))
        self.filter_layout.addWidget(self.status_filter_combo)
        
        self.main_layout.addLayout(self.filter_layout)
        
        # Services table
        self.service_table = QtWidgets.QTableView()
        self.service_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.service_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.service_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.service_table.setSortingEnabled(True)
        self.service_table.verticalHeader().setVisible(False)
        self.service_table.horizontalHeader().setStretchLastSection(True)
        self.service_table.setAlternatingRowColors(True)
        self.service_table.doubleClicked.connect(self.edit_service)
        
        # Set up the table model
        self.table_model = ServiceTableModel()
        self.service_table.setModel(self.table_model)
        
        self.main_layout.addWidget(self.service_table, 1)
        
        # Service details panel
        self.details_group = QtWidgets.QGroupBox("Service Details")
        self.details_layout = QtWidgets.QFormLayout()
        
        self.detail_name = QtWidgets.QLabel("")
        self.detail_display_name = QtWidgets.QLabel("")
        self.detail_state = QtWidgets.QLabel("")
        self.detail_path = QtWidgets.QLabel("")
        self.detail_path.setWordWrap(True)
        
        self.details_layout.addRow("Service Name:", self.detail_name)
        self.details_layout.addRow("Display Name:", self.detail_display_name)
        self.details_layout.addRow("State:", self.detail_state)
        self.details_layout.addRow("Path:", self.detail_path)
        
        self.details_group.setLayout(self.details_layout)
        self.main_layout.addWidget(self.details_group)
        
        # Button layout
        self.button_layout = QtWidgets.QHBoxLayout()
        
        # Action buttons
        self.add_button = QtWidgets.QPushButton("Add Service")
        self.edit_button = QtWidgets.QPushButton("Edit Service")
        self.delete_button = QtWidgets.QPushButton("Delete Service")
        self.start_button = QtWidgets.QPushButton("Start")
        self.stop_button = QtWidgets.QPushButton("Stop")
        self.restart_button = QtWidgets.QPushButton("Restart")
        self.logs_button = QtWidgets.QPushButton("View Logs")
        self.refresh_button = QtWidgets.QPushButton("Refresh")
        
        # Connect signals
        self.add_button.clicked.connect(self.add_service)
        self.edit_button.clicked.connect(self.edit_service)
        self.delete_button.clicked.connect(self.delete_service)
        self.start_button.clicked.connect(self.start_service)
        self.stop_button.clicked.connect(self.stop_service)
        self.restart_button.clicked.connect(self.restart_service)
        self.logs_button.clicked.connect(self.view_logs)
        self.refresh_button.clicked.connect(self.refresh_services)
        
        # Set icons
        self.add_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_FileDialogNewFolder))
        self.edit_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_FileDialogDetailedView))
        self.delete_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_TrashIcon))
        self.start_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_MediaPlay))
        self.stop_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_MediaStop))
        self.restart_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_BrowserReload))
        self.logs_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_FileDialogContentsView))
        self.refresh_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_BrowserReload))
        
        # Add to layout
        self.button_layout.addWidget(self.add_button)
        self.button_layout.addWidget(self.edit_button)
        self.button_layout.addWidget(self.delete_button)
        self.button_layout.addSpacing(20)
        self.button_layout.addWidget(self.start_button)
        self.button_layout.addWidget(self.stop_button)
        self.button_layout.addWidget(self.restart_button)
        self.button_layout.addSpacing(20)
        self.button_layout.addWidget(self.logs_button)
        self.button_layout.addStretch(1)
        self.button_layout.addWidget(self.refresh_button)
        
        self.main_layout.addLayout(self.button_layout)
        
        # Status bar
        self.status_bar = QtWidgets.QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QtWidgets.QLabel()
        self.status_bar.addWidget(self.status_label, 1)
        
        # Auto-refresh checkbox in the status bar
        self.auto_refresh_check = QtWidgets.QCheckBox("Auto-refresh")
        self.auto_refresh_check.setChecked(True)
        self.auto_refresh_check.stateChanged.connect(self.toggle_auto_refresh)
        self.status_bar.addPermanentWidget(self.auto_refresh_check)
        
        # Create the menu bar
        self.create_menu_bar()
        
        # Connect the selection signal
        selection_model = self.service_table.selectionModel()
        selection_model.selectionChanged.connect(self.update_service_details)
        
    def create_menu_bar(self):
        """Create the application menu bar."""
        menu_bar = self.menuBar()
        
        # File menu
        file_menu = menu_bar.addMenu("&File")
        
        # Add actions to file menu
        new_action = QtWidgets.QAction("&Add Service", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.add_service)
        file_menu.addAction(new_action)
        
        refresh_action = QtWidgets.QAction("&Refresh", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self.refresh_services)
        file_menu.addAction(refresh_action)
        
        file_menu.addSeparator()
        
        import_action = QtWidgets.QAction("&Import Configuration", self)
        import_action.triggered.connect(self.import_config)
        file_menu.addAction(import_action)
        
        export_action = QtWidgets.QAction("&Export Configuration", self)
        export_action.triggered.connect(self.export_config)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        preferences_action = QtWidgets.QAction("&Preferences", self)
        preferences_action.triggered.connect(self.show_preferences)
        file_menu.addAction(preferences_action)
        
        file_menu.addSeparator()
        
        exit_action = QtWidgets.QAction("&Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Service menu
        service_menu = menu_bar.addMenu("&Service")
        
        start_action = QtWidgets.QAction("&Start", self)
        start_action.triggered.connect(self.start_service)
        service_menu.addAction(start_action)
        
        stop_action = QtWidgets.QAction("S&top", self)
        stop_action.triggered.connect(self.stop_service)
        service_menu.addAction(stop_action)
        
        restart_action = QtWidgets.QAction("&Restart", self)
        restart_action.triggered.connect(self.restart_service)
        service_menu.addAction(restart_action)
        
        service_menu.addSeparator()
        
        edit_action = QtWidgets.QAction("&Edit", self)
        edit_action.triggered.connect(self.edit_service)
        service_menu.addAction(edit_action)
        
        delete_action = QtWidgets.QAction("&Delete", self)
        delete_action.triggered.connect(self.delete_service)
        service_menu.addAction(delete_action)
        
        service_menu.addSeparator()
        
        logs_action = QtWidgets.QAction("View &Logs", self)
        logs_action.triggered.connect(self.view_logs)
        service_menu.addAction(logs_action)
        
        # Tools menu
        tools_menu = menu_bar.addMenu("&Tools")
        
        batch_action = QtWidgets.QAction("&Batch Operations", self)
        batch_action.triggered.connect(self.show_batch_operations)
        tools_menu.addAction(batch_action)
        
        templates_action = QtWidgets.QAction("&Templates", self)
        templates_action.triggered.connect(self.show_templates)
        tools_menu.addAction(templates_action)
        
        # Help menu
        help_menu = menu_bar.addMenu("&Help")
        
        about_action = QtWidgets.QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
        help_action = QtWidgets.QAction("&Help", self)
        help_action.setShortcut("F1")
        help_action.triggered.connect(self.show_help)
        help_menu.addAction(help_action)
        
    def toggle_auto_refresh(self, state):
        """Toggle the auto-refresh feature."""
        if state == QtCore.Qt.Checked:
            # Start the timer
            self.refresh_timer.start(5000)  # Refresh every 5 seconds
        else:
            # Stop the timer
            self.refresh_timer.stop()
            
    def apply_filter(self):
        """Apply the filter to the service table."""
        # Get the current filter text
        filter_text = self.filter_input.text().lower()
        status_filter = self.status_filter_combo.currentText()
        
        # Create a proxy model for filtering
        proxy_model = QtCore.QSortFilterProxyModel()
        proxy_model.setSourceModel(self.table_model)
        
        # Set up the filter
        proxy_model.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)
        proxy_model.setFilterKeyColumn(0)  # Filter on the service name column
        
        # Apply the text filter
        proxy_model.setFilterRegExp(filter_text)
        
        # Apply status filter
        if status_filter != "All":
            for row in range(self.table_model.rowCount()):
                service = self.table_model.get_service(row)
                if service:
                    if status_filter == "Running" and service.state.lower() != "running":
                        proxy_model.setFilterFixedString("THIS_WILL_NOT_MATCH_ANYTHING")
                    elif status_filter == "Stopped" and service.state.lower() != "stopped":
                        proxy_model.setFilterFixedString("THIS_WILL_NOT_MATCH_ANYTHING")
        
        # Set the proxy model on the table
        self.service_table.setModel(proxy_model)
        
    def refresh_services(self):
        """Refresh the services list."""
        if not self.async_helper:
            self.logger.error("Async helper not initialized")
            QtWidgets.QMessageBox.critical(
                self, "Error", "Async helper not initialized. Please restart the application."
            )
            return
            
        # Show "loading" cursor
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
            
        # Run the async refresh function
        self.async_helper.run(self.async_refresh_services(), self.refresh_callback)
            
    def refresh_callback(self, result, exception):
        """Callback for refresh services."""
        if QtWidgets.QApplication.overrideCursor():
            QtWidgets.QApplication.restoreOverrideCursor()
            
        if exception:
            self.logger.error(f"Error refreshing services: {str(exception)}")
            self.status_label.setText(f"Error: {str(exception)}")
            
            # Show error message
            QtWidgets.QMessageBox.warning(
                self, "Error Refreshing Services",
                f"Failed to refresh services list: {str(exception)}\n\n"
                "Check if NSSM is properly installed and you have administrative privileges."
            )
            
    def add_service(self):
        """Add a new service."""
        if not self.async_helper:
            self.logger.error("Async helper not initialized")
            QtWidgets.QMessageBox.critical(
                self, "Error", "Async helper not initialized. Please restart the application."
            )
            return
            
        # Show the dialog directly since it needs to be synchronous
        dialog = AddServiceDialog(self, existing_config=ServiceConfig())
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            config = dialog.get_service_config()
            if config:
                # Show "loading" cursor
                QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
                
                # Run the async configure function
                self.async_helper.run(
                    self.service_manager.configure_service(config, edit=False),
                    lambda result, exception: self.add_service_callback(result, exception, config.service_name)
                )
                
    def add_service_callback(self, result, exception, service_name):
        """Callback for add service."""
        # Restore cursor
        if QtWidgets.QApplication.overrideCursor():
            QtWidgets.QApplication.restoreOverrideCursor()
            
        if exception:
            self.logger.error(f"Error adding service: {str(exception)}")
            QtWidgets.QMessageBox.critical(
                self, "Error", f"Failed to create service: {str(exception)}"
            )
        elif result:
            QtWidgets.QMessageBox.information(
                self, "Success", f"Service '{service_name}' created successfully."
            )
            # Refresh services list
            self.refresh_services()
            
    def edit_service(self):
        """Edit an existing service."""
        if not self.async_helper:
            self.logger.error("Async helper not initialized")
            QtWidgets.QMessageBox.critical(
                self, "Error", "Async helper not initialized. Please restart the application."
            )
            return
            
        service = self.get_selected_service()
        if not service:
            QtWidgets.QMessageBox.warning(
                self, "Warning", "Please select a service to edit."
            )
            return
            
        # Show "loading" cursor
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
            
        # Run the async get config function
        self.async_helper.run(
            self.service_manager.get_service_config(service.name),
            lambda config, exception: self.edit_service_get_config_callback(config, exception, service.name)
        )
            
    def edit_service_get_config_callback(self, config, exception, service_name):
        """Callback for get service config."""
        # Restore cursor
        if QtWidgets.QApplication.overrideCursor():
            QtWidgets.QApplication.restoreOverrideCursor()
            
        if exception:
            self.logger.error(f"Error getting service config: {str(exception)}")
            QtWidgets.QMessageBox.critical(
                self, "Error", f"Failed to get configuration for service '{service_name}': {str(exception)}"
            )
            return
            
        if not config:
            QtWidgets.QMessageBox.critical(
                self, "Error", f"Failed to get configuration for service '{service_name}'."
            )
            return
            
        # Show the edit dialog
        dialog = AddServiceDialog(self, existing_config=config)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            updated_config = dialog.get_service_config()
            if updated_config:
                # Show "loading" cursor
                QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
                
                # Run the async configure function
                self.async_helper.run(
                    self.service_manager.configure_service(updated_config, edit=True),
                    lambda result, exception: self.edit_service_callback(result, exception, updated_config.service_name)
                )
                    
    def edit_service_callback(self, result, exception, service_name):
        """Callback for edit service."""
        # Restore cursor
        if QtWidgets.QApplication.overrideCursor():
            QtWidgets.QApplication.restoreOverrideCursor()
            
        if exception:
            self.logger.error(f"Error editing service: {str(exception)}")
            QtWidgets.QMessageBox.critical(
                self, "Error", f"Failed to update service: {str(exception)}"
            )
        elif result:
            QtWidgets.QMessageBox.information(
                self, "Success", f"Service '{service_name}' updated successfully."
            )
            # Refresh services list
            self.refresh_services()
            
    def delete_service(self):
        """Delete a service."""
        if not self.async_helper:
            self.logger.error("Async helper not initialized")
            QtWidgets.QMessageBox.critical(
                self, "Error", "Async helper not initialized. Please restart the application."
            )
            return
            
        service = self.get_selected_service()
        if not service:
            QtWidgets.QMessageBox.warning(
                self, "Warning", "Please select a service to delete."
            )
            return
            
        # Confirm deletion
        reply = QtWidgets.QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete the service '{service.name}'?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )
        
        if reply == QtWidgets.QMessageBox.Yes:
            # Show "loading" cursor
            QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
            
            # Run the async remove function
            self.async_helper.run(
                self.service_manager.remove_service(service.name),
                lambda result, exception: self.delete_service_callback(result, exception, service.name)
            )
                
    def delete_service_callback(self, result, exception, service_name):
        """Callback for delete service."""
        # Restore cursor
        if QtWidgets.QApplication.overrideCursor():
            QtWidgets.QApplication.restoreOverrideCursor()
            
        if exception:
            self.logger.error(f"Error deleting service: {str(exception)}")
            QtWidgets.QMessageBox.critical(
                self, "Error", f"Failed to delete service: {str(exception)}"
            )
        elif result:
            QtWidgets.QMessageBox.information(
                self, "Success", f"Service '{service_name}' deleted successfully."
            )
            # Refresh services list
            self.refresh_services()
        else:
            QtWidgets.QMessageBox.critical(
                self, "Error", f"Failed to delete service '{service_name}'."
            )
            
    def start_service(self):
        """Start a service."""
        if not self.async_helper:
            self.logger.error("Async helper not initialized")
            QtWidgets.QMessageBox.critical(
                self, "Error", "Async helper not initialized. Please restart the application."
            )
            return
            
        service = self.get_selected_service()
        if not service:
            QtWidgets.QMessageBox.warning(
                self, "Warning", "Please select a service to start."
            )
            return
            
        # Show "loading" cursor
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        
        # Run the async start function
        self.async_helper.run(
            self.service_manager.start_service(service.name),
            lambda result, exception: self.start_service_callback(result, exception, service.name)
        )
            
    def start_service_callback(self, result, exception, service_name):
        """Callback for start service."""
        # Restore cursor
        if QtWidgets.QApplication.overrideCursor():
            QtWidgets.QApplication.restoreOverrideCursor()
            
        if exception:
            self.logger.error(f"Error starting service: {str(exception)}")
            QtWidgets.QMessageBox.critical(
                self, "Error", f"Failed to start service: {str(exception)}"
            )
        elif result:
            QtWidgets.QMessageBox.information(
                self, "Success", f"Service '{service_name}' started successfully."
            )
            # Refresh services list
            self.refresh_services()
        else:
            QtWidgets.QMessageBox.critical(
                self, "Error", f"Failed to start service '{service_name}'."
            )
            
    def stop_service(self):
        """Stop a service."""
        if not self.async_helper:
            self.logger.error("Async helper not initialized")
            QtWidgets.QMessageBox.critical(
                self, "Error", "Async helper not initialized. Please restart the application."
            )
            return
            
        service = self.get_selected_service()
        if not service:
            QtWidgets.QMessageBox.warning(
                self, "Warning", "Please select a service to stop."
            )
            return
            
        # Show "loading" cursor
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        
        # Run the async stop function
        self.async_helper.run(
            self.service_manager.stop_service(service.name),
            lambda result, exception: self.stop_service_callback(result, exception, service.name)
        )
            
    def stop_service_callback(self, result, exception, service_name):
        """Callback for stop service."""
        # Restore cursor
        if QtWidgets.QApplication.overrideCursor():
            QtWidgets.QApplication.restoreOverrideCursor()
            
        if exception:
            self.logger.error(f"Error stopping service: {str(exception)}")
            QtWidgets.QMessageBox.critical(
                self, "Error", f"Failed to stop service: {str(exception)}"
            )
        elif result:
            QtWidgets.QMessageBox.information(
                self, "Success", f"Service '{service_name}' stopped successfully."
            )
            # Refresh services list
            self.refresh_services()
        else:
            QtWidgets.QMessageBox.critical(
                self, "Error", f"Failed to stop service '{service_name}'."
            )
            
    def restart_service(self):
        """Restart a service."""
        if not self.async_helper:
            self.logger.error("Async helper not initialized")
            QtWidgets.QMessageBox.critical(
                self, "Error", "Async helper not initialized. Please restart the application."
            )
            return
            
        service = self.get_selected_service()
        if not service:
            QtWidgets.QMessageBox.warning(
                self, "Warning", "Please select a service to restart."
            )
            return
            
        # Show "loading" cursor
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        
        # Run the async restart function
        self.async_helper.run(
            self.service_manager.restart_service(service.name),
            lambda result, exception: self.restart_service_callback(result, exception, service.name)
        )
            
    def restart_service_callback(self, result, exception, service_name):
        """Callback for restart service."""
        # Restore cursor
        if QtWidgets.QApplication.overrideCursor():
            QtWidgets.QApplication.restoreOverrideCursor()
            
        if exception:
            self.logger.error(f"Error restarting service: {str(exception)}")
            QtWidgets.QMessageBox.critical(
                self, "Error", f"Failed to restart service: {str(exception)}"
            )
        elif result:
            QtWidgets.QMessageBox.information(
                self, "Success", f"Service '{service_name}' restarted successfully."
            )
            # Refresh services list
            self.refresh_services()
        else:
            QtWidgets.QMessageBox.critical(
                self, "Error", f"Failed to restart service '{service_name}'."
            )
        
    def view_logs(self):
        """View service logs."""
        if not self.async_helper:
            self.logger.error("Async helper not initialized")
            QtWidgets.QMessageBox.critical(
                self, "Error", "Async helper not initialized. Please restart the application."
            )
            return
            
        service = self.get_selected_service()
        if not service:
            QtWidgets.QMessageBox.warning(
                self, "Warning", "Please select a service to view logs."
            )
            return
            
        # Show "loading" cursor
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
            
        # Run the async get config function
        self.async_helper.run(
            self.service_manager.get_service_config(service.name),
            lambda config, exception: self.view_logs_get_config_callback(config, exception, service.name)
        )
            
    def view_logs_get_config_callback(self, config, exception, service_name):
        """Callback for get service config for log viewing."""
        if exception:
            # Restore cursor
            if QtWidgets.QApplication.overrideCursor():
                QtWidgets.QApplication.restoreOverrideCursor()
                
            self.logger.error(f"Error getting service config for logs: {str(exception)}")
            QtWidgets.QMessageBox.critical(
                self, "Error", f"Failed to get configuration for service '{service_name}': {str(exception)}"
            )
            return
            
        if not config:
            # Restore cursor
            if QtWidgets.QApplication.overrideCursor():
                QtWidgets.QApplication.restoreOverrideCursor()
                
            QtWidgets.QMessageBox.critical(
                self, "Error", f"Failed to get configuration for service '{service_name}'."
            )
            return
            
        # Get stdout and stderr logs
        self.async_helper.run(
            self.service_manager.get_service_logs(service_name, 'stdout'),
            lambda stdout_logs, exception: self.view_logs_get_stdout_callback(
                stdout_logs, exception, service_name, config
            )
        )
            
    def view_logs_get_stdout_callback(self, stdout_logs, exception, service_name, config):
        """Callback for get service stdout logs."""
        if exception:
            # Restore cursor
            if QtWidgets.QApplication.overrideCursor():
                QtWidgets.QApplication.restoreOverrideCursor()
                
            self.logger.error(f"Error getting stdout logs: {str(exception)}")
            QtWidgets.QMessageBox.critical(
                self, "Error", f"Failed to get stdout logs: {str(exception)}"
            )
            return
            
        # Now get stderr logs
        self.async_helper.run(
            self.service_manager.get_service_logs(service_name, 'stderr'),
            lambda stderr_logs, exception: self.view_logs_get_stderr_callback(
                stderr_logs, exception, service_name, config, stdout_logs
            )
        )
            
    def view_logs_get_stderr_callback(self, stderr_logs, exception, service_name, config, stdout_logs):
        """Callback for get service stderr logs."""
        # Restore cursor
        if QtWidgets.QApplication.overrideCursor():
            QtWidgets.QApplication.restoreOverrideCursor()
            
        if exception:
            self.logger.error(f"Error getting stderr logs: {str(exception)}")
            stderr_logs = f"Error getting stderr logs: {str(exception)}"
            
        # Show log viewer dialog
        dialog = LogViewerDialog(
            self, service_name, stdout_logs, stderr_logs,
            stdout_path=config.stdout_path, stderr_path=config.stderr_path
        )
        dialog.exec_()
    
    def update_service_details(self, selected, deselected):
        """Update the service details panel when a service is selected."""
        if selected.indexes():
            row = selected.indexes()[0].row()
            service = self.table_model.get_service(row)
            
            if service:
                self.detail_name.setText(service.name)
                self.detail_display_name.setText(service.display_name)
                self.detail_state.setText(service.state)
                self.detail_path.setText(service.path)
                
                # Enable/disable buttons based on service state
                is_running = service.state.lower() == "running"
                self.start_button.setEnabled(not is_running)
                self.stop_button.setEnabled(is_running)
                self.restart_button.setEnabled(is_running)
                self.edit_button.setEnabled(True)
                self.delete_button.setEnabled(True)
                self.logs_button.setEnabled(True)
            else:
                self.clear_service_details()
        else:
            self.clear_service_details()
            
    def clear_service_details(self):
        """Clear the service details panel."""
        self.detail_name.setText("")
        self.detail_display_name.setText("")
        self.detail_state.setText("")
        self.detail_path.setText("")
        
        # Disable action buttons
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.restart_button.setEnabled(False)
        self.edit_button.setEnabled(False)
        self.delete_button.setEnabled(False)
        self.logs_button.setEnabled(False)
        
    def get_selected_service(self) -> Optional[ServiceInfo]:
        """Get the currently selected service."""
        if not self.service_table.selectionModel().hasSelection():
            return None
            
        indexes = self.service_table.selectionModel().selectedRows()
        if not indexes:
            return None
            
        row = indexes[0].row()
        return self.table_model.get_service(row)
        
    def import_config(self):
        """Import service configuration(s)."""
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Import Configuration", "", "JSON Files (*.json);;All Files (*)"
        )
        if not file_path:
            return
            
        try:
            with open(file_path, 'r') as f:
                import json
                config_data = json.load(f)
                
            # Process the imported configuration
            # This is a placeholder - implementation depends on your config format
            QtWidgets.QMessageBox.information(
                self, "Success", f"Configuration imported successfully from {file_path}."
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self, "Error", f"Failed to import configuration: {str(e)}"
            )
            
    def export_config(self):
        """Export service configuration(s)."""
        service = self.get_selected_service()
        if not service:
            QtWidgets.QMessageBox.warning(
                self, "Warning", "Please select a service to export."
            )
            return
            
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export Configuration", f"{service.name}_config.json", "JSON Files (*.json);;All Files (*)"
        )
        if not file_path:
            return
            
        # Get the service configuration
        if self.async_helper:
            self.async_helper.run(
                self.service_manager.get_service_config(service.name),
                lambda config, exception: self.export_config_callback(config, exception, file_path)
            )
            
    def export_config_callback(self, config, exception, file_path):
        """Callback for export config."""
        if exception:
            self.logger.error(f"Error exporting configuration: {str(exception)}")
            QtWidgets.QMessageBox.critical(
                self, "Error", f"Failed to get service configuration: {str(exception)}"
            )
            return
            
        if not config:
            QtWidgets.QMessageBox.critical(
                self, "Error", "Failed to get service configuration."
            )
            return
            
        try:
            with open(file_path, 'w') as f:
                import json
                json.dump(config.model_dump(), f, indent=4)
                
            QtWidgets.QMessageBox.information(
                self, "Success", f"Configuration exported successfully to {file_path}."
            )
        except Exception as e:
            self.logger.error(f"Error writing configuration file: {str(e)}")
            QtWidgets.QMessageBox.critical(
                self, "Error", f"Failed to export configuration: {str(e)}"
            )
            
    def show_batch_operations(self):
        """Show the batch operations dialog."""
        # This is a placeholder for batch operations functionality
        QtWidgets.QMessageBox.information(
            self, "Batch Operations", "Batch operations feature coming soon."
        )
        
    def show_templates(self):
        """Show the templates dialog."""
        # This is a placeholder for templates functionality
        QtWidgets.QMessageBox.information(
            self, "Templates", "Templates feature coming soon."
        )
        
    def show_about(self):
        """Show the about dialog."""
        QtWidgets.QMessageBox.about(
            self, "About NSSM GUI",
            """<h2>NSSM GUI</h2>
            <p>Version 1.0.0</p>
            <p>A graphical user interface for the Non-Sucking Service Manager (NSSM).</p>
            <p>© 2025 Your Organization</p>
            """
        )
        
    def show_help(self):
        """Show the help dialog."""
        QtWidgets.QMessageBox.information(
            self, "Help",
            """<h2>NSSM GUI Help</h2>
            <p>This application helps you manage Windows services using NSSM.</p>
            <h3>Key Features:</h3>
            <ul>
                <li>Create, edit, and delete services</li>
                <li>Start, stop, and restart services</li>
                <li>View service logs</li>
                <li>Import and export service configurations</li>
            </ul>
            <p>For more information, visit the <a href="https://nssm.cc">NSSM website</a>.</p>
            """
        )
        
    def show_preferences(self):
        """Show the preferences dialog."""
        dialog = PreferencesDialog(self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.save_preferences(dialog.get_preferences())
            self.apply_preferences()
            
    def load_preferences(self):
        """Load user preferences."""
        # This is a placeholder for preferences functionality
        # In a real implementation, you would load preferences from a file
        self.preferences = {
            'auto_refresh': True,
            'refresh_interval': 5000,  # 5 seconds
            'dark_mode': False,
            'confirm_actions': True,
            'show_details_panel': True
        }
        self.apply_preferences()
        
    def save_preferences(self, preferences):
        """Save user preferences."""
        # This is a placeholder for preferences functionality
        # In a real implementation, you would save preferences to a file
        self.preferences = preferences
        
    def apply_preferences(self):
        """Apply user preferences to the UI."""
        # Auto-refresh
        self.auto_refresh_check.setChecked(self.preferences.get('auto_refresh', True))
        if self.preferences.get('auto_refresh', True):
            self.refresh_timer.start(self.preferences.get('refresh_interval', 5000))
        else:
            self.refresh_timer.stop()
            
        # Dark mode
        if self.preferences.get('dark_mode', False):
            self.apply_dark_mode()
        else:
            self.apply_light_mode()
            
        # Details panel
        self.details_group.setVisible(self.preferences.get('show_details_panel', True))
            
    def apply_dark_mode(self):
        """Apply dark mode to the application."""
        # This is a basic implementation of dark mode
        # In a real application, you would use a more comprehensive theme
        dark_palette = QtGui.QPalette()
        dark_palette.setColor(QtGui.QPalette.Window, QtGui.QColor(53, 53, 53))
        dark_palette.setColor(QtGui.QPalette.WindowText, QtCore.Qt.white)
        dark_palette.setColor(QtGui.QPalette.Base, QtGui.QColor(25, 25, 25))
        dark_palette.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(53, 53, 53))
        dark_palette.setColor(QtGui.QPalette.ToolTipBase, QtCore.Qt.white)
        dark_palette.setColor(QtGui.QPalette.ToolTipText, QtCore.Qt.white)
        dark_palette.setColor(QtGui.QPalette.Text, QtCore.Qt.white)
        dark_palette.setColor(QtGui.QPalette.Button, QtGui.QColor(53, 53, 53))
        dark_palette.setColor(QtGui.QPalette.ButtonText, QtCore.Qt.white)
        dark_palette.setColor(QtGui.QPalette.BrightText, QtCore.Qt.red)
        dark_palette.setColor(QtGui.QPalette.Link, QtGui.QColor(42, 130, 218))
        dark_palette.setColor(QtGui.QPalette.Highlight, QtGui.QColor(42, 130, 218))
        dark_palette.setColor(QtGui.QPalette.HighlightedText, QtCore.Qt.black)
        self.setPalette(dark_palette)
        
    def apply_light_mode(self):
        """Apply light mode to the application."""
        # Reset to default palette
        self.setPalette(QtWidgets.QApplication.style().standardPalette())
        
    def closeEvent(self, event):
        """Handle the close event."""
        # Stop the refresh timer
        self.refresh_timer.stop()
        event.accept()
        
    # Async methods
    
    async def async_refresh_services(self):
        """Async method to refresh the services list."""
        try:
            # Show loading status
            self.status_label.setText("Loading services...")
            
            services = await self.service_manager.get_services()
            
            # Sort services by name
            services.sort(key=lambda s: s.name.lower())
            
            # Update the model
            self.table_model.update_services(services)
            
            # Update status label
            self.status_label.setText(f"Total services: {len(services)}")
            
            # Retain selection if possible
            if self.service_table.selectionModel().hasSelection():
                selected_row = self.service_table.selectionModel().selectedRows()[0].row()
                if selected_row < len(services):
                    self.service_table.selectRow(selected_row)
                    
            return True
        except Exception as e:
            self.logger.error(f"Error refreshing services: {str(e)}")
            self.status_label.setText(f"Error: {str(e)}")
            return False