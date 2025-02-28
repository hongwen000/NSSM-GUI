import pytest
import json
import subprocess
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from nssm_gui.service_manager import NSSmManager
from nssm_gui.models import ServiceConfig, ServiceInfo

class TestNSSmManager:
    """Test cases for the NSSmManager class."""

    @pytest.fixture
    def service_manager(self):
        """Fixture to create a service manager for testing."""
        return NSSmManager("C:\\path\\to\\nssm.exe")

    @pytest.mark.asyncio
    @patch("asyncio.get_event_loop")
    @patch("asyncio.new_event_loop")
    @patch("subprocess.run")
    async def test_get_services(self, mock_run, mock_new_loop, mock_get_loop, service_manager):
        """Test getting services."""
        # Mock subprocess.run to return services data
        mock_process = MagicMock()
        mock_process.stdout = json.dumps([
            {
                "Name": "TestService1",
                "DisplayName": "Test Service 1",
                "State": "Running",
                "Status": "OK",
                "ProcessId": 1234,
                "PathName": "C:\\path\\to\\nssm.exe"
            },
            {
                "Name": "TestService2",
                "DisplayName": "Test Service 2",
                "State": "Stopped",
                "Status": "OK",
                "ProcessId": None,
                "PathName": "C:\\path\\to\\nssm.exe"
            }
        ])
        mock_process.returncode = 0
        mock_run.return_value = mock_process

        # Mock the event loop
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(return_value=mock_process)
        mock_get_loop.return_value = mock_loop
        mock_new_loop.return_value = mock_loop

        # Call the function
        services = await service_manager.get_services()

        # Check results
        assert len(services) == 2
        assert services[0].name == "TestService1"
        assert services[0].display_name == "Test Service 1"
        assert services[0].state == "Running"
        assert services[0].pid == 1234
        assert services[0].is_nssm is True

        assert services[1].name == "TestService2"
        assert services[1].state == "Stopped"
        assert services[1].pid is None

    @pytest.mark.asyncio
    @patch("subprocess.run")
    async def test_run_nssm_command(self, mock_run, service_manager):
        """Test running NSSM commands."""
        # Mock subprocess.run to return success
        mock_process = MagicMock()
        mock_process.stdout = b"Command succeeded"
        mock_process.stderr = b""
        mock_process.returncode = 0
        mock_run.return_value = mock_process

        # Call the function
        result = await service_manager.run_nssm_command(["test", "command"])

        # Check results
        assert "Command succeeded" in result
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0][0] == "C:\\path\\to\\nssm.exe"
        assert args[0][1] == "test"
        assert args[0][2] == "command"

    @pytest.mark.asyncio
    @patch("nssm_gui.service_manager.NSSmManager.run_nssm_command")
    async def test_get_service_config(self, mock_run_command, service_manager):
        """Test getting service configuration."""
        # Mock run_nssm_command to return service config
        mock_run_command.return_value = """
        "C:\\path\\to\\nssm.exe" install TestService "C:\\app\\test.exe"
        "C:\\path\\to\\nssm.exe" set TestService AppParameters "--arg1 --arg2"
        "C:\\path\\to\\nssm.exe" set TestService AppDirectory "C:\\temp\\app"
        "C:\\path\\to\\nssm.exe" set TestService DisplayName "Test Service"
        "C:\\path\\to\\nssm.exe" set TestService Description "A test service"
        "C:\\path\\to\\nssm.exe" set TestService Start SERVICE_AUTO_START
        """

        # Call the function
        config = await service_manager.get_service_config("TestService")

        # Check results
        assert config is not None
        assert config.service_name == "TestService"
        assert config.application_path == "C:\\app\\test.exe"
        assert config.arguments == "--arg1 --arg2"
        assert config.app_directory == "C:\\temp\\app"
        assert config.display_name == "Test Service"
        assert config.description == "A test service"
        assert config.start == "SERVICE_AUTO_START"

    @pytest.mark.asyncio
    @patch("nssm_gui.service_manager.NSSmManager.run_nssm_command")
    async def test_configure_service_new(self, mock_run_command, service_manager):
        """Test configuring a new service."""
        # Mock run_nssm_command to return success
        mock_run_command.return_value = "Success"

        # Create a test config
        config = ServiceConfig(
            service_name="TestService",
            application_path="C:\\app\\test.exe",
            arguments="--arg1 --arg2",
            app_directory="C:\\app",
            display_name="Test Service",
            description="A test service"
        )

        # Call the function
        result = await service_manager.configure_service(config, edit=False)

        # Check results
        assert result is True
        assert mock_run_command.call_count > 0
        
        # Check that install command was called
        install_call = mock_run_command.call_args_list[0]
        assert install_call[0][0][0] == "install"
        assert install_call[0][0][1] == "TestService"
        assert install_call[0][0][2] == "C:\\app\\test.exe"

    @pytest.mark.asyncio
    @patch("nssm_gui.service_manager.NSSmManager.run_nssm_command")
    async def test_configure_service_edit(self, mock_run_command, service_manager):
        """Test editing an existing service."""
        # Mock run_nssm_command to return success
        mock_run_command.return_value = "Success"

        # Create a test config
        config = ServiceConfig(
            service_name="TestService",
            application_path="C:\\app\\new.exe",
            arguments="--new-arg",
            display_name="Updated Service"
        )

        # Call the function
        result = await service_manager.configure_service(config, edit=True)

        # Check results
        assert result is True
        assert mock_run_command.call_count > 0
        
        # Check that application was updated
        app_call_found = False
        for call in mock_run_command.call_args_list:
            args = call[0][0]
            if len(args) >= 4 and args[0] == "set" and args[1] == "TestService" and args[2] == "Application":
                app_call_found = True
                assert args[3] == "C:\\app\\new.exe"
                break
                
        assert app_call_found, "Application update call not found"
        
    @pytest.mark.asyncio
    @patch("nssm_gui.service_manager.NSSmManager.run_nssm_command")
    async def test_remove_service(self, mock_run_command, service_manager):
        """Test removing a service."""
        # Mock run_nssm_command to return success
        mock_run_command.return_value = "Success"

        # Call the function
        result = await service_manager.remove_service("TestService")

        # Check results
        assert result is True
        assert mock_run_command.call_count == 2  # stop + remove
        
        # Check that stop command was called first
        stop_call = mock_run_command.call_args_list[0]
        assert stop_call[0][0][0] == "stop"
        assert stop_call[0][0][1] == "TestService"
        
        # Check that remove command was called second
        remove_call = mock_run_command.call_args_list[1]
        assert remove_call[0][0][0] == "remove"
        assert remove_call[0][0][1] == "TestService"
        assert remove_call[0][0][2] == "confirm"

    @pytest.mark.asyncio
    @patch("nssm_gui.service_manager.NSSmManager.run_nssm_command")
    async def test_start_service(self, mock_run_command, service_manager):
        """Test starting a service."""
        # Mock run_nssm_command to return success
        mock_run_command.return_value = "Success"

        # Call the function
        result = await service_manager.start_service("TestService")

        # Check results
        assert result is True
        mock_run_command.assert_called_once_with(["start", "TestService"])

    @pytest.mark.asyncio
    @patch("nssm_gui.service_manager.NSSmManager.run_nssm_command")
    async def test_stop_service(self, mock_run_command, service_manager):
        """Test stopping a service."""
        # Mock run_nssm_command to return success
        mock_run_command.return_value = "Success"

        # Call the function
        result = await service_manager.stop_service("TestService")

        # Check results
        assert result is True
        mock_run_command.assert_called_once_with(["stop", "TestService"])

    @pytest.mark.asyncio
    @patch("nssm_gui.service_manager.NSSmManager.stop_service")
    @patch("nssm_gui.service_manager.NSSmManager.start_service")
    async def test_restart_service(self, mock_start, mock_stop, service_manager):
        """Test restarting a service."""
        # Mock start and stop to return success
        mock_stop.return_value = True
        mock_start.return_value = True

        # Call the function
        result = await service_manager.restart_service("TestService")

        # Check results
        assert result is True
        mock_stop.assert_called_once_with("TestService")
        mock_start.assert_called_once_with("TestService")

    @pytest.mark.asyncio
    @patch("subprocess.run")
    async def test_get_service_status(self, mock_run, service_manager):
        """Test getting service status."""
        # Mock subprocess.run to return status
        mock_process = MagicMock()
        mock_process.stdout = """
        SERVICE_NAME: TestService
                TYPE               : 10  WIN32_OWN_PROCESS
                STATE              : 4  RUNNING
                                        (STOPPABLE, NOT_PAUSABLE, ACCEPTS_SHUTDOWN)
                WIN32_EXIT_CODE    : 0  (0x0)
                SERVICE_EXIT_CODE  : 0  (0x0)
                CHECKPOINT         : 0x0
                WAIT_HINT          : 0x0
        """
        mock_process.returncode = 0
        mock_run.return_value = mock_process

        # Call the function
        status = await service_manager.get_service_status("TestService")

        # Check results
        assert status == "RUNNING"
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0][0] == "sc"
        assert args[0][1] == "query"
        assert args[0][2] == "TestService"