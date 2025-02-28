import pytest
import os
import sys
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from PyQt5 import QtWidgets, QtCore, QtTest
from PyQt5.QtCore import Qt

from nssm_gui.models import ServiceConfig, ServiceInfo
from nssm_gui.ui.main_window import NSSmGUI, ServiceTableModel


# Fixture for QApplication
@pytest.fixture
def qapp():
    """Fixture that creates a Qt application."""
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    yield app
    app.quit()

# Fixture for AsyncHelper
@pytest.fixture
def async_helper():
    """Fixture that creates a mock AsyncHelper."""
    helper = MagicMock()
    helper.run = MagicMock()
    return helper

# Fixture for services
@pytest.fixture
def services():
    """Fixture that creates a list of test services."""
    return [
        ServiceInfo(
            name="service1",
            display_name="Service 1",
            state="Running",
            pid=1234,
            path="C:\\path\\to\\service1.exe"
        ),
        ServiceInfo(
            name="service2",
            display_name="Service 2",
            state="Stopped",
            pid=None,
            path="C:\\path\\to\\service2.exe"
        )
    ]

# Fixture for the main window
@pytest.fixture
def main_window(qapp, async_helper):
    """Fixture that creates the main window with mocks."""
    # Mock NSSmManager
    with patch('nssm_gui.service_manager.NSSmManager') as mock_manager_class:
        # Create a mock manager instance
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        
        # Create the main window
        window = NSSmGUI('C:\\path\\to\\nssm.exe', async_helper)
        
        # Replace the refresh timer with a mock
        window.refresh_timer = MagicMock()
        
        # Yield for tests to use
        yield window

class TestServiceTableModel:
    """Test cases for the ServiceTableModel class."""
    
    @pytest.fixture
    def model(self, services):
        """Fixture that creates a ServiceTableModel with test services."""
        return ServiceTableModel(services)
    
    def test_row_count(self, model, services):
        """Test rowCount method."""
        assert model.rowCount() == len(services)
        
    def test_column_count(self, model):
        """Test columnCount method."""
        assert model.columnCount() == 4  # name, display_name, state, pid
        
    def test_data(self, model, services):
        """Test data method."""
        # Test valid index, display role
        for row, service in enumerate(services):
            # Test service name
            index = model.index(row, 0)
            assert model.data(index, Qt.DisplayRole) == service.name
            
            # Test display name
            index = model.index(row, 1)
            assert model.data(index, Qt.DisplayRole) == service.display_name
            
            # Test state
            index = model.index(row, 2)
            assert model.data(index, Qt.DisplayRole) == service.state
            
            # Test PID
            index = model.index(row, 3)
            assert model.data(index, Qt.DisplayRole) == str(service.pid) if service.pid else ""
            
        # Test background role
        # Running service should have green background
        index = model.index(0, 0)  # First service is running
        bg_color = model.data(index, Qt.BackgroundRole)
        assert bg_color is not None
        assert bg_color.red() < bg_color.green()  # Green component should be higher
        
        # Stopped service should have red background
        index = model.index(1, 0)  # Second service is stopped
        bg_color = model.data(index, Qt.BackgroundRole)
        assert bg_color is not None
        assert bg_color.red() > bg_color.green()  # Red component should be higher
        
    def test_header_data(self, model):
        """Test headerData method."""
        headers = ["Service Name", "Display Name", "State", "PID"]
        for col, header in enumerate(headers):
            assert model.headerData(col, Qt.Horizontal, Qt.DisplayRole) == header
            
    def test_update_services(self, model):
        """Test updateServices method."""
        # Create new services
        new_services = [
            ServiceInfo(name="new_service", display_name="New Service", state="Running")
        ]
        
        # Update the model
        model.update_services(new_services)
        
        # Check that model was updated
        assert model.rowCount() == 1
        assert model.data(model.index(0, 0), Qt.DisplayRole) == "new_service"
        
    def test_get_service(self, model, services):
        """Test getService method."""
        # Get existing service
        service = model.get_service(0)
        assert service is services[0]
        
        # Get non-existent service
        service = model.get_service(99)
        assert service is None

