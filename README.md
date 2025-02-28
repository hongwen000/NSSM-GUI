# NSSM-GUI

A graphical user interface for the Non-Sucking Service Manager (NSSM).

## Features

- Create, edit, and delete Windows services using NSSM
- Start, stop, and restart services
- View service logs
- Monitor service resource usage (CPU, memory, I/O)
- Import and export service configurations
- Save and load service templates
- Batch operations on multiple services
- Dark mode support

## Installation

### Prerequisites

- Windows operating system
- Python 3.7 or higher
- Administrator privileges (for service management)

### Steps

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/nssm-gui.git
   cd nssm-gui
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the application:
   ```
   python main.py
   ```

The application will automatically download NSSM if it's not already available on your system.

## Usage

Run the application with administrator privileges to enable all features. The application will prompt for elevation if needed.

### Command-line Options

- `--nssm-path PATH`: Path to NSSM executable (if not using the auto-downloaded version)
- `--no-admin-check`: Skip administrative privileges check
- `--config-dir PATH`: Custom configuration directory
- `--log-level LEVEL`: Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

Example:
```
python main.py --nssm-path "C:\path\to\nssm.exe" --log-level DEBUG
```

## Development

### Project Structure

- `nssm_gui/`: Main package
  - `models.py`: Data models
  - `service_manager.py`: Core service management
  - `ui/`: User interface components
    - `main_window.py`: Main application window
    - `dialogs.py`: Dialog windows
    - `batch_operations.py`: Batch operations interface
    - `templates.py`: Template management
    - `dashboard.py`: Service monitoring dashboard
  - `utils/`: Utility modules
    - `admin.py`: Administrative privileges utilities
    - `config.py`: Configuration management
    - `logging_setup.py`: Logging configuration
    - `monitoring.py`: Service monitoring utilities

### Running Tests

```
pytest tests/
```

## License

MIT

## Acknowledgements

- [NSSM - the Non-Sucking Service Manager](https://nssm.cc/)
- [PyQt5](https://www.riverbankcomputing.com/software/pyqt/)
- [Pydantic](https://pydantic-docs.helpmanual.io/)
