#!/usr/bin/env python3
"""
Configuration Tests

Tests the server's handling of configuration directives according to test.conf:

Main server (port 8080):
- server_name localhost test-server.local www.test-server.local
- client_max_body_size 5m
- Root location (/) allows GET, POST
- Static location (/static) allows only GET with autoindex on
- Exact match location (/exact) allows only GET
- Upload location (/upload) allows only POST
- Custom error pages for 404 and 5xx errors

Alternative server (port 8081):
- client_max_body_size 2m
- Root location (/) allows only GET

Alternative server (port 8082):
- client_max_body_size 1m
- /small_limit location has client_max_body_size 50k
- /large_limit location has client_max_body_size 3m
"""

import os
import tempfile
import shutil
import socket
import random
import time
import re
import requests
from pathlib import Path
from urllib.parse import urlparse
from core.test_case import TestCase
from core.path_utils import get_tester_root, resolve_path

class ConfigTests(TestCase):
    """Tests the server's handling of configuration directives."""
    
    def setup(self):
        """Set up temporary directory for uploads."""
        self.temp_dir = tempfile.mkdtemp()
        self.uploaded_files = []
        self.test_conf_path = resolve_path('data/conf/test.conf')
        
    def teardown(self):
        """Clean up temporary files."""
        for file_path in self.uploaded_files:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass
        
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_server_name(self):
        """
        Test server_name configuration.
        
        This test verifies the server_name directive in test.conf:
        server {
            listen 8080;
            server_name localhost test-server.local www.test-server.local;
            ...
        }
        """
        # Test each server name defined in the config
        server_names = ['localhost', 'test-server.local', 'www.test-server.local']
        
        for server_name in server_names:
            try:
                # Send request with the specific Host header
                response = self.runner.send_request('GET', '/', headers={'Host': server_name + ':8080'})
                
                # Should return 200 OK
                self.assert_equals(response.status_code, 200, 
                                f"Request with Host: {server_name} did not return 200 OK")
                
                # Verify the response contains expected root content
                self.assert_true('Webserv Test Page' in response.text, 
                            f"Response for {server_name} doesn't contain expected content")
                
            except requests.RequestException as e:
                self.assert_true(False, f"Request with Host: {server_name} failed: {e}")
        
        # Test with an invalid server name
        invalid_server = f'invalid-{random.randint(1000, 9999)}.local'
        try:
            # Send request with an invalid Host header
            response = self.runner.send_request('GET', '/', headers={'Host': invalid_server})
            
            # Should either:
            # 1. Return 200 OK (using default server)
            # 2. Return 400 Bad Request (rejecting invalid host)
            self.assert_true(response.status_code in [200, 400], 
                        f"Request with invalid Host: {invalid_server} returned unexpected status {response.status_code}")
            
            # If it returns 200, it should be serving the default server content
            if response.status_code == 200:
                self.assert_true('Webserv Test Page' in response.text, 
                            f"Default server for invalid host {invalid_server} doesn't serve expected content")
        
        except requests.RequestException as e:
            self.assert_true(False, f"Request with invalid Host: {invalid_server} failed: {e}")
    
    def test_client_max_body_size_limit(self):
        """
        Test that client_max_body_size actually limits large requests.
        
        This test verifies that the server correctly enforces maximum body size limits
        by testing against the dedicated test server on port 8082.
        """
        import io
        
        # We'll use the server on port 8082 that has a 1MB global limit
        base_url = f"http://{self.runner.host}:8082"
        
        # Create a request that exceeds the 1MB global limit but is reasonable in size
        large_size = 1.1 * 1024 * 1024  # 1.1MB (exceeds the 1MB limit)
        large_data = io.BytesIO(b'X' * int(large_size))
        files = {'file': ('large.txt', large_data, 'text/plain')}

        try:
            response = requests.post(f"{base_url}/small_limit", files=files, timeout=3)
            # If we get a 413, size limit is working
            self.assert_equals(response.status_code, 413, 
                             f"Expected 413 for oversized request, got {response.status_code}")
        except requests.RequestException as e:
            self.assert_true(False, f"Request failed during size limit test: {e}")
    
    def test_allowed_methods(self):
        """
        Test allowed methods configuration.

        This test verifies the method restrictions defined in test.conf:
        location / {
            methods GET POST;
        }
        
        location /static {
            methods GET;
        }
        
        location = /exact {
            methods GET;
        }
        """
        # Test cases to just two critical paths
        test_cases = [
            # (path, allowed_method, disallowed_method)
            ('/', 'GET', 'DELETE'),  # Root allows GET but not DELETE
            ('/static/', 'GET', 'POST')  # Static allows GET but not POST
        ]
        
        for path, allowed_method, disallowed_method in test_cases:
            # Test allowed method
            try:
                response = self.runner.send_request(allowed_method, path)
                # Check that it's not 405 (method not allowed)
                self.assert_true(response.status_code != 405, 
                            f"{allowed_method} should be allowed for {path}")
            except requests.RequestException as e:
                self.assert_true(False, f"Request with allowed method {allowed_method} to {path} failed: {e}")
            
            # Test disallowed method
            try:
                data = {'test': 'data'} if disallowed_method != 'GET' else None
                response = self.runner.send_request(disallowed_method, path, data=data)
                
                # Verify it's rejected with 405 Method Not Allowed
                self.assert_equals(response.status_code, 405, 
                            f"Disallowed method {disallowed_method} was accepted for {path}")
                
                # Should include Allow header
                self.assert_true('Allow' in response.headers, 
                            "405 response missing Allow header")
                    
            except requests.RequestException as e:
                self.assert_true(False, f"Request with disallowed method {disallowed_method} to {path} failed: {e}")
    
    def test_root_directive(self):
        """Test root directive for resource resolution."""
        # Try to access a file that should exist in the root directory
        try:
            response = self.runner.send_request('GET', '/index.html')
            
            # Should return 200 OK
            self.assert_equals(response.status_code, 200, 
                             f"Expected 200 OK for /index.html, got {response.status_code}")
            
            # Verify it returned HTML content
            self.assert_true('Content-Type' in response.headers, "Missing Content-Type header")
            content_type = response.headers['Content-Type'].lower()
            self.assert_true('text/html' in content_type, f"Expected HTML content, got: {content_type}")
        except requests.RequestException as e:
            self.assert_true(False, f"Request failed for /index.html: {e}")
    
    def test_index_directive(self):
        """Test index directive for directory requests."""
        # Request a directory (should serve the index file)
        try:
            response = self.runner.send_request('GET', '/')
            
            # Should return 200 OK with the index file
            self.assert_equals(response.status_code, 200, "Directory request failed")
            
            # Verify it returned HTML content (typically index.html)
            self.assert_true('Content-Type' in response.headers, "Missing Content-Type header")
            content_type = response.headers['Content-Type'].lower()
            self.assert_true('text/html' in content_type, f"Expected HTML content, got: {content_type}")
            
            # Check for index.html content marker
            self.assert_true('<!-- Test: index_file_location -->' in response.text,
                           "Response doesn't contain expected index.html content")
        except requests.RequestException as e:
            self.assert_true(False, f"Request failed for root directory: {e}")
    
    def test_autoindex(self):
        """
        Test autoindex directive for directory listing.
        
        This test verifies the autoindex setting defined in test.conf:
        location /static {
            root tests/data/www;
            autoindex on;
            methods GET;
        }
        """
        # Test the specific path configured with autoindex on
        autoindex_path = '/static/'
        
        try:
            # Send request to the directory
            response = self.runner.send_request('GET', autoindex_path)
            
            # Should return 200 OK with a directory listing
            self.assert_equals(response.status_code, 200, f"Autoindex path {autoindex_path} did not return 200 OK")
            
            # Verify content type is HTML
            self.assert_true('Content-Type' in response.headers, "Missing Content-Type header")
            content_type = response.headers['Content-Type'].lower()
            self.assert_true('text/html' in content_type, f"Expected HTML content, got: {content_type}")
            
            # Check for common directory listing indicators in the HTML
            directory_listing_indicators = [
                'index of',           # Almost universally present in directory listings
                'parent directory',   # Common navigational element in directory listings
                '<a href'             # Links to files/directories (essential in any listing)
            ]
            
            # Check if at least one indicator is present
            found_indicator = False
            for indicator in directory_listing_indicators:
                if indicator.lower() in response.text.lower():
                    found_indicator = True
                    break
            
            self.assert_true(found_indicator, 
                        f"Directory listing not detected at {autoindex_path} even though autoindex is enabled")
            
            # Test a non-autoindex location for comparison
            non_autoindex_path = '/'
            try:
                non_autoindex_response = self.runner.send_request('GET', non_autoindex_path)
                
                # Should not contain directory listing indicators
                non_autoindex_has_listing = False
                for indicator in directory_listing_indicators:
                    if indicator.lower() in non_autoindex_response.text.lower():
                        # Skip indicators that might appear in normal content
                        if indicator.lower() in ['<li>', '<ul>', '<a href']:
                            continue
                            
                        non_autoindex_has_listing = True
                        break
                
                self.assert_false(non_autoindex_has_listing, 
                                "Directory listing detected at root path where autoindex should be disabled")
            except requests.RequestException as e:
                self.assert_true(False, f"Request failed for non-autoindex path: {e}")
                            
        except requests.RequestException as e:
            self.assert_true(False, f"Request failed during autoindex test: {e}")
    
    def test_error_pages(self):
        """
        Test custom error page configuration.
        
        This test verifies that the server uses the custom error pages defined in test.conf:
        error_page 404 tests/data/www/404.html;
        error_page 500 502 503 504 tests/data/www/50x.html;
        
        It explicitly checks that the custom error page from the tester environment is served,
        not just any error page.
        """
        # Test 404 error page
        try:
            # Generate a unique non-existent path
            non_existent_path = f'/non-existent-{os.urandom(4).hex()}'
            response = self.runner.send_request('GET', non_existent_path)
            
            # Should return 404 Not Found
            self.assert_equals(response.status_code, 404, 
                             f"Expected 404 for non-existent path, got {response.status_code}")
            
            # The most important check: verify this is OUR custom error page by looking for the unique marker
            # that exists in tests/data/www/404.html
            self.assert_true('<!-- Test: custom_404_page -->' in response.text, 
                        "Custom 404 page from tester environment not detected. " +
                        "Server is not using the configured error page.")
        
        except requests.RequestException as e:
            self.assert_true(False, f"Request failed during 404 error page test: {e}")
        
    def test_redirect_directive(self):
        """
        Test HTTP redirection configuration.
        
        This test verifies the redirect defined in test.conf:
        location /old-page {
            return 301 /new-page;
        }
        """
        # Test the specific redirect path defined in the config
        redirect_path = '/old-page'
        
        try:
            # Don't follow redirects so we can inspect the response
            response = self.runner.send_request('GET', redirect_path, allow_redirects=False)
            
            # Should return 301 Moved Permanently
            self.assert_equals(response.status_code, 301, 
                            f"Expected 301 redirect for {redirect_path}, got {response.status_code}")
            
            # Should include Location header
            self.assert_true('Location' in response.headers, 
                        "Redirect missing Location header")
            
            # Location should point to the configured target
            target_path = '/new-page'
            location = response.headers['Location']
            
            # The Location header might be an absolute or relative URL
            self.assert_true(location.endswith(target_path), 
                        f"Expected redirect to {target_path}, got {location}")
            
            # Now follow the redirect and verify it works
            try:
                follow_response = self.runner.send_request('GET', redirect_path, allow_redirects=True)
                
                # Should successfully follow the redirect
                self.assert_true(follow_response.status_code < 400, 
                            f"Following redirect failed with status {follow_response.status_code}")
            except requests.RequestException as e:
                self.assert_true(False, f"Failed to follow redirect: {e}")
            
        except requests.RequestException as e:
            self.assert_true(False, f"Request failed during redirect test: {e}")
    
    def test_multiple_ports(self):
        """
        Test server listening on multiple ports.
        
        This test verifies that the server listens on additional ports as configured in test.conf:
        server {
            listen 8081;
            ...
        }
        
        server {
            listen 8082;
            ...
        }
        """
        # Test the alternative ports defined in the config
        alt_ports = [8081, 8082]
        
        for port in alt_ports:
            try:
                # Create a temporary socket to test port
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex((self.runner.host, port))
                sock.close()
                
                # Port should be open
                self.assert_equals(result, 0, f"Port {port} is not open. Server should be listening on this port.")
                
                # Send a request to verify the server is properly responding
                temp_url = f"http://{self.runner.host}:{port}/"
                try:
                    response = requests.get(temp_url, timeout=2)
                    
                    # Should return 200 OK
                    self.assert_equals(response.status_code, 200, 
                                    f"Request to port {port} did not return 200 OK")
                    
                    # Should serve root content
                    self.assert_true('Webserv Test Page' in response.text, 
                                f"Response from port {port} doesn't contain expected content")
                except requests.RequestException as e:
                    self.assert_true(False, f"HTTP request to port {port} failed: {e}")
                
            except socket.error as e:
                self.assert_true(False, f"Connection to port {port} failed: {e}")
        
        # Verify each port has the correct server configuration
        # Port 8081 has a 2m client_max_body_size limit
        # We can only test this indirectly by checking the server's behavior
        try:
            # Test with a request to server on port 8081
            response = requests.get(f"http://{self.runner.host}:8081/", 
                                headers={'Host': 'localhost'}, 
                                timeout=2)
            self.assert_equals(response.status_code, 200, 
                            "Request to port 8081 with Host: localhost did not return 200 OK")
            
        except requests.RequestException as e:
            self.assert_true(False, f"Request to port 8081 failed: {e}")
    
    def test_listen_port_validity(self):
        """Test that the server's main port is properly configured."""
        # Verify the main port is working
        try:
            response = requests.get(f"http://{self.runner.host}:{self.runner.port}/", timeout=1)
            self.assert_true(response.status_code < 500, f"Server error on main port: {response.status_code}")
            
            # Check for Server header as basic validation
            self.assert_true('Server' in response.headers, "Missing Server header in response")
            
        except requests.RequestException as e:
            self.assert_true(False, f"Main port test failed: {e}. Server must listen on configured port.")
    
    def test_location_block_exact_match(self):
        """
        Test exact path matching in location blocks.
        
        This test verifies the exact match location defined in test.conf:
        location = /exact {
            root tests/data/www/exact_match;
            index exact.html;
            methods GET;
        }
        """
        # Test the exact path defined in the config
        exact_path = '/exact'
        
        try:
            # Send request to the exact path
            response = self.runner.send_request('GET', exact_path)
            
            # Should return 200 OK with the index file
            self.assert_equals(response.status_code, 200, f"Exact path {exact_path} did not return 200 OK")
            
            # Verify content type is HTML
            self.assert_true('Content-Type' in response.headers, "Missing Content-Type header")
            content_type = response.headers['Content-Type'].lower()
            self.assert_true('text/html' in content_type, f"Expected HTML content, got: {content_type}")
            
            # Verify content contains the marker from exact.html
            self.assert_true('EXACT_MATCH_LOCATION_CONTENT' in response.text, 
                        "Exact match location did not serve the expected content")
            
            # Now try a similar path that should not match exactly
            variant_path = f"{exact_path}/extra"
            try:
                variant_response = self.runner.send_request('GET', variant_path)
                
                # Should get a different response (typically 404 Not Found)
                self.assert_true(response.status_code != variant_response.status_code, 
                            f"Path {variant_path} should not match the exact location but returned same status code")
                
                # If we get a 404, it should be the custom 404 page
                if variant_response.status_code == 404:
                    self.assert_true('<!-- Test: custom_404_page -->' in variant_response.text,
                                "Custom 404 page not served for path outside exact match")
            except requests.RequestException as e:
                self.assert_true(False, f"Request to {variant_path} failed: {e}")
            
        except requests.RequestException as e:
            self.assert_true(False, f"Request failed during exact match test: {e}")

    def test_location_block_prefix_match(self):
        """
        Test prefix-based matching in location blocks.
        
        This test verifies the prefix match locations defined in test.conf:
        location /static {
            root tests/data/www;
            autoindex on;
            methods GET;
        }
        
        location /static/nested {
            root tests/data/www;
            index nested.html;
            methods GET;
        }
        """
        # Test both prefix locations defined in the config
        static_path = '/static/prefix_match.html'
        nested_path = '/static/nested/'
        
        try:
            # Test /static/prefix_match.html
            static_response = self.runner.send_request('GET', static_path)
            
            # Should return 200 OK
            self.assert_equals(static_response.status_code, 200, 
                            f"Static path {static_path} did not return 200 OK")
            
            # Verify content contains the marker from prefix_match.html
            self.assert_true('STATIC_PREFIX_LOCATION_CONTENT' in static_response.text, 
                        "Static prefix location did not serve the expected content")
            
            # Test /static/nested/
            try:
                nested_response = self.runner.send_request('GET', nested_path)
                
                # Should return 200 OK with the index file
                self.assert_equals(nested_response.status_code, 200, 
                                f"Nested path {nested_path} did not return 200 OK")
                
                # Verify content contains the marker from nested.html
                self.assert_true('NESTED_PREFIX_LOCATION_CONTENT' in nested_response.text, 
                            "Nested prefix location did not serve the expected content")
                
                # Test priority: longer prefix should take precedence over shorter prefix
                # The /static/nested/ should serve nested.html even though /static/ has autoindex
                nested_has_autoindex = False
                autoindex_indicators = ['<directory', '<dir', 'index of', 'directory listing']
                
                for indicator in autoindex_indicators:
                    if indicator.lower() in nested_response.text.lower():
                        nested_has_autoindex = True
                        break
                
                self.assert_false(nested_has_autoindex, 
                                "Nested location incorrectly served directory listing instead of index file")
            except requests.RequestException as e:
                self.assert_true(False, f"Request to {nested_path} failed: {e}")
            
        except requests.RequestException as e:
            self.assert_true(False, f"Request failed during prefix match test: {e}")

    def test_location_block_inheritance(self):
        """Test directive inheritance in nested location blocks."""
        # Static location should inherit the server-level error page
        static_path = '/static/'
        expected_marker = '<!-- Test: custom_404_page -->'
        
        try:
            # Generate a non-existent resource under /static/
            non_existent = f"{static_path}non-existent-{int(time.time())}-{random.randint(1000, 9999)}"
            response = self.runner.send_request('GET', non_existent)
            
            # Verify it returns a 404 status code
            self.assert_equals(response.status_code, 404, 
                            f"Expected 404 status code for non-existent path {non_existent}")
            
            # Verify it contains the marker from the server-level error page
            self.assert_true(expected_marker in response.text, 
                            f"Static location does not inherit the server-level error page")
                
        except requests.RequestException as e:
            self.assert_true(False, f"Request failed during inheritance test: {e}")

    def test_location_specific_error_pages(self):
        """Test location-specific error page configurations."""
        # Define expected markers for different error pages
        server_error_marker = '<!-- Test: custom_404_page -->'
        nested_error_marker = '<!-- Test: nested_404_page -->'  # Add this to your nested error page
        
        # Test paths with their expected markers
        test_cases = [
            # path, marker_should_contain, description
            ('/', server_error_marker, 'server-level error page'),
            ('/static/', server_error_marker, 'inherited error page'),
            ('/static/nested/', nested_error_marker, 'location-specific error page')
        ]
        
        # Test each path with a non-existent resource
        for base_path, expected_marker, description in test_cases:
            try:
                # Generate a unique non-existent path
                non_existent = f"{base_path}non-existent-{int(time.time())}-{random.randint(1000, 9999)}"
                response = self.runner.send_request('GET', non_existent)
                
                # Check if response status is 404
                self.assert_equals(response.status_code, 404, 
                                f"Expected 404 status for {description} at {base_path}")
                
                # Check if response contains the expected marker
                marker_found = expected_marker in response.text
                self.assert_true(marker_found, 
                            f"Error page at {base_path} does not contain expected marker for {description}")
                
                self.logger.debug(f"Successfully verified {description} at {base_path}")
                
            except requests.RequestException as e:
                self.assert_true(False, f"Request failed during error page test at {base_path}: {e}")

    def test_location_block_priority(self):
        """Test priority handling for overlapping location blocks."""
        # Check that the server handles potentially overlapping routes without errors
        test_paths = [
            '/static',      # Might match exact '/static' and prefix '/static/'
            '/static/',     # Should match prefix '/static/'
            '/static/test', # Should match prefix '/static/'
            '/files.jpg',   # Might match regex for extensions
            '/files/test.jpg'  # Might match both prefix '/files/' and extension regex
        ]
        
        for path in test_paths:
            try:
                response = self.runner.send_request('GET', path)
                
                # We don't know the expected behavior without seeing the config,
                # but we can check that the server handles it without error
                self.assert_true(response.status_code < 500,
                               f"Server error with potentially overlapping location {path}: {response.status_code}")
            except requests.RequestException as e:
                self.assert_true(False, f"Request to potentially overlapping location {path} failed: {e}")
    
    def test_directory_index_order(self):
        """
        Test index file selection order.
        
        This test verifies that directories serve the configured index files:
        For /:
            root tests/data/www;
            index index.html;
        
        For /static/nested:
            root tests/data/www;
            index nested.html;
        """
        # Test directories with configured index files
        test_cases = [
            ('/', 'index.html', 'Webserv Test Page'),  # Root location
            ('/static/nested/', 'nested.html', 'Nested Prefix Location')  # Nested location
        ]
        
        for directory, index_file, expected_content in test_cases:
            try:
                response = self.runner.send_request('GET', directory)
                
                # Should return 200 OK
                self.assert_equals(response.status_code, 200, 
                                f"Directory {directory} did not return 200 OK")
                
                # Verify content type is HTML
                self.assert_true('Content-Type' in response.headers, "Missing Content-Type header")
                content_type = response.headers['Content-Type'].lower()
                self.assert_true('text/html' in content_type, 
                            f"Expected HTML content for {directory}, got: {content_type}")
                
                # Verify content contains expected markers
                self.assert_true(expected_content in response.text, 
                            f"Directory {directory} did not serve the expected index file {index_file}")
                
            except requests.RequestException as e:
                self.assert_true(False, f"Request failed for {directory}: {e}")
        
        # Test a directory with no index file
        try:
            # Create a path that shouldn't have an index file
            no_index_path = '/static/non-existent-directory/'
            no_index_response = self.runner.send_request('GET', no_index_path)
            
            # Should either return directory listing (autoindex on) or 404 Not Found
            self.assert_true(no_index_response.status_code in [200, 404], 
                        f"Unexpected status code {no_index_response.status_code} for directory with no index")
            
            if no_index_response.status_code == 200:
                # Should be a directory listing since /static has autoindex on
                directory_listing_indicators = ['<directory', '<dir', 'index of', 'directory listing']
                found_listing = False
                
                for indicator in directory_listing_indicators:
                    if indicator.lower() in no_index_response.text.lower():
                        found_listing = True
                        break
                
                self.assert_true(found_listing, 
                            "Directory without index file didn't show directory listing when autoindex is on")
            elif no_index_response.status_code == 404:
                # Should be the custom 404 error page
                self.assert_true('<!-- Test: custom_404_page -->' in no_index_response.text,
                             "Custom 404 page not served for non-existent directory")
        
        except requests.RequestException as e:
            self.assert_true(False, f"Request failed for directory with no index: {e}")
    
    def test_directory_index_fallback(self):
        """Test fallback behavior when index files are missing."""
        # Ensure the test directory exists
        empty_dir = resolve_path('data/www/static/empty')
        os.makedirs(empty_dir, exist_ok=True)
        
        # Test two key scenarios: autoindex enabled vs disabled
        test_cases = [
            ('/static/empty/', True),   # autoindex enabled
            ('/nonexistent/', False)    # autoindex disabled (should get 404)
        ]
        
        valid_fallback_found = False
        
        for url_path, autoindex_enabled in test_cases:
            try:
                response = self.runner.send_request('GET', url_path)
                
                if autoindex_enabled:
                    # Should return 200 with directory listing
                    self.assert_equals(response.status_code, 200,
                                     f"Directory {url_path} with autoindex enabled should return 200, got {response.status_code}")
                    # Check if it's a directory listing
                    content_type = response.headers.get('Content-Type', '').lower()
                    self.assert_true('text/html' in content_type,
                                   f"Directory listing should return HTML content type")
                    directory_indicators = ['<directory', '<li>', '<table', '<a href']
                    found_indicator = any(indicator in response.text.lower() for indicator in directory_indicators)
                    self.assert_true(found_indicator,
                                   f"Directory listing should contain directory indicators")
                else:
                    # Should return 403 or 404
                    self.assert_true(response.status_code in [403, 404],
                                   f"Directory {url_path} without autoindex should return 403 or 404, got {response.status_code}")
                
                valid_fallback_found = True
                
            except requests.RequestException as e:
                self.assert_true(False, f"Request failed for directory index fallback test {url_path}: {e}")
        
        # Fail if no valid fallback behavior found
        self.assert_true(valid_fallback_found, 
                        "No valid fallback behavior for missing index files. Directory handling is required.")
    
    def test_virtual_host_server_name(self):
        """Test server_name handling with different domains."""
        try:
            # Test localhost 
            localhost_response = self.runner.send_request('GET', '/', headers={'Host': 'localhost'})
            
            # Test example.com
            example_response = self.runner.send_request('GET', '/', headers={'Host': 'example.com'})
            
            # Both should be handled without server errors
            self.assert_true(localhost_response.status_code < 500, 
                            f"Server error with Host: localhost, status {localhost_response.status_code}")
            self.assert_true(example_response.status_code < 500, 
                            f"Server error with Host: example.com, status {example_response.status_code}")
            
        except requests.RequestException as e:
            # Fail if the requests fail - Host header handling is required
            self.assert_true(False, f"Virtual host test failed: {e}. Host header handling is required.")
    
    def test_virtual_host_default_server(self):
        """
        Test default server selection when no host matches.
        
        This test verifies that when a request comes with a Host header that doesn't
        match any server_name in the configuration, the server correctly selects the
        default server (first one in the config).
        
        Default server in test.conf:
        server {
            listen 8080;
            server_name localhost test-server.local www.test-server.local;
            ...
        }
        """
        # Test with an invalid Host that should not match any server_name
        invalid_host = f'nonexistent-{random.randint(1000, 9999)}.local'
        
        try:
            # Send request with the invalid Host header
            response = self.runner.send_request('GET', '/', headers={'Host': invalid_host})
            
            # Verify the server responds with 200 OK (default server)
            self.assert_equals(response.status_code, 200, 
                            f"Request with invalid Host: {invalid_host} did not return 200 OK")
            
            # Verify it serves the default server content by checking for the unique marker in index.html
            self.assert_true('<!-- Test: index_file_location -->' in response.text, 
                        "Default server content not detected. Server is not using the expected default server.")
            
        except requests.RequestException as e:
            self.assert_true(False, f"Request failed during default server test: {e}")
        
    def test_client_max_body_size_per_location(self):
        """
        Test client_max_body_size settings per location block.
        
        This test verifies the essential functionality of client_max_body_size limits:
        1. Basic size limit enforcement
        2. Different limits for different locations
        
        It uses the most efficient test cases from test.conf:
        - /small_limit on port 8082 with 50KB limit
        - /large_limit on port 8082 with 3MB limit
        """
        import io
        
        # Base URL for testing
        base_url = f"http://{self.runner.host}:8082"
        
        # Test case 1: Test the smallest limit (50KB) on /small_limit
        small_limit_path = '/small_limit'
        small_limit_url = f"{base_url}{small_limit_path}"
        
        # Test 1A: Upload below the limit (40KB) - should succeed
        size_below = 40 * 1024  # 40KB
        data_below = io.BytesIO(b'X' * size_below)
        files_below = {'file': (f'test_40KB.txt', data_below, 'text/plain')}
        
        # Test 1B: Upload above the limit (60KB) - should fail
        size_above = 60 * 1024  # 60KB
        data_above = io.BytesIO(b'X' * size_above)
        files_above = {'file': (f'test_60KB.txt', data_above, 'text/plain')}
        
        # Execute test case 1A: Below limit
        try:
            response = requests.post(small_limit_url, files=files_below, timeout=2)
            self.assert_true(response.status_code != 413, 
                        f"Upload of 40KB to {small_limit_url} was rejected but should be accepted")
        except requests.RequestException as e:
            self.assert_true(False, f"Upload of 40KB to {small_limit_url} failed unexpectedly: {e}")
        
        # Execute test case 1B: Above limit
        try:
            response = requests.post(small_limit_url, files=files_above, timeout=3)
            self.assert_equals(response.status_code, 413, 
                            f"Upload of 60KB to {small_limit_url} was accepted but should be rejected")
        except requests.RequestException as e:
            self.assert_true(False, f"Upload of 60KB to {small_limit_url} failed but should return 413: {e}")
        
        # Test case 2: Test a higher limit on a different location
        # Use a medium-sized upload (500KB) to /large_limit (3MB limit)
        large_limit_path = '/large_limit'
        large_limit_url = f"{base_url}{large_limit_path}"
        
        # Medium size upload (500KB) - should succeed under the 3MB limit
        medium_size = 500 * 1024  # 500KB
        medium_data = io.BytesIO(b'X' * medium_size)
        medium_files = {'file': (f'test_500KB.txt', medium_data, 'text/plain')}
        
        try:
            response = requests.post(large_limit_url, files=medium_files, timeout=5)
            self.assert_true(response.status_code != 413, 
                        f"Upload of 500KB to {large_limit_url} was rejected but should be accepted")
        except requests.RequestException as e:
            self.assert_true(False, f"Upload of 500KB to {large_limit_url} failed unexpectedly: {e}")
            
    def test_file_resolution(self):
        """
        Test basic file resolution and serving.
        
        This test verifies that the server can correctly resolve and serve static files
        from the configured root directory:
        
        location / {
            root tests/data/www;
            index index.html;
            methods GET POST;
        }
        """
        # Test files with their expected content markers
        test_files = [
            # path, content marker, description
            ('/index.html', '<!-- Test: index_file_location -->', 'index file'),
            ('/', '<!-- Test: index_file_location -->', 'root with auto-index'),
            ('/static/prefix_match.html', 'STATIC_PREFIX_LOCATION_CONTENT', 'static prefix file')
        ]
        
        for path, marker, description in test_files:
            try:
                # Request the file
                response = self.runner.send_request('GET', path)
                
                # Should return 200 OK
                self.assert_equals(response.status_code, 200,
                               f"Failed to retrieve {description}: {path} returned {response.status_code}")
                
                # Verify content contains expected marker
                self.assert_true(marker in response.text, 
                            f"{description} doesn't contain expected content marker")
                            
            except requests.RequestException as e:
                self.assert_true(False, f"Request failed for {description}: {e}")
                    
    def test_try_files_fallback(self):
        """
        Test fallback behavior for missing files.
        
        This test verifies the server's behavior when a requested file is not found.
        It should return a 404 error and serve the custom error page defined in test.conf:
        
        error_page 404 tests/data/www/404.html;
        """
        # Generate a unique non-existent path
        non_existent_path = f"/non-existent-{random.randint(1000, 9999)}.html"
        
        try:
            # Request a non-existent file
            response = self.runner.send_request('GET', non_existent_path)
            
            # Should return 404 Not Found
            self.assert_equals(response.status_code, 404, 
                            f"Expected 404 for non-existent file, got {response.status_code}")
            
            # Verify content type is HTML
            self.assert_true('Content-Type' in response.headers, "Missing Content-Type header for 404 response")
            content_type = response.headers['Content-Type'].lower()
            self.assert_true('text/html' in content_type, 
                        f"Expected HTML content for 404 page, got: {content_type}")
            
            # Verify custom error page is served by checking for the unique marker
            self.assert_true('<!-- Test: custom_404_page -->' in response.text, 
                        "Custom 404 error page not served for non-existent file")
            
        except requests.RequestException as e:
            self.assert_true(False, f"Request failed during file fallback test: {e}")
        
        # Test a non-existent directory with trailing slash
        # This might have different behavior depending on the server
        non_existent_dir = f"/non-existent-dir-{random.randint(1000, 9999)}/"
        
        try:
            # Request a non-existent directory
            dir_response = self.runner.send_request('GET', non_existent_dir)
            
            # Should return 404 Not Found
            self.assert_equals(dir_response.status_code, 404, 
                            f"Expected 404 for non-existent directory, got {dir_response.status_code}")
            
            # Verify custom error page is served
            self.assert_true('<!-- Test: custom_404_page -->' in dir_response.text, 
                        "Custom 404 error page not served for non-existent directory")
            
        except requests.RequestException as e:
            self.assert_true(False, f"Request failed during directory fallback test: {e}")

    
    def test_directory_trailing_slash(self):
        """
        Test handling of directories with and without trailing slashes.
        
        This test verifies the server's behavior when accessing directories
        with and without trailing slashes, particularly for the /static location
        which has autoindex enabled.
        
        location /static {
            root tests/data/www;
            autoindex on;
            methods GET;
        }
        """
        # Test directory that exists and has autoindex enabled
        directory = '/static'
        
        try:
            # Try without trailing slash
            no_slash_response = self.runner.send_request('GET', directory, allow_redirects=False)
            
            # Try with trailing slash
            slash_response = self.runner.send_request('GET', directory + '/', allow_redirects=False)
            
            # Both should return valid responses (not server errors)
            self.assert_true(no_slash_response.status_code < 500, 
                            f"Server error for {directory}: {no_slash_response.status_code}")
            self.assert_true(slash_response.status_code < 500, 
                            f"Server error for {directory}/: {slash_response.status_code}")
            
            # Common behavior for directories without trailing slash is to redirect
            if no_slash_response.status_code in [301, 302, 303, 307, 308]:
                self.assert_true('Location' in no_slash_response.headers, 
                            f"Redirect from {directory} missing Location header")
                
                # Verify Location points to the slash-terminated version
                location = no_slash_response.headers.get('Location', '')
                self.assert_true(location.endswith('/'), 
                            f"Location header for {directory} doesn't end with /: {location}")
                
                # If we follow redirects, we should get a 200 OK
                try:
                    redirect_followed = self.runner.send_request('GET', directory, allow_redirects=True)
                    self.assert_equals(redirect_followed.status_code, 200, 
                                    f"Following redirect for {directory} failed")
                except requests.RequestException as e:
                    self.assert_true(False, f"Failed to follow redirect from {directory}: {e}")
                
            # With trailing slash, should directly serve a directory listing (200 OK)
            self.assert_equals(slash_response.status_code, 200, 
                            f"Directory {directory}/ did not return 200 OK")
            
            # Verify it returns HTML
            self.assert_true('Content-Type' in slash_response.headers, 
                        f"Missing Content-Type header for {directory}/")
            content_type = slash_response.headers['Content-Type'].lower()
            self.assert_true('text/html' in content_type, 
                        f"Expected HTML for {directory}/, got: {content_type}")
            
            # Verify it returns a directory listing (since autoindex is on)
            listing_indicators = ['<directory', '<dir', 'index of', 'directory listing',
                                '<table', '<a href', 'parent directory']
            found_indicator = False
            
            for indicator in listing_indicators:
                if indicator.lower() in slash_response.text.lower():
                    found_indicator = True
                    break
            
            self.assert_true(found_indicator, 
                        f"Directory listing not detected for {directory}/")
            
        except requests.RequestException as e:
            self.assert_true(False, f"Request failed during trailing slash test: {e}")

    def test_cgi_resolver(self):
            """
            Test that the CGI resolver correctly identifies interpreters and updates the config.
            
            This test verifies that the CGI resolver can:
            1. Detect the available interpreters on the system
            2. Update the test.conf file with the correct paths
            3. Report on missing interpreters
            """
            # Import CGI resolver
            from core.cgi_resolver import CGIResolver
            
            # Create resolver instance
            resolver = CGIResolver(self.test_conf_path)
            
            # Test .py extension which should be available on all testing systems
            python_path = resolver.find_interpreter('.py')
            self.assert_true(python_path is not None, "Python interpreter should be available on testing systems")
            
            # Test binary CGI scripts which don't need an interpreter
            cgi_path = resolver.find_interpreter('.cgi')
            self.assert_equals(cgi_path, "", "Binary CGI scripts don't need an interpreter")
            
            # Full config update test
            result = resolver.update_config()
            self.assert_true(result, "Config update should succeed")
            
            # Check if the configuration file was actually updated
            with open(self.test_conf_path, 'r') as f:
                content = f.read()
                
            # Verify Python interpreter path was set in the config
            python_pattern = r'cgi_handler \.py (.+);'
            match = re.search(python_pattern, content)
            self.assert_true(match is not None, "Python interpreter path should be set in config")
            
            if match:
                path_in_config = match.group(1).strip()
                self.assert_equals(path_in_config, python_path, 
                                f"Interpreter path in config ({path_in_config}) should match detected path ({python_path})")