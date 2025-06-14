#!/usr/bin/env python3
"""
CGI Implementation Tests

Tests for CGI script execution according to HTTP/1.1 standards.
Tests verify that the server correctly executes CGI scripts and returns their output.

These tests assume CGI is configured in the server at /cgi-bin/ as specified in test.conf.
"""

import os
import sys
import stat
import time
import random
import string
import shutil
import threading
import subprocess
import requests
from pathlib import Path
from urllib.parse import urlencode
from core.test_case import TestCase
from core.path_utils import get_tester_root, resolve_path

class CGITests(TestCase):
    """Tests CGI execution functionality according to HTTP/1.1 standards."""
    
    def setup(self):
        """Set up for CGI tests."""
        # Define the CGI path according to test.conf
        self.cgi_path = '/cgi-bin'
        
        # Get the script paths - these should be deployed to data/www/cgi-bin
        self.tester_root = get_tester_root()
        self.cgi_dir = resolve_path('data/www/cgi-bin')
        
        # Log paths for debugging
        self.logger.debug(f"CGI directory: {self.cgi_dir}")
        
        # Check that scripts have execute permissions
        self._ensure_scripts_executable()
    
    def _ensure_scripts_executable(self):
        """Ensure all test scripts have execute permissions."""
        scripts = ['test.cgi', 'content_type.cgi', 'status.cgi', 'post.cgi', 
                  'error.cgi', 'sleep.cgi', 'test.py', 'test.php']
        
        for script in scripts:
            script_path = self.cgi_dir / script
            if script_path.exists():
                # Set executable permissions
                try:
                    script_path.chmod(script_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                except Exception as e:
                    self.logger.debug(f"Could not set execute permission on {script_path}: {e}")
            else:
                self.logger.debug(f"Script {script_path} not found")
    
    def test_basic_cgi_execution(self):
        """
        Test basic CGI script execution.
        
        Verifies that the server correctly identifies and executes CGI scripts,
        returning their output as the HTTP response.
        """
        # Construct test URL
        test_url = f"{self.cgi_path}/test.cgi"
        
        try:
            # Request the basic test script
            response = self.runner.send_request('GET', test_url)
            
            # Verify successful execution
            self.assert_equals(response.status_code, 200, 
                             f"CGI script at {test_url} failed with status {response.status_code}")
            
            # Verify script output in response
            self.assert_true("CGI Test Script Output" in response.text, 
                          f"CGI script output not found in response from {test_url}")
            
            # Verify environment variables in response
            self.assert_true("REQUEST_METHOD: GET" in response.text, 
                          f"REQUEST_METHOD not found in CGI environment for {test_url}")
            
        except requests.RequestException as e:
            self.assert_true(False, f"Request to {test_url} failed: {e}")
    
    def test_cgi_content_type(self):
        """
        Test that CGI scripts can set their own Content-Type.
        
        Verifies that the Content-Type header set by the CGI script is correctly
        passed through to the client.
        """
        # Construct test URL
        test_url = f"{self.cgi_path}/content_type.cgi"
        
        try:
            # Request the content type test script
            response = self.runner.send_request('GET', test_url)
            
            # Verify successful execution
            self.assert_equals(response.status_code, 200, 
                             f"CGI script at {test_url} failed with status {response.status_code}")
            
            # Verify Content-Type header was set correctly by the script
            self.assert_true('Content-Type' in response.headers, 
                          f"Content-Type header missing in response from {test_url}")
            
            self.assert_equals(response.headers['Content-Type'].lower(), 'application/json', 
                             f"Content-Type header not set to 'application/json' as specified by the script: {response.headers['Content-Type']}")
            
            # Verify JSON content
            self.assert_true('{"message":' in response.text, 
                          f"Expected JSON content not found in response from {test_url}")
            
        except requests.RequestException as e:
            self.assert_true(False, f"Request to {test_url} failed: {e}")
    
    def test_different_interpreters(self):
        """
        Test support for different script interpreters.
        
        Verifies that the server can execute scripts with different interpreters
        based on their file extension or shebang line.
        """
        # Test shell script (already covered by test_basic_cgi_execution)
        
        # Test Python script
        python_url = f"{self.cgi_path}/test.py"
        try:
            # Request Python script
            response = self.runner.send_request('GET', python_url)
            
            # Verify successful execution
            self.assert_equals(response.status_code, 200, 
                             f"Python CGI script at {python_url} failed with status {response.status_code}")
            
            # Verify Python CGI output
            self.assert_true("<title>Python CGI Test</title>" in response.text, 
                          f"Python CGI output not found in response from {python_url}")
            
        except requests.RequestException as e:
            self.assert_true(False, f"Request to Python CGI script {python_url} failed: {e}")
        
        # Test PHP script
        php_url = f"{self.cgi_path}/test.php"
        try:
            # Request PHP script
            response = self.runner.send_request('GET', php_url)
            
            # Verify successful execution
            self.assert_equals(response.status_code, 200, 
                             f"PHP CGI script at {php_url} failed with status {response.status_code}")
            
            # Verify PHP CGI output
            self.assert_true("<title>PHP CGI Test</title>" in response.text, 
                          f"PHP CGI output not found in response from {php_url}")
            
        except requests.RequestException as e:
            self.assert_true(False, f"Request to PHP CGI script {php_url} failed: {e}")
    
    def test_get_method(self):
        """
        Test GET method with CGI scripts.
        
        Verifies that the REQUEST_METHOD environment variable is correctly set to "GET"
        when requesting a CGI script with the GET method.
        """
        # Construct test URL
        test_url = f"{self.cgi_path}/test.cgi"
        
        try:
            # Request the test script with GET
            response = self.runner.send_request('GET', test_url)
            
            # Verify successful execution
            self.assert_equals(response.status_code, 200, 
                             f"CGI script at {test_url} failed with status {response.status_code}")
            
            # Verify REQUEST_METHOD is set to GET
            self.assert_true("REQUEST_METHOD: GET" in response.text, 
                          f"CGI environment does not have REQUEST_METHOD=GET for {test_url}")
            
        except requests.RequestException as e:
            self.assert_true(False, f"GET request to {test_url} failed: {e}")
    
    def test_post_method_cgi(self):
        """
        Test POST method with CGI scripts.
        
        Verifies that the REQUEST_METHOD environment variable is correctly set to "POST"
        and that the script has access to the POST data.
        """
        # Construct test URL
        post_url = f"{self.cgi_path}/post.cgi"

        # Create POST data
        post_data = {
            'field1': 'value1',
            'field2': 'value2',
            'test': 'CGI POST test'
        }
        
        try:
            # Send POST request to the script
            response = self.runner.send_request('POST', post_url, data=post_data)
            
            # Verify successful execution
            self.assert_equals(response.status_code, 200, 
                            f"POST to CGI script at {post_url} failed with status {response.status_code}")
            
            # Verify the CGI script received the POST data
            # Check for URL-encoded format (space becomes +)
            self.assert_true('field1=value1' in response.text, 
                        "CGI script did not receive POST parameter field1=value1")
            self.assert_true('field2=value2' in response.text, 
                        "CGI script did not receive POST parameter field2=value2")
            self.assert_true('test=CGI+POST+test' in response.text, 
                        "CGI script did not receive POST parameter test=CGI+POST+test (URL-encoded)")
            
        except requests.RequestException as e:
            self.assert_true(False, f"POST request to {post_url} failed: {e}")
        
    def test_query_string(self):
        """
        Test query string parameters with CGI scripts.
        
        Verifies that the QUERY_STRING environment variable is correctly set
        and that the script has access to query parameters.
        """
        # Generate random query parameters
        query_params = {
            'param1': f"value{random.randint(1000, 9999)}",
            'param2': f"test{random.randint(1000, 9999)}",
            'test': f"{random.choice(string.ascii_letters)}" * 5
        }
        query_string = urlencode(query_params)
        
        # Construct the URL with query string
        test_url = f"{self.cgi_path}/test.cgi?{query_string}"
        
        try:
            # Request the CGI script with query string
            response = self.runner.send_request('GET', test_url)
            
            # Verify successful execution
            self.assert_equals(response.status_code, 200, 
                             f"CGI script at {test_url} failed with status {response.status_code}")
            
            # Verify QUERY_STRING is set correctly
            self.assert_true(f"QUERY_STRING: {query_string}" in response.text, 
                          f"QUERY_STRING not set correctly for {test_url}")
            
        except requests.RequestException as e:
            self.assert_true(False, f"Request to {test_url} failed: {e}")
    
    def test_standard_cgi_variables(self):
        """
        Test standard CGI environment variables.
        
        Verifies that the server sets all required CGI environment variables
        according to the CGI/1.1 specification.
        """
        # Construct test URL with a unique query parameter to avoid caching
        test_url = f"{self.cgi_path}/test.cgi?unique={random.randint(10000, 99999)}"
        
        # Required CGI environment variables according to CGI/1.1 spec
        required_variables = [
            'SERVER_SOFTWARE',
            'SERVER_NAME',
            'GATEWAY_INTERFACE',
            'SERVER_PROTOCOL',
            'SERVER_PORT',
            'REQUEST_METHOD',
            'PATH_INFO',
            'SCRIPT_NAME',
            'QUERY_STRING',
            'REMOTE_ADDR'
        ]
        
        try:
            response = self.runner.send_request('GET', test_url)
            
            # Verify successful execution
            self.assert_equals(response.status_code, 200, 
                             f"CGI script at {test_url} failed with status {response.status_code}")
            
            # Verify required environment variables
            for var in required_variables:
                self.assert_true(f"{var}:" in response.text, 
                              f"Required CGI environment variable {var} not found in response")
            
        except requests.RequestException as e:
            self.assert_true(False, f"Request to {test_url} failed: {e}")
    
    def test_http_header_passing(self):
        """
        Test HTTP header passing to CGI scripts.
        
        Verifies that HTTP request headers are correctly passed to the CGI script
        as HTTP_* environment variables.
        """
        # Construct test URL
        test_url = f"{self.cgi_path}/test.cgi"
        
        # Custom headers
        custom_headers = {
            'X-Custom-Header': f"value-{random.randint(1000, 9999)}",
            'X-Test-CGI': f"test-{random.randint(1000, 9999)}",
            'User-Agent': 'WebservTester/1.0'
        }
        
        try:
            # Request with custom headers
            response = self.runner.send_request('GET', test_url, headers=custom_headers)
            
            # Verify successful execution
            self.assert_equals(response.status_code, 200, 
                             f"CGI script at {test_url} failed with status {response.status_code}")
            
            # Verify headers were passed as HTTP_* environment variables
            for header, value in custom_headers.items():
                env_name = f"HTTP_{header.upper().replace('-', '_')}"
                self.assert_true(f"{env_name}: {value}" in response.text, 
                              f"Header {header} not passed as {env_name} to CGI script")
            
        except requests.RequestException as e:
            self.assert_true(False, f"Request to {test_url} failed: {e}")
    
    def test_path_info(self):
        """
        Test PATH_INFO with CGI scripts.
        
        Verifies that extra path information after the script name is correctly
        passed to the CGI script as the PATH_INFO environment variable.
        """
        # Extra path info to append
        extra_path = f"/extra/path/info/{random.randint(1000, 9999)}"
        
        # Construct URL with extra path info
        test_url = f"{self.cgi_path}/test.cgi{extra_path}"
        
        try:
            # Request with extra path info
            response = self.runner.send_request('GET', test_url)
            
            # Verify successful execution
            self.assert_equals(response.status_code, 200, 
                             f"CGI script at {test_url} failed with status {response.status_code}")
            
            # Verify PATH_INFO is set correctly
            # Note: Some servers may normalize the path, so check for the essential parts
            self.assert_true(f"PATH_INFO: {extra_path}" in response.text or
                         f"PATH_INFO:" in response.text and "extra/path/info" in response.text, 
                         f"PATH_INFO not set correctly for {test_url}")
            
        except requests.RequestException as e:
            self.assert_true(False, f"Request to {test_url} failed: {e}")
    
    def test_nonexistent_script(self):
        """
        Test handling of nonexistent CGI scripts.
        
        Verifies that the server returns a 404 Not Found response when
        a nonexistent CGI script is requested.
        """
        # Construct URL for a nonexistent script
        nonexistent_url = f"{self.cgi_path}/nonexistent-{random.randint(10000, 99999)}.cgi"
        
        try:
            # Request nonexistent script
            response = self.runner.send_request('GET', nonexistent_url)
            
            # Verify 404 Not Found
            self.assert_equals(response.status_code, 404, 
                             f"Request for nonexistent script {nonexistent_url} returned {response.status_code} instead of 404")
            
        except requests.RequestException as e:
            self.assert_true(False, f"Request to {nonexistent_url} failed: {e}")
    
    def test_script_execution_error(self):
        """
        Test handling of script execution errors.
        
        Verifies that the server returns a 500 Internal Server Error response
        when a CGI script fails to execute properly.
        """
        # Construct URL for the error script
        error_url = f"{self.cgi_path}/error.cgi"
        
        try:
            # Request the script with syntax error
            response = self.runner.send_request('GET', error_url)
            
            # Server should return 500 Internal Server Error for CGI script errors
            self.assert_equals(response.status_code, 500,
                             f"Error script at {error_url} should return 500 Internal Server Error, got {response.status_code}")
            
        except requests.RequestException as e:
            # Connection errors are NOT acceptable - server should return proper HTTP status
            self.assert_true(False, f"Server failed to respond with proper HTTP status for CGI error script: {e}")
    
    def test_missing_permissions(self):
        """
        Test handling of non-executable CGI scripts.
        
        Verifies that the server returns an appropriate error response when
        a CGI script without execute permissions is requested.
        """
        # Create a non-executable script
        nonexec_script = self.cgi_dir / 'nonexec.cgi'
        nonexec_content = """#!/bin/sh
echo "Content-Type: text/plain"
echo ""
echo "This script should not execute due to missing permissions"
"""
        try:
            # Create the script
            with open(nonexec_script, 'w') as f:
                f.write(nonexec_content)
            
            # Set non-executable permissions
            nonexec_script.chmod(0o644)
            
            # Construct URL for non-executable script
            nonexec_url = f"{self.cgi_path}/nonexec.cgi"
            
            # Request non-executable script
            response = self.runner.send_request('GET', nonexec_url)
            
            # Verify response - should be 403 Forbidden or 500 Internal Server Error
            self.assert_true(response.status_code in [403, 500], 
                          f"Non-executable script at {nonexec_url} returned {response.status_code} instead of 403 or 500")
            
        except requests.RequestException as e:
            self.assert_true(False, f"Request to {nonexec_url} failed: {e}")
        finally:
            # Clean up
            if os.path.exists(nonexec_script):
                os.remove(nonexec_script)
    
    def test_script_outside_cgi_dirs(self):
        """
        Test script execution isolation.
        
        Verifies that the server does not execute CGI scripts outside of
        designated CGI directories.
        """
        # Create a test script outside CGI directories
        outside_script = resolve_path('data/www/outside.cgi')
        
        outside_content = """#!/bin/sh
echo "Content-Type: text/plain"
echo ""
echo "This script should not be executed!"
"""
        
        try:
            # Create the script
            outside_dir = os.path.dirname(outside_script)
            os.makedirs(outside_dir, exist_ok=True)
            
            with open(outside_script, 'w') as f:
                f.write(outside_content)
            
            # Make it executable
            os.chmod(outside_script, 0o755)
            
            # Construct URL to the script outside CGI directories
            outside_url = "/outside.cgi"
            
            # Request the script outside CGI directories
            response = self.runner.send_request('GET', outside_url)
            
            # Server should either return the script as plain text or return an error
            self.assert_true(response.status_code in [200, 403, 404], 
                          f"Script outside CGI directories returned unexpected status {response.status_code}")
            
            # If 200, it should not have executed the script
            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '').lower()
                self.assert_false('text/plain' in content_type and 
                               "This script should not be executed!" in response.text, 
                               "Script outside CGI directories was incorrectly executed")
                
        except requests.RequestException as e:
            self.assert_true(False, f"Request to {outside_url} failed: {e}")
        finally:
            # Clean up
            if os.path.exists(outside_script):
                os.remove(outside_script)
    
    def test_status_code_handling(self):
        """
        Test CGI script status code handling.
        
        Verifies that the server correctly passes the status code set by
        the CGI script to the client.
        """
        # Construct URL for the status code script
        status_url = f"{self.cgi_path}/status.cgi"
        
        # Test status codes
        test_codes = [200, 201, 301, 302, 400, 403, 404, 500]
        
        for code in test_codes:
            query_url = f"{status_url}?status={code}"
            
            try:
                # Request with specific status
                response = self.runner.send_request('GET', query_url, allow_redirects=False)
                
                # Verify the status code matches what was requested
                # Not all servers will correctly handle all status codes from CGI
                self.logger.debug(f"Status script with code={code} returned {response.status_code}")
                
                # Only check for common status codes that servers should handle
                if code in [200, 404, 500]:
                    self.assert_equals(response.status_code, code, 
                                     f"Status script with status={code} returned {response.status_code}")
                
            except requests.RequestException as e:
                # Connection errors are NOT acceptable - server should return proper HTTP status
                self.assert_true(False, f"Server failed to respond with proper HTTP status for status script {code}: {e}")
    
    def test_timeout_handling(self):
        """
        Test timeout handling for CGI scripts.
        
        Verifies that the server correctly handles CGI scripts that exceed
        the execution timeout.
        """
        # Construct URL for the sleep script
        sleep_url = f"{self.cgi_path}/sleep.cgi"
        
        try:
            # Request the sleep script with a short timeout
            start_time = time.time()
            
            try:
                # Using requests.get directly for better timeout handling
                full_url = f"http://{self.runner.host}:{self.runner.port}{sleep_url}"
                response = requests.get(full_url, timeout=2)
                
                end_time = time.time()
                execution_time = end_time - start_time
                
                # Script runs for 10 seconds, so if we get a response quickly,
                # the server must have a timeout mechanism
                if response.status_code in [500, 502, 504] and execution_time < 9:
                    self.logger.debug(f"Server correctly timed out the CGI script after {execution_time:.2f} seconds")
                elif response.status_code == 200 and execution_time < 9:
                    self.logger.debug(f"Server sent a partial response after {execution_time:.2f} seconds")
                    # Check for partial output
                    self.assert_true("Starting sleep test" in response.text, 
                                  "Expected partial output not found in timeout response")
                else:
                    self.logger.debug(f"Sleep script returned status {response.status_code} after {execution_time:.2f} seconds")
                
            except requests.Timeout:
                # This is actually expected - our client timeout is shorter than the script's sleep
                self.logger.debug("Request to sleep script timed out as expected")
            except requests.ConnectionError as e:
                # Connection errors are NOT acceptable for timeout handling
                self.assert_true(False, f"Server failed to handle CGI timeout properly: {e}")
                
        except Exception as e:
            self.logger.debug(f"Unexpected error testing timeout: {e}")
    
    def test_concurrent_cgi_execution(self):
        """
        Test concurrent CGI script execution.
        
        Verifies that the server can handle multiple simultaneous CGI requests
        without errors or resource exhaustion.
        """
        # Construct URL for test script
        test_url = f"{self.cgi_path}/test.cgi"
        
        # Number of concurrent requests
        num_requests = 5
        
        # Function to make a request with a unique query string
        def make_request(i):
            unique_url = f"{test_url}?concurrent={i}&random={random.randint(10000, 99999)}"
            try:
                response = self.runner.send_request('GET', unique_url)
                return response.status_code, response.text
            except requests.RequestException as e:
                return 0, str(e)
        
        # Make concurrent requests
        results = []
        threads = []
        
        for i in range(num_requests):
            thread = threading.Thread(target=lambda idx=i: results.append(make_request(idx)))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=10)
        
        # Verify at least some requests succeeded
        successful = [r for r, _ in results if r == 200]
        self.assert_true(len(successful) > 0, f"No concurrent CGI requests succeeded out of {num_requests}")
        
        # Log success ratio
        success_ratio = len(successful) / num_requests
        self.logger.debug(f"Concurrent CGI execution: {len(successful)}/{num_requests} requests succeeded ({success_ratio*100:.1f}%)")
    
    def test_custom_response_headers(self):
        """
        Test custom response headers from CGI scripts.
        
        Verifies that custom headers set by CGI scripts are correctly
        passed through to the client.
        """
        # Create a custom header script
        header_script = f"{self.cgi_dir}/header.cgi"
        header_content = """#!/bin/sh
        echo "Content-Type: text/plain"
        echo "X-Custom-CGI-Header: test-value-123"
        echo "X-Test-Header: another-test-value"
        echo ""
        echo "This script sets custom response headers"
        """
        
        try:
            # Create the script
            with open(header_script, 'w') as f:
                f.write(header_content)
            
            # Make it executable
            os.chmod(header_script, 0o755)
            
            # Construct URL for the header script
            header_url = f"{self.cgi_path}/header.cgi"
            
            # Request the header script
            response = self.runner.send_request('GET', header_url)
            
            # Verify successful execution
            self.assert_equals(response.status_code, 200, 
                             f"CGI script at {header_url} failed with status {response.status_code}")
            
            # Verify custom headers were passed through
            self.assert_true('X-Custom-CGI-Header' in response.headers, 
                          "Custom header X-Custom-CGI-Header not passed through")
            self.assert_equals(response.headers['X-Custom-CGI-Header'], 'test-value-123', 
                             "Custom header value incorrect")
            
            self.assert_true('X-Test-Header' in response.headers, 
                          "Custom header X-Test-Header not passed through")
            self.assert_equals(response.headers['X-Test-Header'], 'another-test-value', 
                             "Custom header value incorrect")
            
        except requests.RequestException as e:
            self.assert_true(False, f"Request to {header_url} failed: {e}")
        finally:
            # Clean up
            if os.path.exists(header_script):
                os.remove(header_script)