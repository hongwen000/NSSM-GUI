import os
import time
import psutil
import logging
import asyncio
from typing import Dict, List, Optional, Tuple, Any
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

logger = logging.getLogger("nssm_gui.monitoring")

class ServiceMonitor:
    """
    Monitor system resource usage of services.
    """
    
    def __init__(self, max_history=60):
        """
        Initialize the service monitor.
        
        Args:
            max_history: Maximum number of data points to keep in history
        """
        self.max_history = max_history
        self.service_data = {}  # Map of service name to monitoring data
        self.running = False
        self.executor = ThreadPoolExecutor(max_workers=4)
        
    def start_monitoring(self):
        """Start the monitoring process."""
        self.running = True
        logger.info("Service monitoring started")
        
    def stop_monitoring(self):
        """Stop the monitoring process."""
        self.running = False
        logger.info("Service monitoring stopped")
        
    async def update_service_data(self, service_name: str, pid: int) -> bool:
        """
        Update monitoring data for a service.
        
        Args:
            service_name: Name of the service
            pid: Process ID of the service
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.running:
                return False
                
            # Initialize service data if it doesn't exist
            if service_name not in self.service_data:
                self.service_data[service_name] = {
                    'cpu_percent': [],
                    'memory_percent': [],
                    'memory_mb': [],
                    'io_read_mb': [],
                    'io_write_mb': [],
                    'timestamps': [],
                    'uptime': 0,
                    'start_time': None,
                    'restarts': 0
                }
                
            # Get process information
            loop = asyncio.get_event_loop()
            stats = await loop.run_in_executor(
                self.executor,
                self._get_process_stats,
                pid
            )
            
            if not stats:
                return False
                
            # Update service data
            data = self.service_data[service_name]
            
            # Add new data points
            data['cpu_percent'].append(stats['cpu_percent'])
            data['memory_percent'].append(stats['memory_percent'])
            data['memory_mb'].append(stats['memory_mb'])
            data['io_read_mb'].append(stats['io_read_mb'])
            data['io_write_mb'].append(stats['io_write_mb'])
            data['timestamps'].append(datetime.now())
            
            # Set start time if not already set
            if data['start_time'] is None and stats['start_time'] is not None:
                data['start_time'] = stats['start_time']
                
            # Update uptime
            if data['start_time'] is not None:
                data['uptime'] = (datetime.now() - data['start_time']).total_seconds()
                
            # Limit history
            if len(data['cpu_percent']) > self.max_history:
                data['cpu_percent'] = data['cpu_percent'][-self.max_history:]
                data['memory_percent'] = data['memory_percent'][-self.max_history:]
                data['memory_mb'] = data['memory_mb'][-self.max_history:]
                data['io_read_mb'] = data['io_read_mb'][-self.max_history:]
                data['io_write_mb'] = data['io_write_mb'][-self.max_history:]
                data['timestamps'] = data['timestamps'][-self.max_history:]
                
            return True
        except Exception as e:
            logger.error(f"Error updating service data for {service_name}: {str(e)}")
            return False
            
    def _get_process_stats(self, pid: int) -> Optional[Dict[str, Any]]:
        """
        Get process statistics.
        
        Args:
            pid: Process ID
            
        Returns:
            Dictionary of process statistics or None if the process doesn't exist
        """
        try:
            process = psutil.Process(pid)
            
            # Get CPU usage (percent)
            cpu_percent = process.cpu_percent(interval=0.1)
            
            # Get memory usage
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024  # Convert to MB
            memory_percent = process.memory_percent()
            
            # Get I/O counters
            io_counters = process.io_counters()
            io_read_mb = io_counters.read_bytes / 1024 / 1024  # Convert to MB
            io_write_mb = io_counters.write_bytes / 1024 / 1024  # Convert to MB
            
            # Get process start time
            start_time = datetime.fromtimestamp(process.create_time())
            
            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory_percent,
                'memory_mb': memory_mb,
                'io_read_mb': io_read_mb,
                'io_write_mb': io_write_mb,
                'start_time': start_time
            }
        except psutil.NoSuchProcess:
            logger.warning(f"Process with PID {pid} no longer exists")
            return None
        except Exception as e:
            logger.error(f"Error getting process stats for PID {pid}: {str(e)}")
            return None
            
    def reset_service_data(self, service_name: str):
        """
        Reset monitoring data for a service.
        
        Args:
            service_name: Name of the service
        """
        if service_name in self.service_data:
            self.service_data[service_name] = {
                'cpu_percent': [],
                'memory_percent': [],
                'memory_mb': [],
                'io_read_mb': [],
                'io_write_mb': [],
                'timestamps': [],
                'uptime': 0,
                'start_time': None,
                'restarts': 0
            }
            
    def increment_restart_count(self, service_name: str):
        """
        Increment the restart count for a service.
        
        Args:
            service_name: Name of the service
        """
        if service_name in self.service_data:
            self.service_data[service_name]['restarts'] += 1
            
    def get_service_stats(self, service_name: str) -> Dict[str, Any]:
        """
        Get monitoring data for a service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Dictionary of service monitoring data
        """
        # Ensure the service exists in service_data
        if service_name not in self.service_data:
            self.reset_service_data(service_name)

        data = self.service_data[service_name]
        
        # Calculate averages, using sensible defaults for empty lists
        cpu_history = data['cpu_percent']
        mem_history = data['memory_percent']
        mem_mb_history = data['memory_mb']
        
        cpu_avg = sum(cpu_history) / len(cpu_history) if cpu_history else 0
        mem_avg = sum(mem_history) / len(mem_history) if mem_history else 0
        mem_mb_avg = sum(mem_mb_history) / len(mem_mb_history) if mem_mb_history else 0
        
        # Calculate current values (or 0 if no data)
        cpu_current = cpu_history[-1] if cpu_history else 0
        mem_current = mem_history[-1] if mem_history else 0
        mem_mb_current = mem_mb_history[-1] if mem_mb_history else 0
        
        # Return formatted stats
        return {
            'cpu_history': cpu_history,
            'memory_history': mem_history,
            'memory_mb_history': mem_mb_history,
            'io_read_history': data['io_read_mb'],
            'io_write_history': data['io_write_mb'],
            'timestamps': data['timestamps'],
            'uptime': data['uptime'],
            'start_time': data['start_time'],
            'restarts': data['restarts'],
            'cpu_avg': cpu_avg,
            'cpu_current': cpu_current,
            'memory_avg': mem_avg,
            'memory_current': mem_current,
            'memory_mb_avg': mem_mb_avg,
            'memory_mb_current': mem_mb_current
        }
        
    def get_all_service_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Get monitoring data for all services.
        
        Returns:
            Dictionary of service name to monitoring data
        """
        result = {}
        for service_name in self.service_data:
            result[service_name] = self.get_service_stats(service_name)
        return result