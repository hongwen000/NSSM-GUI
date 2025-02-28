"""
Configuration file for pytest.
"""
import os
import sys
import pytest
import asyncio
from unittest.mock import patch

# Add the parent directory to sys.path to allow importing the application modules
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Configure asyncio for testing
def pytest_configure(config):
    """Configure asyncio for testing."""
    # Set event loop policy to avoid errors on Windows
    if sys.platform == 'win32':
        try:
            # Use WindowsSelectorEventLoopPolicy to avoid issues with ProactorEventLoop
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except AttributeError:
            # Fallback for older Python versions
            pass

# Global fixtures

@pytest.fixture(scope="session")
def mock_nssm_path():
    """Path to a mock NSSM executable."""
    return 'C:\\path\\to\\nssm.exe'

@pytest.fixture(scope="session", autouse=True)
def mock_platform():
    """Mock the platform to always be Windows."""
    with patch('sys.platform', 'win32'):
        yield

@pytest.fixture(scope="session", autouse=True)
def mock_os_exists():
    """Mock os.path.exists to return True for testing paths."""
    original_exists = os.path.exists
    
    def patched_exists(path):
        # Return True for mock nssm path and common test paths
        if 'nssm.exe' in path or 'test.exe' in path:
            return True
        # Fall back to real implementation for other paths
        return original_exists(path)
    
    with patch('os.path.exists', patched_exists):
        yield

# Mock for file operations to avoid actual file creation/reading
@pytest.fixture(scope="session", autouse=True)
def mock_open_files(tmp_path_factory):
    """Mock file operations to use temporary directory."""
    # Create a temporary directory for test files
    test_dir = tmp_path_factory.mktemp("test_files")
    
    # Return the path to use for testing
    return str(test_dir)

# Ensure proper event loop cleanup for asyncio tests
@pytest.fixture
def event_loop():
    """Create and yield an event loop for each test that needs it."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    
    # Clean up any pending tasks
    pending = asyncio.all_tasks(loop)
    for task in pending:
        task.cancel()
        
    # Run the event loop until all pending tasks are done
    if pending:
        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        
    # Close the loop
    loop.run_until_complete(loop.shutdown_asyncgens())
    loop.close()