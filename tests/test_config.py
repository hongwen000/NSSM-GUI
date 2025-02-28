import pytest
import os
import json
import tempfile
import shutil
from unittest.mock import patch, mock_open, MagicMock

from nssm_gui.utils.config import ConfigManager

class TestConfigManager:
    """Test cases for ConfigManager class."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
        
    @pytest.fixture
    def config_manager(self, temp_dir):
        """Create a ConfigManager with a temporary directory."""
        return ConfigManager(temp_dir)
        
    def test_init(self, temp_dir):
        """Test constructor creates directories and sets paths correctly."""
        # Create a config manager
        config_manager = ConfigManager(temp_dir)
        
        # Check paths
        assert config_manager.config_dir == temp_dir
        assert config_manager.config_file == os.path.join(temp_dir, 'config.json')
        
        # Check directory was created
        assert os.path.exists(temp_dir)
        
    def test_init_default_path(self):
        """Test constructor uses default path when none provided."""
        with patch('os.getenv', return_value='/fake/path'):
            with patch('os.path.exists', return_value=True):
                with patch('pathlib.Path.mkdir'):
                    # Create a config manager with default path
                    config_manager = ConfigManager()
                    
                    # Check paths
                    assert '/fake/path' in config_manager.config_dir
                    assert 'config.json' in config_manager.config_file
                    
    def test_load_config_new(self, config_manager):
        """Test loading config when file doesn't exist."""
        # Ensure the file doesn't exist
        if os.path.exists(config_manager.config_file):
            os.remove(config_manager.config_file)
            
        # Mock the save_config method
        with patch.object(config_manager, 'save_config', return_value=True):
            # Load config
            config_manager.load_config()
            
            # Check that default config was loaded
            assert config_manager.config == config_manager.DEFAULT_CONFIG
            
            # Check that save_config was called
            config_manager.save_config.assert_called_once()
            
    def test_load_config_existing(self, config_manager):
        """Test loading config from existing file."""
        # Create a test config
        test_config = {
            'ui': {
                'dark_mode': True,
                'auto_refresh': False
            }
        }
        
        # Write test config to file
        with open(config_manager.config_file, 'w') as f:
            json.dump(test_config, f)
            
        # Load config
        config_manager.load_config()
        
        # Check that test config was loaded with defaults for missing keys
        assert config_manager.config['ui']['dark_mode'] is True
        assert config_manager.config['ui']['auto_refresh'] is False
        assert 'service' in config_manager.config  # Added from defaults
        
    def test_load_config_error(self, config_manager):
        """Test handling of errors when loading config."""
        # Create an invalid JSON file
        with open(config_manager.config_file, 'w') as f:
            f.write('invalid json')
            
        # Load config (should use defaults on error)
        config_manager.load_config()
        
        # Check that default config was loaded
        assert config_manager.config == config_manager.DEFAULT_CONFIG
        
    def test_save_config(self, config_manager):
        """Test saving config to file."""
        # Set a test config
        config_manager.config = {
            'test': 'value'
        }
        
        # Save config
        success = config_manager.save_config()
        
        # Check result
        assert success
        
        # Check that file was created
        assert os.path.exists(config_manager.config_file)
        
        # Check file contents
        with open(config_manager.config_file, 'r') as f:
            saved_config = json.load(f)
            assert saved_config == {'test': 'value'}
            
    def test_save_config_error(self, config_manager):
        """Test handling of errors when saving config."""
        # Mock open to raise an exception
        with patch('builtins.open', side_effect=Exception('Test error')):
            # Save config
            success = config_manager.save_config()
            
            # Check result
            assert not success
            
    def test_get(self, config_manager):
        """Test getting config values."""
        # Set a test config
        config_manager.config = {
            'section1': {
                'key1': 'value1',
                'key2': 'value2'
            },
            'section2': {
                'key3': 'value3'
            }
        }
        
        # Get existing values
        assert config_manager.get('section1', 'key1') == 'value1'
        assert config_manager.get('section1', 'key2') == 'value2'
        assert config_manager.get('section2', 'key3') == 'value3'
        
        # Get non-existent values with default
        assert config_manager.get('section1', 'non_existent', 'default') == 'default'
        assert config_manager.get('non_existent', 'key', 'default') == 'default'
        
    def test_set(self, config_manager):
        """Test setting config values."""
        # Set a test config
        config_manager.config = {
            'section1': {
                'key1': 'value1'
            }
        }
        
        # Set existing value
        success = config_manager.set('section1', 'key1', 'new_value')
        assert success
        assert config_manager.config['section1']['key1'] == 'new_value'
        
        # Set new value in existing section
        success = config_manager.set('section1', 'key2', 'value2')
        assert success
        assert config_manager.config['section1']['key2'] == 'value2'
        
        # Set value in new section
        success = config_manager.set('section2', 'key3', 'value3')
        assert success
        assert config_manager.config['section2']['key3'] == 'value3'
        
    def test_get_ui_preferences(self, config_manager):
        """Test getting UI preferences."""
        # Set a test config
        config_manager.config = {
            'ui': {
                'dark_mode': True,
                'auto_refresh': False
            }
        }
        
        # Get UI preferences
        prefs = config_manager.get_ui_preferences()
        
        # Check results
        assert prefs['dark_mode'] is True
        assert prefs['auto_refresh'] is False
        
        # Check that default values are included
        assert 'refresh_interval' in prefs
        
    def test_set_ui_preferences(self, config_manager):
        """Test setting UI preferences."""
        # Set a test preferences
        prefs = {
            'dark_mode': True,
            'auto_refresh': False,
            'refresh_interval': 10000
        }
        
        # Mock save_config
        with patch.object(config_manager, 'save_config', return_value=True):
            # Set UI preferences
            success = config_manager.set_ui_preferences(prefs)
            
            # Check results
            assert success
            assert config_manager.config['ui'] == prefs
            
            # Check that save_config was called
            config_manager.save_config.assert_called_once()
            
    def test_add_recent_service(self, config_manager):
        """Test adding a service to recent services list."""
        # Set initial recent services
        config_manager.config['recent_services'] = ['service1', 'service2']
        
        # Mock save_config
        with patch.object(config_manager, 'save_config', return_value=True):
            # Add a new service
            success = config_manager.add_recent_service('service3')
            
            # Check results
            assert success
            assert config_manager.config['recent_services'] == ['service3', 'service1', 'service2']
            
            # Check that save_config was called
            config_manager.save_config.assert_called_once()
            
            # Reset mock
            config_manager.save_config.reset_mock()
            
            # Add an existing service (should move to front)
            success = config_manager.add_recent_service('service2')
            
            # Check results
            assert success
            assert config_manager.config['recent_services'] == ['service2', 'service3', 'service1']
            
    def test_get_recent_services(self, config_manager):
        """Test getting recent services list."""
        # Set a test list
        config_manager.config['recent_services'] = ['service1', 'service2', 'service3']
        
        # Get recent services
        services = config_manager.get_recent_services()
        
        # Check results
        assert services == ['service1', 'service2', 'service3']
        
    def test_save_service_template(self, config_manager):
        """Test saving a service template."""
        # Set initial templates
        config_manager.config['service_templates'] = {
            'template1': {'key1': 'value1'}
        }
        
        # Mock save_config
        with patch.object(config_manager, 'save_config', return_value=True):
            # Save a new template
            success = config_manager.save_service_template('template2', {'key2': 'value2'})
            
            # Check results
            assert success
            assert config_manager.config['service_templates'] == {
                'template1': {'key1': 'value1'},
                'template2': {'key2': 'value2'}
            }
            
            # Check that save_config was called
            config_manager.save_config.assert_called_once()
            
    def test_get_service_template(self, config_manager):
        """Test getting a service template."""
        # Set test templates
        config_manager.config['service_templates'] = {
            'template1': {'key1': 'value1'},
            'template2': {'key2': 'value2'}
        }
        
        # Get existing template
        template = config_manager.get_service_template('template1')
        assert template == {'key1': 'value1'}
        
        # Get non-existent template
        template = config_manager.get_service_template('non_existent')
        assert template is None
        
    def test_get_all_templates(self, config_manager):
        """Test getting all service templates."""
        # Set test templates
        test_templates = {
            'template1': {'key1': 'value1'},
            'template2': {'key2': 'value2'}
        }
        config_manager.config['service_templates'] = test_templates
        
        # Get all templates
        templates = config_manager.get_all_templates()
        
        # Check results
        assert templates == test_templates
        
    def test_delete_template(self, config_manager):
        """Test deleting a service template."""
        # Set initial templates
        config_manager.config['service_templates'] = {
            'template1': {'key1': 'value1'},
            'template2': {'key2': 'value2'}
        }
        
        # Mock save_config
        with patch.object(config_manager, 'save_config', return_value=True):
            # Delete an existing template
            success = config_manager.delete_template('template1')
            
            # Check results
            assert success
            assert config_manager.config['service_templates'] == {
                'template2': {'key2': 'value2'}
            }
            
            # Check that save_config was called
            config_manager.save_config.assert_called_once()
            
            # Reset mock
            config_manager.save_config.reset_mock()
            
            # Delete a non-existent template
            success = config_manager.delete_template('non_existent')
            
            # Check results
            assert not success
            assert config_manager.config['service_templates'] == {
                'template2': {'key2': 'value2'}
            }