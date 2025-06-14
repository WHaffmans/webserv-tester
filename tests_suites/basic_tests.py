#!/usr/bin/env python3
"""
Basic Tests

Smoke tests for fundamental webserver functionality.
These tests verify core features and serve as a quick check that the server is working properly.
"""

import requests
import time
from core.test_case import TestCase

class BasicTests(TestCase):
    """Smoke tests for fundamental webserver functionality."""
    
    def test_server_running(self):
        """Test that the server is running and responsive."""
        self.assert_true(self.runner.wait_for_server(), "Server is not responsive")
    
    def test_get_request(self):
        """Test basic GET request."""
        response = self.runner.send_request('GET', '/')
        self.assert_true(response.status_code < 500, f"Server error: {response.status_code}")
    
    def test_response_headers(self):
        """Test that responses include basic required headers."""
        response = self.runner.send_request('GET', '/')
        
        self.assert_true('Date' in response.headers, "Missing Date header")
        self.assert_true('Server' in response.headers, "Missing Server header")
        
        # Check Content-Type presence for non-empty responses
        if len(response.content) > 0:
            self.assert_true('Content-Type' in response.headers, "Missing Content-Type header")
            self.assert_true('Content-Length' in response.headers, "Missing Content-Length header")
    
    def test_static_file(self):
        """Test serving a static file."""
        # Try a few common static file paths
        paths = ['/index.html', '/favicon.ico', '/css/style.css', '/js/script.js', '/img/logo.png']
        
        found_one = False
        for path in paths:
            try:
                response = self.runner.send_request('GET', path)
                if response.status_code == 200:
                    found_one = True
                    self.assert_true('Content-Type' in response.headers, f"Missing Content-Type for {path}")
                    break
            except requests.RequestException:
                continue
        
        # If none of the common paths worked, we'll test the root
        if not found_one:
            response = self.runner.send_request('GET', '/')
            self.assert_true(response.status_code < 500, f"Server error: {response.status_code}")

    def test_main_page_content(self):
        """Test that the main page contains the expected HTML comment identifier."""
        response = self.runner.send_request('GET', '/')
        
        # Verify status code is 200 OK
        self.assert_equals(response.status_code, 200, "Main page did not return 200 OK")
        
        # Check content type is HTML
        self.assert_true('Content-Type' in response.headers, "Missing Content-Type header")
        content_type = response.headers['Content-Type'].lower()
        self.assert_true('text/html' in content_type, f"Expected HTML content, got: {content_type}")
        
        # Verify content contains the expected HTML comment identifier
        # This specific comment is present in the index.html file as shown in the provided files
        self.assert_true('<!-- Test: index_file_location -->' in response.text, 
                        "Main page does not contain the expected identifier")