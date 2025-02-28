import os
import logging
import logging.handlers
import sys
from datetime import datetime
from pathlib import Path

def setup_logging(log_dir=None, log_level=logging.INFO):
    """
    Set up application logging with rotating file handler and console output.
    
    Args:
        log_dir: Directory to store log files, defaults to user's AppData directory
        log_level: Logging level (default: INFO)
    
    Returns:
        The configured logger
    """
    # Create logger
    logger = logging.getLogger("nssm_gui")
    logger.setLevel(log_level)
    
    # Clear any existing handlers
    if logger.handlers:
        logger.handlers.clear()
    
    # Determine log directory
    if not log_dir:
        if sys.platform == 'win32':
            app_data = os.getenv('APPDATA')
            log_dir = os.path.join(app_data, 'nssm-gui', 'logs')
        else:
            log_dir = os.path.expanduser(os.path.join('~', '.nssm-gui', 'logs'))
    
    # Create log directory if it doesn't exist
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    
    # Generate log filename with date
    current_date = datetime.now().strftime('%Y-%m-%d')
    log_file = os.path.join(log_dir, f'nssm_gui_{current_date}.log')
    
    # Create a formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create handlers
    
    # File handler with rotation (10 MB max size, keep 5 backups)
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=10_485_760, backupCount=5, encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Add a null handler to libraries to prevent propagation of logs
    logging.getLogger('PyQt5').addHandler(logging.NullHandler())
    
    # Log startup message
    logger.info(f"Logging initialized. Log file: {log_file}")
    logger.info(f"Log level: {logging.getLevelName(log_level)}")
    
    return logger

def get_logger(name):
    """
    Get a logger with the given name, inheriting from the main logger.
    
    Args:
        name: Logger name
        
    Returns:
        A logger instance
    """
    return logging.getLogger(f"nssm_gui.{name}")

class LogCaptureHandler(logging.Handler):
    """
    A handler that captures log records in memory for display in the UI.
    """
    def __init__(self, max_records=1000):
        super().__init__()
        self.records = []
        self.max_records = max_records
    
    def emit(self, record):
        if len(self.records) >= self.max_records:
            self.records.pop(0)  # Remove oldest record
        self.records.append(self.format(record))
    
    def get_records(self):
        """Return all captured records."""
        return self.records
    
    def clear(self):
        """Clear all captured records."""
        self.records.clear()