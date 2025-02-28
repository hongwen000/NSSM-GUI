from PyQt5 import QtWidgets, QtGui, QtCore, QtChart
import datetime
import logging
from typing import Dict, Any, Optional, List

from ..utils.monitoring import ServiceMonitor

logger = logging.getLogger("nssm_gui.dashboard")

class ServiceResourceWidget(QtWidgets.QGroupBox):
    """Widget for displaying service resource usage."""
    
    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI components."""
        layout = QtWidgets.QVBoxLayout(self)
        
        # Create chart view
        self.chart_view = QtChart.QChartView()
        self.chart_view.setRenderHint(QtGui.QPainter.Antialiasing)
        self.chart_view.setMinimumHeight(200)
        
        # Create chart
        self.chart = QtChart.QChart()
        self.chart.setAnimationOptions(QtChart.QChart.SeriesAnimations)
        self.chart.legend().setVisible(True)
        self.chart.legend().setAlignment(QtCore.Qt.AlignBottom)
        
        # Create axes
        self.axis_x = QtChart.QDateTimeAxis()
        self.axis_x.setFormat("hh:mm:ss")
        self.axis_x.setTitleText("Time")
        
        self.axis_y = QtChart.QValueAxis()
        self.axis_y.setLabelFormat("%.1f")
        
        # Set axes on chart
        self.chart.addAxis(self.axis_x, QtCore.Qt.AlignBottom)
        self.chart.addAxis(self.axis_y, QtCore.Qt.AlignLeft)
        
        # Set chart on view
        self.chart_view.setChart(self.chart)
        
        # Stats labels
        stats_layout = QtWidgets.QHBoxLayout()
        
        self.current_label = QtWidgets.QLabel("Current: N/A")
        self.average_label = QtWidgets.QLabel("Average: N/A")
        self.peak_label = QtWidgets.QLabel("Peak: N/A")
        
        stats_layout.addWidget(self.current_label)
        stats_layout.addWidget(self.average_label)
        stats_layout.addWidget(self.peak_label)
        
        # Add to layout
        layout.addWidget(self.chart_view)
        layout.addLayout(stats_layout)
        
    def setup_chart(self, title, y_title, color, max_value=100):
        """Set up the chart with specific parameters."""
        self.chart.setTitle(title)
        self.axis_y.setTitleText(y_title)
        self.axis_y.setRange(0, max_value)
        
        # Create series
        self.series = QtChart.QLineSeries()
        self.series.setName(title)
        
        # Set series color
        pen = self.series.pen()
        pen.setColor(color)
        pen.setWidth(2)
        self.series.setPen(pen)
        
        # Add series to chart
        self.chart.addSeries(self.series)
        
        # Attach axes to series
        self.series.attachAxis(self.axis_x)
        self.series.attachAxis(self.axis_y)
        
    def update_data(self, values, timestamps):
        """Update the chart with new data."""
        # Clear existing points
        self.series.clear()
        
        # Add data points
        for i, value in enumerate(values):
            timestamp = timestamps[i]
            msecs = int(timestamp.timestamp() * 1000)  # Convert to milliseconds
            self.series.append(msecs, value)
            
        # Update axes ranges
        if timestamps:
            start_time = int(timestamps[0].timestamp() * 1000)
            end_time = int(timestamps[-1].timestamp() * 1000)
            self.axis_x.setRange(
                QtCore.QDateTime.fromMSecsSinceEpoch(start_time),
                QtCore.QDateTime.fromMSecsSinceEpoch(end_time)
            )
            
        # Calculate stats
        if values:
            current = values[-1]
            average = sum(values) / len(values)
            peak = max(values)
            
            self.current_label.setText(f"Current: {current:.1f}")
            self.average_label.setText(f"Average: {average:.1f}")
            self.peak_label.setText(f"Peak: {peak:.1f}")
            
            # Adjust y-axis to fit data
            max_value = peak * 1.2  # Add 20% margin
            self.axis_y.setRange(0, max(max_value, 0.1))  # Ensure non-zero range
            
class ServiceDashboardDialog(QtWidgets.QDialog):
    """Dialog for monitoring service resource usage."""
    
    def __init__(self, parent=None, service_name="", pid=None, service_monitor=None):
        super().__init__(parent)
        self.setWindowTitle(f'Service Dashboard - {service_name}')
        self.setGeometry(100, 100, 800, 600)
        
        self.service_name = service_name
        self.pid = pid
        self.service_monitor = service_monitor
        
        self.init_ui()
        self.setup_update_timer()
        
    def init_ui(self):
        """Initialize the UI components."""
        layout = QtWidgets.QVBoxLayout(self)
        
        # Service info
        info_layout = QtWidgets.QHBoxLayout()
        
        self.service_label = QtWidgets.QLabel(f"<b>Service:</b> {self.service_name}")
        self.pid_label = QtWidgets.QLabel(f"<b>PID:</b> {self.pid or 'N/A'}")
        self.uptime_label = QtWidgets.QLabel("<b>Uptime:</b> N/A")
        self.status_label = QtWidgets.QLabel("<b>Status:</b> Unknown")
        
        info_layout.addWidget(self.service_label)
        info_layout.addWidget(self.pid_label)
        info_layout.addWidget(self.uptime_label)
        info_layout.addWidget(self.status_label)
        info_layout.addStretch(1)
        
        # Add restart count
        self.restart_label = QtWidgets.QLabel("<b>Restarts:</b> 0")
        info_layout.addWidget(self.restart_label)
        
        layout.addLayout(info_layout)
        
        # Tabs for different metrics
        self.tabs = QtWidgets.QTabWidget()
        layout.addWidget(self.tabs)
        
        # CPU tab
        self.cpu_tab = QtWidgets.QWidget()
        cpu_layout = QtWidgets.QVBoxLayout(self.cpu_tab)
        
        self.cpu_chart = ServiceResourceWidget("CPU Usage")
        self.cpu_chart.setup_chart("CPU Usage", "Percent", QtGui.QColor(0, 128, 255))
        
        cpu_layout.addWidget(self.cpu_chart)
        
        # Memory tab
        self.memory_tab = QtWidgets.QWidget()
        memory_layout = QtWidgets.QVBoxLayout(self.memory_tab)
        
        self.memory_percent_chart = ServiceResourceWidget("Memory Usage (Percent)")
        self.memory_percent_chart.setup_chart("Memory Usage", "Percent", QtGui.QColor(255, 128, 0))
        
        self.memory_mb_chart = ServiceResourceWidget("Memory Usage (MB)")
        self.memory_mb_chart.setup_chart("Memory Usage", "MB", QtGui.QColor(0, 192, 0), 1000)
        
        memory_layout.addWidget(self.memory_percent_chart)
        memory_layout.addWidget(self.memory_mb_chart)
        
        # I/O tab
        self.io_tab = QtWidgets.QWidget()
        io_layout = QtWidgets.QVBoxLayout(self.io_tab)
        
        self.io_read_chart = ServiceResourceWidget("Disk Read (MB)")
        self.io_read_chart.setup_chart("Disk Read", "MB", QtGui.QColor(128, 0, 128), 1000)
        
        self.io_write_chart = ServiceResourceWidget("Disk Write (MB)")
        self.io_write_chart.setup_chart("Disk Write", "MB", QtGui.QColor(128, 128, 0), 1000)
        
        io_layout.addWidget(self.io_read_chart)
        io_layout.addWidget(self.io_write_chart)
        
        # Add tabs
        self.tabs.addTab(self.cpu_tab, "CPU")
        self.tabs.addTab(self.memory_tab, "Memory")
        self.tabs.addTab(self.io_tab, "I/O")
        
        # Bottom buttons
        button_layout = QtWidgets.QHBoxLayout()
        
        self.refresh_button = QtWidgets.QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_data)
        
        self.auto_refresh_check = QtWidgets.QCheckBox("Auto-refresh")
        self.auto_refresh_check.setChecked(True)
        
        self.restart_button = QtWidgets.QPushButton("Restart Service")
        self.restart_button.clicked.connect(self.restart_service)
        
        self.close_button = QtWidgets.QPushButton("Close")
        self.close_button.clicked.connect(self.accept)
        
        button_layout.addWidget(self.refresh_button)
        button_layout.addWidget(self.auto_refresh_check)
        button_layout.addStretch(1)
        button_layout.addWidget(self.restart_button)
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
        
    def setup_update_timer(self):
        """Set up a timer for automatic updates."""
        self.update_timer = QtCore.QTimer(self)
        self.update_timer.timeout.connect(self.refresh_data)
        self.update_timer.start(1000)  # Update every second
        
    def refresh_data(self):
        """Refresh the dashboard data."""
        if not self.service_monitor:
            return
            
        # Check if auto-refresh is enabled
        if not self.auto_refresh_check.isChecked():
            return
            
        # Get service stats
        stats = self.service_monitor.get_service_stats(self.service_name)
        
        # Update service info
        if stats['start_time']:
            uptime_seconds = stats['uptime']
            hours, remainder = divmod(uptime_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            uptime_str = f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
            self.uptime_label.setText(f"<b>Uptime:</b> {uptime_str}")
            
        self.restart_label.setText(f"<b>Restarts:</b> {stats['restarts']}")
        
        # Update charts
        if stats['cpu_history'] and stats['timestamps']:
            self.cpu_chart.update_data(
                stats['cpu_history'],
                stats['timestamps']
            )
            
        if stats['memory_history'] and stats['timestamps']:
            self.memory_percent_chart.update_data(
                stats['memory_history'],
                stats['timestamps']
            )
            
        if stats['memory_mb_history'] and stats['timestamps']:
            self.memory_mb_chart.update_data(
                stats['memory_mb_history'],
                stats['timestamps']
            )
            
        if stats['io_read_history'] and stats['timestamps']:
            self.io_read_chart.update_data(
                stats['io_read_history'],
                stats['timestamps']
            )
            
        if stats['io_write_history'] and stats['timestamps']:
            self.io_write_chart.update_data(
                stats['io_write_history'],
                stats['timestamps']
            )
            
    def restart_service(self):
        """Restart the service."""
        reply = QtWidgets.QMessageBox.question(
            self, "Confirm Restart",
            f"Are you sure you want to restart the service '{self.service_name}'?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )
        
        if reply == QtWidgets.QMessageBox.Yes:
            self.accept()
            
    def closeEvent(self, event):
        """Handle the close event."""
        # Stop the update timer
        self.update_timer.stop()
        event.accept()
        
class ServiceMonitoringDialog(QtWidgets.QDialog):
    """Dialog for monitoring multiple services."""
    
    def __init__(self, parent=None, services=None, service_monitor=None):
        super().__init__(parent)
        self.setWindowTitle('Service Monitoring')
        self.setGeometry(100, 100, 1000, 700)
        
        self.services = services or []
        self.service_monitor = service_monitor
        
        self.init_ui()
        self.setup_update_timer()
        self.refresh_data()
        
    def init_ui(self):
        """Initialize the UI components."""
        layout = QtWidgets.QVBoxLayout(self)
        
        # Main splitter
        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        
        # Services table
        self.table_widget = QtWidgets.QWidget()
        table_layout = QtWidgets.QVBoxLayout(self.table_widget)
        
        # Filter controls
        filter_layout = QtWidgets.QHBoxLayout()
        
        filter_label = QtWidgets.QLabel("Filter:")
        self.filter_input = QtWidgets.QLineEdit()
        self.filter_input.setPlaceholderText("Filter services...")
        self.filter_input.textChanged.connect(self.apply_filter)
        
        filter_layout.addWidget(filter_label)
        filter_layout.addWidget(self.filter_input)
        
        # Services table
        self.services_table = QtWidgets.QTableWidget()
        self.services_table.setColumnCount(8)
        self.services_table.setHorizontalHeaderLabels([
            'Service Name', 'PID', 'Status', 'CPU (%)', 'Memory (%)', 
            'Memory (MB)', 'Uptime', 'Restarts'
        ])
        self.services_table.horizontalHeader().setStretchLastSection(True)
        self.services_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.services_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.services_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.services_table.setSortingEnabled(True)
        self.services_table.doubleClicked.connect(self.show_service_dashboard)
        
        table_layout.addLayout(filter_layout)
        table_layout.addWidget(self.services_table)
        
        # Overview charts
        self.charts_widget = QtWidgets.QWidget()
        charts_layout = QtWidgets.QVBoxLayout(self.charts_widget)
        
        # Chart tabs
        self.chart_tabs = QtWidgets.QTabWidget()
        
        # CPU chart tab
        self.cpu_tab = QtWidgets.QWidget()
        cpu_layout = QtWidgets.QVBoxLayout(self.cpu_tab)
        
        self.cpu_chart = QtChart.QChartView()
        self.cpu_chart.setRenderHint(QtGui.QPainter.Antialiasing)
        self.cpu_chart.setMinimumHeight(200)
        
        self.cpu_chart_obj = QtChart.QChart()
        self.cpu_chart_obj.setTitle("CPU Usage by Service")
        self.cpu_chart_obj.setAnimationOptions(QtChart.QChart.SeriesAnimations)
        self.cpu_chart_obj.legend().setVisible(True)
        self.cpu_chart_obj.legend().setAlignment(QtCore.Qt.AlignBottom)
        
        self.cpu_chart.setChart(self.cpu_chart_obj)
        
        cpu_layout.addWidget(self.cpu_chart)
        
        # Memory chart tab
        self.memory_tab = QtWidgets.QWidget()
        memory_layout = QtWidgets.QVBoxLayout(self.memory_tab)
        
        self.memory_chart = QtChart.QChartView()
        self.memory_chart.setRenderHint(QtGui.QPainter.Antialiasing)
        self.memory_chart.setMinimumHeight(200)
        
        self.memory_chart_obj = QtChart.QChart()
        self.memory_chart_obj.setTitle("Memory Usage by Service")
        self.memory_chart_obj.setAnimationOptions(QtChart.QChart.SeriesAnimations)
        self.memory_chart_obj.legend().setVisible(True)
        self.memory_chart_obj.legend().setAlignment(QtCore.Qt.AlignBottom)
        
        self.memory_chart.setChart(self.memory_chart_obj)
        
        memory_layout.addWidget(self.memory_chart)
        
        # Add tabs
        self.chart_tabs.addTab(self.cpu_tab, "CPU Usage")
        self.chart_tabs.addTab(self.memory_tab, "Memory Usage")
        
        charts_layout.addWidget(self.chart_tabs)
        
        # Add widgets to splitter
        self.splitter.addWidget(self.table_widget)
        self.splitter.addWidget(self.charts_widget)
        
        # Set initial sizes
        self.splitter.setSizes([500, 300])
        
        layout.addWidget(self.splitter)
        
        # Bottom buttons
        button_layout = QtWidgets.QHBoxLayout()
        
        self.refresh_button = QtWidgets.QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_data)
        
        self.auto_refresh_check = QtWidgets.QCheckBox("Auto-refresh")
        self.auto_refresh_check.setChecked(True)
        
        self.view_button = QtWidgets.QPushButton("View Dashboard")
        self.view_button.clicked.connect(self.show_service_dashboard)
        
        self.close_button = QtWidgets.QPushButton("Close")
        self.close_button.clicked.connect(self.accept)
        
        button_layout.addWidget(self.refresh_button)
        button_layout.addWidget(self.auto_refresh_check)
        button_layout.addStretch(1)
        button_layout.addWidget(self.view_button)
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
        
    def setup_update_timer(self):
        """Set up a timer for automatic updates."""
        self.update_timer = QtCore.QTimer(self)
        self.update_timer.timeout.connect(self.refresh_data)
        self.update_timer.start(1000)  # Update every second
        
    def refresh_data(self):
        """Refresh the monitoring data."""
        if not self.service_monitor:
            return
            
        # Check if auto-refresh is enabled
        if not self.auto_refresh_check.isChecked():
            return
            
        # Get all service stats
        all_stats = self.service_monitor.get_all_service_stats()
        
        # Update services table
        self.update_services_table(all_stats)
        
        # Update charts
        self.update_charts(all_stats)
        
    def update_services_table(self, all_stats):
        """Update the services table with current data."""
        # Save current selection
        current_row = -1
        if self.services_table.selectionModel().hasSelection():
            current_row = self.services_table.currentRow()
            
        # Clear table
        self.services_table.setRowCount(0)
        
        # Add services
        for i, service in enumerate(self.services):
            stats = all_stats.get(service.name, {})
            
            self.services_table.insertRow(i)
            
            # Service name
            self.services_table.setItem(i, 0, QtWidgets.QTableWidgetItem(service.name))
            
            # PID
            pid_item = QtWidgets.QTableWidgetItem(str(service.pid) if service.pid else "N/A")
            self.services_table.setItem(i, 1, pid_item)
            
            # Status
            status_item = QtWidgets.QTableWidgetItem(service.state)
            if service.state.lower() == "running":
                status_item.setForeground(QtGui.QColor(0, 128, 0))  # Green
            elif service.state.lower() == "stopped":
                status_item.setForeground(QtGui.QColor(128, 0, 0))  # Red
            self.services_table.setItem(i, 2, status_item)
            
            # CPU
            cpu_current = stats.get('cpu_current', 0)
            cpu_item = QtWidgets.QTableWidgetItem(f"{cpu_current:.1f}")
            self.services_table.setItem(i, 3, cpu_item)
            
            # Memory %
            mem_current = stats.get('memory_current', 0)
            mem_item = QtWidgets.QTableWidgetItem(f"{mem_current:.1f}")
            self.services_table.setItem(i, 4, mem_item)
            
            # Memory MB
            mem_mb_current = stats.get('memory_mb_current', 0)
            mem_mb_item = QtWidgets.QTableWidgetItem(f"{mem_mb_current:.1f}")
            self.services_table.setItem(i, 5, mem_mb_item)
            
            # Uptime
            uptime_seconds = stats.get('uptime', 0)
            hours, remainder = divmod(uptime_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            uptime_str = f"{int(hours)}:{int(minutes):02}:{int(seconds):02}"
            uptime_item = QtWidgets.QTableWidgetItem(uptime_str)
            self.services_table.setItem(i, 6, uptime_item)
            
            # Restarts
            restarts = stats.get('restarts', 0)
            restart_item = QtWidgets.QTableWidgetItem(str(restarts))
            self.services_table.setItem(i, 7, restart_item)
            
        # Restore selection
        if current_row >= 0 and current_row < self.services_table.rowCount():
            self.services_table.selectRow(current_row)
            
        # Resize columns to content
        self.services_table.resizeColumnsToContents()
        
    def update_charts(self, all_stats):
        """Update the overview charts."""
        # Clear existing charts
        self.cpu_chart_obj.removeAllSeries()
        self.memory_chart_obj.removeAllSeries()
        
        # Create series for CPU and memory charts
        cpu_series = QtChart.QBarSeries()
        memory_series = QtChart.QPieSeries()
        
        # Get data for charts
        cpu_data = []
        memory_data = []
        
        for service in self.services:
            stats = all_stats.get(service.name, {})
            
            if stats:
                # CPU data
                cpu_current = stats.get('cpu_current', 0)
                cpu_data.append((service.name, cpu_current))
                
                # Memory data
                mem_mb_current = stats.get('memory_mb_current', 0)
                memory_data.append((service.name, mem_mb_current))
                
        # Sort data by usage (descending)
        cpu_data.sort(key=lambda x: x[1], reverse=True)
        memory_data.sort(key=lambda x: x[1], reverse=True)
        
        # Limit to top 10 services
        cpu_data = cpu_data[:10]
        memory_data = memory_data[:10]
        
        # Create CPU chart
        if cpu_data:
            cpu_bar_set = QtChart.QBarSet("CPU Usage")
            
            for name, value in cpu_data:
                cpu_bar_set.append(value)
                
            cpu_series.append(cpu_bar_set)
            
            self.cpu_chart_obj.addSeries(cpu_series)
            
            # Create axes
            axis_x = QtChart.QBarCategoryAxis()
            axis_x.append([name for name, _ in cpu_data])
            
            axis_y = QtChart.QValueAxis()
            axis_y.setRange(0, max([val for _, val in cpu_data]) * 1.2)  # Add 20% margin
            axis_y.setTitleText("CPU Usage (%)")
            
            self.cpu_chart_obj.addAxis(axis_x, QtCore.Qt.AlignBottom)
            self.cpu_chart_obj.addAxis(axis_y, QtCore.Qt.AlignLeft)
            
            cpu_series.attachAxis(axis_x)
            cpu_series.attachAxis(axis_y)
            
        # Create memory chart
        if memory_data:
            for name, value in memory_data:
                slice = memory_series.append(name, value)
                slice.setLabelVisible()
                
            self.memory_chart_obj.addSeries(memory_series)
            
    def apply_filter(self):
        """Apply filter to the services table."""
        filter_text = self.filter_input.text().lower()
        
        for i in range(self.services_table.rowCount()):
            service_name = self.services_table.item(i, 0).text().lower()
            match = filter_text in service_name
            self.services_table.setRowHidden(i, not match)
            
    def show_service_dashboard(self):
        """Show the detailed dashboard for the selected service."""
        # Get the selected service
        if not self.services_table.selectionModel().hasSelection():
            QtWidgets.QMessageBox.warning(
                self, "No Selection", "Please select a service to view."
            )
            return
            
        current_row = self.services_table.currentRow()
        service_name = self.services_table.item(current_row, 0).text()
        pid_text = self.services_table.item(current_row, 1).text()
        
        pid = None
        if pid_text != "N/A":
            try:
                pid = int(pid_text)
            except ValueError:
                pass
                
        # Find the corresponding service object
        service = next((s for s in self.services if s.name == service_name), None)
        
        if not service:
            QtWidgets.QMessageBox.warning(
                self, "Service Not Found", f"Service '{service_name}' not found."
            )
            return
            
        # Show the dashboard
        dashboard = ServiceDashboardDialog(
            self, service_name, pid, self.service_monitor
        )
        dashboard.exec_()
        
    def closeEvent(self, event):
        """Handle the close event."""
        # Stop the update timer
        self.update_timer.stop()
        event.accept()