#!/usr/bin/env python3
"""
File Upload Tests

Tests for file upload functionality according to test.conf configuration:
- Location /upload {
-     root data/www/upload;
-     methods POST;
-     upload_store data/uploads;
- }

Verifies correct handling of single and multiple file uploads, size limits, and error cases.
"""

import requests
import os
import tempfile
import shutil
import time
from pathlib import Path
from core.test_case import TestCase
from core.path_utils import resolve_path

class UploadTests(TestCase):
    """Tests file upload functionality based on test.conf configuration."""
    
    def setup(self):
        """Set up temporary directory for uploads."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_files = []
        
        # Create test files of different sizes
        self.small_file_path = os.path.join(self.temp_dir, "small.txt")
        with open(self.small_file_path, "w") as f:
            f.write("Small test file for upload")
        
        self.medium_file_path = os.path.join(self.temp_dir, "medium.txt")
        with open(self.medium_file_path, "w") as f:
            f.write("A" * 10000)  # 10KB file
        
        self.test_files.extend([self.small_file_path, self.medium_file_path])
        
        # From test.conf configuration, we know the upload endpoint
        self.upload_endpoint = '/upload'
        
        # Clean up upload directory before testing
        self._clean_uploads_directory()
    
    def teardown(self):
        """Clean up temporary files and directories."""
        for file_path in self.test_files:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass
        
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        
        # Clean up upload directory after testing
        self._clean_uploads_directory()
    
    def _clean_uploads_directory(self):
        """Remove all files from the uploads directory."""
        uploads_dir = resolve_path('data/uploads')
        errors = []
        if os.path.exists(uploads_dir):
            self.logger.debug(f"Cleaning uploads directory: {uploads_dir}")
            for item in os.listdir(uploads_dir):
                item_path = os.path.join(uploads_dir, item)
                if os.path.isfile(item_path):
                    try:
                        os.remove(item_path)
                        self.logger.debug(f"Removed file: {item_path}")
                    except Exception as e:
                        self.logger.debug(f"Error removing file {item_path}: {e}")
                        errors.append(f"File: {item_path} - {e}")
                elif os.path.isdir(item_path):
                    try:
                        shutil.rmtree(item_path)
                        self.logger.debug(f"Removed directory: {item_path}")
                    except Exception as e:
                        self.logger.debug(f"Error removing directory {item_path}: {e}")
                        errors.append(f"Directory: {item_path} - {e}")
        if errors:
            self.logger.error(f"Upload directory cleanup encountered errors: {errors}")
            raise RuntimeError(f"Upload directory cleanup failed for some items: {errors}")
    
    def test_upload_single_file(self):
        """
        Test basic single file upload to the /upload endpoint.
        
        According to test.conf:
        location /upload {
            root data/www/upload;
            methods POST;
            upload_store data/uploads;
        }
        """
        try:
            # Open the small test file
            with open(self.small_file_path, "rb") as f:
                files = {"file": ("test.txt", f, "text/plain")}
                
                # Send upload request to the configured upload endpoint
                response = self.runner.send_request('POST', self.upload_endpoint, files=files)
                
                # Check response - should be 200-299 for success
                self.assert_true(200 <= response.status_code < 300, 
                                f"Upload failed with status code {response.status_code}")
        except requests.RequestException as e:
            self.assert_true(False, f"Upload request failed: {e}")
    
    def test_upload_multiple_files(self):
        """
        Test uploading multiple files in a single request to the /upload endpoint.
        
        According to test.conf:
        location /upload {
            root data/www/upload;
            methods POST;
            upload_store data/uploads;
        }
        """
        try:
            # Prepare multiple files
            with open(self.small_file_path, "rb") as f1, open(self.medium_file_path, "rb") as f2:
                files = {
                    "file1": ("test1.txt", f1, "text/plain"),
                    "file2": ("test2.txt", f2, "text/plain")
                }
                
                # Send upload request to the configured upload endpoint
                response = self.runner.send_request('POST', self.upload_endpoint, files=files)
                
                # Check response - should be 200-299 for success
                self.assert_true(200 <= response.status_code < 300, 
                                f"Multiple file upload failed with status code {response.status_code}")
        except requests.RequestException as e:
            self.assert_true(False, f"Multiple file upload request failed: {e}")
    
    def test_upload_with_fields(self):
        """
        Test uploading file with additional form fields to the /upload endpoint.
        
        According to test.conf:
        location /upload {
            root data/www/upload;
            methods POST;
            upload_store data/uploads;
        }
        """
        try:
            # Prepare file and additional fields
            with open(self.small_file_path, "rb") as f:
                files = {"file": ("test.txt", f, "text/plain")}
                data = {"field1": "value1", "field2": "value2"}
                
                # Send upload request to the configured upload endpoint
                response = self.runner.send_request('POST', self.upload_endpoint, files=files, data=data)
                
                # Check response - should be 200-299 for success
                self.assert_true(200 <= response.status_code < 300, 
                                f"Upload with fields failed with status code {response.status_code}")
        except requests.RequestException as e:
            self.assert_true(False, f"Upload with fields request failed: {e}")
    
    def test_upload_zero_length_file(self):
        """
        Test uploading an empty (zero length) file to the /upload endpoint.
        
        According to test.conf:
        location /upload {
            root data/www/upload;
            methods POST;
            upload_store data/uploads;
        }
        """
        # Create empty file
        empty_file_path = os.path.join(self.temp_dir, "empty.txt")
        with open(empty_file_path, "w") as f:
            pass  # Create empty file
        
        self.test_files.append(empty_file_path)
        
        try:
            # Open the empty test file
            with open(empty_file_path, "rb") as f:
                files = {"file": ("empty.txt", f, "text/plain")}
                
                # Send upload request to the configured upload endpoint
                response = self.runner.send_request('POST', self.upload_endpoint, files=files)
                
                # Check response - should be 200-299 for success
                self.assert_true(200 <= response.status_code < 300, 
                                f"Empty file upload failed with status code {response.status_code}")
        except requests.RequestException as e:
            self.assert_true(False, f"Empty file upload request failed: {e}")
    
    def test_upload_to_disallowed_location(self):
        """
        Test upload to a location where uploads are not allowed.
        
        According to test.conf, only /upload allows POST:
        location / {
            index index.html;
            methods GET POST;
        }
        
        location /static {
            autoindex on;
            methods GET;
        }
        """
        disallowed_location = '/static'
        
        try:
            # Try to upload to a location that doesn't allow POST
            with open(self.small_file_path, "rb") as f:
                files = {"file": ("test.txt", f, "text/plain")}
                
                response = self.runner.send_request('POST', disallowed_location, files=files)
                
                # Should be rejected with 405 Method Not Allowed
                self.assert_equals(response.status_code, 405, 
                                f"Upload to {disallowed_location} should be rejected with 405, got {response.status_code}")
                
                # Should include Allow header
                if response.status_code == 405:
                    self.assert_true('Allow' in response.headers, 
                                    "405 Method Not Allowed response must include Allow header")
        except requests.RequestException as e:
            # Connection errors are NOT acceptable - server should return proper HTTP status
            self.assert_true(False, f"Server failed to respond with proper HTTP status for rejected upload to {disallowed_location}: {e}")
    
    def test_get_request_to_upload_endpoint(self):
        """
        Test sending GET to the upload endpoint which only allows POST.
        
        According to test.conf:
        location /upload {
            root data/www/upload;
            methods POST;
            upload_store data/uploads;
        }
        """
        try:
            # Send GET request to upload endpoint
            response = self.runner.send_request('GET', self.upload_endpoint)
            
            # Should be rejected with 405 Method Not Allowed
            self.assert_equals(response.status_code, 405, 
                            f"GET to {self.upload_endpoint} should be rejected with 405, got {response.status_code}")
            
            # Should include Allow header with POST
            if response.status_code == 405:
                self.assert_true('Allow' in response.headers, 
                                "405 Method Not Allowed response must include Allow header")
                self.assert_true('POST' in response.headers['Allow'], 
                                "Allow header should include POST")
        except requests.RequestException as e:
            # Connection errors are NOT acceptable - server should return proper HTTP status
            self.assert_true(False, f"Server failed to respond with proper HTTP status for GET request to upload endpoint: {e}")
    
    def test_client_max_body_size_limit(self):
        """
        Test file upload size limits based on client_max_body_size.
        
        According to test.conf:
        - Main server (8080) has client_max_body_size 5m
        - Server on port 8082 has client_max_body_size 1m
        - /small_limit on port 8082 has client_max_body_size 50k
        """
        import io
        
        # Test case 1: Upload to main server (5MB limit)
        main_server_url = f"http://{self.runner.host}:{self.runner.port}{self.upload_endpoint}"
        
        # Create a 4MB file (below the 5MB limit)
        size_below_limit = 4 * 1024 * 1024  # 4MB
        data_below_limit = io.BytesIO(b'X' * size_below_limit)
        files_below_limit = {'file': ('test_4MB.txt', data_below_limit, 'text/plain')}
        
        try:
            # This should succeed (below limit)
            response = requests.post(main_server_url, files=files_below_limit, timeout=5)
            self.assert_true(response.status_code < 400, 
                            f"Upload of 4MB to main server rejected with status {response.status_code}")
        except requests.RequestException as e:
            if "timed out" in str(e):
                # Timeout is NOT acceptable - server should handle large uploads properly
                # Increase timeout and retry once, or fail if server can't handle it
                try:
                    response = requests.post(main_server_url, files=files_below_limit, timeout=30)
                    self.assert_true(response.status_code < 400, 
                                    f"Upload of 4MB to main server rejected with status {response.status_code}")
                except requests.RequestException as retry_e:
                    self.assert_true(False, f"Upload of 4MB failed even with extended timeout: {retry_e}")
            else:
                self.assert_true(False, f"Upload of 4MB failed: {e}")
        
        # Test case 2: Upload to server on port 8082/small_limit (50KB limit)
        small_limit_url = f"http://{self.runner.host}:8082/small_limit"
        
        # Create a 60KB file (above the 50KB limit)
        size_above_limit = 60 * 1024  # 60KB
        data_above_limit = io.BytesIO(b'X' * size_above_limit)
        files_above_limit = {'file': ('test_60KB.txt', data_above_limit, 'text/plain')}
        
        try:
            # This should fail with 413 Payload Too Large
            response = requests.post(small_limit_url, files=files_above_limit, timeout=2)
            self.assert_equals(response.status_code, 413, 
                            f"Upload of 60KB to /small_limit should be rejected with 413, got {response.status_code}")
        except requests.RequestException as e:
            # Connection errors are NOT acceptable - server should return proper HTTP status
            self.assert_true(False, f"Server failed to respond with proper HTTP status for oversized upload: {e}")

    def test_upload_with_form_urlencoded(self):
        """
        Test POST to upload endpoint with application/x-www-form-urlencoded.
        
        This test verifies that the upload endpoint properly handles form-encoded
        data submissions without file attachments.
        """
        # Test POST to upload endpoint
        upload_path = '/upload'
        
        # Create form data
        form_data = {
            'text_field': 'Sample text input',
            'number_field': '12345',
            'checkbox_field': 'on'
        }
        
        try:
            # Send POST request with form data
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            response = self.runner.send_request('POST', upload_path, data=form_data, headers=headers)
            
            # First, check that POST method is accepted (not 405)
            self.assert_true(response.status_code != 405, 
                          f"POST to {upload_path} returned 405 Method Not Allowed")
            
            # Then, verify successful response (2xx status code)
            self.assert_true(200 <= response.status_code < 300, 
                          f"POST to {upload_path} with application/x-www-form-urlencoded returned {response.status_code}, expected 2xx success code")
            
        except requests.RequestException as e:
            self.assert_true(False, f"Request failed for upload test with application/x-www-form-urlencoded: {e}")