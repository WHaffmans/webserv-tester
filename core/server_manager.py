#!/usr/bin/env python3
"""
Server Manager

Controls the webserver process for testing.
Responsible for starting, stopping, and monitoring the server.
"""

import subprocess
import os
import signal
import time
import socket
import psutil
from pathlib import Path
from core.logger import get_logger
from core.logger import Emoji, Colors

class ServerManager:
    """Manages the webserver process."""
    
    def __init__(self, server_path, config_path):
        """
        Initialize the server manager.
        
        Args:
            server_path (str): Path to the webserver executable
            config_path (str): Path to server configuration file
        """
        self.server_path = server_path
        self.config_path = config_path
        self.process = None
        self.logger = get_logger()
        self.stdout_file = None
        self.stderr_file = None
    
    def check_port_availability(self):
        """
        Check if the ports used by the webserver are available.
        Based on the test.conf file, checks ports 8080, 8081, and 8082.
        
        Returns:
            list: List of ports that are not available (already in use)
        """
        ports_to_check = [8080, 8081, 8082]  # Ports from test.conf
        unavailable_ports = []
        
        for port in ports_to_check:
            try:
                # Try to bind to the port
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    result = sock.bind(('localhost', port))
                    # If we get here, the port is available
            except OSError:
                # Port is already in use
                unavailable_ports.append(port)
        
        return unavailable_ports
    
    def start(self, timeout=5):
        """
        Start the webserver.
        
        Args:
            timeout (int): Maximum time to wait for server to start in seconds
            
        Returns:
            bool: True if server started successfully, False otherwise
        """
        # Check if required ports are available first
        unavailable_ports = self.check_port_availability()
        if unavailable_ports:
            self.logger.error(f"{Emoji.ERROR} Found ports already in use:")
            for port in unavailable_ports:
                self.logger.error(f"{Colors.RED}  Port {port} is already in use{Colors.RESET}")
            self.logger.error(f"{Colors.RED}Please free up these ports before running tests.{Colors.RESET}")
            self.logger.error(f"{Colors.YELLOW}  You can check what's using a port with: lsof -i :{unavailable_ports[0]} {Colors.RESET}")
            return False
        
        if self.process is not None:
            self.logger.debug("Server is already running")
            return True
        
        # Create log directory if it doesn't exist
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Open log files
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        self.stdout_file = open(log_dir / f"server-{timestamp}.out", "w")
        self.stderr_file = open(log_dir / f"server-{timestamp}.err", "w")
        
        self.logger.info(f"{Emoji.START} Starting server: {self.server_path} -c {self.config_path}")
        
        # Try different argument formats that webserv implementations might expect
        for args in [[self.server_path, "-c", self.config_path, "-v"],
                     [self.server_path, "-c", self.config_path],
                     [self.server_path, self.config_path],  # Config as positional argument
                     [self.server_path]]:
            try:
                self.process = subprocess.Popen(
                    args,
                    stdout=self.stdout_file,
                    stderr=self.stderr_file,
                    preexec_fn=os.setsid  # Create a new process group
                )
                
                # Wait briefly to see if the process crashes immediately
                time.sleep(0.5)
                
                if self.process.poll() is None:
                    return True
                
                # Process exited, try next option
                self._cleanup_process()
                
            except Exception:
                self._cleanup_process()
        
        self.logger.error(f"{Emoji.ERROR} Failed to start server")
        return False
    
    def stop(self):
        """
        Stop the webserver.
        
        Returns:
            bool: True if server stopped successfully, False otherwise
        """
        if self.process is None:
            self.logger.debug("No server process to stop")
            return True
        
        try:
            # Try graceful termination first
            os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            
            # Wait for process to terminate
            for _ in range(5):  # Wait up to 5 seconds
                if self.process.poll() is not None:
                    break
                time.sleep(1)
            
            # If process still running, force kill
            if self.process.poll() is None:
                self.logger.debug("Server did not terminate gracefully, forcing termination")
                os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
            
            self._cleanup_process()
            return True
            
        except Exception as e:
            self.logger.debug(f"Error stopping server: {e}")
            self._cleanup_process()
            return False
    
    def _cleanup_process(self):
        """Clean up process resources."""
        if self.process is not None:
            try:
                # Ensure process is terminated
                if self.process.poll() is None:
                    self.process.terminate()
                    self.process.wait(timeout=1)
            except:
                pass
            
            self.process = None
        
        # Close log files and delete if empty
        if self.stdout_file:
            stdout_path = self.stdout_file.name
            self.stdout_file.close()
            self.stdout_file = None
            
            # Check if file is empty and delete if it is
            if os.path.exists(stdout_path) and os.path.getsize(stdout_path) == 0:
                os.remove(stdout_path)
                
        if self.stderr_file:
            stderr_path = self.stderr_file.name
            self.stderr_file.close()
            self.stderr_file = None
            
            # Check if file is empty and delete if it is
            if os.path.exists(stderr_path) and os.path.getsize(stderr_path) == 0:
                os.remove(stderr_path)
    
    def is_running(self):
        """
        Check if the webserver is running.
        
        Returns:
            bool: True if server is running, False otherwise
        """
        if self.process is None:
            return False
        
        # Check if process is still running
        if self.process.poll() is not None:
            self.logger.debug(f"Server process exited with code {self.process.returncode}")
            self._cleanup_process()
            return False
        
        return True
    
    def restart(self):
        """
        Restart the webserver.
        
        Returns:
            bool: True if server restarted successfully, False otherwise
        """
        self.stop()
        return self.start()
    
    def get_stdout(self):
        """
        Get server stdout content.
        
        Returns:
            str: Content of stdout log file
        """
        if self.stdout_file:
            # Flush any buffered output
            self.stdout_file.flush()
            
            # Read file content
            with open(self.stdout_file.name, "r") as f:
                return f.read()
        
        return ""
    
    def get_stderr(self):
        """
        Get server stderr content.
        
        Returns:
            str: Content of stderr log file
        """
        if self.stderr_file:
            # Flush any buffered output
            self.stderr_file.flush()
            
            # Read file content
            with open(self.stderr_file.name, "r") as f:
                return f.read()
        
        return ""
    
    def __del__(self):
        """Ensure cleanup on object destruction."""
        self.stop()