class TestNSSmGUI:
    """Test cases for the NSSmGUI class."""
    
    def test_init(self, main_window):
        """Test constructor."""
        assert main_window.nssm_path == 'C:\\path\\to\\nssm.exe'
        assert main_window.service_manager is not None
        assert main_window.async_helper is not None
        
    def test_init_ui(self, main_window):
        """Test initUI method created all UI elements."""
        # Check main UI components
        assert main_window.central_widget is not None
        assert main_window.service_table is not None
        assert main_window.table_model is not None
        assert main_window.details_group is not None
        assert main_window.filter_input is not None
        
        # Check buttons
        assert main_window.add_button is not None
        assert main_window.edit_button is not None
        assert main_window.delete_button is not None
        assert main_window.start_button is not None
        assert main_window.stop_button is not None
        assert main_window.restart_button is not None
        assert main_window.logs_button is not None
        assert main_window.refresh_button is not None
        
    def test_refresh_services(self, main_window):
        """Test refreshServices method."""
        # Call refresh_services
        main_window.refresh_services()
        
        # Check that async_helper.run was called
        main_window.async_helper.run.assert_called_once()
        args, kwargs = main_window.async_helper.run.call_args
        assert asyncio.iscoroutine(args[0])  # First arg should be a coroutine
        assert kwargs.get('callback') == main_window.refresh_callback
        
    def test_refresh_callback(self, main_window):
        """Test refreshCallback method."""
        # Set up a mock cursor
        with patch('PyQt5.QtWidgets.QApplication.overrideCursor', return_value=True):
            with patch('PyQt5.QtWidgets.QApplication.restoreOverrideCursor') as mock_restore:
                # Test successful refresh
                main_window.refresh_callback(True, None)
                mock_restore.assert_called_once()
                
                # Reset mock
                mock_restore.reset_mock()
                
                # Test failed refresh
                with patch('PyQt5.QtWidgets.QMessageBox.warning') as mock_warning:
                    main_window.refresh_callback(False, Exception("Test error"))
                    mock_restore.assert_called_once()
                    mock_warning.assert_called_once()
                    
    def test_add_service(self, main_window):
        """Test addService method."""
        # Mock the AddServiceDialog
        with patch('nssm_gui.ui.main_window.AddServiceDialog') as mock_dialog_class:
            # Set up the mock dialog
            mock_dialog = MagicMock()
            mock_dialog_class.return_value = mock_dialog
            mock_dialog.exec_.return_value = QtWidgets.QDialog.Accepted
            
            # Create a test config
            test_config = ServiceConfig(service_name="test_service")
            mock_dialog.get_service_config.return_value = test_config
            
            # Call add_service
            main_window.add_service()
            
            # Check that dialog was created and shown
            mock_dialog_class.assert_called_once()
            mock_dialog.exec_.assert_called_once()
            
            # Check that async_helper.run was called
            main_window.async_helper.run.assert_called_once()
            
    def test_add_service_callback(self, main_window):
        """Test addServiceCallback method."""
        # Set up a mock cursor
        with patch('PyQt5.QtWidgets.QApplication.overrideCursor', return_value=True):
            with patch('PyQt5.QtWidgets.QApplication.restoreOverrideCursor') as mock_restore:
                # Mock QMessageBox
                with patch('PyQt5.QtWidgets.QMessageBox.information') as mock_info:
                    with patch('PyQt5.QtWidgets.QMessageBox.critical') as mock_critical:
                        # Test successful add
                        with patch.object(main_window, 'refresh_services') as mock_refresh:
                            main_window.add_service_callback(True, None, "test_service")
                            mock_restore.assert_called_once()
                            mock_info.assert_called_once()
                            mock_refresh.assert_called_once()
                            mock_critical.assert_not_called()
                            
                            # Reset mocks
                            mock_restore.reset_mock()
                            mock_info.reset_mock()
                            mock_refresh.reset_mock()
                            
                            # Test failed add
                            main_window.add_service_callback(False, Exception("Test error"), "test_service")
                            mock_restore.assert_called_once()
                            mock_critical.assert_called_once()
                            mock_info.assert_not_called()
                            mock_refresh.assert_not_called()
                            
    def test_apply_filter(self, main_window, services):
        """Test applyFilter method."""
        # Set up the model with test services
        main_window.table_model.update_services(services)
        
        # Mock QSortFilterProxyModel
        with patch('PyQt5.QtCore.QSortFilterProxyModel') as mock_proxy_class:
            # Set up the mock proxy
            mock_proxy = MagicMock()
            mock_proxy_class.return_value = mock_proxy
            
            # Test text filter
            main_window.filter_input.setText("service1")
            main_window.apply_filter()
            
            # Check that proxy was created and configured
            mock_proxy_class.assert_called_once()
            mock_proxy.setSourceModel.assert_called_once_with(main_window.table_model)
            mock_proxy.setFilterCaseSensitivity.assert_called_once_with(Qt.CaseInsensitive)
            mock_proxy.setFilterKeyColumn.assert_called_once_with(0)
            mock_proxy.setFilterRegExp.assert_called_once_with("service1")
            
            # Check that proxy was set on the table
            main_window.service_table.setModel.assert_called_once_with(mock_proxy)
            
    def test_get_selected_service(self, main_window, services):
        """Test getSelectedService method."""
        # Set up the model with test services
        main_window.table_model.update_services(services)
        
        # Mock selection model
        mock_selection = MagicMock()
        main_window.service_table.selectionModel = MagicMock(return_value=mock_selection)
        
        # Test no selection
        mock_selection.hasSelection.return_value = False
        assert main_window.get_selected_service() is None
        
        # Test with selection
        mock_selection.hasSelection.return_value = True
        mock_selection.selectedRows.return_value = [MagicMock(row=MagicMock(return_value=0))]
        service = main_window.get_selected_service()
        assert service is services[0]
        
    def test_update_service_details(self, main_window, services):
        """Test updateServiceDetails method."""
        # Set up the model with test services
        main_window.table_model.update_services(services)
        
        # Create mock selected indexes
        mock_selected = MagicMock()
        mock_index = MagicMock()
        mock_index.row.return_value = 0
        mock_selected.indexes.return_value = [mock_index]
        
        mock_deselected = MagicMock()
        mock_deselected.indexes.return_value = []
        
        # Call updateServiceDetails
        main_window.update_service_details(mock_selected, mock_deselected)
        
        # Check that details were updated
        assert main_window.detail_name.text() == services[0].name
        assert main_window.detail_display_name.text() == services[0].display_name
        assert main_window.detail_state.text() == services[0].state
        assert main_window.detail_path.text() == services[0].path
        
        # Check button state
        assert main_window.start_button.isEnabled() == False  # Service is running
        assert main_window.stop_button.isEnabled() == True    # Service is running
        assert main_window.restart_button.isEnabled() == True # Service is running
        
    def test_clear_service_details(self, main_window):
        """Test clearServiceDetails method."""
        # Set some initial values
        main_window.detail_name.setText("test")
        main_window.detail_display_name.setText("test")
        main_window.detail_state.setText("test")
        main_window.detail_path.setText("test")
        
        # Enable buttons
        main_window.start_button.setEnabled(True)
        main_window.stop_button.setEnabled(True)
        main_window.restart_button.setEnabled(True)
        main_window.edit_button.setEnabled(True)
        main_window.delete_button.setEnabled(True)
        main_window.logs_button.setEnabled(True)
        
        # Call clearServiceDetails
        main_window.clear_service_details()
        
        # Check that details were cleared
        assert main_window.detail_name.text() == ""
        assert main_window.detail_display_name.text() == ""
        assert main_window.detail_state.text() == ""
        assert main_window.detail_path.text() == ""
        
        # Check that buttons were disabled
        assert not main_window.start_button.isEnabled()
        assert not main_window.stop_button.isEnabled()
        assert not main_window.restart_button.isEnabled()
        assert not main_window.edit_button.isEnabled()
        assert not main_window.delete_button.isEnabled()
        assert not main_window.logs_button.isEnabled()
        
    def test_toggle_auto_refresh(self, main_window):
        """Test toggleAutoRefresh method."""
        # Test enabling auto-refresh
        main_window.toggle_auto_refresh(Qt.Checked)
        main_window.refresh_timer.start.assert_called_once()
        
        # Reset mock
        main_window.refresh_timer.start.reset_mock()
        
        # Test disabling auto-refresh
        main_window.toggle_auto_refresh(Qt.Unchecked)
        main_window.refresh_timer.stop.assert_called_once()
        
    def test_apply_preferences(self, main_window):
        """Test applyPreferences method."""
        # Set test preferences
        main_window.preferences = {
            'auto_refresh': True,
            'refresh_interval': 10000,
            'dark_mode': True,
            'show_details_panel': False
        }
        
        # Mock methods
        with patch.object(main_window, 'apply_dark_mode') as mock_dark_mode:
            with patch.object(main_window, 'apply_light_mode') as mock_light_mode:
                # Call applyPreferences
                main_window.apply_preferences()
                
                # Check auto-refresh
                assert main_window.auto_refresh_check.isChecked() == True
                main_window.refresh_timer.start.assert_called_with(10000)
                
                # Check dark mode
                mock_dark_mode.assert_called_once()
                mock_light_mode.assert_not_called()
                
                # Check details panel
                assert main_window.details_group.isVisible() == False
                
                # Reset mocks
                mock_dark_mode.reset_mock()
                mock_light_mode.reset_mock()
                main_window.refresh_timer.start.reset_mock()
                
                # Test with different preferences
                main_window.preferences = {
                    'auto_refresh': False,
                    'dark_mode': False,
                    'show_details_panel': True
                }
                
                # Call applyPreferences again
                main_window.apply_preferences()
                
                # Check auto-refresh
                assert main_window.auto_refresh_check.isChecked() == False
                main_window.refresh_timer.stop.assert_called_once()
                
                # Check dark mode
                mock_dark_mode.assert_not_called()
                mock_light_mode.assert_called_once()
                
                # Check details panel
                assert main_window.details_group.isVisible() == True
                
    @pytest.mark.asyncio
    async def test_async_refresh_services(self, main_window, services):
        """Test asyncRefreshServices method."""
        # Mock service_manager.get_services
        main_window.service_manager.get_services = AsyncMock(return_value=services)
        
        # Call asyncRefreshServices
        result = await main_window.async_refresh_services()
        
        # Check that get_services was called
        main_window.service_manager.get_services.assert_called_once()
        
        # Check that table model was updated
        assert main_window.table_model.services == services
        
        # Check result
        assert result is True
        
        # Test error handling
        main_window.service_manager.get_services.reset_mock()
        main_window.service_manager.get_services.side_effect = Exception("Test error")
        
        # Call asyncRefreshServices again
        result = await main_window.async_refresh_services()
        
        # Check result
        assert result is False