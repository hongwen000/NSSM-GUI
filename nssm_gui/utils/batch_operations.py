from PyQt5 import QtWidgets, QtGui, QtCore
from typing import List, Dict, Callable, Optional
import asyncio
import logging

from ..models import ServiceInfo
from ..service_manager import NSSmManager

logger = logging.getLogger("nssm_gui.batch_operations")

class BatchOperationsDialog(QtWidgets.QDialog):
    """Dialog for performing batch operations on multiple services."""
    
    def __init__(self, parent=None, service_manager: NSSmManager = None, services: List[ServiceInfo] = None):
        super().__init__(parent)
        self.setWindowTitle('Batch Operations')
        self.setGeometry(100, 100, 700, 500)
        
        self.service_manager = service_manager
        self.services = services or []
        self.selected_services = []
        
        self.init_ui()
        self.populate_services()
        
    def init_ui(self):
        """Initialize the UI components."""
        layout = QtWidgets.QVBoxLayout(self)
        
        # Instructions
        instructions = QtWidgets.QLabel(
            "Select services and operations to perform on them."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Services group
        services_group = QtWidgets.QGroupBox("Services")
        services_layout = QtWidgets.QVBoxLayout()
        
        # Service filter
        filter_layout = QtWidgets.QHBoxLayout()
        filter_label = QtWidgets.QLabel("Filter:")
        self.filter_input = QtWidgets.QLineEdit()
        self.filter_input.setPlaceholderText("Filter services...")
        self.filter_input.textChanged.connect(self.filter_services)
        
        filter_layout.addWidget(filter_label)
        filter_layout.addWidget(self.filter_input)
        services_layout.addLayout(filter_layout)
        
        # Services list
        self.services_list = QtWidgets.QListWidget()
        self.services_list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        services_layout.addWidget(self.services_list)
        
        # Select all/none buttons
        select_buttons_layout = QtWidgets.QHBoxLayout()
        self.select_all_button = QtWidgets.QPushButton("Select All")
        self.select_none_button = QtWidgets.QPushButton("Select None")
        self.select_running_button = QtWidgets.QPushButton("Select Running")
        self.select_stopped_button = QtWidgets.QPushButton("Select Stopped")
        
        self.select_all_button.clicked.connect(self.select_all)
        self.select_none_button.clicked.connect(self.select_none)
        self.select_running_button.clicked.connect(self.select_running)
        self.select_stopped_button.clicked.connect(self.select_stopped)
        
        select_buttons_layout.addWidget(self.select_all_button)
        select_buttons_layout.addWidget(self.select_none_button)
        select_buttons_layout.addWidget(self.select_running_button)
        select_buttons_layout.addWidget(self.select_stopped_button)
        
        services_layout.addLayout(select_buttons_layout)
        services_group.setLayout(services_layout)
        
        # Operations group
        operations_group = QtWidgets.QGroupBox("Operations")
        operations_layout = QtWidgets.QVBoxLayout()
        
        # Operation radio buttons
        self.operation_start = QtWidgets.QRadioButton("Start Services")
        self.operation_stop = QtWidgets.QRadioButton("Stop Services")
        self.operation_restart = QtWidgets.QRadioButton("Restart Services")
        self.operation_enable = QtWidgets.QRadioButton("Enable Services")
        self.operation_disable = QtWidgets.QRadioButton("Disable Services")
        self.operation_delete = QtWidgets.QRadioButton("Delete Services")
        
        # Select start by default
        self.operation_start.setChecked(True)
        
        # Make delete operation red to indicate danger
        self.operation_delete.setStyleSheet("color: red;")
        
        operations_layout.addWidget(self.operation_start)
        operations_layout.addWidget(self.operation_stop)
        operations_layout.addWidget(self.operation_restart)
        operations_layout.addWidget(self.operation_enable)
        operations_layout.addWidget(self.operation_disable)
        operations_layout.addWidget(self.operation_delete)
        
        # Additional options
        self.sequential_check = QtWidgets.QCheckBox("Execute Sequentially")
        self.sequential_check.setToolTip("Execute operations one after another instead of all at once")
        self.sequential_check.setChecked(True)
        
        self.confirm_each_check = QtWidgets.QCheckBox("Confirm Each Operation")
        self.confirm_each_check.setToolTip("Ask for confirmation before executing each operation")
        
        operations_layout.addWidget(self.sequential_check)
        operations_layout.addWidget(self.confirm_each_check)
        
        operations_group.setLayout(operations_layout)
        
        # Main layout organization
        main_content = QtWidgets.QHBoxLayout()
        main_content.addWidget(services_group, 2)
        main_content.addWidget(operations_group, 1)
        
        layout.addLayout(main_content)
        
        # Progress information
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.status_label = QtWidgets.QLabel()
        layout.addWidget(self.status_label)
        
        # Buttons
        button_box = QtWidgets.QDialogButtonBox()
        self.execute_button = button_box.addButton("Execute", QtWidgets.QDialogButtonBox.AcceptRole)
        self.close_button = button_box.addButton("Close", QtWidgets.QDialogButtonBox.RejectRole)
        
        self.execute_button.clicked.connect(self.execute_operations)
        self.close_button.clicked.connect(self.reject)
        
        layout.addWidget(button_box)
        
    def populate_services(self):
        """Populate the services list."""
        self.services_list.clear()
        
        for service in self.services:
            item = QtWidgets.QListWidgetItem(f"{service.name} - {service.state}")
            item.setData(QtCore.Qt.UserRole, service)
            
            # Color based on state
            if service.state.lower() == "running":
                item.setForeground(QtGui.QColor(0, 128, 0))  # Green
            elif service.state.lower() == "stopped":
                item.setForeground(QtGui.QColor(128, 0, 0))  # Red
                
            self.services_list.addItem(item)
            
    def filter_services(self):
        """Filter the services list based on text input."""
        filter_text = self.filter_input.text().lower()
        
        for i in range(self.services_list.count()):
            item = self.services_list.item(i)
            service = item.data(QtCore.Qt.UserRole)
            
            # Hide if doesn't match filter
            item.setHidden(
                filter_text not in service.name.lower() and
                filter_text not in service.display_name.lower()
            )
            
    def select_all(self):
        """Select all services."""
        for i in range(self.services_list.count()):
            item = self.services_list.item(i)
            if not item.isHidden():
                item.setSelected(True)
                
    def select_none(self):
        """Deselect all services."""
        self.services_list.clearSelection()
        
    def select_running(self):
        """Select running services."""
        for i in range(self.services_list.count()):
            item = self.services_list.item(i)
            service = item.data(QtCore.Qt.UserRole)
            
            if not item.isHidden() and service.state.lower() == "running":
                item.setSelected(True)
            else:
                item.setSelected(False)
                
    def select_stopped(self):
        """Select stopped services."""
        for i in range(self.services_list.count()):
            item = self.services_list.item(i)
            service = item.data(QtCore.Qt.UserRole)
            
            if not item.isHidden() and service.state.lower() == "stopped":
                item.setSelected(True)
            else:
                item.setSelected(False)
                
    def get_selected_services(self) -> List[ServiceInfo]:
        """Get the list of selected services."""
        selected = []
        
        for item in self.services_list.selectedItems():
            service = item.data(QtCore.Qt.UserRole)
            selected.append(service)
            
        return selected
        
    def get_selected_operation(self) -> str:
        """Get the selected operation."""
        if self.operation_start.isChecked():
            return "start"
        elif self.operation_stop.isChecked():
            return "stop"
        elif self.operation_restart.isChecked():
            return "restart"
        elif self.operation_enable.isChecked():
            return "enable"
        elif self.operation_disable.isChecked():
            return "disable"
        elif self.operation_delete.isChecked():
            return "delete"
        return "start"  # Default
        
    def execute_operations(self):
        """Execute the selected operations on the selected services."""
        selected_services = self.get_selected_services()
        
        if not selected_services:
            QtWidgets.QMessageBox.warning(
                self, "No Services Selected",
                "Please select at least one service."
            )
            return
            
        operation = self.get_selected_operation()
        
        # Check for dangerous operations
        if operation == "delete":
            reply = QtWidgets.QMessageBox.warning(
                self, "Confirm Delete",
                f"Are you sure you want to DELETE {len(selected_services)} services?\n"
                "This action cannot be undone!",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No
            )
            
            if reply != QtWidgets.QMessageBox.Yes:
                return
                
        # Configure progress bar
        self.progress_bar.setVisible(True)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(len(selected_services))
        self.progress_bar.setValue(0)
        
        # Store selected services for the async operation
        self.selected_services = selected_services
        
        # Disable buttons during operation
        self.execute_button.setEnabled(False)
        self.close_button.setEnabled(False)
        
        # Start the async operation
        asyncio.ensure_future(self.run_operations(operation))
        
    async def run_operations(self, operation: str):
        """
        Run the selected operation on all selected services.
        
        Args:
            operation: Operation to perform ('start', 'stop', etc.)
        """
        sequential = self.sequential_check.isChecked()
        confirm_each = self.confirm_each_check.isChecked()
        
        total = len(self.selected_services)
        completed = 0
        success = 0
        
        # Operation functions
        operations = {
            'start': self.service_manager.start_service,
            'stop': self.service_manager.stop_service,
            'restart': self.service_manager.restart_service,
            'delete': self.service_manager.remove_service
        }
        
        if sequential:
            # Process services one by one
            for service in self.selected_services:
                if confirm_each:
                    # Run in the main thread
                    reply = QtWidgets.QMessageBox.question(
                        self, f"Confirm {operation.capitalize()}",
                        f"Do you want to {operation} service '{service.name}'?",
                        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                        QtWidgets.QMessageBox.Yes
                    )
                    
                    if reply != QtWidgets.QMessageBox.Yes:
                        completed += 1
                        self.progress_bar.setValue(completed)
                        self.status_label.setText(f"Skipped {service.name}... ({completed}/{total})")
                        continue
                        
                try:
                    self.status_label.setText(f"Processing {service.name}... ({completed+1}/{total})")
                    
                    if operation in operations:
                        result = await operations[operation](service.name)
                    else:
                        # Handle operations that need different implementation
                        result = await self._handle_special_operation(operation, service.name)
                        
                    if result:
                        success += 1
                except Exception as e:
                    logger.error(f"Error performing {operation} on {service.name}: {str(e)}")
                    
                completed += 1
                self.progress_bar.setValue(completed)
        else:
            # Process all services at once
            if confirm_each:
                reply = QtWidgets.QMessageBox.question(
                    self, f"Confirm {operation.capitalize()}",
                    f"Do you want to {operation} {total} services?",
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                    QtWidgets.QMessageBox.Yes
                )
                
                if reply != QtWidgets.QMessageBox.Yes:
                    self.finish_operations(0, total)
                    return
                    
            self.status_label.setText(f"Processing {total} services...")
            
            tasks = []
            for service in self.selected_services:
                if operation in operations:
                    task = asyncio.ensure_future(operations[operation](service.name))
                else:
                    task = asyncio.ensure_future(self._handle_special_operation(operation, service.name))
                    
                tasks.append(task)
                
            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                completed += 1
                self.progress_bar.setValue(completed)
                
                if result is True:
                    success += 1
                    
        # Operation complete
        self.finish_operations(success, total)
        
    async def _handle_special_operation(self, operation: str, service_name: str) -> bool:
        """
        Handle operations that need special implementation.
        
        Args:
            operation: Operation type ('enable', 'disable', etc.)
            service_name: Name of the service
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if operation == 'enable':
                # Run SC command to enable the service
                process = await asyncio.create_subprocess_exec(
                    'sc', 'config', service_name, 'start=', 'auto',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.communicate()
                return process.returncode == 0
            elif operation == 'disable':
                # Run SC command to disable the service
                process = await asyncio.create_subprocess_exec(
                    'sc', 'config', service_name, 'start=', 'disabled',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.communicate()
                return process.returncode == 0
            else:
                logger.warning(f"Unknown operation: {operation}")
                return False
        except Exception as e:
            logger.error(f"Error in _handle_special_operation: {str(e)}")
            return False
            
    def finish_operations(self, success_count: int, total_count: int):
        """
        Finish the batch operations and update the UI.
        
        Args:
            success_count: Number of successful operations
            total_count: Total number of operations
        """
        self.status_label.setText(
            f"Operation complete. {success_count} of {total_count} services processed successfully."
        )
        
        # Re-enable buttons
        self.execute_button.setEnabled(True)
        self.close_button.setEnabled(True)
        
        # Signal the parent to refresh services
        self.accept()