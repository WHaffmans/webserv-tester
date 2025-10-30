#!/usr/bin/env python3
"""
HTTP Protocol Compliance Tests

Comprehensive tests for HTTP/1.1 protocol compliance specific to test.conf configuration:

Server configuration in test.conf:
- Main server on port 8080 with client_max_body_size 5m
- Root location (/) allows GET, POST
- Static location (/static) allows only GET with autoindex on
- Exact match location (/exact) allows only GET
- Upload location (/upload) allows only POST
- Custom error pages for 404 and 5xx errors

This test suite focuses on protocol-level behavior rather than specific paths.
"""

import requests
import socket
import time
import random
import string
from urllib.parse import urlencode, quote
from core.test_case import TestCase


class HttpTests(TestCase):
    """Tests HTTP protocol compliance of the webserver."""
    # Default ports defined in test.conf
    DEFAULT_PORT = 8080
    ALT_PORT_1 = 8081
    ALT_PORT_2 = 8082
    
    def test_http_version_support(self):
        """Test HTTP/1.1 support."""
        # Send a raw HTTP request with HTTP/1.1
        request = "GET / HTTP/1.1\r\nHost: localhost:8080\r\nConnection: close\r\n\r\n"
        response = self.runner.send_raw_request(request)
        
        # Check response starts with HTTP/1.1
        self.assert_true(response.startswith('HTTP/1.1 '), 
                         f"Expected HTTP/1.1 response, got: {response[:20]}")
    
    def test_http_10_support(self):
        """Test HTTP/1.0 backward compatibility."""
        # Send a raw HTTP request with HTTP/1.0
        request = "GET / HTTP/1.0\r\n\r\n"
        response = self.runner.send_raw_request(request)
        
        # Check response starts with HTTP/1.0 or HTTP/1.1
        self.assert_true(response.startswith('HTTP/1.0 ') or response.startswith('HTTP/1.1 '), 
                         f"Expected HTTP/1.0 or HTTP/1.1 response, got: {response[:20]}")
    
    def test_invalid_http_version(self):
        """Test handling of invalid HTTP version."""
        # Send a raw HTTP request with invalid version
        request = "GET / HTTP/9.9\r\nHost: localhost:8080\r\nConnection: close\r\n\r\n"
        response = self.runner.send_raw_request(request)
        
        # Should respond with 505 HTTP Version Not Supported or 400 Bad Request
        self.assert_true('505' in response[:20] or '400' in response[:20], 
                         f"Expected 505 or 400 response for invalid HTTP version, got: {response[:50]}")
    
    def test_host_header_required(self):
        """Test that Host header is required for HTTP/1.1."""
        # Send a raw HTTP/1.1 request without Host header
        request = "GET / HTTP/1.1\r\nConnection: close\r\n\r\n"
        response = self.runner.send_raw_request(request)
        
        # Should respond with 400 Bad Request
        self.assert_true('400' in response[:20], 
                         f"Expected 400 response for missing Host header, got: {response[:50]}")
    
    def test_chunked_transfer_encoding(self):
        """Test handling of chunked transfer encoding."""
        # Create a chunked request
        request = (
            "POST / HTTP/1.1\r\n"
            "Host: localhost:8080\r\n"
            "Connection: close\r\n"
            "Transfer-Encoding: chunked\r\n"
            "Content-Type: text/plain\r\n"
            "\r\n"
            "5\r\n"
            "Hello\r\n"
            "5\r\n"
            "World\r\n"
            "0\r\n"
            "\r\n"
        )
        
        try:
            response = self.runner.send_raw_request(request)
            # If server supports chunked encoding, it should return a valid status code
            self.assert_true(response.startswith('HTTP/1.1 '), 
                          f"Invalid response to chunked request: {response[:50]}")
            
            # Should be a valid status code (either success or error, but properly formatted)
            status_code = int(response.split(' ')[1])
            self.assert_true(100 <= status_code < 600, 
                          f"Invalid status code {status_code} for chunked request")
        except socket.error as e:
            self.assert_true(False, f"Socket error during chunked transfer test: {e}")
    
    def test_headers_case_insensitivity(self):
        """Test that HTTP headers are treated as case-insensitive."""
        # Send requests with different header case
        headers1 = {'Host': 'localhost', 'User-Agent': 'Tester'}
        headers2 = {'host': 'localhost', 'user-agent': 'Tester'}
        
        try:
            response1 = self.runner.send_request('GET', '/', headers=headers1)
            response2 = self.runner.send_request('GET', '/', headers=headers2)
            
            # Both should succeed and have similar responses
            self.assert_equals(response1.status_code, response2.status_code, 
                           "Different status codes for case-different headers")
        except requests.RequestException as e:
            self.assert_true(False, f"Request failed during headers case test: {e}")
    
    def test_malformed_request_line(self):
        """Test handling of malformed request line."""
        # Send a raw HTTP request with malformed request line
        request = "INVALID / HTTP/1.1\r\nHost: localhost:8080\r\nConnection: close\r\n\r\n"
        response = self.runner.send_raw_request(request)
        
        # Should respond with 400 Bad Request or 501 Not Implemented
        self.assert_true('400' in response[:20] or '501' in response[:20], 
                         f"Expected 400 or 501 response for malformed request line, got: {response[:50]}")
    
    def test_malformed_headers(self):
        """Test handling of malformed headers."""
        # Send a raw HTTP request with malformed headers
        request = "GET / HTTP/1.1\r\nMalformed-Header\r\nHost: localhost:8080\r\nConnection: close\r\n\r\n"
        response = self.runner.send_raw_request(request)
        
        # Should respond with 400 Bad Request
        self.assert_true('400' in response[:20], 
                         f"Expected 400 response for malformed headers, got: {response[:50]}")
    
    def test_empty_request(self):
        """Test handling of empty request."""
        # Send an empty request
        request = "\r\n\r\n"
        response = self.runner.send_raw_request(request)
        
        # Should respond with 400 Bad Request
        self.assert_true('400' in response[:20], 
                         f"Expected 400 response for empty request, got: {response[:50]}")
    
    def test_keep_alive(self):
        """Test handling of Connection: keep-alive."""
        # Create a socket and send multiple requests
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.runner.timeout)
        
        try:
            sock.connect((self.runner.host, self.DEFAULT_PORT))
            
            # Send first request with keep-alive
            request1 = "GET / HTTP/1.1\r\nHost: localhost\r\nConnection: keep-alive\r\n\r\n"
            sock.sendall(request1.encode('utf-8'))
            
            # Read response (this is simplified)
            response1 = b''
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response1 += chunk
                if b'\r\n\r\n' in response1 and not self._is_chunked(response1):
                    # Got headers and not chunked, look for Content-Length
                    content_length = self._get_content_length(response1)
                    if content_length is not None:
                        # Check if we've received the full body
                        headers_end = response1.find(b'\r\n\r\n') + 4
                        if len(response1) - headers_end >= content_length:
                            break
            
            # Send second request on same connection
            request2 = "GET /favicon.ico HTTP/1.1\r\nHost: localhost:8080\r\nConnection: close\r\n\r\n"
            sock.sendall(request2.encode('utf-8'))
            
            # Read response
            response2 = b''
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response2 += chunk
            
            # Both responses should be valid HTTP responses
            self.assert_true(response1.startswith(b'HTTP/1.1 '), 
                             "First response is not a valid HTTP response")
            self.assert_true(response2.startswith(b'HTTP/1.1 '), 
                             "Second response is not a valid HTTP response")
            
        except Exception as e:
            self.assert_true(False, f"Keep-alive test failed: {e}")
        finally:
            sock.close()
    
    def test_header_size_limits(self):
        """Test handling of header size limits."""
        # Create a request with very large headers
        headers = {
            'X-Large-Header': 'A' * 8193,  # 8KB + 1 byte header (exceeds 8192 limit)
            'Host': 'localhost'
        }
        
        try:
            response = self.runner.send_request('GET', '/', headers=headers)
            
            # Server should reject oversized headers with 400 Bad Request or 431 Request Header Fields Too Large
            self.assert_true(response.status_code in [400, 431], 
                             f"Server should reject oversized headers with 400 or 431, got {response.status_code}")
        except requests.RequestException as e:
            self.assert_true(False, f"Request failed during header size test: {e}")
    
    def test_many_headers(self):
        """Test handling of many headers."""
        # Create a request with many headers
        headers = {'Host': 'localhost'}
        
        for i in range(100):
            headers[f'X-Custom-Header-{i}'] = f'Value {i}'
        
        try:
            response = self.runner.send_request('GET', '/', headers=headers)
            
            # Server should reject too many headers with 400 Bad Request or 431 Request Header Fields Too Large
            self.assert_true(response.status_code in [400, 431], 
                             f"Server should reject too many headers with 400 or 431, got {response.status_code}")
        except requests.RequestException as e:
            self.assert_true(False, f"Request failed during many headers test: {e}")
    
    # HTTP Status Code Tests
    
    def test_200_ok(self):
        """Test 200 OK status code for successful requests to allowed paths."""
        # Test paths that should return 200 OK according to test.conf
        # / and /static/ should return 200 OK for GET
        paths = ['/', '/static/', '/exact']
        
        for path in paths:
            try:
                response = self.runner.send_request('GET', path)
                self.assert_equals(response.status_code, 200, f"Expected 200 OK for {path}")
            except requests.RequestException as e:
                self.assert_true(False, f"Request failed for {path}: {e}")
    
    def test_404_not_found(self):
        """Test 404 Not Found status code for missing resources."""
        # Generate a random non-existent path
        random_path = '/' + ''.join(random.choices(string.ascii_letters, k=10))
        
        try:
            response = self.runner.send_request('GET', random_path)
            self.assert_equals(response.status_code, 404, f"Expected 404 Not Found for {random_path}")
            
            # Check for custom error page as defined in test.conf
            self.assert_true('<!-- Test: custom_404_page -->' in response.text,
                        "Custom 404.html error page not served for non-existent path")
        except requests.RequestException as e:
            self.assert_true(False, f"Request failed during 404 test: {e}")
    
    def test_400_bad_request(self):
        """Test 400 Bad Request for malformed requests."""
        # We already test this in test_malformed_headers, but add a direct test
        request = "GET / HTTP/1.1\r\nBadly-Formed:: Header\r\nHost: localhost:8080\r\nConnection: close\r\n\r\n"
        response = self.runner.send_raw_request(request)
        self.assert_true('400' in response[:20], "Expected 400 Bad Request for malformed header")
    
    def test_413_payload_too_large(self):
        """
        Test 413 Payload Too Large for oversized requests according to test.conf.
        
        According to test.conf:
        - Main server has client_max_body_size 5m
        - Port 8082 has client_max_body_size 1m
        - /small_limit on port 8082 has client_max_body_size 50k
        """
        # Test /small_limit on port 8082 which has a 50KB limit
        large_body = 'X' * (60 * 1024)  # 60KB (above 50KB limit)
        headers = {'Host': f'localhost:{self.ALT_PORT_2}', 'Content-Type': 'text/plain'}
        url = f"http://{self.runner.host}:{self.ALT_PORT_2}/small_limit"
        
        try:
            response = requests.post(url, data=large_body, headers=headers, timeout=5)
            # Server should return 413 Payload Too Large
            self.assert_equals(response.status_code, 413, 
                            f"Expected 413 for large payload to /small_limit, got: {response.status_code}")
        except requests.RequestException as e:
            self.assert_true(False, f"Request failed during 413 test: {e}")
    
    # Content Validation Tests
    
    def test_content_length_validation(self):
        """Test Content-Length header matches actual content."""
        # Test with paths defined in test.conf
        paths = ['/', '/static/', '/exact']
        
        for path in paths:
            try:
                response = self.runner.send_request('GET', path)
                
                # Check if Content-Length header is present and accurate
                if 'Content-Length' in response.headers:
                    content_length = int(response.headers['Content-Length'])
                    actual_length = len(response.content)
                    self.assert_equals(content_length, actual_length, 
                                    f"Content-Length header ({content_length}) doesn't match actual content length ({actual_length}) for {path}")
            except requests.RequestException as e:
                self.assert_true(False, f"Request failed during content-length test for {path}: {e}")
    
    def test_transfer_encoding_chunked(self):
        """Test proper handling of chunked transfer encoding in responses."""
        # Make a request that might trigger a chunked response
        headers = {'Accept-Encoding': 'chunked'}
        
        try:
            response = self.runner.send_request('GET', '/', headers=headers)
            
            # Check if response uses chunked encoding
            if 'Transfer-Encoding' in response.headers:
                if response.headers['Transfer-Encoding'].lower() == 'chunked':
                    # Chunked responses should not have Content-Length
                    self.assert_true('Content-Length' not in response.headers,
                                "Chunked response should not include Content-Length header")
        except requests.RequestException as e:
            self.assert_true(False, f"Request failed during chunked encoding test: {e}")
    
    def test_content_type_validation(self):
        """
        Test correct Content-Type headers for different resources.
        
        Validates content types for paths defined in test.conf:
        - / and /index.html should be text/html
        - /static/ with autoindex should be text/html
        - /exact with exact.html should be text/html
        """
        # Test paths and their expected content types
        test_cases = [
            ('/', 'text/html'),                # Root serves index.html
            ('/static/', 'text/html'),         # Static serves directory listing (autoindex on)
            ('/exact', 'text/html'),           # Exact match serves exact.html
            ('/static/prefix_match.html', 'text/html')  # Static HTML file
        ]
        
        for path, expected_type in test_cases:
            try:
                response = self.runner.send_request('GET', path)
                if response.status_code == 200:
                    self.assert_true('Content-Type' in response.headers,
                                  f"Missing Content-Type header for {path}")
                    content_type = response.headers['Content-Type'].lower()
                    self.assert_true(expected_type in content_type,
                                  f"Expected {expected_type} for {path}, got: {content_type}")
            except requests.RequestException as e:
                self.assert_true(False, f"Request failed for content type test on {path}: {e}")
    
    # Header Handling Tests
    
    def test_duplicate_headers(self):
        """Test handling of duplicate headers in requests."""
        # Unfortunately, requests library normalizes headers
        # We need to use raw socket for this test
        request = (
            "GET / HTTP/1.1\r\n"
            "Host: localhost:8080\r\n"
            "Connection: close\r\n"
            "X-Custom-Header: value1\r\n"
            "X-Custom-Header: value2\r\n"
            "\r\n"
        )
        
        try:
            response = self.runner.send_raw_request(request)
            
            # Server should handle this without error
            self.assert_true(response.startswith('HTTP/1.1 2') or response.startswith('HTTP/1.1 3'),
                        f"Unexpected response to duplicate headers: {response[:50]}")
        except socket.error as e:
            self.assert_true(False, f"Socket error during duplicate headers test: {e}")
    
    def test_header_folding(self):
        """Test support for folded headers (multi-line headers)."""
        # Folded headers are deprecated in HTTP/1.1 but should be handled
        request = (
            "GET / HTTP/1.1\r\n"
            "Host: localhost:8080\r\n"
            "Connection: close\r\n"
            "X-Folded-Header: part1\r\n"
            " part2\r\n"
            "\r\n"
        )
        
        try:
            response = self.runner.send_raw_request(request)
            
            # Server should reject folded headers with 400 Bad Request (obsolete per RFC 7230)
            self.assert_true(response.startswith('HTTP/1.1 400'),
                        f"Server should reject folded headers with 400 Bad Request, got: {response[:50]}")
        except socket.error as e:
            self.assert_true(False, f"Socket error during header folding test: {e}")
    
    # Request Line Tests
    
    def test_absolute_url_in_request(self):
        """Test handling of absolute URLs in request line."""
        # Send a request with an absolute URL in the request line
        request = f"GET http://{self.runner.host}:{self.DEFAULT_PORT}/ HTTP/1.1\r\nHost: localhost:8080\r\nConnection: close\r\n\r\n"
        
        try:
            response = self.runner.send_raw_request(request)
            
            # Server should handle this properly
            self.assert_true(response.startswith('HTTP/1.1 2'),
                        f"Unexpected response to absolute URL: {response[:50]}")
        except socket.error as e:
            self.assert_true(False, f"Socket error during absolute URL test: {e}")
    
    def test_request_line_length_limits(self):
        """Test maximum length for request line."""
        # Create a request with a very long path
        long_path = '/' + 'a' * 8000
        request = f"GET {long_path} HTTP/1.1\r\nHost: localhost:8080\r\nConnection: close\r\n\r\n"

        try:
            response = self.runner.send_raw_request(request)
            
            # Server should reject with 414 URI Too Long or 400 Bad Request
            self.assert_true('414' in response[:20] or '400' in response[:20],
                        f"Expected 414 or 400 for long URI, got: {response[:50]}")
        except socket.error as e:
            self.assert_true(False, f"Socket error during request line length test: {e}")
    
    def test_uri_parameter_handling(self):
        """Test handling of complex query strings."""
        # Create a request with complex query parameters
        complex_params = {
            'param1': 'value with spaces',
            'param2': 'value with !@#$%^&*()',
            'param3[]': '1',
            'param3[]': '2',
            'param4': '日本語'  # Unicode characters
        }
        
        try:
            query_string = urlencode(complex_params, doseq=True)
            response = self.runner.send_request('GET', f'/?{query_string}')
            
            # Server should handle this properly
            self.assert_true(response.status_code < 500,
                        f"Server error with complex query string: {response.status_code}")
        except requests.RequestException as e:
            self.assert_true(False, f"Request failed during URI parameter test: {e}")
    
    def test_special_uri_characters(self):
        """Test handling of special characters in URIs."""
        # Test a few URIs with special characters according to test.conf paths
        special_paths = [
            '/static%20with%20spaces/',        # URL-encoded spaces in path
            '/static/file%2Bwith%2Bplus.html', # Plus signs in filename
            '/static/file.with.dots',          # Multiple dots in filename
            '/exact?param=value&param2=value2' # Query string on exact match
        ]
        
        for path in special_paths:
            try:
                response = self.runner.send_request('GET', path)
                # We don't know if these paths exist, but the server should respond properly
                self.assert_true(response.status_code in [200, 404],
                            f"Invalid response for special URI {path}: {response.status_code}")
                
                # If 404, it should be the custom error page
                if response.status_code == 404:
                    self.assert_true('<!-- Test: custom_404_page -->' in response.text,
                                "Custom 404 page not served for special URI path")
            except requests.RequestException as e:
                self.assert_true(False, f"Request failed for special URI {path}: {e}")
    
    def test_virtual_hosts(self):
        """
        Test virtual host functionality according to test.conf.
        
        According to test.conf:
        - Main server on port 8080 has server_name localhost test-server.local www.test-server.local
        """
        # Test each server name defined in test.conf
        server_names = ['localhost', 'test-server.local', 'www.test-server.local']
        
        for server_name in server_names:
            try:
                # Send request with specific Host header
                response = self.runner.send_request('GET', '/', headers={'Host': server_name})
                
                # Should return 200 OK
                self.assert_true(response.status_code == 200,
                              f"Request with Host {server_name} failed with status {response.status_code}")
                
                # Should contain the main page content
                self.assert_true('<!-- Test: index_file_location -->' in response.text,
                              f"Response for Host {server_name} doesn't contain expected content")
            except requests.RequestException as e:
                self.assert_true(False, f"Request with Host {server_name} failed: {e}")
    
    def _is_chunked(self, response):
        """Check if response is using chunked transfer encoding."""
        headers = response.split(b'\r\n\r\n')[0].lower()
        return b'transfer-encoding: chunked' in headers
    
    def _get_content_length(self, response):
        """Extract Content-Length from response headers."""
        headers = response.split(b'\r\n\r\n')[0].decode('utf-8', errors='ignore')
        for line in headers.split('\r\n'):
            if line.lower().startswith('content-length:'):
                try:
                    return int(line.split(':', 1)[1].strip())
                except ValueError:
                    return None
        return None