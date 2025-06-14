#!/usr/bin/env python3
"""
HTTP Method Tests

Tests for specific HTTP methods (GET, POST, DELETE) implementation according to test.conf:

- Root location (/) allows GET, POST:
  location / {
    index index.html;
    methods GET POST;
  }

- Static location (/static) allows only GET:
  location /static {
    autoindex on;
    methods GET;
  }

- Exact match location (/exact) allows only GET:
  location = /exact {
    root data/www/exact_match;
    index exact.html;
    methods GET;
  }

- Upload location (/upload) allows only POST:
  location /upload {
    root data/www/upload;
    methods POST;
    upload_store data/uploads;
  }
"""

import requests
import time
import random
import os
import tempfile
from urllib.parse import urlencode
from core.test_case import TestCase

class MethodTests(TestCase):
    """Tests HTTP method implementations according to test.conf settings."""
    
    def setup(self):
        """Set up test environment for method tests."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_files = []
        
        # Create a small test file for POST tests
        self.test_file_path = os.path.join(self.temp_dir, "test_data.txt")
        with open(self.test_file_path, "w") as f:
            f.write("Test data for HTTP method tests")
        
        self.test_files.append(self.test_file_path)
        
        # Define locations based on test.conf
        self.locations = {
            'root': {
                'path': '/',
                'allowed_methods': ['GET', 'POST'],
            },
            'static': {
                'path': '/static/',
                'allowed_methods': ['GET'],
            },
            'exact': {
                'path': '/exact',
                'allowed_methods': ['GET'],
            },
            'upload': {
                'path': '/upload',
                'allowed_methods': ['POST'],
            }
        }
    
    def teardown(self):
        """Clean up test environment after method tests."""
        # Clean up temporary files
        for file_path in self.test_files:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    self.logger.debug(f"Error removing file {file_path}: {e}")
        
        # Remove temporary directory
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            try:
                os.rmdir(self.temp_dir)
            except Exception as e:
                self.logger.debug(f"Error removing directory {self.temp_dir}: {e}")
    
    def test_method_restrictions(self):
        """
        Test that HTTP methods are properly restricted based on location configuration.
        
        RFC 7231, Section 4.1 - Request Methods
        """
        for location_name, location_info in self.locations.items():
            path = location_info['path']
            allowed_methods = location_info['allowed_methods']
            
            # Test each allowed method for this location
            for method in allowed_methods:
                try:
                    if method == 'POST':
                        # For POST, send some test data
                        data = {'test_field': 'test_value'}
                        response = self.runner.send_request(method, path, data=data)
                    else:
                        # For other methods, no data needed
                        response = self.runner.send_request(method, path)
                    
                    # Response should not be 405 Method Not Allowed
                    self.assert_true(response.status_code != 405, 
                                   f"Method {method} should be allowed for {path} but got 405 Method Not Allowed")
                    
                    # For disallowed methods on this location, test that they are properly rejected
                    disallowed_methods = [m for m in ['GET', 'POST', 'DELETE'] if m not in allowed_methods]
                    
                    for disallowed_method in disallowed_methods:
                        try:
                            if disallowed_method == 'POST':
                                # For POST, send some test data
                                data = {'test_field': 'test_value'}
                                response = self.runner.send_request(disallowed_method, path, data=data)
                            else:
                                # For other methods, no data needed
                                response = self.runner.send_request(disallowed_method, path)
                            
                            # Should return 405 Method Not Allowed
                            self.assert_equals(response.status_code, 405, 
                                             f"Method {disallowed_method} should not be allowed for {path}")
                        except requests.RequestException as e:
                            # Connection errors are NOT acceptable - server should return proper HTTP status
                            self.assert_true(False, f"Server failed to respond with proper HTTP status for disallowed method {disallowed_method} on {path}: {e}")
                
                except requests.RequestException as e:
                    self.assert_true(False, f"Request failed for allowed method {method} on {path}: {e}")
    
    def test_405_method_not_allowed(self):
        """
        Test 405 Method Not Allowed for unsupported methods according to test.conf.
        
        RFC 7231, Section 6.5.5 - 405 Method Not Allowed
        """
        # Test cases for disallowed methods on specific paths
        test_cases = [
            # path, disallowed_method
            ('/static/', 'POST'),  # Static should only allow GET
            ('/upload', 'GET'),    # Upload should only allow POST
            ('/exact', 'POST'),    # Exact should only allow GET
            ('/', 'DELETE'),       # Root should only allow GET and POST
        ]
        
        for path, disallowed_method in test_cases:
            try:
                # Set up appropriate data for the method
                data = None
                if disallowed_method == 'POST':
                    data = {'test_field': 'test_value'}
                
                # Send the disallowed request
                response = self.runner.send_request(disallowed_method, path, data=data)
                
                # Verify it's rejected with 405 Method Not Allowed
                self.assert_equals(response.status_code, 405, 
                                 f"Disallowed method {disallowed_method} was accepted for {path}")
                
                # Check for Allow header
                self.assert_true('Allow' in response.headers, 
                               "405 response missing required Allow header")
                
                # Verify Allow header contains the allowed methods
                allow_header = response.headers['Allow']
                if path == '/static/' or path == '/exact':
                    self.assert_true('GET' in allow_header, 
                                   f"Allow header for {path} should include GET")
                    self.assert_false('POST' in allow_header, 
                                    f"Allow header for {path} should not include POST")
                elif path == '/upload':
                    self.assert_true('POST' in allow_header, 
                                   f"Allow header for {path} should include POST")
                    self.assert_false('GET' in allow_header, 
                                    f"Allow header for {path} should not include GET")
                elif path == '/':
                    self.assert_true('GET' in allow_header, 
                                   f"Allow header for {path} should include GET")
                    self.assert_true('POST' in allow_header, 
                                   f"Allow header for {path} should include POST")
                    self.assert_false('DELETE' in allow_header, 
                                    f"Allow header for {path} should not include DELETE")
                
            except requests.RequestException as e:
                # Connection errors might be expected for some disallowed methods
                self.logger.debug(f"Request exception for disallowed method {disallowed_method} on {path}: {e}")
    
    def test_allow_header(self):
        """
        Test that Allow header is properly set in 405 responses.
        
        RFC 7231, Section 7.4.1 - Allow
        """
        # Test cases for checking Allow header
        test_cases = [
            # path, disallowed_method, expected_allowed_methods
            ('/static/', 'POST', ['GET']),
            ('/upload', 'GET', ['POST']),
            ('/exact', 'DELETE', ['GET']),
            ('/', 'DELETE', ['GET', 'POST']),
        ]
        
        for path, disallowed_method, expected_allowed_methods in test_cases:
            try:
                # Set up appropriate data for the method
                data = None
                if disallowed_method == 'POST':
                    data = {'test_field': 'test_value'}
                
                # Send the disallowed request
                response = self.runner.send_request(disallowed_method, path, data=data)
                
                # For 405 responses, check the Allow header
                if response.status_code == 405:
                    self.assert_true('Allow' in response.headers, 
                                   f"405 response for {path} missing required Allow header")
                    
                    allow_header = response.headers['Allow']
                    
                    # Check that all expected methods are in the Allow header
                    for method in expected_allowed_methods:
                        self.assert_true(method in allow_header, 
                                       f"Allow header for {path} should include {method}")
                    
                    # Check that disallowed method is not in the Allow header
                    self.assert_false(disallowed_method in allow_header, 
                                    f"Allow header for {path} should not include {disallowed_method}")
                
            except requests.RequestException as e:
                self.logger.debug(f"Request exception for {disallowed_method} on {path}: {e}")
    
    def test_post_method(self):
        """
        Test basic POST functionality to allowed locations.
        
        RFC 7231, Section 4.3.3 - POST
        """
        # Test POST to root location (which allows POST)
        root_path = '/'
        
        try:
            # Create form data for POST
            post_data = {
                'field1': 'value1',
                'field2': 'value2',
                'test': f'test-{random.randint(1000, 9999)}'
            }
            
            # Send POST request
            response = self.runner.send_request('POST', root_path, data=post_data)
            
            # POST to root should be accepted (not 405)
            self.assert_true(response.status_code != 405, 
                           f"POST to {root_path} returned 405 Method Not Allowed but should be accepted")
            
            # Test POST to upload location
            upload_path = '/upload'
            
            # Create a file for upload
            with open(self.test_file_path, "rb") as f:
                files = {"file": ("test.txt", f, "text/plain")}
                
                # Send upload request
                upload_response = self.runner.send_request('POST', upload_path, files=files)
                
                # POST to upload should be accepted (not 405)
                self.assert_true(upload_response.status_code != 405, 
                               f"POST to {upload_path} returned 405 Method Not Allowed but should be accepted")
            
        except requests.RequestException as e:
            self.assert_true(False, f"Request failed for POST test: {e}")
            
    def test_delete_method(self):
        """
        Test DELETE method handling.
        
        RFC 7231, Section 4.3.5 - DELETE
        """
        # Test DELETE method on various paths
        test_paths = ['/', '/static/', '/exact', '/upload', '/nonexistent']
        
        for path in test_paths:
            try:
                # Send DELETE request
                response = self.runner.send_request('DELETE', path)
                
                # All locations in test.conf don't allow DELETE, so should return 405
                self.assert_equals(response.status_code, 405, 
                                 f"DELETE to {path} should return 405 Method Not Allowed")
                
                # Check for Allow header
                self.assert_true('Allow' in response.headers, 
                               f"405 response for DELETE to {path} missing required Allow header")
                
                # DELETE should not be in the Allow header
                self.assert_false('DELETE' in response.headers['Allow'], 
                                f"Allow header should not include DELETE")
                
            except requests.RequestException as e:
                # Connection errors might be expected for some paths with DELETE
                self.logger.debug(f"Request exception for DELETE on {path}: {e}")
    
    def test_unsupported_methods(self):
        """
        Test server response to unsupported HTTP methods.
        
        RFC 7231, Section 4.1 - Request Methods (general)
        RFC 7231, Section 6.5.5 - 405 Method Not Allowed
        RFC 7231, Section 6.6.2 - 501 Not Implemented
        """
        # Standard methods that server recognizes but doesn't support on root path
        # Based on test.conf, root path (/) only allows GET and POST
        standard_unsupported = ['PUT', 'PATCH', 'OPTIONS', 'HEAD']
        
        # Non-standard/unknown methods that server doesn't recognize
        unknown_methods = ['PROPFIND', 'CUSTOM', 'FOOBAR', 'TRACE']
        
        root_path = '/'
        
        # Test standard unsupported methods - should return 405
        for method in standard_unsupported:
            try:
                response = self.runner.send_request(method, root_path)
                
                self.assert_equals(response.status_code, 405, 
                            f"Standard unsupported method {method} should return 405 Method Not Allowed, got {response.status_code}")
                
                # Must include Allow header per RFC 7231
                self.assert_true('Allow' in response.headers, 
                            f"405 response for {method} missing required Allow header")
                
            except requests.RequestException as e:
                # Timeout or connection error means server isn't responding properly
                self.fail(f"Server failed to respond to standard method {method}: {e}")
        
        # Test unknown methods - should return 501
        for method in unknown_methods:
            try:
                response = self.runner.send_request(method, root_path)
                
                self.assert_equals(response.status_code, 501, 
                            f"Unknown method {method} should return 501 Not Implemented, got {response.status_code}")
                
            except requests.RequestException as e:
                # Timeout or connection error means server isn't responding properly
                self.fail(f"Server failed to respond to unknown method {method}: {e}")
                    
    def test_method_combinations(self):
        """
        Test combinations of methods on the same resource.
        
        RFC 7231, Section 4.1 - Request Methods (general)
        """
        # Test path that allows both GET and POST
        path = '/'
        
        try:
            # First, send a GET request
            get_response = self.runner.send_request('GET', path)
            
            # Should return 200 OK
            self.assert_equals(get_response.status_code, 200, 
                             f"GET to {path} returned unexpected status {get_response.status_code}")
            
            # Then send a POST request to the same resource
            post_data = {'field1': 'value1', 'field2': 'value2'}
            post_response = self.runner.send_request('POST', path, data=post_data)
            
            # Should not return 405 Method Not Allowed
            self.assert_true(post_response.status_code != 405, 
                           f"POST to {path} returned 405 Method Not Allowed but should be accepted")
            
            # Finally, send a DELETE request which should be rejected
            delete_response = self.runner.send_request('DELETE', path)
            
            # Should return 405 Method Not Allowed
            self.assert_equals(delete_response.status_code, 405, 
                             f"DELETE to {path} should return 405 Method Not Allowed")
            
        except requests.RequestException as e:
            self.assert_true(False, f"Request failed for method combinations test: {e}")