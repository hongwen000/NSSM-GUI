import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta

import psutil

from nssm_gui.utils.monitoring import ServiceMonitor

class TestServiceMonitor:
    """Test cases for the ServiceMonitor class."""
    
    @pytest.fixture
    def monitor(self):
        """Fixture to create a ServiceMonitor."""
        monitor = ServiceMonitor(max_history=10)
        return monitor
        
    def test_init(self, monitor):
        """Test constructor."""
        assert monitor.max_history == 10
        assert isinstance(monitor.service_data, dict)
        assert monitor.running is False
        assert monitor.executor is not None
        
    def test_start_monitoring(self, monitor):
        """Test startMonitoring method."""
        # Start monitoring
        monitor.start_monitoring()
        
        # Check state
        assert monitor.running is True
        
    def test_stop_monitoring(self, monitor):
        """Test stopMonitoring method."""
        # Start first
        monitor.start_monitoring()
        assert monitor.running is True
        
        # Stop monitoring
        monitor.stop_monitoring()
        
        # Check state
        assert monitor.running is False
        
    @pytest.mark.asyncio
    @patch('asyncio.get_event_loop')
    async def test_update_service_data_not_running(self, mock_get_loop, monitor):
        """Test updateServiceData when not running."""
        # Don't start monitoring
        assert monitor.running is False
        
        # Call updateServiceData
        result = await monitor.update_service_data("test-service", 1234)
        
        # Check result
        assert result is False
        
    @pytest.mark.asyncio
    @patch('asyncio.get_event_loop')
    async def test_update_service_data_new_service(self, mock_get_loop, monitor):
        """Test updateServiceData for a new service."""
        # Start monitoring
        monitor.start_monitoring()
        
        # Mock _get_process_stats
        process_stats = {
            'cpu_percent': 10.5,
            'memory_percent': 5.2,
            'memory_mb': 128.5,
            'io_read_mb': 2.1,
            'io_write_mb': 1.3,
            'start_time': datetime.now()
        }
        
        # Create a mock loop with run_in_executor
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(return_value=process_stats)
        mock_get_loop.return_value = mock_loop
        
        # Add a spy on _get_process_stats
        with patch.object(monitor, '_get_process_stats', return_value=process_stats) as mock_get_stats:
            # Call updateServiceData
            result = await monitor.update_service_data("test-service", 1234)
            
            # Check result
            assert result is True
            
            # Check that service was added to service_data
            assert "test-service" in monitor.service_data
            
            # Check that data was recorded correctly
            service_data = monitor.service_data["test-service"]
            assert service_data['cpu_percent'] == [10.5]
            assert service_data['memory_percent'] == [5.2]
            assert service_data['memory_mb'] == [128.5]
            assert service_data['io_read_mb'] == [2.1]
            assert service_data['io_write_mb'] == [1.3]
            assert len(service_data['timestamps']) == 1
            assert service_data['uptime'] > 0
            assert service_data['start_time'] == process_stats['start_time']
            
    @pytest.mark.asyncio
    @patch('asyncio.get_event_loop')
    async def test_update_service_data_existing_service(self, mock_get_loop, monitor):
        """Test updateServiceData for an existing service."""
        # Start monitoring
        monitor.start_monitoring()
        
        # Initialize service data
        start_time = datetime.now() - timedelta(hours=1)  # Service started 1 hour ago
        monitor.service_data["test-service"] = {
            'cpu_percent': [5.0],
            'memory_percent': [2.5],
            'memory_mb': [64.0],
            'io_read_mb': [1.0],
            'io_write_mb': [0.5],
            'timestamps': [datetime.now() - timedelta(minutes=5)],  # Last update was 5 minutes ago
            'uptime': 3600.0,  # 1 hour
            'start_time': start_time,
            'restarts': 1
        }
        
        # Mock process stats
        process_stats = {
            'cpu_percent': 10.5,
            'memory_percent': 5.2,
            'memory_mb': 128.5,
            'io_read_mb': 2.1,
            'io_write_mb': 1.3,
            'start_time': start_time
        }
        
        # Create a mock loop with run_in_executor
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(return_value=process_stats)
        mock_get_loop.return_value = mock_loop
        
        # Add a spy on _get_process_stats
        with patch.object(monitor, '_get_process_stats', return_value=process_stats) as mock_get_stats:
            # Call updateServiceData
            result = await monitor.update_service_data("test-service", 1234)
            
            # Check result
            assert result is True
            
            # Check that data was updated correctly
            service_data = monitor.service_data["test-service"]
            assert service_data['cpu_percent'] == [5.0, 10.5]
            assert service_data['memory_percent'] == [2.5, 5.2]
            assert service_data['memory_mb'] == [64.0, 128.5]
            assert service_data['io_read_mb'] == [1.0, 2.1]
            assert service_data['io_write_mb'] == [0.5, 1.3]
            assert len(service_data['timestamps']) == 2
            assert service_data['uptime'] > 3600.0  # Should be more than before
            assert service_data['start_time'] == start_time
            assert service_data['restarts'] == 1  # Should be unchanged
            
    @pytest.mark.asyncio
    @patch('asyncio.get_event_loop')
    async def test_update_service_data_limit_history(self, mock_get_loop, monitor):
        """Test updateServiceData limits history to max_history."""
        # Set a smaller max_history for testing
        monitor.max_history = 3
        
        # Start monitoring
        monitor.start_monitoring()
        
        # Initialize service data with max_history items
        monitor.service_data["test-service"] = {
            'cpu_percent': [1.0, 2.0, 3.0],
            'memory_percent': [1.0, 2.0, 3.0],
            'memory_mb': [1.0, 2.0, 3.0],
            'io_read_mb': [1.0, 2.0, 3.0],
            'io_write_mb': [1.0, 2.0, 3.0],
            'timestamps': [
                datetime.now() - timedelta(minutes=15),
                datetime.now() - timedelta(minutes=10),
                datetime.now() - timedelta(minutes=5)
            ],
            'uptime': 0.0,
            'start_time': None,
            'restarts': 0
        }
        
        # Mock process stats
        process_stats = {
            'cpu_percent': 4.0,
            'memory_percent': 4.0,
            'memory_mb': 4.0,
            'io_read_mb': 4.0,
            'io_write_mb': 4.0,
            'start_time': datetime.now()
        }
        
        # Create a mock loop with run_in_executor
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(return_value=process_stats)
        mock_get_loop.return_value = mock_loop
        
        # Add a spy on _get_process_stats
        with patch.object(monitor, '_get_process_stats', return_value=process_stats) as mock_get_stats:
            # Call updateServiceData
            result = await monitor.update_service_data("test-service", 1234)
            
            # Check result
            assert result is True
            
            # Check that history was limited to max_history
            service_data = monitor.service_data["test-service"]
            assert service_data['cpu_percent'] == [2.0, 3.0, 4.0]  # First item should be removed
            assert service_data['memory_percent'] == [2.0, 3.0, 4.0]
            assert service_data['memory_mb'] == [2.0, 3.0, 4.0]
            assert service_data['io_read_mb'] == [2.0, 3.0, 4.0]
            assert service_data['io_write_mb'] == [2.0, 3.0, 4.0]
            assert len(service_data['timestamps']) == 3
            
    @patch('psutil.Process')
    def test_get_process_stats(self, mock_process_class, monitor):
        """Test _getProcessStats method."""
        # Create a mock process
        mock_process = MagicMock()
        mock_process_class.return_value = mock_process
        
        # Configure the mock process
        mock_process.cpu_percent.return_value = 10.5
        mock_process.memory_percent.return_value = 5.2
        
        # Mock memory_info
        mock_memory_info = MagicMock()
        mock_memory_info.rss = 128 * 1024 * 1024  # 128 MB in bytes
        mock_process.memory_info.return_value = mock_memory_info
        
        # Mock io_counters
        mock_io_counters = MagicMock()
        mock_io_counters.read_bytes = 2.1 * 1024 * 1024  # 2.1 MB in bytes
        mock_io_counters.write_bytes = 1.3 * 1024 * 1024  # 1.3 MB in bytes
        mock_process.io_counters.return_value = mock_io_counters
        
        # Mock create_time
        mock_process.create_time.return_value = datetime.now().timestamp()
        
        # Call _get_process_stats
        stats = monitor._get_process_stats(1234)
        
        # Check that process was created with correct PID
        mock_process_class.assert_called_once_with(1234)
        
        # Check stats
        assert stats['cpu_percent'] == 10.5
        assert stats['memory_percent'] == 5.2
        assert stats['memory_mb'] == 128.0
        assert stats['io_read_mb'] == 2.1
        assert stats['io_write_mb'] == 1.3
        assert isinstance(stats['start_time'], datetime)
        
    @patch('psutil.Process')
    def test_get_process_stats_no_process(self, mock_process_class, monitor):
        """Test _getProcessStats when process doesn't exist."""
        # Make Process constructor raise NoSuchProcess
        mock_process_class.side_effect = psutil.NoSuchProcess(1234)
        
        # Call _get_process_stats
        stats = monitor._get_process_stats(1234)
        
        # Check result
        assert stats is None
        
    def test_reset_service_data(self, monitor):
        """Test resetServiceData method."""
        # Initialize service data
        monitor.service_data["test-service"] = {
            'cpu_percent': [10.5],
            'memory_percent': [5.2],
            'memory_mb': [128.5],
            'io_read_mb': [2.1],
            'io_write_mb': [1.3],
            'timestamps': [datetime.now()],
            'uptime': 3600.0,
            'start_time': datetime.now(),
            'restarts': 2
        }
        
        # Call resetServiceData
        monitor.reset_service_data("test-service")
        
        # Check that data was reset
        service_data = monitor.service_data["test-service"]
        assert service_data['cpu_percent'] == []
        assert service_data['memory_percent'] == []
        assert service_data['memory_mb'] == []
        assert service_data['io_read_mb'] == []
        assert service_data['io_write_mb'] == []
        assert service_data['timestamps'] == []
        assert service_data['uptime'] == 0
        assert service_data['start_time'] is None
        assert service_data['restarts'] == 0
        
    def test_increment_restart_count(self, monitor):
        """Test incrementRestartCount method."""
        # Initialize service data
        monitor.service_data["test-service"] = {
            'cpu_percent': [],
            'memory_percent': [],
            'memory_mb': [],
            'io_read_mb': [],
            'io_write_mb': [],
            'timestamps': [],
            'uptime': 0,
            'start_time': None,
            'restarts': 2
        }
        
        # Call incrementRestartCount
        monitor.increment_restart_count("test-service")
        
        # Check that restart count was incremented
        assert monitor.service_data["test-service"]['restarts'] == 3
        
    def test_get_service_stats(self, monitor):
        """Test getServiceStats method."""
        # Initialize service data
        now = datetime.now()
        start_time = now - timedelta(hours=1)
        monitor.service_data["test-service"] = {
            'cpu_percent': [5.0, 10.0, 15.0],
            'memory_percent': [2.5, 5.0, 7.5],
            'memory_mb': [64.0, 128.0, 192.0],
            'io_read_mb': [1.0, 2.0, 3.0],
            'io_write_mb': [0.5, 1.0, 1.5],
            'timestamps': [
                now - timedelta(minutes=15),
                now - timedelta(minutes=10),
                now - timedelta(minutes=5)
            ],
            'uptime': 3600.0,
            'start_time': start_time,
            'restarts': 2
        }
        
        # Call getServiceStats
        stats = monitor.get_service_stats("test-service")
        
        # Check stats
        assert stats['cpu_history'] == [5.0, 10.0, 15.0]
        assert stats['memory_history'] == [2.5, 5.0, 7.5]
        assert stats['memory_mb_history'] == [64.0, 128.0, 192.0]
        assert stats['io_read_history'] == [1.0, 2.0, 3.0]
        assert stats['io_write_history'] == [0.5, 1.0, 1.5]
        assert stats['timestamps'] == monitor.service_data["test-service"]['timestamps']
        assert stats['uptime'] == 3600.0
        assert stats['start_time'] == start_time
        assert stats['restarts'] == 2
        
        # Check calculated stats
        assert stats['cpu_avg'] == 10.0
        assert stats['cpu_current'] == 15.0
        assert stats['memory_avg'] == 5.0
        assert stats['memory_current'] == 7.5
        assert stats['memory_mb_avg'] == 128.0
        assert stats['memory_mb_current'] == 192.0
        
    def test_get_service_stats_unknown_service(self, monitor):
        """Test getServiceStats for unknown service."""
        # Call getServiceStats for unknown service
        stats = monitor.get_service_stats("unknown-service")
        
        # Check that service was initialized
        assert "unknown-service" in monitor.service_data
        
        # Check stats
        assert stats['cpu_history'] == []
        assert stats['memory_history'] == []
        assert stats['cpu_avg'] == 0
        assert stats['cpu_current'] == 0
        
    def test_get_all_service_stats(self, monitor):
        """Test getAllServiceStats method."""
        # Initialize service data for two services
        monitor.service_data["service1"] = {
            'cpu_percent': [10.0],
            'memory_percent': [5.0],
            'memory_mb': [128.0],
            'io_read_mb': [2.0],
            'io_write_mb': [1.0],
            'timestamps': [datetime.now()],
            'uptime': 3600.0,
            'start_time': datetime.now() - timedelta(hours=1),
            'restarts': 1
        }
        
        monitor.service_data["service2"] = {
            'cpu_percent': [20.0],
            'memory_percent': [10.0],
            'memory_mb': [256.0],
            'io_read_mb': [4.0],
            'io_write_mb': [2.0],
            'timestamps': [datetime.now()],
            'uptime': 7200.0,
            'start_time': datetime.now() - timedelta(hours=2),
            'restarts': 0
        }
        
        # Call getAllServiceStats
        all_stats = monitor.get_all_service_stats()
        
        # Check results
        assert "service1" in all_stats
        assert "service2" in all_stats
        assert all_stats["service1"]['cpu_current'] == 10.0
        assert all_stats["service2"]['cpu_current'] == 20.0