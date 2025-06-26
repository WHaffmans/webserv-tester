#!/usr/bin/env python3
"""
Security Tests

Tests for security aspects of the webserver according to test.conf configuration:

Server configuration in test.conf:
- Main server has root directory 'data/www'
- Location blocks for /, /static, /exact, and /upload
- Upload store directory is 'data/uploads'

Tests verify protection against common vulnerabilities and attacks.
"""

import os
import re
import time
import random
import string
import socket
import tempfile
import requests
from urllib.parse import quote, quote_plus
from pathlib import Path
from core.test_case import TestCase
from core.path_utils import get_tester_root, resolve_path

class SecurityTests(TestCase):
    """Tests security aspects of the webserver based on test.conf configuration."""
    
    def setup(self):
        """Set up the testing environment for security tests."""
        # Create a temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()
        self.test_files = []
        
        # Prepare some paths for testing
        self.www_root = resolve_path('data/www')
        self.upload_dir = resolve_path('data/uploads')
        
        # Create a test file for testing path traversal
        self.secret_file_path = os.path.join(self.temp_dir, "secret.txt")
        with open(self.secret_file_path, "w") as f:
            f.write("SECRET_CONTENT_SHOULD_NOT_BE_ACCESSIBLE")
        
        self.test_files.append(self.secret_file_path)
    
    def teardown(self):
        """Clean up resources after tests."""
        # Remove any test files
        for file_path in self.test_files:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass
        
        # Remove the temporary directory
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            os.rmdir(self.temp_dir)
    
    def test_path_traversal_prevention(self):
        """
        Test protection against path traversal attacks.
        
        Path traversal attacks try to access files outside the web root
        using sequences like '../' to navigate up directories.
        """
        # Test different path traversal patterns
        traversal_patterns = [
            '/../../../../../../etc/passwd',
            '/%2e%2e/%2e%2e/%2e%2e/%2e%2e/etc/passwd',  # URL encoded '../'
            '/static/..%2f..%2f..%2f..%2fetc/passwd',   # Mixed encoding
            '/static/../../../../../../etc/passwd',
            '/static/images/../../../../../../etc/passwd',
            '/..\\..\\..\\..\\..\\..\\windows\\win.ini',  # Windows path attempt
            '/.././.././.././.././../etc/passwd',
            '/static/././././../../../../../../etc/passwd'
        ]
        
        for pattern in traversal_patterns:
            try:
                response = self.runner.send_request('GET', pattern)
                
                # The server should either return 403 (Forbidden) or 404 (Not Found)
                self.assert_true(response.status_code in [403, 404], 
                               f"Path traversal attack not prevented: {pattern} returned {response.status_code}")
                
                # Verify the response does not contain sensitive file content
                self.assert_false('root:' in response.text and 'daemon:' in response.text, 
                               f"Path traversal attack succeeded for: {pattern}")
                
            except requests.RequestException as e:
                # Connection errors are NOT acceptable - server should return proper HTTP status
                self.assert_true(False, f"Server failed to respond with proper HTTP status for path traversal pattern {pattern}: {e}")
    
    def test_null_byte_injection(self):
        """
        Test protection against null byte injection attacks.
        
        Null byte injection can trick some file handling code to truncate paths
        and potentially access unintended files.
        """
        # Test paths with null bytes (URL encoded as %00)
        null_byte_patterns = [
            '/index.html%00.jpg',
            '/static/%00../../etc/passwd',
            '/static/image.jpg%00.php',
            '/index%00.html'
        ]
        
        for pattern in null_byte_patterns:
            try:
                response = self.runner.send_request('GET', pattern)
                
                # The server should return an appropriate error (400, 403, or 404)
                self.assert_true(response.status_code in [400, 403, 404], 
                               f"Null byte injection not properly handled: {pattern} returned {response.status_code}")
                
            except requests.RequestException as e:
                # Connection errors are NOT acceptable - server should return proper HTTP status
                self.assert_true(False, f"Server failed to respond with proper HTTP status for null byte pattern {pattern}: {e}")
    
    def test_long_url_handling(self):
        """
        Test handling of excessively long URLs.
        
        Long URLs can be used to perform buffer overflow attacks or
        cause denial of service conditions.
        """
        # Create extremely long URLs with different lengths
        url_lengths = [100, 1000, 2048, 4000]
        
        for length in url_lengths:
            # Generate a random string of the specified length
            random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=length))
            
            # Create long URLs with the random string
            long_url = f"/index.html?param={random_str}"
            
            try:
                response = self.runner.send_request('GET', long_url)
                
                # For very long URLs (>2000 chars), many servers reject with 414 or 400
                if length > 2000 and response.status_code in [400, 414]:
                    self.logger.debug(f"Server correctly rejected URL length {length} with status {response.status_code}")
                else:
                    # For shorter URLs, server should handle properly, for longer URLs should reject with specific errors
                    if length <= 1000:
                        self.assert_equals(response.status_code, 200, 
                                         f"Short URL ({length} chars) should be handled properly, got {response.status_code}")
                    else:
                        self.assert_true(response.status_code in [400, 414], 
                                       f"Long URL ({length} chars) should be rejected with 400 or 414, got {response.status_code}")
                
            except requests.RequestException as e:
                # Connection errors are NOT acceptable - server should return proper HTTP status
                self.assert_true(False, f"Server failed to respond with proper HTTP status for URL length {length}: {e}")
    
    def test_header_injection(self):
        """
        Test protection against HTTP header injection.
        
        Header injection can occur when untrusted input is included in response headers,
        potentially allowing attackers to add malicious headers or split responses.
        """
        # Test raw requests with malicious headers
        malicious_requests = [
            "GET / HTTP/1.1\r\nHost: localhost\r\nX-Custom-Header: malicious\r\nX-Injected-Header: injected\r\nConnection: close\r\n\r\n",
            "GET / HTTP/1.1\r\nHost: localhost\r\nUser-Agent: normal\r\nX-Injected: injected\r\nConnection: close\r\n\r\n",
            "GET / HTTP/1.1\r\nHost: localhost\r\nReferer: http://example.com\r\nX-CSRF-Token: fake\r\nConnection: close\r\n\r\n",
            "GET / HTTP/1.1\r\nHost: localhost\r\nCookie: normal=value\r\nX-Injected: value\r\nConnection: close\r\n\r\n"
        ]
        
        for i, request in enumerate(malicious_requests):
            try:
                response = self.runner.send_raw_request(request)
                
                # Server should handle the request properly (not crash)
                self.assert_true(response.startswith('HTTP/1.1'), 
                            f"Invalid response format for malicious request {i+1}")
                
                # Check that injected headers don't appear in response
                self.assert_false('X-Injected-Header' in response, 
                                f"Injected header appeared in response for request {i+1}")
                self.assert_false('X-CSRF-Token' in response, 
                                f"Injected CSRF token appeared in response for request {i+1}")
                
                # Server should return appropriate status (not 500)
                self.assert_false('500' in response[:20], 
                                f"Server error for malicious request {i+1}")
                
            except Exception as e:
                self.assert_true(False, f"Server failed to handle malicious request {i+1}: {e}")
    
    def test_request_smuggling(self):
        """
        Test protection against HTTP request smuggling.
        
        Request smuggling occurs when an attacker sends specially crafted HTTP requests
        that cause the server to process subsequent requests incorrectly.
        """
        # Test with ambiguous Content-Length and Transfer-Encoding headers
        smuggling_request = (
            "POST / HTTP/1.1\r\n"
            "Host: localhost\r\n"
            "Content-Length: 32\r\n"
            "Transfer-Encoding: chunked\r\n"
            "\r\n"
            "0\r\n"
            "\r\n"
            "GET /admin HTTP/1.1\r\n"
            "Host: localhost\r\n"
            "\r\n"
        )
        
        try:
            # Send the smuggling request using a raw socket
            response = self.runner.send_raw_request(smuggling_request)
            
            # Verify the server handles it properly (no 500 error)
            error_codes = re.findall(r'HTTP/1\.[01] (5\d\d)', response)
            self.assert_true(len(error_codes) == 0, 
                           f"Server error when handling request smuggling attempt: {error_codes}")
            
            # Verify the server doesn't process the smuggled request
            self.assert_false('/admin' in response, 
                            "Request smuggling attempt might have succeeded")
            
        except socket.error as e:
            # Connection reset is NOT acceptable - server should return proper HTTP status
            self.assert_true(False, f"Server failed to respond with proper HTTP status for request smuggling test: {e}")
    
    def test_directory_listing_restriction(self):
        """
        Test that directory listing is properly restricted.
        
        Directory listing should only be enabled for locations where it's explicitly
        allowed in the configuration.
        """
        # Test directories with and without autoindex enabled
        test_cases = [
            # (path, autoindex_enabled)
            ('/static/', True),  # Autoindex enabled in test.conf
            ('/', False),        # No autoindex in test.conf
            ('/upload/', False)  # No autoindex in test.conf
        ]
        
        for path, autoindex_enabled in test_cases:
            try:
                response = self.runner.send_request('GET', path)
                
                # Check content type and status code
                if response.status_code == 200:
                    content_type = response.headers.get('Content-Type', '').lower()
                    is_html = 'text/html' in content_type
                    
                    # Check response content for directory listing indicators
                    listing_indicators = ['directory listing', 'index of']
                    has_listing = any(indicator in response.text.lower() for indicator in listing_indicators)
                    
                    if autoindex_enabled:
                        # For directories with autoindex, listing should be allowed
                        self.assert_true(is_html and has_listing, 
                                       f"Directory listing not enabled for {path} where it should be")
                    else:
                        # For directories without autoindex, listing should not be allowed
                        self.assert_false(has_listing, 
                                        f"Directory listing incorrectly enabled for {path}")
            
            except requests.RequestException as e:
                self.assert_true(False, f"Request failed for directory listing test on {path}: {e}")
    
    def test_upload_file_extension_handling(self):
        """
        Test that file uploads properly handle potentially dangerous file extensions.
        
        Some file extensions can be security risks if improperly handled, especially
        executable scripts and server-side code.
        """
        # Test uploading files with potentially dangerous extensions
        dangerous_extensions = ['.php', '.pl', '.cgi', '.sh', '.jsp', '.asp', '.exe']
        
        for ext in dangerous_extensions:
            # Create a test file with the extension
            file_content = "echo 'This is a test file';"
            filename = f"test_file{ext}"
            
            try:
                temp_file = os.path.join(self.temp_dir, filename)
                with open(temp_file, "w") as f:
                    f.write(file_content)
                
                self.test_files.append(temp_file)
                
                # Attempt to upload the file
                with open(temp_file, "rb") as f:
                    files = {"file": (filename, f, "text/plain")}
                    response = self.runner.send_request('POST', '/upload', files=files)
                
                # Check if upload was allowed or properly rejected
                if response.status_code in [200, 201, 202, 204]:
                    # If upload was allowed, the server should not execute it
                    uploaded_path = f"/upload/{filename}"
                    try:
                        exec_response = self.runner.send_request('GET', uploaded_path)
                        
                        # If the file is accessible, it should not be executed as code
                        if exec_response.status_code == 200:
                            content_type = exec_response.headers.get('Content-Type', '').lower()
                            # Check if it's treated as plain text or download, not executed
                            self.assert_true('text/plain' in content_type or 
                                          'application/octet-stream' in content_type,
                                          f"File with {ext} extension might be executed")
                            
                            # Content should be returned as-is, not executed
                            self.assert_true(file_content in exec_response.text,
                                          f"File with {ext} extension might be executed")
                    except requests.RequestException as e:
                        # File access should return proper HTTP status (404, 403, etc.), not connection error
                        self.assert_true(False, f"Server failed to respond with proper HTTP status for file access {filename}: {e}")
                
            except requests.RequestException as e:
                # Upload rejection should return proper HTTP status, not connection error
                self.assert_true(False, f"Server failed to respond with proper HTTP status for executable file upload {filename}: {e}")
    
    def test_server_information_disclosure(self):
        """
        Test that the server doesn't disclose sensitive information.
        
        Headers and error pages should not reveal detailed information about
        the server implementation, version, or file paths.
        """
        try:
            # Make a basic request
            response = self.runner.send_request('GET', '/')
            
            # Check Server header if present
            if 'Server' in response.headers:
                server_header = response.headers['Server']
                # Server header should not reveal detailed version information
                self.assert_false(re.search(r'\d+\.\d+\.\d+', server_header),
                                f"Server header reveals detailed version: {server_header}")
            
            # Check for other potentially sensitive headers
            sensitive_headers = ['X-Powered-By', 'X-AspNet-Version', 'X-Runtime']
            for header in sensitive_headers:
                self.assert_false(header in response.headers,
                                f"Server reveals sensitive information in {header} header")
            
            # Test error response for information disclosure
            # Request a non-existent path
            error_response = self.runner.send_request('GET', '/non-existent-' + str(random.randint(10000, 99999)))
            
            # Check that error response doesn't contain file paths or stack traces
            if error_response.status_code in [404, 500]:
                error_text = error_response.text.lower()
                # Look for common signs of information leakage
                info_leakage_indicators = [
                    r'/\w+/\w+/\w+',  # File paths
                    r'exception in',   # Exception details
                    r'stack trace',    # Stack traces
                    r'line \d+',       # Line numbers
                    r'syntax error',   # Parsing errors
                    r'failed to open'  # File operation errors
                ]
                
                for indicator in info_leakage_indicators:
                    self.assert_false(re.search(indicator, error_text),
                                    f"Error page may be leaking sensitive information")
        
        except requests.RequestException as e:
            self.assert_true(False, f"Request failed during information disclosure test: {e}")
    
    def test_xss_prevention(self):
        """
        Test basic XSS prevention in error pages.
        
        Error pages should properly escape user input to prevent XSS attacks.
        """
        # Create a URL with potential XSS payload
        xss_payloads = [
            '<script>alert("XSS")</script>',
            '"><script>alert("XSS")</script>',
            '<img src="x" onerror="alert(\'XSS\')">',
            '<svg/onload=alert("XSS")>'
        ]
        
        for payload in xss_payloads:
            # URL encode the payload
            encoded_payload = quote(payload)
            test_url = f"/test?param={encoded_payload}"
            
            try:
                response = self.runner.send_request('GET', test_url)
                
                # If the payload appears in the response, check if it's properly escaped
                if payload in response.text or encoded_payload in response.text:
                    # Check if the response contains the unescaped script tags
                    self.assert_false(re.search(r'<script>alert\("XSS"\)</script>', response.text),
                                    f"XSS payload not properly escaped: {payload}")
                    
                    # Check if the HTML entities are escaped
                    escaped_lt = "&lt;"
                    escaped_gt = "&gt;"
                    
                    # If the response contains the payload, but it's escaped, that's good
                    if escaped_lt in response.text and escaped_gt in response.text:
                        self.logger.debug(f"XSS payload properly escaped: {payload}")
                
            except requests.RequestException as e:
                self.logger.debug(f"Request with XSS payload failed: {e}")
    
    def test_cgi_parameter_handling(self):
        """
        Test secure handling of CGI script parameters.
        
        CGI scripts should properly handle and sanitize input parameters
        to prevent command injection and other attacks.
        """
        # Test injection attempts in CGI parameters
        cgi_path = '/cgi-bin/test.cgi'
        injection_attempts = [
            '?cmd=ls%20-la',
            '?$(ls)',
            '?%0Aid',
            '?`id`',
            '?test=\'";<>/&',
            '?test=%0A%0DHTTP/1.1%20200%20OK'
        ]
        
        for attempt in injection_attempts:
            try:
                response = self.runner.send_request('GET', cgi_path + attempt)
                
                # Check that the response doesn't contain evidence of command execution
                command_execution_indicators = [
                    'uid=', 'gid=',        # Output of id command
                    'root:', 'daemon:',     # /etc/passwd content
                    'total ',               # ls -la output
                    'HTTP/1.1 200 OK'       # Response splitting
                ]
                
                for indicator in command_execution_indicators:
                    self.assert_false(indicator in response.text,
                                    f"Possible command injection in CGI with parameter: {attempt}")
                
                # Check for shell metacharacters in environment variables
                shell_metacharacters = ['`', '$', '|', ';', '&']
                env_var_output = f"QUERY_STRING: {attempt[1:]}"  # Remove the ? from the query string
                
                if env_var_output in response.text:
                    # Verify that shell metacharacters were properly quoted or escaped
                    # This is more of a heuristic check, as exact escaping depends on the implementation
                    for char in shell_metacharacters:
                        if char in attempt:
                            # If the character is in the request, it should either be filtered, 
                            # URL-encoded, or quoted in the response
                            raw_char_pattern = f"QUERY_STRING: .*{re.escape(char)}"
                            has_raw_char = re.search(raw_char_pattern, response.text)
                            
                            # If the raw character is present in the response, it might be a problem
                            if has_raw_char:
                                self.logger.debug(f"Shell metacharacter '{char}' in CGI environment variable")
            
            except requests.RequestException as e:
                # Some injection attempts might cause connection failures, which is acceptable
                self.logger.debug(f"Request with CGI injection attempt failed: {e}")
    
    def test_method_restriction_security(self):
        """
        Test enforcement of HTTP method restrictions for security.
        
        The server should properly restrict HTTP methods according to the configuration,
        which is important for preventing unauthorized actions.
        
        HTTP standards define different status codes for method handling:
        - 405 Method Not Allowed: Method is recognized but not allowed for the resource
        - 501 Not Implemented: Method is not recognized/implemented by the server
        """
        # Test restricted methods on different paths
        test_cases = [
            # (path, method, should_be_allowed, expected_status_codes)
            ('/', 'DELETE', False, [405]),                      # DELETE should be rejected with 405
            ('/static/', 'POST', False, [405]),                 # POST not allowed on /static/
            ('/static/', 'PUT', False, [405, 501]),             # PUT might be 405 or 501
            ('/upload', 'DELETE', False, [405]),                # DELETE should be rejected with 405
            ('/upload', 'GET', False, [405, 404]),              # GET not allowed or path not found
            ('/upload', 'POST', True, [200, 201, 202, 204]),   # POST allowed on /upload
            ('/', 'OPTIONS', False, [405, 501]),                # OPTIONS might not be implemented
            ('/', 'TRACE', False, [405, 501]),                  # TRACE might not be implemented
            ('/', 'PROPFIND', False, [405, 501])                # WebDAV not implemented
        ]
        
        for path, method, should_be_allowed, expected_status in test_cases:
            try:
                # Create data for non-GET methods
                data = {'test': 'data'} if method not in ['GET', 'HEAD'] else None
                
                response = self.runner.send_request(method, path, data=data)
                
                if should_be_allowed:
                    # Method should be allowed
                    self.assert_true(response.status_code in expected_status, 
                                f"{method} should return one of {expected_status} for {path}, got {response.status_code}")
                else:
                    # Method should not be allowed
                    self.assert_true(response.status_code in expected_status, 
                                f"{method} should be rejected with one of {expected_status} for {path}, got {response.status_code}")
                    
                    # If 405, check for Allow header
                    if response.status_code == 405:
                        self.assert_true('Allow' in response.headers, 
                                    f"405 response for {method} {path} missing Allow header")
            
            except requests.RequestException as e:
                # Connection failures are NOT acceptable - server should return proper HTTP status
                self.assert_true(False, f"Server failed to respond with proper HTTP status for {method} {path}: {e}")
    
    def test_resource_access_control(self):
        """
        Test access control for server resources.
        
        The server should prevent access to sensitive files even when they exist.
        """
        # Create one sensitive test file in the web root
        test_dir = os.path.join(self.www_root, 'test_security')
        sensitive_file = os.path.join(test_dir, '.htaccess')
        try:
            # Create test directory and sensitive file
            os.makedirs(test_dir, exist_ok=True)
            if test_dir not in self.test_files:
                self.test_files.append(test_dir)
            # Create the sensitive file with identifiable content
            with open(sensitive_file, 'w') as f:
                f.write("SENSITIVE_TEST_CONTENT")
            if sensitive_file not in self.test_files:
                self.test_files.append(sensitive_file)
            # Create a normal HTML file to verify directory is accessible
            normal_file = os.path.join(test_dir, 'index.html')
            with open(normal_file, 'w') as f:
                f.write("<html><body><h1>Test Directory</h1></body></html>")
            if normal_file not in self.test_files:
                self.test_files.append(normal_file)
            # Verify the directory is accessible (confirming our test setup works)
            try:
                response = self.runner.send_request('GET', '/test_security/')
                self.assert_equals(response.status_code, 200, "Test directory not accessible")
                # Now test access to the sensitive file
                response = self.runner.send_request('GET', '/test_security/.htaccess')
                # Should be blocked with 403 Forbidden or 404 Not Found
                self.assert_true(response.status_code in [403, 404], 
                               f"Sensitive file accessible with status {response.status_code}")
                # Verify content isn't leaked
                self.assert_false("SENSITIVE_TEST_CONTENT" in response.text,
                               "Sensitive content leaked in error response")
            except requests.RequestException as e:
                self.assert_true(False, f"Request failed: {e}")
        except Exception:
            pass
    
    def test_malformed_request_handling(self):
        """
        Test handling of malformed HTTP requests.
        
        The server should properly handle malformed requests without crashing
        or revealing sensitive information.
        """
        # Test various malformed requests
        malformed_requests = [
            # Invalid HTTP method
            "INVALID / HTTP/1.1\r\nHost: localhost\r\n\r\n",
            
            # Missing HTTP version
            "GET /\r\nHost: localhost\r\n\r\n",
            
            # Invalid HTTP version
            "GET / HTTP/9.9\r\nHost: localhost\r\n\r\n",
            
            # Extremely long method
            "GET" + ("X" * 1000) + " / HTTP/1.1\r\nHost: localhost\r\n\r\n",
            
            # Malformed header format
            "GET / HTTP/1.1\r\nMalformed-Header\r\nHost: localhost\r\n\r\n",
            
            # Invalid Content-Length
            "GET / HTTP/1.1\r\nHost: localhost\r\nContent-Length: invalid\r\n\r\n"
        ]
        
        for i, request in enumerate(malformed_requests):
            try:
                # Send the malformed request
                response = self.runner.send_raw_request(request)
                
                # Server should respond with appropriate error code (400 Bad Request is common)
                # We check the response string since we're using a raw request
                expected_status_codes = ['400', '404', '405', '501', '505']
                
                # Check if the response starts with HTTP/1.x followed by one of the expected status codes
                status_code_match = re.search(r'HTTP/1\.[01] ([0-9]{3})', response)
                if status_code_match:
                    status_code = status_code_match.group(1)
                    self.assert_true(status_code in expected_status_codes, 
                                   f"Malformed request {i+1} returned unexpected status {status_code}")
                else:
                    # If no status code pattern found, the response format might be invalid
                    self.assert_true(False, f"Malformed request {i+1} returned invalid HTTP response format")
                
                # Server should not crash or return an unhandled error (500)
                self.assert_false('500' in response[:20], 
                                f"Malformed request {i+1} caused server error")
                
            except socket.error as e:
                # Connection reset is NOT acceptable - server should return proper HTTP status
                self.assert_true(False, f"Server failed to respond with proper HTTP status for malformed request {i+1}: {e}")
            