from PyQt5 import QtWidgets, QtGui, QtCore
import json
import os
from typing import Dict, Any, Optional
import logging

from ..models import ServiceConfig
from .dialogs import AddServiceDialog

logger = logging.getLogger("nssm_gui.templates")

class TemplateManagerDialog(QtWidgets.QDialog):
    """Dialog for managing service templates."""
    
    def __init__(self, parent=None, config_manager=None):
        super().__init__(parent)
        self.setWindowTitle('Service Templates')
        self.setGeometry(100, 100, 800, 600)
        
        self.config_manager = config_manager
        self.templates = {}
        self.current_template = None
        
        self.init_ui()
        self.load_templates()
        
    def init_ui(self):
        """Initialize the UI components."""
        layout = QtWidgets.QVBoxLayout(self)
        
        # Instructions
        instructions = QtWidgets.QLabel(
            "Service templates allow you to save and reuse service configurations. "
            "Create templates from existing services or build them from scratch."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Templates list and details
        split_layout = QtWidgets.QHBoxLayout()
        
        # Templates list
        templates_group = QtWidgets.QGroupBox("Templates")
        templates_layout = QtWidgets.QVBoxLayout()
        
        self.templates_list = QtWidgets.QListWidget()
        self.templates_list.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.templates_list.currentItemChanged.connect(self.template_selected)
        
        templates_buttons_layout = QtWidgets.QHBoxLayout()
        
        self.new_template_button = QtWidgets.QPushButton("New")
        self.import_template_button = QtWidgets.QPushButton("Import")
        self.export_template_button = QtWidgets.QPushButton("Export")
        self.delete_template_button = QtWidgets.QPushButton("Delete")
        
        self.new_template_button.clicked.connect(self.create_new_template)
        self.import_template_button.clicked.connect(self.import_template)
        self.export_template_button.clicked.connect(self.export_template)
        self.delete_template_button.clicked.connect(self.delete_template)
        
        templates_buttons_layout.addWidget(self.new_template_button)
        templates_buttons_layout.addWidget(self.import_template_button)
        templates_buttons_layout.addWidget(self.export_template_button)
        templates_buttons_layout.addWidget(self.delete_template_button)
        
        templates_layout.addWidget(self.templates_list)
        templates_layout.addLayout(templates_buttons_layout)
        
        templates_group.setLayout(templates_layout)
        
        # Template details
        details_group = QtWidgets.QGroupBox("Template Details")
        details_layout = QtWidgets.QVBoxLayout()
        
        name_layout = QtWidgets.QHBoxLayout()
        name_label = QtWidgets.QLabel("Name:")
        self.name_input = QtWidgets.QLineEdit()
        self.name_input.setPlaceholderText("Template name")
        
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_input)
        
        # Details table
        self.details_table = QtWidgets.QTableWidget()
        self.details_table.setColumnCount(2)
        self.details_table.setHorizontalHeaderLabels(['Setting', 'Value'])
        self.details_table.horizontalHeader().setStretchLastSection(True)
        self.details_table.verticalHeader().setVisible(False)
        self.details_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        
        # Save/Edit buttons
        details_buttons_layout = QtWidgets.QHBoxLayout()
        
        self.save_button = QtWidgets.QPushButton("Save Changes")
        self.edit_button = QtWidgets.QPushButton("Edit Template")
        self.use_button = QtWidgets.QPushButton("Use Template")
        
        self.save_button.clicked.connect(self.save_template)
        self.edit_button.clicked.connect(self.edit_template)
        self.use_button.clicked.connect(self.use_template)
        
        details_buttons_layout.addWidget(self.save_button)
        details_buttons_layout.addWidget(self.edit_button)
        details_buttons_layout.addWidget(self.use_button)
        
        details_layout.addLayout(name_layout)
        details_layout.addWidget(self.details_table)
        details_layout.addLayout(details_buttons_layout)
        
        details_group.setLayout(details_layout)
        
        # Add to split layout
        split_layout.addWidget(templates_group, 1)
        split_layout.addWidget(details_group, 2)
        
        layout.addLayout(split_layout)
        
        # Bottom buttons
        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Close)
        button_box.rejected.connect(self.reject)
        
        layout.addWidget(button_box)
        
        # Initial state
        self.update_details_ui(enabled=False)
        
    def update_details_ui(self, enabled=True):
        """Enable or disable the details UI."""
        self.name_input.setEnabled(enabled)
        self.details_table.setEnabled(enabled)
        self.save_button.setEnabled(enabled)
        self.edit_button.setEnabled(enabled)
        self.use_button.setEnabled(enabled)
        self.export_template_button.setEnabled(enabled)
        self.delete_template_button.setEnabled(enabled)
        
    def load_templates(self):
        """Load templates from the configuration manager."""
        if not self.config_manager:
            return
            
        try:
            self.templates = self.config_manager.get_all_templates()
            
            # Clear and repopulate the list
            self.templates_list.clear()
            
            for name in sorted(self.templates.keys()):
                item = QtWidgets.QListWidgetItem(name)
                self.templates_list.addItem(item)
                
            if self.templates_list.count() > 0:
                self.templates_list.setCurrentRow(0)
            else:
                self.update_details_ui(enabled=False)
                
        except Exception as e:
            logger.error(f"Error loading templates: {str(e)}")
            QtWidgets.QMessageBox.critical(
                self, "Error", f"Failed to load templates: {str(e)}"
            )
            
    def template_selected(self, current, previous):
        """Handle selection of a template from the list."""
        if not current:
            self.current_template = None
            self.update_details_ui(enabled=False)
            return
            
        template_name = current.text()
        template_data = self.templates.get(template_name, {})
        
        self.current_template = template_name
        self.name_input.setText(template_name)
        
        # Update details table
        self.populate_details_table(template_data)
        
        # Enable UI
        self.update_details_ui(enabled=True)
        
    def populate_details_table(self, template_data: Dict[str, Any]):
        """Populate the details table with template settings."""
        self.details_table.setRowCount(0)
        
        # Filter out empty values and non-user-friendly fields
        excluded_keys = {
            'service_name',  # This is set when using the template
            'env_variables',  # Complex structure
            'dependencies',   # Complex structure
            'hooks'           # Complex structure
        }
        
        # Add main settings
        for key, value in template_data.items():
            if key in excluded_keys or value is None or (isinstance(value, (list, dict)) and not value):
                continue
                
            row = self.details_table.rowCount()
            self.details_table.insertRow(row)
            
            # Format the key for display
            display_key = key.replace('_', ' ').title()
            
            # Format the value for display
            if isinstance(value, bool):
                display_value = "Yes" if value else "No"
            elif isinstance(value, (list, dict)):
                display_value = f"{len(value)} items"
            else:
                display_value = str(value)
                
            self.details_table.setItem(row, 0, QtWidgets.QTableWidgetItem(display_key))
            self.details_table.setItem(row, 1, QtWidgets.QTableWidgetItem(display_value))
            
        # Add the complex items
        self.add_complex_items(template_data)
        
        # Resize columns to content
        self.details_table.resizeColumnsToContents()
        
    def add_complex_items(self, template_data: Dict[str, Any]):
        """Add complex items to the details table."""
        # Environment Variables
        env_vars = template_data.get('env_variables', {})
        if env_vars:
            row = self.details_table.rowCount()
            self.details_table.insertRow(row)
            self.details_table.setItem(row, 0, QtWidgets.QTableWidgetItem("Environment Variables"))
            self.details_table.setItem(row, 1, QtWidgets.QTableWidgetItem(f"{len(env_vars)} variables"))
            
            # Item is expandable
            item = self.details_table.item(row, 0)
            font = item.font()
            font.setBold(True)
            item.setFont(font)
            
        # Dependencies
        dependencies = template_data.get('dependencies', [])
        if dependencies:
            row = self.details_table.rowCount()
            self.details_table.insertRow(row)
            self.details_table.setItem(row, 0, QtWidgets.QTableWidgetItem("Dependencies"))
            self.details_table.setItem(row, 1, QtWidgets.QTableWidgetItem(f"{len(dependencies)} services"))
            
            # Item is expandable
            item = self.details_table.item(row, 0)
            font = item.font()
            font.setBold(True)
            item.setFont(font)
            
        # Hooks
        hooks = template_data.get('hooks', {})
        if hooks:
            row = self.details_table.rowCount()
            self.details_table.insertRow(row)
            self.details_table.setItem(row, 0, QtWidgets.QTableWidgetItem("Hooks"))
            self.details_table.setItem(row, 1, QtWidgets.QTableWidgetItem(f"{len(hooks)} hooks"))
            
            # Item is expandable
            item = self.details_table.item(row, 0)
            font = item.font()
            font.setBold(True)
            item.setFont(font)
            
    def create_new_template(self):
        """Create a new template from scratch."""
        # Create a new empty service config
        config = ServiceConfig()
        
        # Show dialog to edit the config
        dialog = AddServiceDialog(self, existing_config=config)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            config = dialog.get_service_config()
            if config:
                # Ask for template name
                name, ok = QtWidgets.QInputDialog.getText(
                    self, "Template Name", "Enter a name for this template:"
                )
                
                if ok and name:
                    # Save the template
                    self.save_template_to_config(name, config.model_dump())
                    
    def import_template(self):
        """Import a template from a file."""
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Import Template", "", "JSON Files (*.json);;All Files (*)"
        )
        
        if not file_path:
            return
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                template_data = json.load(f)
                
            # Validate template data
            ServiceConfig(**template_data)
            
            # Ask for template name
            name, ok = QtWidgets.QInputDialog.getText(
                self, "Template Name", "Enter a name for this template:",
                text=os.path.splitext(os.path.basename(file_path))[0]
            )
            
            if ok and name:
                # Save the template
                self.save_template_to_config(name, template_data)
                
        except Exception as e:
            logger.error(f"Error importing template: {str(e)}")
            QtWidgets.QMessageBox.critical(
                self, "Import Error", f"Failed to import template: {str(e)}"
            )
            
    def export_template(self):
        """Export the selected template to a file."""
        if not self.current_template:
            return
            
        template_data = self.templates.get(self.current_template, {})
        
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export Template", f"{self.current_template}.json",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if not file_path:
            return
            
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(template_data, f, indent=4)
                
            QtWidgets.QMessageBox.information(
                self, "Export Successful",
                f"Template exported to {file_path}"
            )
            
        except Exception as e:
            logger.error(f"Error exporting template: {str(e)}")
            QtWidgets.QMessageBox.critical(
                self, "Export Error", f"Failed to export template: {str(e)}"
            )
            
    def delete_template(self):
        """Delete the selected template."""
        if not self.current_template:
            return
            
        reply = QtWidgets.QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete the template '{self.current_template}'?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )
        
        if reply != QtWidgets.QMessageBox.Yes:
            return
            
        # Delete from config manager
        if self.config_manager:
            success = self.config_manager.delete_template(self.current_template)
            
            if success:
                # Remove from the list
                item = self.templates_list.currentItem()
                self.templates_list.takeItem(self.templates_list.row(item))
                
                # Clear current template
                self.current_template = None
                
                # Update UI
                self.update_details_ui(enabled=False)
                
                # Clear details
                self.name_input.clear()
                self.details_table.setRowCount(0)
                
                # Reload templates
                self.load_templates()
                
    def save_template(self):
        """Save changes to the current template."""
        if not self.current_template:
            return
            
        # Get the new name
        new_name = self.name_input.text().strip()
        
        if not new_name:
            QtWidgets.QMessageBox.warning(
                self, "Invalid Name", "Template name cannot be empty."
            )
            return
            
        # Get the template data
        template_data = self.templates.get(self.current_template, {})
        
        # If name changed, delete old template
        if new_name != self.current_template:
            self.config_manager.delete_template(self.current_template)
            
        # Save the template with new name
        self.save_template_to_config(new_name, template_data)
        
    def edit_template(self):
        """Edit the selected template."""
        if not self.current_template:
            return
            
        template_data = self.templates.get(self.current_template, {})
        
        try:
            # Create a ServiceConfig object from the template data
            config = ServiceConfig(**template_data)
            
            # Show dialog to edit the config
            dialog = AddServiceDialog(self, existing_config=config)
            if dialog.exec_() == QtWidgets.QDialog.Accepted:
                config = dialog.get_service_config()
                if config:
                    # Save the template
                    self.save_template_to_config(self.current_template, config.model_dump())
                    
        except Exception as e:
            logger.error(f"Error editing template: {str(e)}")
            QtWidgets.QMessageBox.critical(
                self, "Edit Error", f"Failed to edit template: {str(e)}"
            )
            
    def use_template(self):
        """Use the selected template to create a new service."""
        if not self.current_template:
            return
            
        template_data = self.templates.get(self.current_template, {})
        
        try:
            # Create a ServiceConfig object from the template data
            config = ServiceConfig(**template_data)
            
            # Clear the service name (it will be set by the user)
            config.service_name = ""
            
            # Show dialog to edit the config
            dialog = AddServiceDialog(self, existing_config=config)
            
            if dialog.exec_() == QtWidgets.QDialog.Accepted:
                # Return the service config to the caller
                self.accept()
                
        except Exception as e:
            logger.error(f"Error using template: {str(e)}")
            QtWidgets.QMessageBox.critical(
                self, "Error", f"Failed to use template: {str(e)}"
            )
            
    def save_template_to_config(self, name: str, template_data: Dict[str, Any]):
        """Save a template to the configuration manager."""
        if not self.config_manager:
            return
            
        try:
            success = self.config_manager.save_service_template(name, template_data)
            
            if success:
                # Update the templates dictionary
                self.templates[name] = template_data
                
                # Update the current template
                self.current_template = name
                
                # Reload templates
                self.load_templates()
                
                # Select the new template
                for i in range(self.templates_list.count()):
                    if self.templates_list.item(i).text() == name:
                        self.templates_list.setCurrentRow(i)
                        break
                        
                QtWidgets.QMessageBox.information(
                    self, "Template Saved", f"Template '{name}' saved successfully."
                )
                
        except Exception as e:
            logger.error(f"Error saving template: {str(e)}")
            QtWidgets.QMessageBox.critical(
                self, "Save Error", f"Failed to save template: {str(e)}"
            )