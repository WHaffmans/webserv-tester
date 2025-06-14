#!/usr/bin/env python3
"""
Test Runner

Manages the execution of test cases against the webserver.
Provides utility methods for sending requests and validating responses.
"""

import requests
import socket
import time
from requests.exceptions import RequestException
from urllib.parse import urljoin
from core.logger import get_logger

class TestRunner:
    """Handles execution of test cases against the webserver."""
    
    def __init__(self, host, port, timeout, results):
        """
        Initialize the test runner.
        
        Args:
            host (str): Server hostname or IP
            port (int): Server port
            timeout (int): Request timeout in seconds
            results (TestResults): Results collector instance
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.base_url = f"http://{host}:{port}"
        self.results = results
        self.logger = get_logger()
    
    def get_url(self, path):
        """
        Construct a full URL from a path.
        
        Args:
            path (str): URL path
            
        Returns:
            str: Complete URL
        """
        return urljoin(self.base_url, path)
    
    def wait_for_server(self, max_retries=5, retry_delay=1):
        """
        Wait for the server to become available.
        
        Args:
            max_retries (int): Maximum number of connection attempts
            retry_delay (int): Delay between retries in seconds
            
        Returns:
            bool: True if server is available, False otherwise
        """
        self.logger.info(f"Waiting for server at {self.host}:{self.port}...")
        
        for i in range(max_retries):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex((self.host, self.port))
                sock.close()
                
                if result == 0:
                    self.logger.info("Server is available")
                    return True
                
                self.logger.debug(f"Attempt {i+1}/{max_retries}: Server not available, retrying in {retry_delay}s")
                time.sleep(retry_delay)
                
            except socket.error as e:
                self.logger.debug(f"Socket error: {e}")
                time.sleep(retry_delay)
        
        self.logger.error(f"Server at {self.host}:{self.port} is not available after {max_retries} attempts")
        return False
    
    def send_request(self, method, path, **kwargs):
        """
        Send an HTTP request to the server.
        
        Args:
            method (str): HTTP method (GET, POST, etc.)
            path (str): URL path
            **kwargs: Additional arguments to pass to requests
            
        Returns:
            requests.Response: HTTP response object
            
        Raises:
            RequestException: If the request fails
        """
        url = self.get_url(path)
        
        # Set default timeout if not provided
        if 'timeout' not in kwargs:
            kwargs['timeout'] = self.timeout
        
        self.logger.debug(f"Sending {method} request to {url}")
        
        try:
            response = requests.request(method, url, **kwargs)
            self.logger.debug(f"Received response: {response.status_code}")
            return response
        except RequestException as e:
            # Instead of logging to console, log as debug which will only go to the log file
            self.logger.debug(f"Request failed: {e}")
            raise
    
    def send_raw_request(self, raw_request, path=None):
        """
        Send a raw HTTP request to the server.
        
        Args:
            raw_request (str): Raw HTTP request
            path (str, optional): URL path (used for logging)
            
        Returns:
            str: Raw HTTP response
            
        Raises:
            socket.error: If socket communication fails
        """
        self.logger.debug(f"Sending raw request to {self.host}:{self.port}")
        
        try:
            # Create socket and connect
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((self.host, self.port))
            
            # Send request
            sock.sendall(raw_request.encode('utf-8'))
            
            # Receive response
            response = b''
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk
            
            sock.close()
            return response.decode('utf-8')
            
        except socket.error as e:
            # Log to debug instead of error
            self.logger.debug(f"Socket error: {e}")
            raise
    
    def check_status_code(self, response, expected_code):
        """
        Check if response has the expected status code.
        
        Args:
            response (requests.Response): HTTP response
            expected_code (int): Expected HTTP status code
            
        Returns:
            bool: True if status code matches, False otherwise
        """
        if response.status_code == expected_code:
            return True
        
        self.logger.debug(f"Status code mismatch: expected {expected_code}, got {response.status_code}")
        return False
    
    def check_header(self, response, header_name, expected_value=None, should_exist=True):
        """
        Check if a header exists and optionally matches a value.
        
        Args:
            response (requests.Response): HTTP response
            header_name (str): Header name to check
            expected_value (str, optional): Expected header value
            should_exist (bool): Whether the header should exist
            
        Returns:
            bool: True if header check passes, False otherwise
        """
        header_name = header_name.lower()  # HTTP headers are case-insensitive
        
        if header_name in response.headers:
            if not should_exist:
                self.logger.debug(f"Header '{header_name}' exists but shouldn't")
                return False
            
            if expected_value is not None:
                actual_value = response.headers[header_name]
                if expected_value != actual_value:
                    self.logger.debug(f"Header '{header_name}' value mismatch: expected '{expected_value}', got '{actual_value}'")
                    return False
            
            return True
        else:
            if should_exist:
                self.logger.debug(f"Header '{header_name}' not found")
                return False
            
            return True
    
    def check_body_contains(self, response, expected_content):
        """
        Check if response body contains expected content.
        
        Args:
            response (requests.Response): HTTP response
            expected_content (str): Content to check for
            
        Returns:
            bool: True if body contains expected content, False otherwise
        """
        if expected_content in response.text:
            return True
        
        self.logger.debug(f"Response body does not contain: '{expected_content}'")
        return False
    
    def check_body_equals(self, response, expected_content):
        """
        Check if response body equals expected content.
        
        Args:
            response (requests.Response): HTTP response
            expected_content (str): Expected body content
            
        Returns:
            bool: True if body equals expected content, False otherwise
        """
        if response.text == expected_content:
            return True
        
        self.logger.debug(f"Response body mismatch: expected '{expected_content}', got '{response.text}'")
        return False