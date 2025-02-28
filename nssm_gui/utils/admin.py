import os
import sys
import ctypes
from PyQt5 import QtWidgets
import logging

logger = logging.getLogger("nssm_gui.admin")

def is_admin() -> bool:
    """
    Check if the current process has administrative privileges.
    
    Returns:
        bool: True if the process has admin rights, False otherwise
    """
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception as e:
        logger.error(f"Error checking admin status: {str(e)}")
        return False

def run_as_admin() -> bool:
    """
    Relaunch the current application with administrative privileges.
    
    Returns:
        bool: True if elevation was initiated, False if it failed
    """
    try:
        # Get the absolute path of the current Python executable
        python_exe = sys.executable
        
        # Get the absolute path of the current script
        script = os.path.abspath(sys.argv[0])
        
        # Reconstruct the command-line arguments
        params = ' '.join([f'"{arg}"' for arg in sys.argv[1:]])
        
        # Initialize the SHELLEXECUTEINFO structure
        SEE_MASK_DEFAULT = 0x00000000
        SW_SHOW = 5
        
        class SHELLEXECUTEINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.c_ulong),
                ("fMask", ctypes.c_ulong),
                ("hwnd", ctypes.c_void_p),
                ("lpVerb", ctypes.c_wchar_p),
                ("lpFile", ctypes.c_wchar_p),
                ("lpParameters", ctypes.c_wchar_p),
                ("lpDirectory", ctypes.c_wchar_p),
                ("nShow", ctypes.c_int),
                ("hInstApp", ctypes.c_void_p),
                ("lpIDList", ctypes.c_void_p),
                ("lpClass", ctypes.c_wchar_p),
                ("hkeyClass", ctypes.c_void_p),
                ("dwHotKey", ctypes.c_ulong),
                ("hIconOrMonitor", ctypes.c_void_p),
                ("hProcess", ctypes.c_void_p)
            ]
        
        sei = SHELLEXECUTEINFO()
        sei.cbSize = ctypes.sizeof(SHELLEXECUTEINFO)
        sei.fMask = SEE_MASK_DEFAULT
        sei.hwnd = None
        sei.lpVerb = "runas"  # Causes UAC elevation prompt
        sei.lpFile = python_exe
        sei.lpParameters = f'"{script}" {params}'
        sei.lpDirectory = None
        sei.nShow = SW_SHOW
        sei.hInstApp = None
        
        # Execute the ShellExecuteEx function
        if not ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(sei)):
            error = ctypes.GetLastError()
            QtWidgets.QMessageBox.critical(
                None, 'Elevation Error',
                f"Failed to elevate privileges. Error code: {error}"
            )
            logger.error(f"Failed to elevate privileges. Error code: {error}")
            return False
            
        return True
    except Exception as e:
        QtWidgets.QMessageBox.critical(
            None, 'Elevation Error',
            f"Failed to elevate privileges:\n{str(e)}"
        )
        logger.error(f"Failed to elevate privileges: {str(e)}", exc_info=True)
        return False

def ensure_admin() -> bool:
    """
    Ensure the application runs with administrative privileges.
    If not, try to elevate and restart the application.
    
    Returns:
        bool: True if the application has admin rights or elevation was initiated,
              False if it failed
    """
    # Check if already running as admin
    if is_admin():
        return True
        
    # Create a temporary QApplication to show message boxes
    temp_app = QtWidgets.QApplication.instance()
    if not temp_app:
        temp_app = QtWidgets.QApplication([])
    
    # Ask for permission to elevate
    reply = QtWidgets.QMessageBox.question(
        None, 'Administrator Privileges Required',
        'This application requires administrative privileges to manage services.\n\n'
        'Do you want to restart with elevated privileges?',
        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        QtWidgets.QMessageBox.Yes
    )
    
    if reply == QtWidgets.QMessageBox.Yes:
        # Attempt to elevate
        success = run_as_admin()
        if success:
            # Successfully initiated elevation; exit the current instance
            sys.exit(0)
        else:
            return False
    else:
        QtWidgets.QMessageBox.warning(
            None, 'Limited Functionality',
            'The application will run with limited functionality.\n'
            'Some operations may fail due to insufficient privileges.'
        )
        return False