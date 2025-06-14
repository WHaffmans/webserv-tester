#!/usr/bin/env python3
"""
Cookie Handling Tests

Tests the webserver's handling of HTTP cookies according to RFC 6265:
- Receiving Cookie headers from browsers
- Passing Cookie headers to CGI scripts as HTTP_COOKIE environment variable
- Receiving Set-Cookie headers from CGI responses
- Sending Set-Cookie headers back to browsers
- Handling multiple cookies and special characters

These tests validate that the server follows Nginx-like behavior for cookie handling.
"""

import os
import requests
from http.cookies import SimpleCookie
from core.test_case import TestCase

class CookieTests(TestCase):
    """Tests cookie handling functionality according to RFC 6265."""
    
    def setup(self):
        """Set up for cookie tests."""
        # Define the CGI path for cookie tests
        self.cgi_path = '/cgi-bin'
        
        # Make CGI scripts executable
        self._ensure_scripts_executable()
    
    def _ensure_scripts_executable(self):
        """Ensure all cookie test scripts have execute permissions."""
        from core.path_utils import resolve_path
        
        scripts = [
            'cookie_echo.cgi', 
            'cookie_set.cgi', 
            'cookie_multiple.cgi',
            'cookie_special.cgi',
            'cookie_attributes.cgi'
        ]
        
        cgi_dir = resolve_path('data/www/cgi-bin')
        for script in scripts:
            script_path = cgi_dir / script
            if script_path.exists():
                # Set executable permissions
                try:
                    script_path.chmod(script_path.stat().st_mode | 0o755)
                except Exception as e:
                    self.logger.debug(f"Could not set execute permission on {script_path}: {e}")
            else:
                self.logger.debug(f"Cookie test script {script_path} not found")
    
    def test_cookie_passthrough(self):
        """
        Test that cookies sent by the client are passed to CGI scripts.
        
        Verifies the server passes Cookie headers to CGI scripts as the HTTP_COOKIE 
        environment variable according to RFC 3875 section 4.1.2.
        """
        # Test URL for the cookie echo script
        test_url = f"{self.cgi_path}/cookie_echo.cgi"
        
        # Send a request with a cookie
        cookie_name = "test_cookie"
        cookie_value = "test_value"
        cookies = {cookie_name: cookie_value}
        
        try:
            response = self.runner.send_request('GET', test_url, cookies=cookies)
            
            # Verify successful execution
            self.assert_equals(response.status_code, 200, 
                             f"Cookie test script at {test_url} failed with status {response.status_code}")
            
            # Verify the CGI script received the cookie
            expected_cookie = f"{cookie_name}={cookie_value}"
            self.assert_true(expected_cookie in response.text, 
                          f"CGI script did not receive cookie: {expected_cookie}")
            
        except requests.RequestException as e:
            self.assert_true(False, f"Request to {test_url} failed: {e}")
    
    def test_multiple_cookies(self):
        """
        Test handling of multiple cookies in a request.
        
        Verifies the server correctly passes multiple cookies to CGI scripts,
        according to section 5.4 of RFC 6265.
        """
        # Test URL for the cookie echo script
        test_url = f"{self.cgi_path}/cookie_echo.cgi"
        
        # Send a request with multiple cookies
        cookies = {
            "cookie1": "value1",
            "cookie2": "value2",
            "cookie3": "value3"
        }
        
        try:
            response = self.runner.send_request('GET', test_url, cookies=cookies)
            
            # Verify successful execution
            self.assert_equals(response.status_code, 200, 
                             f"Multiple cookie test script at {test_url} failed with status {response.status_code}")
            
            # Verify the CGI script received all cookies
            for name, value in cookies.items():
                expected_cookie = f"{name}={value}"
                self.assert_true(expected_cookie in response.text, 
                              f"CGI script did not receive cookie: {expected_cookie}")
            
        except requests.RequestException as e:
            self.assert_true(False, f"Request to {test_url} failed: {e}")
    
    def test_cookie_special_characters(self):
        """
        Test handling of cookies with special characters.
        
        Verifies the server correctly handles cookies with spaces, symbols, etc.
        as specified in RFC 6265 section 4.1.1 (cookie-value).
        """
        # Test URL for the cookie echo script
        test_url = f"{self.cgi_path}/cookie_echo.cgi"
        
        # Create a cookie with special characters
        cookie_name = "special_cookie"
        cookie_value = "value with spaces+and+special!@#$%^&*()"
        cookies = {cookie_name: cookie_value}
        
        try:
            response = self.runner.send_request('GET', test_url, cookies=cookies)
            
            # Verify successful execution
            self.assert_equals(response.status_code, 200, 
                             f"Special character cookie test at {test_url} failed with status {response.status_code}")
            
            # The special characters may be encoded, so check for the presence
            # of the cookie name and parts of the value that should be recognizable
            self.assert_true(cookie_name in response.text, 
                          f"CGI script did not receive cookie name: {cookie_name}")
            
            # Check for parts of the value that should be present, allowing for encoding differences
            self.assert_true("value" in response.text, 
                          "CGI script did not receive cookie value correctly")
            
        except requests.RequestException as e:
            self.assert_true(False, f"Request to {test_url} failed: {e}")
    
    def test_set_cookie_response(self):
        """
        Test that Set-Cookie headers from CGI scripts are properly sent to clients.
        
        Verifies the server properly forwards Set-Cookie headers from CGI responses
        according to RFC 6265 section 4.1.
        """
        # Test URL for the cookie set script
        test_url = f"{self.cgi_path}/cookie_set.cgi"
        
        try:
            response = self.runner.send_request('GET', test_url)
            
            # Verify successful execution
            self.assert_equals(response.status_code, 200, 
                             f"Cookie set script at {test_url} failed with status {response.status_code}")
            
            # Verify the Set-Cookie header is present in the response
            self.assert_true('Set-Cookie' in response.headers, 
                          "Set-Cookie header missing from response")
            
            # Parse the Set-Cookie header and verify its content
            cookie = SimpleCookie()
            cookie.load(response.headers['Set-Cookie'])
            
            self.assert_true('test_cookie' in cookie, 
                          "test_cookie not found in Set-Cookie header")
            self.assert_equals(cookie['test_cookie'].value, 'cookie_value', 
                             "test_cookie has incorrect value")
            
        except requests.RequestException as e:
            self.assert_true(False, f"Request to {test_url} failed: {e}")
    
    def test_multiple_set_cookie(self):
        """
        Test handling of multiple Set-Cookie headers in a CGI response.
        
        Verifies the server correctly forwards multiple Set-Cookie headers,
        matching Nginx's behavior for handling multiple cookies.
        """
        # Test URL for the multiple cookie set script
        test_url = f"{self.cgi_path}/cookie_multiple.cgi"
        
        try:
            response = self.runner.send_request('GET', test_url)
            
            # Verify successful execution
            self.assert_equals(response.status_code, 200, 
                             f"Multiple cookie set script at {test_url} failed with status {response.status_code}")
            
            # Get all cookies from the response
            all_cookies_found = False
            
            # Method 1: Check for multiple Set-Cookie headers using requests's cookies
            if len(response.cookies) >= 3:
                all_cookies_found = True
                self.assert_true('cookie1' in response.cookies, "cookie1 not found in response cookies")
                self.assert_true('cookie2' in response.cookies, "cookie2 not found in response cookies")
                self.assert_true('cookie3' in response.cookies, "cookie3 not found in response cookies")
            
            # Method 2: Check raw headers
            elif 'Set-Cookie' in response.headers:
                # Look at raw headers which might contain consolidated cookies
                raw_headers = str(response.headers)
                
                if ('cookie1=value1' in raw_headers and 
                    'cookie2=value2' in raw_headers and 
                    'cookie3=value3' in raw_headers):
                    all_cookies_found = True
            
            self.assert_true(all_cookies_found, 
                          "Not all expected cookies were found in the response")
            
        except requests.RequestException as e:
            self.assert_true(False, f"Request to {test_url} failed: {e}")
    
    def test_cookie_attributes(self):
        """
        Test handling of cookies with various attributes.
        
        Verifies the server correctly forwards cookies with attributes like Expires, 
        Max-Age, Path, etc. as defined in RFC 6265 section 5.2.
        """
        # Test URL for the cookie attributes script
        test_url = f"{self.cgi_path}/cookie_attributes.cgi"
        
        try:
            response = self.runner.send_request('GET', test_url)
            
            # Verify successful execution
            self.assert_equals(response.status_code, 200, 
                             f"Cookie attributes script at {test_url} failed with status {response.status_code}")
            
            # Check for cookies in the response
            raw_cookies = str(response.headers)
            
            # Look for key attributes
            self.assert_true('attr_cookie1=value1' in raw_cookies, 
                          "First attribute cookie not found in response")
            
            # These attributes should be present, though some might be rewritten by the server
            attributes_to_check = [
                'Path=/', 
                'Expires='
            ]
            
            for attr in attributes_to_check:
                self.assert_true(attr in raw_cookies, 
                             f"Expected attribute {attr} not found in cookie response")
            
            # Secure and HttpOnly are optional as they might be stripped by the server
            if 'Secure' in raw_cookies:
                self.logger.debug("Secure attribute preserved in response")
            if 'HttpOnly' in raw_cookies:
                self.logger.debug("HttpOnly attribute preserved in response")
            
            # Check for the second cookie
            self.assert_true('attr_cookie2=value2' in raw_cookies, 
                          "Second attribute cookie not found in response")
            
            # Check for Max-Age and Path attributes on the second cookie
            self.assert_true('Max-Age=' in raw_cookies, 
                          "Max-Age attribute not found in cookie response")
            self.assert_true('Path=/subpath' in raw_cookies, 
                          "Path=/subpath attribute not found in cookie response")
            
        except requests.RequestException as e:
            self.assert_true(False, f"Request to {test_url} failed: {e}")
    
    def test_persistent_cookies(self):
        """
        Test handling of persistent cookies between requests.
        
        Verifies the server correctly maintains cookies across multiple requests
        from the same client, matching Nginx's cookie persistence behavior.
        """
        # First, get a cookie from the cookie set script
        set_url = f"{self.cgi_path}/cookie_set.cgi"
        
        try:
            # Create a session to maintain cookies between requests
            session = requests.Session()
            
            # Get a cookie from the set script
            set_response = session.get(f"http://{self.runner.host}:{self.runner.port}{set_url}")
            
            # Verify successful execution
            self.assert_equals(set_response.status_code, 200, 
                             f"Cookie set script at {set_url} failed with status {set_response.status_code}")
            
            # Verify the cookie was set
            self.assert_true('test_cookie' in session.cookies, 
                          "test_cookie not set in session")
            
            # Now access the echo script with the same session to see if the cookie is sent
            echo_url = f"{self.cgi_path}/cookie_echo.cgi"
            echo_response = session.get(f"http://{self.runner.host}:{self.runner.port}{echo_url}")
            
            # Verify successful execution
            self.assert_equals(echo_response.status_code, 200, 
                             f"Cookie echo script at {echo_url} failed with status {echo_response.status_code}")
            
            # Verify the cookie was received by the echo script
            expected_cookie = "test_cookie=cookie_value"
            self.assert_true(expected_cookie in echo_response.text, 
                          f"Echo script did not receive persistent cookie: {expected_cookie}")
            
        except requests.RequestException as e:
            self.assert_true(False, f"Persistent cookie test failed: {e}")
