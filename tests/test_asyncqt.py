import pytest
import asyncio
import threading
import time
from unittest.mock import MagicMock, patch

from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication

from nssm_gui.utils.asyncqt import (
    AsyncRunner, 
    AsyncHelper, 
    get_event_loop, 
    run_async
)

# Fixture for QApplication
@pytest.fixture
def qapp():
    """Fixture that creates a Qt application."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    app.quit()

# Simple async functions for testing
async def async_success():
    """Test async function that succeeds."""
    await asyncio.sleep(0.1)
    return "success"

async def async_fail():
    """Test async function that raises an exception."""
    await asyncio.sleep(0.1)
    raise ValueError("Test error")

class TestAsyncRunner:
    """Test cases for the AsyncRunner class."""
    
    def test_init(self):
        """Test constructor."""
        with patch('nssm_gui.utils.asyncqt.get_event_loop') as mock_get_loop:
            mock_loop = MagicMock()
            mock_get_loop.return_value = mock_loop
            
            runner = AsyncRunner()
            assert runner.loop is mock_loop

class TestAsyncHelper:
    """Test cases for the AsyncHelper class."""
    
    def test_init(self, qapp):
        """Test constructor."""
        with patch('nssm_gui.utils.asyncqt.get_event_loop') as mock_get_loop:
            with patch('threading.Thread') as mock_thread:
                mock_loop = MagicMock()
                mock_get_loop.return_value = mock_loop
                
                helper = AsyncHelper(qapp)
                assert helper.app is qapp
                assert helper.loop is mock_loop
                assert helper.runner is not None
                
                # Check that thread was started
                mock_thread.assert_called_once()
                mock_thread_instance = mock_thread.return_value
                mock_thread_instance.start.assert_called_once()
    
    def test_run(self, qapp):
        """Test running a coroutine."""
        # Instead of actually running the coroutine, we'll mock the AsyncRunner
        with patch('nssm_gui.utils.asyncqt.AsyncRunner') as mock_runner_class:
            # Create a mock runner
            mock_runner = MagicMock()
            mock_runner_class.return_value = mock_runner
            
            # Setup AsyncHelper with the mock
            helper = AsyncHelper(qapp)
            
            # Create a mock callback
            callback = MagicMock()
            
            # Mock coroutine
            mock_coro = MagicMock()
            
            # Call run
            helper.run(mock_coro, callback)
            
            # Check that runner.run_coroutine was called
            mock_runner.run_coroutine.assert_called_once_with(mock_coro, callback)

class TestRunAsyncDecorator:
    """Test cases for the run_async decorator."""
    
    def test_decorator(self, qapp):
        """Test the run_async decorator."""
        # Create a test class with a mocked AsyncHelper
        class TestClass:
            def __init__(self):
                self.async_helper = MagicMock()
                self.async_helper.run = MagicMock()
                
            @run_async
            async def test_method(self, value):
                return value
                
        # Create an instance
        test_obj = TestClass()
        
        # Call the decorated method
        test_obj.test_method("test_value")
        
        # Check that async_helper.run was called
        test_obj.async_helper.run.assert_called_once()
        args, kwargs = test_obj.async_helper.run.call_args
        assert asyncio.iscoroutine(args[0])  # First arg should be a coroutine

class TestGetEventLoop:
    """Test cases for get_event_loop function."""
    
    def test_get_event_loop(self):
        """Test getting the event loop."""
        with patch('asyncio.new_event_loop') as mock_new_loop:
            with patch('asyncio.set_event_loop') as mock_set_loop:
                # Create a mock loop
                mock_loop = MagicMock()
                mock_new_loop.return_value = mock_loop
                
                # First call should create a new loop
                loop1 = get_event_loop()
                assert loop1 is mock_loop
                mock_new_loop.assert_called_once()
                mock_set_loop.assert_called_once_with(mock_loop)
                
                # Reset mocks
                mock_new_loop.reset_mock()
                mock_set_loop.reset_mock()
                
                # Mock the global _loop variable
                with patch('nssm_gui.utils.asyncqt._loop', mock_loop):
                    # Second call should return the same loop
                    loop2 = get_event_loop()
                    assert loop2 is mock_loop
                    mock_new_loop.assert_not_called()
                    mock_set_loop.assert_not_called()