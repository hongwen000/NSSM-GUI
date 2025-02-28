import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("nssm_gui.config")

class ConfigManager:
    """
    Manager for application configuration and user preferences.
    """
    
    DEFAULT_CONFIG = {
        "ui": {
            "auto_refresh": True,
            "refresh_interval": 5000,  # 5 seconds
            "dark_mode": False,
            "confirm_actions": True,
            "show_details_panel": True,
            "font_size": 9
        },
        "service": {
            "default_stdout_path": "${TEMP}\\${SERVICE_NAME}_stdout.log",
            "default_stderr_path": "${TEMP}\\${SERVICE_NAME}_stderr.log",
            "default_priority": "NORMAL_PRIORITY_CLASS",
            "default_exit_action": "Restart"
        },
        "advanced": {
            "enable_service_monitoring": True,
            "monitoring_interval": 5000,  # 5 seconds
            "monitor_cpu_usage": True,
            "monitor_memory_usage": True,
            "backup_service_configs": True,
            "backup_directory": ""  # Will be set during initialization
        },
        "recent_services": [],  # List of recently accessed services
        "service_templates": {}  # Templates for service configurations
    }
    
    def __init__(self, config_dir=None):
        """
        Initialize the configuration manager.
        
        Args:
            config_dir: Directory to store configuration files,
                       defaults to user's AppData directory
        """
        self.config = {}
        
        # Determine config directory
        if not config_dir:
            if os.name == 'nt':  # Windows
                app_data = os.getenv('APPDATA')
                self.config_dir = os.path.join(app_data, 'nssm-gui')
            else:  # Unix/Linux/Mac
                self.config_dir = os.path.expanduser(os.path.join('~', '.nssm-gui'))
        else:
            self.config_dir = config_dir
            
        # Create config directory if it doesn't exist
        Path(self.config_dir).mkdir(parents=True, exist_ok=True)
        
        # Set config file path
        self.config_file = os.path.join(self.config_dir, 'config.json')
        
        # Set default backup directory
        backup_dir = os.path.join(self.config_dir, 'backups')
        self.DEFAULT_CONFIG["advanced"]["backup_directory"] = backup_dir
        
        # Load configuration
        self.load_config()
        
    def load_config(self):
        """Load configuration from file or create default if it doesn't exist."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                    
                # Make sure all default keys exist
                self._ensure_defaults()
                logger.info(f"Configuration loaded from {self.config_file}")
            else:
                # Create a new configuration with defaults
                self.config = self.DEFAULT_CONFIG.copy()
                self.save_config()
                logger.info("Created new configuration with defaults")
        except Exception as e:
            logger.error(f"Error loading configuration: {str(e)}")
            # Use defaults if there's an error
            self.config = self.DEFAULT_CONFIG.copy()
            
    def _ensure_defaults(self):
        """Ensure all default configuration keys exist."""
        def update_nested_dict(d, u):
            for k, v in u.items():
                if isinstance(v, dict) and k in d and isinstance(d[k], dict):
                    update_nested_dict(d[k], v)
                elif k not in d:
                    d[k] = v
            return d
            
        self.config = update_nested_dict(self.config, self.DEFAULT_CONFIG)
        
    def save_config(self):
        """Save configuration to file."""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4)
            logger.info(f"Configuration saved to {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving configuration: {str(e)}")
            return False
            
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            section: Configuration section
            key: Configuration key
            default: Default value if not found
            
        Returns:
            The configuration value or default
        """
        try:
            return self.config.get(section, {}).get(key, default)
        except Exception as e:
            logger.error(f"Error getting config value [{section}.{key}]: {str(e)}")
            return default
            
    def set(self, section: str, key: str, value: Any) -> bool:
        """
        Set a configuration value.
        
        Args:
            section: Configuration section
            key: Configuration key
            value: Value to set
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if section not in self.config:
                self.config[section] = {}
            self.config[section][key] = value
            return True
        except Exception as e:
            logger.error(f"Error setting config value [{section}.{key}]: {str(e)}")
            return False
            
    def get_ui_preferences(self) -> Dict[str, Any]:
        """
        Get UI preferences.
        
        Returns:
            Dictionary of UI preferences
        """
        return self.config.get('ui', self.DEFAULT_CONFIG['ui'].copy())
        
    def set_ui_preferences(self, preferences: Dict[str, Any]) -> bool:
        """
        Set UI preferences.
        
        Args:
            preferences: Dictionary of UI preferences
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.config['ui'] = preferences
            return self.save_config()
        except Exception as e:
            logger.error(f"Error setting UI preferences: {str(e)}")
            return False
            
    def add_recent_service(self, service_name: str, max_recent: int = 10) -> bool:
        """
        Add a service to the recent services list.
        
        Args:
            service_name: Name of the service
            max_recent: Maximum number of recent services to keep
            
        Returns:
            True if successful, False otherwise
        """
        try:
            recent = self.config.get('recent_services', [])
            
            # Remove if it already exists
            if service_name in recent:
                recent.remove(service_name)
                
            # Add to the beginning of the list
            recent.insert(0, service_name)
            
            # Limit the number of recent services
            self.config['recent_services'] = recent[:max_recent]
            
            return self.save_config()
        except Exception as e:
            logger.error(f"Error adding recent service: {str(e)}")
            return False
            
    def get_recent_services(self) -> list:
        """
        Get the list of recent services.
        
        Returns:
            List of recent service names
        """
        return self.config.get('recent_services', [])
        
    def save_service_template(self, template_name: str, config_dict: Dict[str, Any]) -> bool:
        """
        Save a service configuration as a template.
        
        Args:
            template_name: Name of the template
            config_dict: Service configuration dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            templates = self.config.get('service_templates', {})
            templates[template_name] = config_dict
            self.config['service_templates'] = templates
            
            return self.save_config()
        except Exception as e:
            logger.error(f"Error saving service template: {str(e)}")
            return False
            
    def get_service_template(self, template_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a service template by name.
        
        Args:
            template_name: Name of the template
            
        Returns:
            Service template configuration or None if not found
        """
        templates = self.config.get('service_templates', {})
        return templates.get(template_name)
        
    def get_all_templates(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all service templates.
        
        Returns:
            Dictionary of template name to configuration
        """
        return self.config.get('service_templates', {})
        
    def delete_template(self, template_name: str) -> bool:
        """
        Delete a service template.
        
        Args:
            template_name: Name of the template
            
        Returns:
            True if successful, False otherwise
        """
        try:
            templates = self.config.get('service_templates', {})
            if template_name in templates:
                del templates[template_name]
                self.config['service_templates'] = templates
                return self.save_config()
            return False
        except Exception as e:
            logger.error(f"Error deleting service template: {str(e)}")
            return False