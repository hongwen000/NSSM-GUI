#!/usr/bin/env python3
"""
NSSM GUI - A graphical user interface for the Non-Sucking Service Manager (NSSM).

This application provides a user-friendly interface for managing Windows services
using NSSM (the Non-Sucking Service Manager).
"""

import os
import sys
import argparse
import logging
import asyncio
import requests
import zipfile
from io import BytesIO
from pathlib import Path
from PyQt5 import QtWidgets, QtGui, QtCore
import traceback

# Add the parent directory to sys.path
parent_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, parent_dir)

# Import internal modules
from nssm_gui.models import ServiceConfig, ServiceInfo
from nssm_gui.service_manager import NSSmManager
from nssm_gui.ui.main_window import NSSmGUI
from nssm_gui.utils.admin import ensure_admin, is_admin
from nssm_gui.utils.logging_setup import setup_logging
from nssm_gui.utils.config import ConfigManager

# Default paths
CACHE_DIR = os.path.join(os.getenv('APPDATA'), 'nssm-gui')
NSSM_EXE_PATH = os.path.join(CACHE_DIR, 'nssm.exe')
NSSM_URL = 'https://nssm.cc/ci/nssm-2.24-103-gdee49fc.zip'
LOG_FILE = os.path.join(CACHE_DIR, 'nssm-gui.log')

def download_nssm(url=NSSM_URL, target_dir=CACHE_DIR):
    """
    Download and extract the NSSM executable.
    
    Args:
        url: URL to download NSSM from
        target_dir: Directory to store the executable
    
    Returns:
        Path to the NSSM executable
    """
    # Create the target directory if it doesn't exist
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
        
    nssm_exe_path = os.path.join(target_dir, 'nssm.exe')
    
    # Check if NSSM is already downloaded
    if os.path.exists(nssm_exe_path):
        return nssm_exe_path
        
    try:
        # Download the NSSM zip file
        response = requests.get(url)
        response.raise_for_status()
        
        # Extract the executable
        with zipfile.ZipFile(BytesIO(response.content)) as z:
            for file in z.namelist():
                if file.endswith('win64/nssm.exe'):
                    with z.open(file) as source, open(nssm_exe_path, 'wb') as target:
                        target.write(source.read())
                    break
                    
        if not os.path.exists(nssm_exe_path):
            raise FileNotFoundError("Could not find nssm.exe in the downloaded ZIP")
            
        return nssm_exe_path
    except Exception as e:
        print(f"Error downloading NSSM: {str(e)}")
        raise
        
def parse_arguments():
    """
    Parse command-line arguments.
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(description='NSSM GUI - Graphical user interface for NSSM')
    
    parser.add_argument('--nssm-path', help='Path to NSSM executable')
    parser.add_argument('--no-admin-check', action='store_true', help='Skip admin rights check')
    parser.add_argument('--config-dir', help='Configuration directory')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        default='INFO', help='Logging level')
    
    return parser.parse_args()

def setup_crash_handler():
    """Set up a handler for unhandled exceptions."""
    def excepthook(exc_type, exc_value, exc_traceback):
        """Handle unhandled exceptions."""
        # Log the exception
        logging.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback))
        
        # Format the traceback
        tb = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        
        # Show an error dialog
        error_dialog = QtWidgets.QMessageBox()
        error_dialog.setIcon(QtWidgets.QMessageBox.Critical)
        error_dialog.setWindowTitle("Critical Error")
        error_dialog.setText("An unhandled exception occurred. The application will now exit.")
        error_dialog.setDetailedText(tb)
        error_dialog.exec_()
        
        # Call the original excepthook
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        
    # Set the excepthook
    sys.excepthook = excepthook

def setup_async_loop():
    """Set up the asyncio event loop for Qt."""
    try:
        # Get the current event loop
        loop = asyncio.get_event_loop()
    except RuntimeError:
        # Create a new event loop if not already running
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # Create a QEventLoop (for future use if needed)
    qt_loop = QtCore.QEventLoop()

    return loop

def main():
    """Main entry point for the application."""
    # Parse command-line arguments
    args = parse_arguments()
    
    # Set up logging
    log_level = getattr(logging, args.log_level)
    logger = setup_logging(log_level=log_level)
    
    # Log startup info
    logger.info(f"NSSM GUI starting up - Version 1.0.0")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Arguments: {args}")
    
    # Check for administrative privileges if required
    if not args.no_admin_check:
        admin = ensure_admin()
        if not admin:
            logger.warning("Running without administrative privileges. Some operations may fail.")
    
    # Create Qt application
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("NSSM GUI")
    app.setApplicationVersion("1.0.0")
    
    # Set up crash handler
    setup_crash_handler()
    
    # Set up asyncio integration with Qt
    from nssm_gui.utils.asyncqt import AsyncHelper
    async_helper = AsyncHelper(app)
    
    # Initialize configuration manager
    config_manager = ConfigManager(args.config_dir)
    
    # Get NSSM path
    nssm_path = args.nssm_path
    if not nssm_path:
        try:
            nssm_path = download_nssm()
            logger.info(f"Using downloaded NSSM at {nssm_path}")
        except Exception as e:
            logger.error(f"Failed to download NSSM: {str(e)}")
            QtWidgets.QMessageBox.critical(
                None, "Error",
                f"Failed to download NSSM: {str(e)}\n\n"
                "Please specify the path to NSSM executable using --nssm-path argument."
            )
            return 1
    
    # Check if NSSM exists
    if not os.path.exists(nssm_path):
        logger.error(f"NSSM executable not found at {nssm_path}")
        QtWidgets.QMessageBox.critical(
            None, "Error",
            f"NSSM executable not found at {nssm_path}.\n\n"
            "Please make sure NSSM is installed and provide the correct path."
        )
        return 1
    
    # Initialize main window
    window = NSSmGUI(nssm_path, async_helper)
    window.show()
    
    # Start the application event loop
    return app.exec_()

if __name__ == "__main__":
    sys.exit(main())