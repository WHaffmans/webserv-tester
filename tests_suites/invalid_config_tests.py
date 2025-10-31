#!/usr/bin/env python3
"""
Invalid Configuration Tests

Tests the server's handling of invalid configuration files.
Verifies proper error reporting and graceful failure for malformed configs.
"""

import os
import tempfile
import time
import subprocess
from pathlib import Path
import re
from core.test_case import TestCase

class InvalidConfigTests(TestCase):
    """Tests the server's handling of invalid configuration files."""
    
    def setup(self):
        """Set up the test environment for invalid config tests."""
        # Create directory for invalid config files if it doesn't exist
        self.invalid_configs_dir = Path("data/conf/invalid")
        self.invalid_configs_dir.mkdir(exist_ok=True, parents=True)
        
        # Store paths to created config files for cleanup
        self.config_files = []
        
        # Path to webserv executable, relative to the tester root
        self.webserv_path = Path("../build/webserv")
        
        # Verify webserv executable exists
        if not self.webserv_path.exists():
            self.logger.error(f"Webserv executable not found at {self.webserv_path}")
            raise FileNotFoundError(f"Webserv executable not found at {self.webserv_path}")
    
    def teardown(self):
        """Clean up temporary config files."""
        # Clean up config files
        for config_file in self.config_files:
            try:
                if os.path.exists(config_file):
                    os.remove(config_file)
            except Exception as e:
                self.logger.debug(f"Error removing config file {config_file}: {e}")
        # Extra: clean up any stray files in the invalid config dir
        for stray in self.invalid_configs_dir.glob('*.conf'):
            try:
                if stray.exists():
                    os.remove(stray)
            except Exception as e:
                self.logger.debug(f"Error removing stray config file {stray}: {e}")
        self.config_files = []
    
    def create_invalid_config(self, content, filename_prefix):
        """
        Create a temporary invalid config file.
        
        Args:
            content (str): Content of the invalid config file
            filename_prefix (str): Prefix for the temporary filename
            
        Returns:
            str: Path to the created config file
        """
        # Create unique filename
        filename = f"{filename_prefix}_{int(time.time())}.conf"
        file_path = self.invalid_configs_dir / filename
        try:
            with open(file_path, 'w') as f:
                f.write(content)
        finally:
            # Always add to config_files for cleanup, even if write fails
            if file_path not in self.config_files:
                self.config_files.append(file_path)
        return str(file_path)
    
    def run_webserv_with_config(self, config_path, test_name):
        """
        Run webserv with the specified config file and capture output.
        
        Args:
            config_path (str): Path to the config file
            test_name (str): Name of the test being run
            
        Returns:
            tuple: (return_code, stdout, stderr)
        """
        try:
            # Create temporary files to capture this test's output
            with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_stdout:
                with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_stderr:
                    try:
                        # Run webserv with the config file, redirecting output to temp files
                        process = subprocess.Popen(
                            [str(self.webserv_path), "-c", config_path],
                            stdout=temp_stdout,
                            stderr=temp_stderr,
                            text=True
                        )
                        
                        # For invalid config tests, the process should exit quickly
                        # Use a short initial sleep followed by polling
                        time.sleep(0.05)  # Give it just 50ms to fail with config errors
                        
                        # If it's still running, wait a bit more with polling
                        max_wait = 0.3  # Maximum total wait time in seconds
                        start_time = time.time()
                        while process.poll() is None and (time.time() - start_time) < max_wait:
                            time.sleep(0.05)  # Check every 50ms
                        
                        # Check if process is still running
                        if process.poll() is None:
                            # Server started successfully, terminate it
                            process.terminate()
                            try:
                                process.wait(timeout=2)
                            except subprocess.TimeoutExpired:
                                # Force kill if it doesn't terminate
                                process.kill()
                                process.wait()
                        
                        return_code = process.returncode
                        
                        # Close the temp files to ensure all data is written
                        temp_stdout.close()
                        temp_stderr.close()
                        
                        # Read the temp files with error handling for encoding issues
                        with open(temp_stdout.name, 'r', encoding='utf-8', errors='replace') as f:
                            stdout = f.read()
                        with open(temp_stderr.name, 'r', encoding='utf-8', errors='replace') as f:
                            stderr = f.read()
                        
                        # Log the captured output to the debug logger instead of writing to separate files
                        if stdout.strip():  # Only log non-empty output
                            self.logger.debug(f"[{test_name}] stdout: {stdout}")
                        
                        if stderr.strip():  # Only log non-empty output
                            self.logger.debug(f"[{test_name}] stderr: {stderr}")
                        
                        return (return_code, stdout, stderr)
                    
                    finally:
                        # Clean up temp files
                        try:
                            os.unlink(temp_stdout.name)
                            os.unlink(temp_stderr.name)
                        except Exception as e:
                            self.logger.debug(f"Error cleaning up temp files: {e}")
            
        except Exception as e:
            self.logger.debug(f"Error running webserv: {e}")
            return (-1, "", str(e))
    
    def check_error_log(self, stdout, stderr, keyword):
        """
        Check if error logs contain expected error messages on a single line.
        
        Args:
            stdout (str): Standard output from the server
            stderr (str): Standard error from the server
            keyword (str): Specific keyword to look for in the error message
            
        Returns:
            bool: True if appropriate error message found on a single line, False otherwise
        """
        # Combine stdout and stderr for checking
        output = stdout + stderr
        
        # Look for lines containing both error/fatal AND the keyword
        lines = output.lower().split('\n')
        keyword_lower = keyword.lower()
        
        for line in lines:
            if ('error' in line or 'fatal' in line) and keyword_lower in line:
                return True
        
        # Log for debugging (to file only)
        self.logger.debug(f"No error line found containing both error indicator and keyword: '{keyword_lower}'")
        self.logger.debug(f"Output sample: {output[:200]}...")  # Log first 200 chars
        
        return False
    
    def test_empty_config_file(self):
        """Test server's handling of an empty config file."""
        # Create empty config file
        config_path = self.create_invalid_config("", "empty_config")
        
        # Run webserv with the empty config
        return_code, stdout, stderr = self.run_webserv_with_config(config_path, "empty_config_file")
        
        # Check that server reports error
        self.assert_true(return_code != 0, "Server should fail with empty config file")
        self.assert_true(self.check_error_log(stdout, stderr, "empty"), 
                         "Server should report error about empty config")
    
    def test_missing_server_block(self):
        """Test server's handling of config without any server blocks."""
        # Create config without server blocks
        config_content = """
        # Config without server blocks
        client_max_body_size 1m;
        
        """
        config_path = self.create_invalid_config(config_content, "no_server_block")
        
        # Run webserv with the invalid config
        return_code, stdout, stderr = self.run_webserv_with_config(config_path, "missing_server_block")
        
        # Check that server reports error
        self.assert_true(return_code != 0, "Server should fail without server blocks")
        self.assert_true(self.check_error_log(stdout, stderr, "server"), 
                         "Server should report error about missing server block")
    
    def test_invalid_directive(self):
        """Test server's handling of invalid directive."""
        # Create config with invalid directive
        config_content = """
        server {
            listen 8080;
            invalid_directive value;
            root www;
        }
        """
        config_path = self.create_invalid_config(config_content, "invalid_directive")
        
        # Run webserv with the invalid config
        return_code, stdout, stderr = self.run_webserv_with_config(config_path, "invalid_directive")
        
        # Check that server reports error
        self.assert_true(return_code != 0, "Server should fail with invalid directive")
        self.assert_true(self.check_error_log(stdout, stderr, "directive"), 
                         "Server should report error about invalid directive")
    
    def test_missing_semicolon(self):
        """Test server's handling of missing semicolon."""
        # Create config with missing semicolon
        config_content = """
        server {
            listen 8080
            root www;
        }
        """
        config_path = self.create_invalid_config(config_content, "missing_semicolon")
        
        # Run webserv with the invalid config
        return_code, stdout, stderr = self.run_webserv_with_config(config_path, "missing_semicolon")
        
        # Check that server reports error
        self.assert_true(return_code != 0, "Server should fail with missing semicolon")
        self.assert_true(self.check_error_log(stdout, stderr, "semicolon"), 
                         "Server should report error about missing semicolon")
    
    def test_unclosed_block(self):
        """Test server's handling of unclosed blocks."""
        # Create config with unclosed block
        config_content = """
        server {
            listen 8080;
            root www;
            
            location / {
                index index.html;
            # Missing closing brace
        }
        """
        config_path = self.create_invalid_config(config_content, "unclosed_block")
        
        # Run webserv with the invalid config
        return_code, stdout, stderr = self.run_webserv_with_config(config_path, "unclosed_block")
        
        # Check that server reports error
        self.assert_true(return_code != 0, "Server should fail with unclosed block")
        self.assert_true(self.check_error_log(stdout, stderr, "block"), 
                         "Server should report error about unclosed block")
    
    def test_invalid_port(self):
        """Test server's handling of invalid port number."""
        # Create config with invalid port
        config_content = """
        server {
            listen 99999;
            root www;
        }
        """
        config_path = self.create_invalid_config(config_content, "invalid_port")
        
        # Run webserv with the invalid config
        return_code, stdout, stderr = self.run_webserv_with_config(config_path, "invalid_port")
        
        # Check that server reports error
        self.assert_true(return_code != 0, "Server should fail with invalid port")
        self.assert_true(self.check_error_log(stdout, stderr, "port"), 
                         "Server should report error about invalid port")
    
    def test_invalid_client_max_body_size(self):
        """Test server's handling of invalid client_max_body_size value."""
        # Create config with invalid client_max_body_size
        config_content = """
        server {
            listen 8080;
            client_max_body_size -1m;
            root www;
        }
        """
        config_path = self.create_invalid_config(config_content, "invalid_body_size")
        
        # Run webserv with the invalid config
        return_code, stdout, stderr = self.run_webserv_with_config(config_path, "invalid_client_max_body_size")
        
        # Check that server reports error
        self.assert_true(return_code != 0, "Server should fail with invalid client_max_body_size")
        self.assert_true(self.check_error_log(stdout, stderr, "body"), 
                         "Server should report error about invalid client_max_body_size")
    
    def test_missing_root(self):
        """Test server's handling of missing root directive."""
        # Create config without root directive
        config_content = """
        server {
            listen 8080;
            server_name localhost;
            # Missing root directive
        }
        """
        config_path = self.create_invalid_config(config_content, "missing_root")
        
        # Run webserv with the invalid config
        return_code, stdout, stderr = self.run_webserv_with_config(config_path, "missing_root")
        
        # Check that server reports error
        self.assert_true(return_code != 0, "Server should fail with missing root directive")
        self.assert_true(self.check_error_log(stdout, stderr, "root"), 
                         "Server should report error about missing root directive")
    
    def test_invalid_error_page(self):
        """Test server's handling of invalid error_page directive."""
        # Create config with invalid error_page
        config_content = """
        server {
            listen 8080;
            root www;
            error_page abc /404.html;
        }
        """
        config_path = self.create_invalid_config(config_content, "invalid_error_page")
        
        # Run webserv with the invalid config
        return_code, stdout, stderr = self.run_webserv_with_config(config_path, "invalid_error_page")
        
        # Check that server reports error
        self.assert_true(return_code != 0, "Server should fail with invalid error_page directive")
        self.assert_true(self.check_error_log(stdout, stderr, "error_page"), 
                         "Server should report error about invalid error_page directive")
    
    def test_invalid_method(self):
        """Test server's handling of invalid HTTP method."""
        # Create config with invalid HTTP method
        config_content = """
        server {
            listen 8080;
            root www;
            
            location / {
                methods GET INVALID;
            }
        }
        """
        config_path = self.create_invalid_config(config_content, "invalid_method")
        
        # Run webserv with the invalid config
        return_code, stdout, stderr = self.run_webserv_with_config(config_path, "invalid_method")
        
        # Check that server reports error
        self.assert_true(return_code != 0, "Server should fail with invalid HTTP method")
        self.assert_true(self.check_error_log(stdout, stderr, "method"), 
                         "Server should report error about invalid HTTP method")
    
    def test_conflicting_location(self):
        """Test server's handling of conflicting location blocks."""
        # Create config with duplicate exact location blocks
        config_content = """
        server {
            listen 8080;
            root www;
            
            location = /exact {
                index index.html;
            }
            
            location = /exact {
                index other.html;
            }
        }
        """
        config_path = self.create_invalid_config(config_content, "conflicting_location")
        
        # Run webserv with the invalid config
        return_code, stdout, stderr = self.run_webserv_with_config(config_path, "conflicting_location")
        
        # Check that server reports error
        self.assert_true(return_code != 0, "Server should fail with conflicting location blocks")
        self.assert_true(self.check_error_log(stdout, stderr, "location"), 
                         "Server should report error about conflicting location blocks")
    
    def test_invalid_client_body_size_format(self):
        """Test server's handling of incorrectly formatted client_max_body_size."""
        # Create config with incorrectly formatted client_max_body_size
        config_content = """
        server {
            listen 8080;
            root www;
            client_max_body_size 5xyz;
        }
        """
        config_path = self.create_invalid_config(config_content, "invalid_body_size_format")
        
        # Run webserv with the invalid config
        return_code, stdout, stderr = self.run_webserv_with_config(config_path, "invalid_client_body_size_format")
        
        # Check that server reports error
        self.assert_true(return_code != 0, "Server should fail with incorrectly formatted client_max_body_size")
        self.assert_true(self.check_error_log(stdout, stderr, "body"), 
                         "Server should report error about incorrectly formatted client_max_body_size")

    def test_invalid_directive_context(self):
        """Test server's handling of directives in invalid context."""
        # Create config with location outside server block
        config_content = """
        # location outside server block
        location / {
            root www;
        }
        
        server {
            listen 8080;
        }
        """
        config_path = self.create_invalid_config(config_content, "invalid_directive_context")
        
        # Run webserv with the invalid config
        return_code, stdout, stderr = self.run_webserv_with_config(config_path, "invalid_directive_context")
        
        # Check that server reports error
        self.assert_true(return_code != 0, "Server should fail with directive in invalid context")
        self.assert_true(self.check_error_log(stdout, stderr, "context"), 
                        "Server should report error about invalid directive context")
    
    def test_unbalanced_braces(self):
        """Test server's handling of unbalanced braces in configuration."""
        # Create config with unbalanced braces
        config_content = """
        server {
            listen 8080;
            root www;
            location / {
                index index.html;
            # Missing closing brace for location
        }
        """
        config_path = self.create_invalid_config(config_content, "unbalanced_braces")
        
        # Run webserv with the invalid config
        return_code, stdout, stderr = self.run_webserv_with_config(config_path, "unbalanced_braces")
        
        # Check that server reports error
        self.assert_true(return_code != 0, "Server should fail with unbalanced braces")
        self.assert_true(self.check_error_log(stdout, stderr, "brace") or
                        self.check_error_log(stdout, stderr, "bracket") or
                        self.check_error_log(stdout, stderr, "block") or
                        self.check_error_log(stdout, stderr, "}"),
                        "Server should report error about unbalanced braces")


    def test_invalid_directive_context(self):
        """Test server's handling of directives used in invalid contexts."""
        # Create config with location outside server block
        config_content = """
        # Location outside server block
        location / {
            root www;
            index index.html;
        }
        
        server {
            listen 8080;
        }
        """
        config_path = self.create_invalid_config(config_content, "invalid_context")
        
        # Run webserv with the invalid config
        return_code, stdout, stderr = self.run_webserv_with_config(config_path, "invalid_directive_context")
        
        # Check that server reports error
        self.assert_true(return_code != 0, "Server should fail with directive in invalid context")
        self.assert_true(self.check_error_log(stdout, stderr, "location") or
                        self.check_error_log(stdout, stderr, "context") or
                        self.check_error_log(stdout, stderr, "outside"),
                        "Server should report error about directive in invalid context")


    def test_server_directive_inside_location(self):
        """Test server's handling of server-level directives inside location blocks."""
        # Create config with server directive inside location block
        config_content = """
        server {
            listen 8080;
            root www;
            
            location / {
                listen 8081;  # This is only valid at server level
                index index.html;
            }
        }
        """
        config_path = self.create_invalid_config(config_content, "server_directive_in_location")
        
        # Run webserv with the invalid config
        return_code, stdout, stderr = self.run_webserv_with_config(config_path, "server_directive_inside_location")
        
        # Check that server reports error
        self.assert_true(return_code != 0, "Server should fail with server directive inside location")
        self.assert_true(self.check_error_log(stdout, stderr, "listen") or
                        self.check_error_log(stdout, stderr, "invalid") or
                        self.check_error_log(stdout, stderr, "location"),
                        "Server should report error about invalid directive context")


    def test_invalid_http_status_codes(self):
        """Test server's handling of invalid HTTP status codes in error_page directive."""
        # Create config with invalid HTTP status codes
        config_content = """
        server {
            listen 8080;
            root www;
            error_page abc /404.html;  # Not a number
        }
        """
        config_path = self.create_invalid_config(config_content, "invalid_status_code_text")
        
        # Run webserv with the invalid config
        return_code, stdout, stderr = self.run_webserv_with_config(config_path, "invalid_http_status_codes_text")
        
        # Check that server reports error
        self.assert_true(return_code != 0, "Server should fail with non-numeric status code")
        self.assert_true(self.check_error_log(stdout, stderr, "error_page") or
                        self.check_error_log(stdout, stderr, "status") or
                        self.check_error_log(stdout, stderr, "code"),
                        "Server should report error about invalid status code")
        
        # Create config with out-of-range HTTP status code
        config_content = """
        server {
            listen 8080;
            root www;
            error_page 999 /error.html;  # Invalid status code (out of range)
        }
        """
        config_path = self.create_invalid_config(config_content, "invalid_status_code_range")
        
        # Run webserv with the invalid config
        return_code, stdout, stderr = self.run_webserv_with_config(config_path, "invalid_http_status_codes_range")
        
        # Check that server reports error
        self.assert_true(return_code != 0, "Server should fail with out-of-range status code")
        self.assert_true(self.check_error_log(stdout, stderr, "error_page") or
                        self.check_error_log(stdout, stderr, "status") or
                        self.check_error_log(stdout, stderr, "code") or
                        self.check_error_log(stdout, stderr, "999"),
                        "Server should report error about invalid status code range")

    def test_unparseable_number_value(self):
        """Test server's handling of unparseable numeric values."""
        # Create config with invalid numeric value
        config_content = """
        server {
            listen notanumber;
            root www;
        }
        """
        config_path = self.create_invalid_config(config_content, "unparseable_number")
        
        # Run webserv with the invalid config
        return_code, stdout, stderr = self.run_webserv_with_config(config_path, "unparseable_number_value")
        
        # Check that server reports error
        self.assert_true(return_code != 0, "Server should fail with unparseable number")
        self.assert_true(self.check_error_log(stdout, stderr, "invalid port") or
                        self.check_error_log(stdout, stderr, "invalid number") or
                        self.check_error_log(stdout, stderr, "not a valid number") or
                        self.check_error_log(stdout, stderr, "numeric value expected"),
                        "Server should report error about invalid number value")

    def test_multiple_incompatible_directives(self):
        """Test server's handling of multiple incompatible directives."""
        # Create config with contradictory directives
        config_content = """
        server {
            listen 8080;
            root www;
            
            location / {
                return 301 /redirect;  # Redirect
                root different/path;  # Conflicts with 'return' (can't set root for a redirect)
            }
        }
        """
        config_path = self.create_invalid_config(config_content, "incompatible_directives")
        
        # Run webserv with the invalid config
        return_code, stdout, stderr = self.run_webserv_with_config(config_path, "multiple_incompatible_directives")
        
        # Check that server reports error
        self.assert_true(return_code != 0, "Server should fail with incompatible directives")
        self.assert_true(self.check_error_log(stdout, stderr, "conflicting directives") or
                        self.check_error_log(stdout, stderr, "directives are incompatible") or
                        self.check_error_log(stdout, stderr, "cannot be used together") or
                        self.check_error_log(stdout, stderr, "directive conflicts") or
                        self.check_error_log(stdout, stderr, "return") or
                        self.check_error_log(stdout, stderr, "root"),
                        "Server should report error about incompatible directives")

    def test_empty_directive_values(self):
        """Test server's handling of empty directive values."""
        # Create config with empty directive values
        config_content = """
        server {
            listen 8080;
            server_name ;
            root www;
        }
        """
        config_path = self.create_invalid_config(config_content, "empty_directive_value")
        
        # Run webserv with the invalid config
        return_code, stdout, stderr = self.run_webserv_with_config(config_path, "empty_directive_values")
        
        # Check that server reports error
        self.assert_true(return_code != 0, "Server should fail with empty directive value")
        self.assert_true(self.check_error_log(stdout, stderr, "server_name"), 
                        "Server should report error about empty server_name directive")


    def test_unescaped_quotes(self):
        """Test server's handling of unescaped quotes in directive values."""
        # Create config with unescaped quotes in string
        config_content = """
        server {
            listen 8080;
            server_name "example"com";
            root www;
        }
        """
        config_path = self.create_invalid_config(config_content, "unescaped_quotes")
        
        # Run webserv with the invalid config
        return_code, stdout, stderr = self.run_webserv_with_config(config_path, "unescaped_quotes")
        
        # Check that server reports error
        self.assert_true(return_code != 0, "Server should fail with unescaped quotes")
        self.assert_true(self.check_error_log(stdout, stderr, "quote"), 
                        "Server should report error about unescaped quotes")


    def test_comment_like_directives(self):
        """Test server's handling of comments that look like directives."""
        # Create config with tricky comments
        config_content = """
        server {
            listen 8080;
            #listen 8080;
            listen# 8080;
            root www;
        }
        """
        config_path = self.create_invalid_config(config_content, "comment_like_directives")
        
        # Run webserv with the invalid config
        return_code, stdout, stderr = self.run_webserv_with_config(config_path, "comment_like_directives")
        
        # Check that server reports error (second 'listen' line should be invalid)
        self.assert_true(return_code != 0, "Server should fail with malformed directive")
        self.assert_true(self.check_error_log(stdout, stderr, "Syntax error"), 
                        "Server should report error about malformed listen directive")


    def test_extremely_long_values(self):
        """Test server's handling of extremely long directive values."""
        # Create config with very long server name
        long_name = "a" * 10000  # 10,000 character server name
        config_content = f"""
        server {{
            listen 8080;
            server_name {long_name};
            root www;
        }}
        """
        config_path = self.create_invalid_config(config_content, "extremely_long_value")
        
        # Run webserv with the invalid config
        return_code, stdout, stderr = self.run_webserv_with_config(config_path, "extremely_long_values")
        
        # Check that server reports error
        self.assert_true(return_code != 0, "Server should fail with extremely long value")
        self.assert_true(self.check_error_log(stdout, stderr, "long") or 
                        self.check_error_log(stdout, stderr, "length") or
                        self.check_error_log(stdout, stderr, "limit"), 
                        "Server should report error about value length or size limit")


    def test_unicode_special_characters(self):
        """Test server's handling of Unicode and special characters in paths."""
        # Create config with Unicode characters in path
        config_content = """
        server {
            listen 8080;
            root www/sitè/παράδειγμα;
        }
        """
        config_path = self.create_invalid_config(config_content, "unicode_chars")
        
        # Run webserv with the invalid config
        return_code, stdout, stderr = self.run_webserv_with_config(config_path, "unicode_special_characters")
        
        # Check for error or acceptance - some servers might handle this, others might not
        if return_code != 0:
            self.assert_true(self.check_error_log(stdout, stderr, "invalid character in path") or
                            self.check_error_log(stdout, stderr, "unexpected character") or
                            self.check_error_log(stdout, stderr, "special character not allowed") or
                            self.check_error_log(stdout, stderr, "invalid root path"),
                            "Server should report meaningful error about path or character")


    def test_nested_blocks_depth(self):
        """Test server's handling of deeply nested blocks."""
        # Create config with excessively nested location blocks
        config_content = """
        server {
            listen 8080;
            root www;
            
            location / {
                index index.html;
                
                location /inner {
                    index inner.html;
                    
                    location /inner/deeper {
                        index deeper.html;
                        
                        location /inner/deeper/too-deep {
                            index too-deep.html;
                        }
                    }
                }
            }
        }
        """
        config_path = self.create_invalid_config(config_content, "nested_blocks")
        
        # Run webserv with the invalid config
        return_code, stdout, stderr = self.run_webserv_with_config(config_path, "nested_blocks_depth")
        
        # Server should reject excessive nesting
        self.assert_true(return_code != 0, 
                        "Server should reject configuration with excessive nesting depth")
        
        self.assert_true(self.check_error_log(stdout, stderr, "too many levels") or
                        self.check_error_log(stdout, stderr, "maximum depth") or
                        self.check_error_log(stdout, stderr, "nesting limit") or
                        self.check_error_log(stdout, stderr, "too deeply nested") or
                        self.check_error_log(stdout, stderr, "expected directive value"),
                        "Server should report meaningful error about nesting or depth")


    def test_null_bytes_in_config(self):
        """Test server's handling of null bytes in configuration."""
        # Create config with null byte in path
        config_content = """
        server {
            listen 8080;
            root www\0/hidden;
        }
        """
        config_path = self.create_invalid_config(config_content, "null_bytes")
        
        # Run webserv with the invalid config
        return_code, stdout, stderr = self.run_webserv_with_config(config_path, "null_bytes_in_config")
        
        # Check that server reports error
        self.assert_true(return_code != 0, "Server should fail with null bytes in configuration")
        self.assert_true(self.check_error_log(stdout, stderr, "null byte detected") or
                        self.check_error_log(stdout, stderr, "invalid byte sequence") or
                        self.check_error_log(stdout, stderr, "illegal character in path") or
                        self.check_error_log(stdout, stderr, "unexpected character"),
                        "Server should report error about null bytes or invalid characters")

    def test_mixed_block_types(self):
        """Test server's handling of mixed block types where not allowed."""
        # Create config with http block inside server block
        config_content = """
        server {
            listen 8080;
            
            http {
                root www;
            }
        }
        """
        config_path = self.create_invalid_config(config_content, "mixed_blocks")
        
        # Run webserv with the invalid config
        return_code, stdout, stderr = self.run_webserv_with_config(config_path, "mixed_block_types")
        
        # Check that server reports error
        self.assert_true(return_code != 0, "Server should fail with mixed block types")
        self.assert_true(self.check_error_log(stdout, stderr, "http block not allowed") or
                        self.check_error_log(stdout, stderr, "invalid block type") or
                        self.check_error_log(stdout, stderr, "unexpected block directive") or
                        self.check_error_log(stdout, stderr, "block not permitted") or
                        self.check_error_log(stdout, stderr, "expected directive value"),
                        "Server should report error about invalid block type or context")


    def test_multiple_semicolons(self):
        """Test server's handling of multiple semicolons after directives."""
        # Create config with multiple semicolons
        config_content = """
        server {
            listen 8080;;;
            root www;
        }
        """
        config_path = self.create_invalid_config(config_content, "multiple_semicolons")
        
        # Run webserv with the invalid config
        return_code, stdout, stderr = self.run_webserv_with_config(config_path, "multiple_semicolons")
        
        # Check that server reports error
        self.assert_true(return_code != 0, "Server should fail with multiple semicolons")
        self.assert_true(self.check_error_log(stdout, stderr, "unexpected semicolon") or
                        self.check_error_log(stdout, stderr, "syntax error") or
                        self.check_error_log(stdout, stderr, "unexpected token") or
                        self.check_error_log(stdout, stderr, "multiple semicolons"),
                        "Server should report error about multiple semicolons or syntax")

    def test_location_directive_incompatibilities(self):
        """Test server's handling of incompatible directives in location blocks."""
        # Test cases for different incompatible directive combinations
        incompatible_pairs = [
            # (directive1, value1, directive2, value2, keyword)
            ("return", "301 /new-path", "index", "index.html", "incompatible"),
            ("return", "301 /new-path", "autoindex", "on", "incompatible"),
            ("return", "301 /new-path", "upload_store", "/uploads", "incompatible")
        ]
        
        for i, (directive1, value1, directive2, value2, keyword) in enumerate(incompatible_pairs):
            # Create config with incompatible directives
            config_content = f"""
            server {{
                listen 8080;
                root www;
                
                location / {{
                    {directive1} {value1};
                    {directive2} {value2};  # Should be incompatible with {directive1}
                }}
            }}
            """
            config_path = self.create_invalid_config(config_content, f"case_{i}")
            
            # Run webserv with the invalid config
            return_code, stdout, stderr = self.run_webserv_with_config(config_path, f"location_directive_incompatibilities_{directive1}_{directive2}")
            
            # Check that server reports error
            self.assert_true(return_code != 0, f"Server should fail with incompatible directives {directive1} and {directive2}")
            self.assert_true(self.check_error_log(stdout, stderr, directive1) or
                            self.check_error_log(stdout, stderr, directive2) or
                            self.check_error_log(stdout, stderr, keyword),
                            f"Server should report error about incompatibility between {directive1} and {directive2}")

    def test_multiple_default_servers(self):
        """Test server's handling of multiple default directives on the same port."""
        # Create config with multiple default directives
        config_content = """
        server {
            listen 8080;
            default;
            root www;
        }
        server {
            listen 8080;
            default;  # Conflict: already defined a default for this port
            root www2;
        }
        """
        config_path = self.create_invalid_config(config_content, "config_file")
        
        # Run webserv with the invalid config
        return_code, stdout, stderr = self.run_webserv_with_config(config_path, "multiple_default_servers")
        
        # Check that server reports error
        self.assert_true(return_code != 0, "Server should fail with multiple default_server directives")
        self.assert_true(self.check_error_log(stdout, stderr, "default_server") or
                        self.check_error_log(stdout, stderr, "default server") or
                        self.check_error_log(stdout, stderr, "already defined"),
                        "Server should report error about multiple default servers on same port")

    def test_invalid_location_paths(self):
        """Test server's handling of invalid location paths."""
        # Create config with location path not starting with /
        config_content = """
        server {
            listen 8080;
            root www;
            
            location invalid_path {  # Should start with /
                index index.html;
            }
        }
        """
        config_path = self.create_invalid_config(config_content, "test_cfg")
        
        # Run webserv with the invalid config
        return_code, stdout, stderr = self.run_webserv_with_config(config_path, "invalid_location_paths")
        
        # Check that server reports error
        self.assert_true(return_code != 0, "Server should fail with invalid location path")
        self.assert_true(self.check_error_log(stdout, stderr, "location") or
                        self.check_error_log(stdout, stderr, "path") or
                        self.check_error_log(stdout, stderr, "start with"),
                        "Server should report error about location path not starting with /")

    def test_nested_locations_in_exact_match(self):
        """Test server's handling of nested locations in exact match locations."""
        # Create config with nested location in exact match location
        config_content = """
        server {
            listen 8080;
            root www;
            
            location = /exact {  # Exact match location
                index exact.html;
                
                location /nested {  # Nested location not allowed in exact match
                    index nested.html;
                }
            }
        }
        """
        config_path = self.create_invalid_config(config_content, "webserv_config")
        
        # Run webserv with the invalid config
        return_code, stdout, stderr = self.run_webserv_with_config(config_path, "nested_locations_in_exact_match")
        
        # Check that server reports error
        self.assert_true(return_code != 0, "Server should fail with nested location in exact match")
        self.assert_true(self.check_error_log(stdout, stderr, "nested") or
                        self.check_error_log(stdout, stderr, "exact match") or
                        self.check_error_log(stdout, stderr, "location inside") or
                        self.check_error_log(stdout, stderr, "expected directive"),
                        "Server should report error about nested location in exact match")

    def test_empty_methods_directive(self):
        """Test server's handling of empty methods directive."""
        # Create config with empty methods directive
        config_content = """
        server {
            listen 8080;
            root www;
            
            location / {
                methods;  # Empty methods directive, no methods allowed
                index index.html;
            }
        }
        """
        config_path = self.create_invalid_config(config_content, "config_test")
        
        # Run webserv with the invalid config
        return_code, stdout, stderr = self.run_webserv_with_config(config_path, "empty_methods_directive")
        
        # Check that server reports error
        self.assert_true(return_code != 0, "Server should fail with empty methods directive")
        self.assert_true(self.check_error_log(stdout, stderr, "methods") or
                        self.check_error_log(stdout, stderr, "empty") or
                        self.check_error_log(stdout, stderr, "no method"),
                        "Server should report error about empty methods directive")

    def test_excessive_client_max_body_size(self):
        """Test server's handling of excessively large client_max_body_size."""
        # Create config with excessively large client_max_body_size
        config_content = """
        server {
            listen 8080;
            client_max_body_size 9999999999m;  # Unreasonably large
            root www;
        }
        """
        config_path = self.create_invalid_config(config_content, "cfg_test")
        
        # Run webserv with the invalid config
        return_code, stdout, stderr = self.run_webserv_with_config(config_path, "excessive_client_max_body_size")
        
        # Check that server reports error
        self.assert_true(return_code != 0, "Server should fail with excessively large client_max_body_size")
        self.assert_true(self.check_error_log(stdout, stderr, "client_max_body_size") or
                        self.check_error_log(stdout, stderr, "exceeds") or
                        self.check_error_log(stdout, stderr, "too large") or
                        self.check_error_log(stdout, stderr, "limit"),
                        "Server should report error about excessively large client_max_body_size")

    def test_invalid_cgi_configuration(self):
        """Test server's handling of invalid CGI configuration."""
        # Test case: Invalid file extension format (missing dot)
        config_content = """
        server {
            listen 8080;
            root www;
            
            location /cgi-bin {
                cgi_handler php /usr/bin/php;  # Missing dot before extension
                methods GET POST;
            }
        }
        """
        config_path = self.create_invalid_config(config_content, "server_conf")
        
        # Run webserv with the invalid config
        return_code, stdout, stderr = self.run_webserv_with_config(config_path, "invalid_cgi_extension_format")
        
        # Check that server reports error
        self.assert_true(return_code != 0, "Server should fail with invalid CGI extension format")
        self.assert_true(self.check_error_log(stdout, stderr, "cgi_handler") or
                        self.check_error_log(stdout, stderr, "extension") or
                        self.check_error_log(stdout, stderr, "format") or
                        self.check_error_log(stdout, stderr, "missing dot"),
                        "Server should report error about CGI handler extension format")

    def test_error_page_invalid_status_range(self):
        """Test server's handling of error_page with status codes outside valid range."""
        # Create configs with various invalid status codes
        invalid_status_codes = [0, 99, 600, 1000]
        
        for i, status_code in enumerate(invalid_status_codes):
            config_content = f"""
            server {{
                listen 8080;
                root www;
                error_page {status_code} /error.html;  # Invalid status code (outside 100-599 range)
            }}
            """
            config_path = self.create_invalid_config(config_content, f"conf_test_{i}")
            
            # Run webserv with the invalid config
            return_code, stdout, stderr = self.run_webserv_with_config(config_path, f"error_page_invalid_status_{status_code}")
            
            # Check that server reports error
            self.assert_true(return_code != 0, f"Server should fail with invalid status code {status_code}")
            self.assert_true(self.check_error_log(stdout, stderr, "error_page") or
                            self.check_error_log(stdout, stderr, "status") or
                            self.check_error_log(stdout, stderr, "invalid") or
                            self.check_error_log(stdout, stderr, str(status_code)),
                            f"Server should report error about invalid status code {status_code}")

    def test_duplicate_server_configurations(self):
        """Test server's handling of duplicate server_name:port combinations."""
        # Create config with duplicate server_name:port combinations
        config_content = """
        server {
            listen 8080;
            server_name example.com;
            root www;
        }
        server {
            listen 8080;
            server_name example.com;  # Duplicate of the first server
            root www2;
        }
        """
        config_path = self.create_invalid_config(config_content, "http_conf")
        
        # Run webserv with the invalid config
        return_code, stdout, stderr = self.run_webserv_with_config(config_path, "duplicate_server_configurations")
        
        # Check that server reports error
        self.assert_true(return_code != 0, "Server should fail with duplicate server configurations")
        self.assert_true(self.check_error_log(stdout, stderr, "duplicate") or
                        self.check_error_log(stdout, stderr, "server_name") or
                        self.check_error_log(stdout, stderr, "example.com") or
                        self.check_error_log(stdout, stderr, "already defined"),
                        "Server should report error about duplicate server_name:port combination")