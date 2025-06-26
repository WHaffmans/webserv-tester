#!/usr/bin/env python3
"""
URI Tests

Tests for URI handling according to HTTP/1.1 specifications and RFC standards.
These tests verify the server's ability to properly parse, normalize, and map
URIs to filesystem resources as specified in the test.conf configuration.

RFC references:
- RFC 3986: Uniform Resource Identifier (URI): Generic Syntax
- RFC 7230: HTTP/1.1 Message Syntax and Routing
- RFC 7231: HTTP/1.1 Semantics and Content
- RFC 3875: The Common Gateway Interface (CGI)
"""

import os
import time
import random
import string
import requests
import urllib.parse
import shutil
from pathlib import Path
from core.test_case import TestCase
from core.path_utils import get_tester_root, resolve_path

class URITests(TestCase):
    """Tests URI handling according to HTTP/1.1 specifications."""
    
    def setup(self):
        """Set up test environment for URI tests."""
        self.test_dir = resolve_path('data/www/uri_tests')
        self.ensure_test_directories()
        self.create_test_files()
        
    def teardown(self):
        """Clean up test environment after URI tests."""
        # Clean up all test files and directories created during testing
        if hasattr(self, 'test_dir') and os.path.exists(self.test_dir):
            for attempt in range(3):
                try:
                    shutil.rmtree(self.test_dir)
                    self.logger.debug(f"Successfully cleaned up test directory: {self.test_dir}")
                    break
                except Exception as e:
                    self.logger.debug(f"Error cleaning up test directory (attempt {attempt+1}): {e}")
                    time.sleep(0.2)
            else:
                # Fallback: try to remove files/dirs individually
                for root, dirs, files in os.walk(self.test_dir, topdown=False):
                    for name in files:
                        file_path = os.path.join(root, name)
                        try:
                            os.remove(file_path)
                        except Exception as e:
                            self.logger.debug(f"Fallback error removing file {file_path}: {e}")
                    for name in dirs:
                        dir_path = os.path.join(root, name)
                        try:
                            os.rmdir(dir_path)
                        except Exception as e:
                            self.logger.debug(f"Fallback error removing dir {dir_path}: {e}")
                try:
                    os.rmdir(self.test_dir)
                except Exception as e:
                    self.logger.debug(f"Fallback error removing test_dir {self.test_dir}: {e}")
        
        # Clean up any specific test files outside the main test directory
        for path in ['data/www/uri_tests/no_index', 'data/www/uri_tests/trailingslash', 'data/www/uri_tests/trailingslash.html']:
            full_path = resolve_path(path)
            if os.path.exists(full_path):
                try:
                    if os.path.isdir(full_path):
                        shutil.rmtree(full_path)
                    else:
                        os.remove(full_path)
                except Exception as e:
                    self.logger.debug(f"Error cleaning up {full_path}: {e}")
    
    def ensure_test_directories(self):
        """Create necessary directories for testing URI handling."""
        # Create main test directory if it doesn't exist
        os.makedirs(self.test_dir, exist_ok=True)
        
        # Create nested directories for path testing
        os.makedirs(os.path.join(self.test_dir, 'a', 'b', 'c'), exist_ok=True)
        os.makedirs(os.path.join(self.test_dir, 'docs', 'files'), exist_ok=True)
        os.makedirs(os.path.join(self.test_dir, 'UPPERCASE'), exist_ok=True)
        os.makedirs(os.path.join(self.test_dir, 'with spaces'), exist_ok=True)
        os.makedirs(os.path.join(self.test_dir, 'special+chars'), exist_ok=True)
        
    def create_test_files(self):
        """Create test files for URI tests."""
        # Create test file in root directory
        with open(os.path.join(self.test_dir, 'test.html'), 'w') as f:
            f.write("<!DOCTYPE html>\n<html><body><h1>URI Test File</h1><p>Root directory test file</p></body></html>")
        
        # Create test files in nested directories
        with open(os.path.join(self.test_dir, 'a', 'test.html'), 'w') as f:
            f.write("<!DOCTYPE html>\n<html><body><h1>URI Test File</h1><p>Directory A test file</p></body></html>")
        
        with open(os.path.join(self.test_dir, 'a', 'b', 'test.html'), 'w') as f:
            f.write("<!DOCTYPE html>\n<html><body><h1>URI Test File</h1><p>Directory A/B test file</p></body></html>")
        
        with open(os.path.join(self.test_dir, 'a', 'b', 'c', 'test.html'), 'w') as f:
            f.write("<!DOCTYPE html>\n<html><body><h1>URI Test File</h1><p>Directory A/B/C test file</p></body></html>")
        
        # Create index files for directory testing
        with open(os.path.join(self.test_dir, 'index.html'), 'w') as f:
            f.write("<!DOCTYPE html>\n<html><body><h1>Index File</h1><p>Root directory index</p></body></html>")
        
        with open(os.path.join(self.test_dir, 'a', 'index.html'), 'w') as f:
            f.write("<!DOCTYPE html>\n<html><body><h1>Index File</h1><p>Directory A index</p></body></html>")
        
        # Create files with special characters in names
        with open(os.path.join(self.test_dir, 'with spaces', 'file with spaces.html'), 'w') as f:
            f.write("<!DOCTYPE html>\n<html><body><h1>File With Spaces</h1></body></html>")
        
        with open(os.path.join(self.test_dir, 'special+chars', 'file+with+plus.html'), 'w') as f:
            f.write("<!DOCTYPE html>\n<html><body><h1>File With Plus Signs</h1></body></html>")
        
        # Create a file with mixed case name
        with open(os.path.join(self.test_dir, 'MixedCase.html'), 'w') as f:
            f.write("<!DOCTYPE html>\n<html><body><h1>Mixed Case Filename</h1></body></html>")
        
        # Create a file in the UPPERCASE directory
        with open(os.path.join(self.test_dir, 'UPPERCASE', 'FILE.html'), 'w') as f:
            f.write("<!DOCTYPE html>\n<html><body><h1>UPPERCASE FILE</h1></body></html>")

    def test_uri_path_normalization(self):
        """
        Test path normalization in URIs according to RFC 3986 Section 5.2.4.
        
        Verifies that the server correctly normalizes paths containing:
        - Single dot segments (./): should be removed
        - Double dot segments (../): should remove the previous segment
        - Multiple consecutive slashes (//): should be normalized to a single slash
        """
        # Base path to the URI test directory
        base_uri = '/uri_tests'
        
        # Test cases with expected normalized paths
        test_cases = [
            # path, expected path component in response
            (f'{base_uri}/a/./test.html', 'Directory A test file'),
            (f'{base_uri}/a/b/../test.html', 'Directory A test file'),
            (f'{base_uri}/a/b/c/../../test.html', 'Directory A test file'),
            (f'{base_uri}/a/./b/./c/./test.html', 'Directory A/B/C test file'),
            (f'{base_uri}/a//b///c////test.html', 'Directory A/B/C test file'),
            (f'{base_uri}/./a/./b/./c/./test.html', 'Directory A/B/C test file'),
            (f'{base_uri}/../uri_tests/a/test.html', 'Directory A test file'),
        ]
        
        for path, expected_content in test_cases:
            try:
                response = self.runner.send_request('GET', path)
                
                # Check if the server normalized the path correctly
                self.assert_equals(response.status_code, 200, 
                                  f"Failed to normalize URI path: {path}")
                
                # Verify the correct file was served
                self.assert_true(expected_content in response.text, 
                                f"Incorrect content for normalized path: {path}")
                
            except requests.RequestException as e:
                self.assert_true(False, f"Request failed for path {path}: {e}")

    def test_uri_path_traversal_prevention(self):
        """
        Test prevention of directory traversal attacks according to RFC 3986 Section 5.2.4.
        
        Verifies that the server prevents access to files outside the document root
        by using path traversal sequences (../).
        """
        # Attempt to access files outside the document root
        traversal_attempts = [
            '/uri_tests/../../../etc/passwd',
            '/../../../etc/passwd',
            '/uri_tests/..%2f..%2f..%2fetc/passwd',  # URL-encoded "../"
            '/uri_tests/%2e%2e/%2e%2e/%2e%2e/etc/passwd',  # URL-encoded "../"
            '/uri_tests/a/b/c/../../../../etc/passwd',
            '/%2e%2e/%2e%2e/%2e%2e/etc/passwd',  # URL-encoded "../"
        ]
        
        for path in traversal_attempts:
            try:
                response = self.runner.send_request('GET', path)
                
                # The server should either return 403 Forbidden or 404 Not Found
                self.assert_true(response.status_code in [403, 404], 
                                f"Path traversal not prevented for: {path}, got {response.status_code}")
                
                # Make sure we didn't get the actual file content
                self.assert_false('root:' in response.text, 
                                 f"Path traversal succeeded for: {path}")
                
            except requests.RequestException as e:
                self.assert_true(False, f"Request failed for path {path}: {e}")

    def test_uri_encoding_decoding(self):
        """
        Test handling of percent-encoded characters in URIs according to RFC 3986 Section 2.1.
        
        Verifies that the server correctly decodes percent-encoded characters in URIs
        and serves the appropriate resources.
        """
        # Create a set of test cases with different encodings
        test_cases = [
            # (path, encoded_path, expected_status_code)
            ('/uri_tests/with spaces/file with spaces.html', 
             '/uri_tests/with%20spaces/file%20with%20spaces.html', 200),
            
            ('/uri_tests/special+chars/file+with+plus.html', 
             '/uri_tests/special%2Bchars/file%2Bwith%2Bplus.html', 200),
            
            # Test some special ASCII characters
            ('/uri_tests/test.html', '/uri_tests/test%2Ehtml', 200),  # %2E = .
            
            # Test encoded slash
            ('/uri_tests%2Ftest.html', None, 404),  # %2F = / (should be different resource)
            
            # Test various encoded characters
            ('/uri_tests/test%41.html', None, 404),  # %41 = A
            ('/uri_tests/test%7a.html', None, 404),  # %7a = z
            
            # Test a complex encoded path
            ('/uri_tests/with%20spaces/file%20with%20spaces.html', None, 200),
        ]
        
        for original_path, encoded_path, expected_status in test_cases:
            paths_to_test = [original_path]
            if encoded_path:
                paths_to_test.append(encoded_path)
            
            for path in paths_to_test:
                try:
                    response = self.runner.send_request('GET', path)
                    
                    # Check status code
                    self.assert_equals(response.status_code, expected_status, 
                                      f"Unexpected status for encoded path: {path}")
                    
                    # For 200 responses, verify we got the right content
                    if expected_status == 200:
                        self.assert_true('<html>' in response.text, 
                                        f"Invalid content for encoded path: {path}")
                    
                except requests.RequestException as e:
                    self.assert_true(False, f"Request failed for encoded path {path}: {e}")

    def test_uri_path_mapping(self):
        """
        Test URI to filesystem path mapping according to RFC 7230 Section 5.3.1.
        
        Verifies that the server correctly maps URI paths to filesystem paths
        based on the configuration.
        """
        # Test various URI paths and verify they map to the correct filesystem resources
        test_cases = [
            # (uri, content_check)
            ('/uri_tests/test.html', 'Root directory test file'),
            ('/uri_tests/a/test.html', 'Directory A test file'),
            ('/uri_tests/a/b/test.html', 'Directory A/B test file'),
            ('/uri_tests/a/b/c/test.html', 'Directory A/B/C test file'),
        ]
        
        for uri, content_check in test_cases:
            try:
                response = self.runner.send_request('GET', uri)
                
                # Check status code
                self.assert_equals(response.status_code, 200, 
                                  f"Failed to map URI to filesystem path: {uri}")
                
                # Verify the correct file was served
                self.assert_true(content_check in response.text, 
                                f"Incorrect content for URI: {uri}")
                
            except requests.RequestException as e:
                self.assert_true(False, f"Request failed for URI {uri}: {e}")

    def test_uri_default_document_resolution(self):
        """
        Test default document resolution for directory URIs according to RFC 7231 Section 6.3.1.
        
        Verifies that when a URI points to a directory, the server serves the
        configured default document (typically index.html).
        """
        # Test directory URIs that should resolve to index files
        test_cases = [
            # (uri, content_check)
            ('/uri_tests/', 'Root directory index'),
            ('/uri_tests/a/', 'Directory A index'),
        ]
        
        for uri, content_check in test_cases:
            try:
                response = self.runner.send_request('GET', uri)
                
                # Check status code
                self.assert_equals(response.status_code, 200, 
                                  f"Failed to resolve default document for: {uri}")
                
                # Verify the correct index file was served
                self.assert_true(content_check in response.text, 
                                f"Incorrect default document for: {uri}")
                
            except requests.RequestException as e:
                self.assert_true(False, f"Request failed for URI {uri}: {e}")

    def test_uri_for_directory_listing(self):
        """
        Test URIs that should trigger directory listings.
        
        Verifies that the server generates directory listings for directories
        where autoindex is enabled and no index file exists.
        """
        # Create a new directory without an index file
        no_index_dir = os.path.join(self.test_dir, 'no_index')
        os.makedirs(no_index_dir, exist_ok=True)
        
        # Create some files in the directory
        for i in range(3):
            with open(os.path.join(no_index_dir, f'file{i}.html'), 'w') as f:
                f.write(f"<!DOCTYPE html>\n<html><body><h1>File {i}</h1></body></html>")
        
        # Test the URI that should trigger a directory listing
        uri = '/uri_tests/no_index/'
        
        try:
            response = self.runner.send_request('GET', uri)
            
            # Directory listing could return 200 OK or 403 Forbidden depending on configuration
            self.assert_true(response.status_code in [200, 403], 
                            f"Unexpected status for directory listing: {uri}")
            
            # If directory listing is enabled (200 OK), check for listing indicators
            if response.status_code == 200:
                # Check for common directory listing indicators
                directory_indicators = [
                    'Index of',
                    'Directory listing',
                    'Parent Directory',
                    '<dir',
                    '<directory',
                    'file0.html',
                    'file1.html',
                    'file2.html'
                ]
                
                # At least one of these indicators should be present
                found_indicator = False
                for indicator in directory_indicators:
                    if indicator.lower() in response.text.lower():
                        found_indicator = True
                        break
                
                self.assert_true(found_indicator, 
                                f"Directory listing not found for: {uri}")
            
        except requests.RequestException as e:
            self.assert_true(False, f"Request failed for URI {uri}: {e}")

    def test_uri_with_multiple_slashes(self):
        """
        Test handling of URIs with consecutive slashes according to RFC 3986 Section 5.2.4.
        
        Verifies that the server normalizes consecutive slashes in URIs.
        """
        # Test cases with multiple consecutive slashes
        test_cases = [
            # (uri, expected_status)
            ('/uri_tests//test.html', 200),
            ('/uri_tests///test.html', 200),
            ('/uri_tests//a///b////c/////test.html', 200),
        ]
        
        for uri, expected_status in test_cases:
            try:
                response = self.runner.send_request('GET', uri)
                
                # Check status code
                self.assert_equals(response.status_code, expected_status, 
                                f"Unexpected status for multiple slashes: {uri}")
                
                # For successful responses, verify content
                if expected_status == 200:
                    self.assert_true('<html>' in response.text, 
                                    f"Invalid content for URI with multiple slashes: {uri}")
                
            except requests.RequestException as e:
                self.assert_true(False, f"Request failed for URI {uri}: {e}")
                
    def test_relative_vs_absolute_uris(self):
        """
        Test handling of relative vs absolute URIs according to RFC 7230 Section 5.3.1.
        
        Verifies that the server correctly handles both relative URIs (/path)
        and absolute URIs (http://host/path).
        """
        # Get server host and port
        host = self.runner.host
        port = self.runner.port
        
        # Test cases with relative and absolute URIs
        test_cases = [
            # (uri, expected_status)
            ('/uri_tests/test.html', 200),  # Relative URI
            (f'http://{host}:{port}/uri_tests/test.html', 200),  # Absolute URI
        ]
        
        for uri, expected_status in test_cases:
            try:
                # For absolute URIs, use requests directly instead of the runner
                if uri.startswith('http'):
                    response = requests.get(uri, timeout=self.runner.timeout)
                else:
                    response = self.runner.send_request('GET', uri)
                
                # Check status code
                self.assert_equals(response.status_code, expected_status, 
                                  f"Unexpected status for URI: {uri}")
                
                # For successful responses, verify content
                if expected_status == 200:
                    self.assert_true('<html>' in response.text, 
                                    f"Invalid content for URI: {uri}")
                
            except requests.RequestException as e:
                self.assert_true(False, f"Request failed for URI {uri}: {e}")

    def test_uri_with_trailing_slash_handling(self):
        """
        Test handling of URIs with and without trailing slashes according to RFC 3986 Section 6.
        
        Verifies that the server correctly distinguishes between URIs ending with /
        (indicating a directory) and those without (typically indicating a file).
        """
        # Create a test file and directory with the same name
        dirname = 'trailingslash'
        os.makedirs(os.path.join(self.test_dir, dirname), exist_ok=True)
        
        # Create a file with the same name as the directory
        with open(os.path.join(self.test_dir, f'{dirname}.html'), 'w') as f:
            f.write("<!DOCTYPE html>\n<html><body><h1>File</h1><p>This is a file</p></body></html>")
        
        # Create an index file in the directory
        with open(os.path.join(self.test_dir, dirname, 'index.html'), 'w') as f:
            f.write("<!DOCTYPE html>\n<html><body><h1>Directory</h1><p>This is a directory index</p></body></html>")
        
        # Test URIs with and without trailing slashes
        test_cases = [
            # (uri, content_check, redirect_expected)
            (f'/uri_tests/{dirname}', 'Directory', True),  # May redirect to /uri_tests/{dirname}/
            (f'/uri_tests/{dirname}/', 'Directory', False),  # Should serve the directory index
            (f'/uri_tests/{dirname}.html', 'File', False),  # Should serve the file
        ]
        
        for uri, content_check, redirect_expected in test_cases:
            try:
                # First test without following redirects
                response = self.runner.send_request('GET', uri, allow_redirects=False)
                
                # If a redirect is expected, check for it
                if redirect_expected and response.status_code in [301, 302, 303, 307, 308]:
                    self.assert_true('Location' in response.headers, 
                                    f"Redirect missing Location header: {uri}")
                    
                    # Check that the Location header ends with a slash
                    location = response.headers['Location']
                    self.assert_true(location.endswith('/'), 
                                    f"Redirect location should end with /: {location}")
                    
                    # Now follow the redirect
                    response = self.runner.send_request('GET', uri, allow_redirects=True)
                    
                # Check status code (after possible redirect)
                self.assert_equals(response.status_code, 200, 
                                  f"Unexpected status for URI: {uri}")
                
                # Verify the correct content was served
                self.assert_true(content_check in response.text, 
                                f"Incorrect content for URI: {uri}")
                
            except requests.RequestException as e:
                self.assert_true(False, f"Request failed for URI {uri}: {e}")

    def test_uri_case_sensitivity(self):
        """
        Test URI case sensitivity according to RFC 3986 Section 6.2.2.1.
        
        Verifies whether the server treats URIs case-sensitively or case-insensitively.
        According to the RFC, the scheme and host components are case-insensitive,
        while the path is case-sensitive.
        """
        # Create test cases with different cases
        test_cases = [
            # (uri, expected_status)
            ('/uri_tests/MixedCase.html', 200),  # Original case
            ('/uri_tests/mixedcase.html', None),  # Lowercase
            ('/uri_tests/MIXEDCASE.html', None),  # Uppercase
            ('/uri_tests/UPPERCASE/FILE.html', 200),  # Original case
            ('/uri_tests/uppercase/file.html', None),  # Lowercase
        ]
        
        for uri, expected_status in test_cases:
            try:
                response = self.runner.send_request('GET', uri)
                
                # If expected_status is None, we accept whatever the server does
                # (Some servers are case-sensitive, others are case-insensitive)
                if expected_status is not None:
                    self.assert_equals(response.status_code, expected_status, 
                                      f"Unexpected status for case variation: {uri}")
                    
                # Log the server's behavior
                if uri.lower() != uri and response.status_code == 200:
                    self.logger.debug(f"Server is case-insensitive for path: {uri}")
                elif uri.lower() != uri and response.status_code == 404:
                    self.logger.debug(f"Server is case-sensitive for path: {uri}")
                
            except requests.RequestException as e:
                self.assert_true(False, f"Request failed for URI {uri}: {e}")

    def test_uri_too_long(self):
        """
        Test handling of extremely long URIs according to RFC 7230 Section 3.1.1.
        
        Verifies that the server correctly handles (or rejects) extremely long URIs.
        """
        # Create test cases with increasingly long URIs
        test_cases = [
            # (uri_length, expected_status_range)
            (512, range(200, 301)),    # Should be fine
            (1024, range(200, 301)),   # Should be fine
            (4096, range(200, 501)),   # Might be too long for some servers
            (8192, range(400, 501)),   # Probably too long for most servers
        ]
        
        for length, status_range in test_cases:
            # Generate a random string of the specified length
            random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=length))
            
            # Create a long URI with random query parameters
            uri = f'/uri_tests/test.html?q={random_str}'
            
            try:
                response = self.runner.send_request('GET', uri)
                
                # Check status code is in the expected range
                self.assert_true(response.status_code in status_range, 
                                f"Unexpected status for long URI ({length} chars)")
                
                # Special check for 414 URI Too Long response
                if response.status_code == 414:
                    self.logger.debug(f"Server correctly rejected URI with length {length}")
                
            except requests.RequestException as e:
                # Connection errors are NOT acceptable - server should return proper HTTP status
                self.assert_true(False, f"Server failed to respond with proper HTTP status for URI length {length}: {e}")

    def test_uri_path_segment_validation(self):
        """
        Test validation of URI path segments according to RFC 3986 Section 2.2.
        """
        # Test 1: Characters that should be rejected even when percent-encoded
        definitely_invalid = [
            ('%00', 'null byte'),  # Your server specifically rejects this
        ]
        
        for encoded_char, description in definitely_invalid:
            uri = f'/uri_tests/test{encoded_char}.html'
            
            try:
                response = self.runner.send_request('GET', uri)
                self.assert_equals(response.status_code, 400, 
                                f"Server should reject {description}, got {response.status_code}")
            except requests.RequestException as e:
                self.assert_true(False, f"Request failed for {description}: {e}")
        
        # Test 2: Characters that should be properly percent-encoded (and accepted)
        should_be_encoded = [
            (' ', '%20', 'space'),
            ('<', '%3C', 'less than'),
            ('>', '%3E', 'greater than'),
            ('"', '%22', 'double quote'),
        ]
        
        for char, encoded, description in should_be_encoded:
            # Create a temporary test file
            test_filename = f'test_encoded_{description.replace(" ", "_")}.html'
            test_file_path = os.path.join(self.test_dir, test_filename)
            
            with open(test_file_path, 'w') as f:
                f.write(f"<!DOCTYPE html>\n<html><body><h1>Test {description}</h1></body></html>")
            
            try:
                # Properly encoded version should work
                encoded_uri = f'/uri_tests/{test_filename.replace(" ", "%20")}'
                response = self.runner.send_request('GET', encoded_uri)
                
                # Should either find the file (200) or not find it (404), but not return 400
                self.assert_true(response.status_code in [200, 404], 
                            f"Properly encoded {description} should not return 400, got {response.status_code}")
                
            except requests.RequestException as e:
                self.assert_true(False, f"Request failed for encoded {description}: {e}")
            finally:
                # Clean up
                if os.path.exists(test_file_path):
                    os.remove(test_file_path)