import pytest
import os
from pydantic import ValidationError
from nssm_gui.models import ServiceConfig, ServiceInfo

class TestServiceConfig:
    """Test cases for the ServiceConfig model."""
    
    def test_default_constructor(self):
        """Test default constructor creates a valid instance."""
        config = ServiceConfig()
        assert config.service_name == ""
        assert config.application_path == ""
        assert config.start == "SERVICE_AUTO_START"
        assert config.process_priority == "NORMAL_PRIORITY_CLASS"
        assert isinstance(config.dependencies, list)
        assert isinstance(config.env_variables, dict)
        
    def test_custom_constructor(self):
        """Test constructor with custom values."""
        config = ServiceConfig(
            service_name="test-service",
            application_path="C:\\test.exe",
            arguments="--arg1 --arg2",
            app_directory="C:\\",
            display_name="Test Service",
            description="A test service",
            start="SERVICE_DEMAND_START"
        )
        
        assert config.service_name == "test-service"
        assert config.application_path == "C:\\test.exe"
        assert config.arguments == "--arg1 --arg2"
        assert config.app_directory == "C:\\"
        assert config.display_name == "Test Service"
        assert config.description == "A test service"
        assert config.start == "SERVICE_DEMAND_START"
        
    def test_service_name_validation(self):
        """Test service name validation."""
        # Valid names
        for name in ["valid-name", "valid_name", "valid.name", "valid123"]:
            config = ServiceConfig(service_name=name)
            assert config.service_name == name
            
        # Invalid names
        for name in ["invalid name", "invalid/name", "invalid\\name", "invalid$name"]:
            with pytest.raises(ValidationError):
                ServiceConfig(service_name=name)
                
    def test_start_value_validation(self):
        """Test validation of start values."""
        # Valid values
        valid_values = [
            "SERVICE_AUTO_START",
            "SERVICE_DELAYED_AUTO_START",
            "SERVICE_DEMAND_START",
            "SERVICE_DISABLED"
        ]
        
        for value in valid_values:
            config = ServiceConfig(start=value)
            assert config.start == value
            
        # Invalid value
        with pytest.raises(ValidationError):
            ServiceConfig(start="INVALID_VALUE")
            
    def test_process_priority_validation(self):
        """Test validation of process priority values."""
        # Valid values
        valid_values = [
            "REALTIME_PRIORITY_CLASS",
            "HIGH_PRIORITY_CLASS",
            "ABOVE_NORMAL_PRIORITY_CLASS",
            "NORMAL_PRIORITY_CLASS",
            "BELOW_NORMAL_PRIORITY_CLASS",
            "IDLE_PRIORITY_CLASS"
        ]
        
        for value in valid_values:
            config = ServiceConfig(process_priority=value)
            assert config.process_priority == value
            
        # Invalid value
        with pytest.raises(ValidationError):
            ServiceConfig(process_priority="INVALID_PRIORITY")
            
    def test_object_name_validation(self):
        """Test validation of object name values."""
        # Valid values
        valid_values = [
            "LocalSystem",
            "LocalService",
            "NetworkService",
            "DOMAIN\\User"
        ]
        
        for value in valid_values:
            config = ServiceConfig(object_name=value)
            assert config.object_name == value
            
        # Invalid values
        invalid_values = [
            "InvalidName",
            "\\NoUser",
            "Domain\\"
        ]
        
        for value in invalid_values:
            with pytest.raises(ValidationError):
                ServiceConfig(object_name=value)
                
    def test_model_export(self):
        """Test model can be properly exported to dict."""
        config = ServiceConfig(
            service_name="test-service",
            application_path="C:\\test.exe",
            arguments="--arg1 --arg2"
        )
        
        data = config.model_dump()
        assert isinstance(data, dict)
        assert data["service_name"] == "test-service"
        assert data["application_path"] == "C:\\test.exe"
        assert data["arguments"] == "--arg1 --arg2"
        
class TestServiceInfo:
    """Test cases for the ServiceInfo model."""
    
    def test_default_constructor(self):
        """Test default constructor creates a valid instance."""
        info = ServiceInfo(name="test-service")
        assert info.name == "test-service"
        assert info.display_name == ""
        assert info.state == "Unknown"
        assert info.status == "Unknown"
        assert info.pid is None
        assert info.is_nssm is False
        assert info.path == ""
        
    def test_custom_constructor(self):
        """Test constructor with custom values."""
        info = ServiceInfo(
            name="test-service",
            display_name="Test Service",
            state="Running",
            status="Started",
            pid=1234,
            is_nssm=True,
            path="C:\\nssm.exe"
        )
        
        assert info.name == "test-service"
        assert info.display_name == "Test Service"
        assert info.state == "Running"
        assert info.status == "Started"
        assert info.pid == 1234
        assert info.is_nssm is True
        assert info.path == "C:\\nssm.exe"
        
    def test_is_running_property(self):
        """Test is_running property."""
        # Running service
        info = ServiceInfo(name="test", state="Running")
        assert info.is_running is True
        
        # Stopped service
        info = ServiceInfo(name="test", state="Stopped")
        assert info.is_running is False
        
        # Case insensitive
        info = ServiceInfo(name="test", state="running")
        assert info.is_running is True