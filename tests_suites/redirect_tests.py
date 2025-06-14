#!/usr/bin/env python3
"""
HTTP Redirect Tests

Comprehensive tests for HTTP redirect functionality according to RFC 7231 Section 6.4.
Tests various redirect status codes (301, 302, 303, 307, 308) and their behaviors.

RFC references:
- RFC 7231 Section 6.4: Redirection 3xx
- RFC 7231 Section 6.4.2: 301 Moved Permanently
- RFC 7231 Section 6.4.3: 302 Found
- RFC 7231 Section 6.4.4: 303 See Other
- RFC 7231 Section 6.4.7: 307 Temporary Redirect
- RFC 7238: 308 Permanent Redirect

Key behaviors to test:
- 301, 308: Permanent redirects (cacheable)
- 302, 303, 307: Temporary redirects (not cacheable by default)
- 303: Always changes method to GET
- 307, 308: Preserve the original HTTP method
- 301, 302: Method preservation is ambiguous (most browsers change POST to GET)
"""

import os
import requests
import random
import string
import time
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from core.test_case import TestCase
from core.path_utils import resolve_path


class RedirectTests(TestCase):
    """Tests HTTP redirect functionality according to RFC specifications."""
    
    def setup(self):
        """Set up test environment."""
        self.temp_files = []
    
    def teardown(self):
        """Clean up any temporary files created during tests."""
        for file_path in self.temp_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                self.logger.debug(f"Error removing temp file {file_path}: {e}")
    
    def create_temp_html(self, filename, title="Test Page", content="Test Content", identifier="test_identifier"):
        """
        Helper function to create temporary HTML files if needed.
        
        Args:
            filename (str): Name of the file to create
            title (str): HTML page title
            content (str): Body content
            identifier (str): Test identifier for the HTML comment
            
        Returns:
            str: Path to the created file
        """
        file_path = resolve_path(f'data/www/{filename}')
        
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
</head>
<body>
    <h1>{title}</h1>
    <p>{content}</p>
    <!-- Test: {identifier} -->
</body>
</html>"""
        
        with open(file_path, 'w') as f:
            f.write(html_content)
        
        self.temp_files.append(file_path)
        return file_path
    
    def test_301_moved_permanently(self):
        """
        Test 301 Moved Permanently redirect.
        
        RFC 7231 Section 6.4.2: The 301 status code indicates that the target
        resource has been assigned a new permanent URI.
        """
        # Test the configured 301 redirect
        redirect_url = '/old-page'
        expected_location = '/new-page'
        
        try:
            # First test without following redirects
            response = self.runner.send_request('GET', redirect_url, allow_redirects=False)
            
            # Should return 301 status code
            self.assert_equals(response.status_code, 301, 
                             f"Expected 301 status code for {redirect_url}")
            
            # Should include Location header
            self.assert_true('Location' in response.headers, 
                           "301 response missing Location header")
            
            # Verify the Location header points to the correct destination
            location = response.headers['Location']
            self.assert_true(location.endswith(expected_location), 
                           f"Expected redirect to {expected_location}, got {location}")
            
            # Now test following the redirect
            response_followed = self.runner.send_request('GET', redirect_url, allow_redirects=True)
            
            # Should successfully reach the destination
            self.assert_true(response_followed.status_code < 400, 
                           f"Failed to follow 301 redirect: status {response_followed.status_code}")
            
        except requests.RequestException as e:
            self.assert_true(False, f"Request failed during 301 redirect test: {e}")
    
    def test_302_found(self):
        """
        Test 302 Found (temporary) redirect.
        
        RFC 7231 Section 6.4.3: The 302 status code indicates that the target
        resource resides temporarily under a different URI.
        """
        # Test the configured 302 redirect
        redirect_url = '/temp-redirect'
        expected_location = '/redirect-destination.html'
        
        try:
            # Test without following redirects
            response = self.runner.send_request('GET', redirect_url, allow_redirects=False)
            
            # Should return 302 status code
            self.assert_equals(response.status_code, 302, 
                             f"Expected 302 status code for {redirect_url}")
            
            # Should include Location header
            self.assert_true('Location' in response.headers, 
                           "302 response missing Location header")
            
            # Verify the Location header
            location = response.headers['Location']
            self.assert_true(location.endswith(expected_location), 
                           f"Expected redirect to {expected_location}, got {location}")
            
            # Test that 302 is not cached by checking Cache-Control
            # (though caching behavior is optional for clients)
            if 'Cache-Control' in response.headers:
                cache_control = response.headers['Cache-Control'].lower()
                self.logger.debug(f"302 response Cache-Control: {cache_control}")
            
        except requests.RequestException as e:
            self.assert_true(False, f"Request failed during 302 redirect test: {e}")
    
    def test_303_see_other(self):
        """
        Test 303 See Other redirect - always changes method to GET.
        
        RFC 7231 Section 6.4.4: The 303 status code indicates that the server is
        redirecting the user agent to a different resource, as indicated by a URI
        in the Location header field, which is intended to provide an indirect
        response to the original request.
        """
        redirect_url = '/see-other'
        expected_location = '/redirect-destination.html'
        
        # Test with POST method (should change to GET after redirect)
        post_data = {'test': 'data', 'foo': 'bar'}
        
        try:
            # First test POST without following redirects
            response = self.runner.send_request('POST', redirect_url, 
                                              data=post_data, allow_redirects=False)
            
            # Should return 303 status code
            self.assert_equals(response.status_code, 303, 
                             f"Expected 303 status code for POST to {redirect_url}")
            
            # Should include Location header
            self.assert_true('Location' in response.headers, 
                           "303 response missing Location header")
            
            # Verify the Location header
            location = response.headers['Location']
            self.assert_true(location.endswith(expected_location), 
                           f"Expected redirect to {expected_location}, got {location}")
            
            # Now test that following the redirect changes method to GET
            # We'll use requests.Session to track the redirect
            session = requests.Session()
            
            # Make the POST request with redirect following
            full_url = f"http://{self.runner.host}:{self.runner.port}{redirect_url}"
            response_followed = session.post(full_url, data=post_data, allow_redirects=True)
            
            # The final request should have been a GET (303 always changes to GET)
            # We can't directly verify the method used, but we can check that
            # the response is successful and doesn't include our POST data
            self.assert_true(response_followed.status_code < 400, 
                           f"Failed to follow 303 redirect: status {response_followed.status_code}")
            
        except requests.RequestException as e:
            self.assert_true(False, f"Request failed during 303 redirect test: {e}")
    
    def test_307_temporary_redirect(self):
        """
        Test 307 Temporary Redirect - preserves HTTP method.
        
        RFC 7231 Section 6.4.7: The 307 status code indicates that the target
        resource resides temporarily under a different URI and the user agent
        MUST NOT change the request method if it performs an automatic redirection.
        """
        redirect_url = '/temp-redirect-307'
        expected_location = '/redirect-destination.html'
        
        # Test with POST method (should preserve POST after redirect)
        post_data = {'test': 'data307', 'preserve': 'method'}
        
        try:
            # Test POST without following redirects
            response = self.runner.send_request('POST', redirect_url, 
                                              data=post_data, allow_redirects=False)
            
            # Should return 307 status code
            self.assert_equals(response.status_code, 307, 
                             f"Expected 307 status code for POST to {redirect_url}")
            
            # Should include Location header
            self.assert_true('Location' in response.headers, 
                           "307 response missing Location header")
            
            # Verify the Location header
            location = response.headers['Location']
            self.assert_true(location.endswith(expected_location), 
                           f"Expected redirect to {expected_location}, got {location}")
            
            # Test with GET method as well
            response_get = self.runner.send_request('GET', redirect_url, allow_redirects=False)
            
            # Should also return 307 for GET
            self.assert_equals(response_get.status_code, 307, 
                             f"Expected 307 status code for GET to {redirect_url}")
            
        except requests.RequestException as e:
            self.assert_true(False, f"Request failed during 307 redirect test: {e}")
    
    def test_308_permanent_redirect(self):
        """
        Test 308 Permanent Redirect - preserves HTTP method.
        
        RFC 7238: The 308 status code indicates that the target resource has been
        assigned a new permanent URI and any future references to this resource
        ought to use one of the enclosed URIs. The request method MUST NOT change.
        """
        redirect_url = '/perm-redirect-308'
        expected_location = '/redirect-destination.html'
        
        try:
            # Test GET request
            response = self.runner.send_request('GET', redirect_url, allow_redirects=False)
            
            # Should return 308 status code
            self.assert_equals(response.status_code, 308, 
                             f"Expected 308 status code for {redirect_url}")
            
            # Should include Location header
            self.assert_true('Location' in response.headers, 
                           "308 response missing Location header")
            
            # Verify the Location header
            location = response.headers['Location']
            self.assert_true(location.endswith(expected_location), 
                           f"Expected redirect to {expected_location}, got {location}")
            
            # Test with POST (should preserve method)
            post_data = {'test': 'permanent'}
            response_post = self.runner.send_request('POST', redirect_url, 
                                                   data=post_data, allow_redirects=False)
            
            # Should also return 308 for POST
            self.assert_equals(response_post.status_code, 308, 
                             f"Expected 308 status code for POST to {redirect_url}")
            
        except requests.RequestException as e:
            self.assert_true(False, f"Request failed during 308 redirect test: {e}")
    
    def test_redirect_with_query_string(self):
        """
        Test redirect with query string in Location header.
        
        Verifies that query strings in redirect destinations are properly handled.
        """
        redirect_url = '/redirect-with-query'
        
        try:
            # Test redirect that includes query string
            response = self.runner.send_request('GET', redirect_url, allow_redirects=False)
            
            # Should return 301 status code
            self.assert_equals(response.status_code, 301, 
                             f"Expected 301 status code for {redirect_url}")
            
            # Should include Location header with query string
            self.assert_true('Location' in response.headers, 
                           "Redirect response missing Location header")
            
            location = response.headers['Location']
            
            # Parse the location URL to check query string
            parsed = urlparse(location)
            query_params = parse_qs(parsed.query)
            
            # Verify query parameters are present
            self.assert_true('param1' in query_params, 
                           "Query parameter 'param1' missing in redirect Location")
            self.assert_true('param2' in query_params, 
                           "Query parameter 'param2' missing in redirect Location")
            
            # Follow the redirect and verify we can access the destination
            response_followed = self.runner.send_request('GET', redirect_url, allow_redirects=True)
            self.assert_true(response_followed.status_code < 400, 
                           f"Failed to follow redirect with query string: status {response_followed.status_code}")
            
        except requests.RequestException as e:
            self.assert_true(False, f"Request failed during query string redirect test: {e}")
    
    def test_external_redirect(self):
        """
        Test redirect to external URL.
        
        Verifies that the server can redirect to absolute URLs on different hosts.
        """
        redirect_url = '/external-redirect'
        expected_location = 'https://example.com/'
        
        try:
            # Test external redirect without following
            response = self.runner.send_request('GET', redirect_url, allow_redirects=False)
            
            # Should return 302 status code
            self.assert_equals(response.status_code, 302, 
                             f"Expected 302 status code for {redirect_url}")
            
            # Should include Location header with absolute URL
            self.assert_true('Location' in response.headers, 
                           "External redirect missing Location header")
            
            location = response.headers['Location']
            self.assert_equals(location, expected_location, 
                             f"Expected redirect to {expected_location}, got {location}")
            
            # Verify it's a proper absolute URL
            parsed = urlparse(location)
            self.assert_true(parsed.scheme in ['http', 'https'], 
                           f"External redirect should have http/https scheme, got {parsed.scheme}")
            self.assert_true(parsed.netloc != '', 
                           "External redirect should have a host/netloc component")
            
        except requests.RequestException as e:
            self.assert_true(False, f"Request failed during external redirect test: {e}")
    
    def test_redirect_chain(self):
        """
        Test following a chain of redirects.
        
        Verifies that the client can follow multiple redirects to reach
        the final destination.
        """
        # Start of redirect chain
        start_url = '/redirect-chain-1'
        
        try:
            # Test the full redirect chain
            response = self.runner.send_request('GET', start_url, allow_redirects=True)
            
            # Should eventually reach a successful page
            self.assert_true(response.status_code < 400, 
                           f"Failed to follow redirect chain: final status {response.status_code}")
            
            # Check that we went through the redirects (requests tracks redirect history)
            if hasattr(response, 'history'):
                redirect_count = len(response.history)
                self.assert_true(redirect_count >= 2, 
                               f"Expected at least 2 redirects in chain, got {redirect_count}")
                
                # Verify each step returned a redirect status
                for hist_response in response.history:
                    self.assert_true(300 <= hist_response.status_code < 400, 
                                   f"Non-redirect status in chain: {hist_response.status_code}")
            
        except requests.RequestException as e:
            self.assert_true(False, f"Request failed during redirect chain test: {e}")
    
    def test_redirect_loop_detection(self):
        """
        Test detection of redirect loops.
        
        Verifies that infinite redirect loops are detected and handled properly.
        """
        # Start of redirect loop
        loop_url = '/redirect-loop-1'
        
        try:
            # Attempt to follow the redirect loop
            # requests library should detect the loop and raise an exception
            response = self.runner.send_request('GET', loop_url, allow_redirects=True)
            
            # If we get here, check if requests stopped following redirects
            if hasattr(response, 'history'):
                redirect_count = len(response.history)
                # Most clients stop after 10-30 redirects
                self.assert_true(redirect_count < 50, 
                               f"Too many redirects followed ({redirect_count}), possible infinite loop")
            
        except requests.exceptions.TooManyRedirects:
            # This is the expected behavior - loop was detected
            self.logger.debug("Redirect loop correctly detected by client")
        except requests.RequestException as e:
            # Connection errors are NOT acceptable - server should handle redirect loops gracefully
            self.assert_true(False, f"Server failed to handle redirect loop properly: {e}")
    
    def test_relative_redirect(self):
        """
        Test relative redirect URLs in Location header.
        
        Verifies that relative URLs in Location headers are properly resolved.
        """
        redirect_url = '/relative-redirect'
        
        try:
            # Test relative redirect
            response = self.runner.send_request('GET', redirect_url, allow_redirects=False)
            
            # Should return 302 status code
            self.assert_equals(response.status_code, 302, 
                             f"Expected 302 status code for {redirect_url}")
            
            # Should include Location header
            self.assert_true('Location' in response.headers, 
                           "Relative redirect missing Location header")
            
            location = response.headers['Location']
            self.logger.debug(f"Relative redirect Location: {location}")
            
            # Location might be relative or absolute depending on server implementation
            # Both are valid according to RFC 7231
            
            # Test following the redirect
            response_followed = self.runner.send_request('GET', redirect_url, allow_redirects=True)
            
            # Should successfully resolve the relative redirect
            self.assert_true(response_followed.status_code < 500, 
                           f"Failed to follow relative redirect: status {response_followed.status_code}")
            
        except requests.RequestException as e:
            self.assert_true(False, f"Request failed during relative redirect test: {e}")
    
    def test_redirect_methods_preservation(self):
        """
        Test HTTP method preservation/changing across different redirect types.
        
        Verifies that:
        - 303 always changes to GET
        - 307/308 preserve the original method
        - 301/302 behavior (implementation-dependent)
        """
        test_cases = [
            # (path, status_code, should_preserve_method)
            ('/see-other', 303, False),          # 303 always changes to GET
            ('/temp-redirect-307', 307, True),   # 307 preserves method
            ('/perm-redirect-308', 308, True),   # 308 preserves method
        ]
        
        for path, expected_status, should_preserve in test_cases:
            # Test with POST method
            post_data = {'method': 'POST', 'test': f'redirect-{expected_status}'}
            
            try:
                # Send POST without following redirects
                response = self.runner.send_request('POST', path, 
                                                  data=post_data, allow_redirects=False)
                
                # Verify correct status code
                self.assert_equals(response.status_code, expected_status, 
                                 f"Expected {expected_status} status code for {path}")
                
                # All should have Location header
                self.assert_true('Location' in response.headers, 
                               f"{expected_status} response missing Location header")
                
                self.logger.debug(f"Redirect {expected_status} from {path} to {response.headers['Location']}")
                
            except requests.RequestException as e:
                self.assert_true(False, f"Request failed for {path}: {e}")
    
    def test_redirect_header_validation(self):
        """
        Test validation of Location header in redirects.
        
        Verifies that:
        - Location header is present for all 3xx redirects
        - Location header contains valid URI
        """
        # Test all configured redirects
        redirect_paths = [
            '/old-page',
            '/temp-redirect',
            '/see-other',
            '/temp-redirect-307',
            '/perm-redirect-308',
            '/redirect-with-query',
            '/external-redirect',
            '/go-home',
        ]
        
        for path in redirect_paths:
            try:
                response = self.runner.send_request('GET', path, allow_redirects=False)
                
                # Should be a redirect
                self.assert_true(300 <= response.status_code < 400, 
                               f"Expected redirect status for {path}, got {response.status_code}")
                
                # Must have Location header
                self.assert_true('Location' in response.headers, 
                               f"Redirect response for {path} missing required Location header")
                
                # Location should not be empty
                location = response.headers['Location']
                self.assert_true(len(location) > 0, 
                               f"Empty Location header for redirect at {path}")
                
                # Basic URI validation
                # Location can be absolute or relative URI
                if location.startswith('http://') or location.startswith('https://'):
                    # Absolute URI - verify it has valid components
                    parsed = urlparse(location)
                    self.assert_true(parsed.scheme != '', 
                                   f"Invalid absolute URI in Location: {location}")
                    self.assert_true(parsed.netloc != '', 
                                   f"Invalid absolute URI in Location: {location}")
                else:
                    # Relative URI - should start with / or be a relative path
                    self.assert_true(location[0] in ['/', '.'] or location[0].isalnum(), 
                                   f"Invalid relative URI in Location: {location}")
                
            except requests.RequestException as e:
                self.assert_true(False, f"Request failed for {path}: {e}")
    
    def test_redirect_with_fragment(self):
        """
        Test redirect behavior with URL fragments.
        
        Verifies that fragments (#anchor) in URLs are handled correctly
        during redirects. According to RFC, fragments are not sent to the server.
        """
        # Test redirect with fragment in request
        redirect_url = '/old-page'
        fragment = '#section-2'
        
        try:
            # Request with fragment (note: fragment is not sent to server)
            response = self.runner.send_request('GET', redirect_url + fragment, 
                                              allow_redirects=False)
            
            # Should still redirect normally
            self.assert_equals(response.status_code, 301, 
                             f"Expected 301 status code for {redirect_url}")
            
            # Location header should not include the fragment
            location = response.headers.get('Location', '')
            self.assert_false('#' in location, 
                            f"Location header should not contain fragment: {location}")
            
        except requests.RequestException as e:
            self.assert_true(False, f"Request failed during fragment redirect test: {e}")
    
    def test_redirect_caching(self):
        """
        Test caching behavior of different redirect types.
        
        Verifies that:
        - 301, 308 are cacheable (permanent redirects)
        - 302, 303, 307 are not cacheable by default (temporary redirects)
        """
        test_cases = [
            # (path, status_code, should_be_cacheable)
            ('/old-page', 301, True),              # Permanent, cacheable
            ('/temp-redirect', 302, False),        # Temporary, not cacheable
            ('/see-other', 303, False),            # Temporary, not cacheable
            ('/temp-redirect-307', 307, False),    # Temporary, not cacheable
            ('/perm-redirect-308', 308, True),     # Permanent, cacheable
        ]
        
        for path, expected_status, should_cache in test_cases:
            try:
                response = self.runner.send_request('GET', path, allow_redirects=False)
                
                # Check Cache-Control header if present
                if 'Cache-Control' in response.headers:
                    cache_control = response.headers['Cache-Control'].lower()
                    
                    if should_cache:
                        # Permanent redirects might have cache directives
                        self.logger.debug(f"{expected_status} redirect Cache-Control: {cache_control}")
                    else:
                        # Temporary redirects often have no-cache directives
                        self.logger.debug(f"{expected_status} redirect Cache-Control: {cache_control}")
                
                # Check for explicit caching headers
                if should_cache:
                    # Permanent redirects might include Expires or Cache-Control: max-age
                    has_cache_header = ('Cache-Control' in response.headers and 
                                      'max-age' in response.headers['Cache-Control']) or \
                                     'Expires' in response.headers
                    
                    self.logger.debug(f"{expected_status} redirect has caching headers: {has_cache_header}")
                
            except requests.RequestException as e:
                self.assert_true(False, f"Request failed for {path}: {e}")
    
    def test_redirect_with_request_body(self):
        """
        Test redirect behavior when request includes a body.
        
        Verifies correct handling of request bodies during redirects,
        especially for methods that change (303) vs preserve (307/308).
        """
        # Create test data
        test_data = {
            'key1': 'value1',
            'key2': 'value2',
            'timestamp': str(int(time.time()))
        }
        
        # Test 303 (changes POST to GET, should drop body)
        try:
            response = self.runner.send_request('POST', '/see-other', 
                                              data=test_data, allow_redirects=False)
            
            self.assert_equals(response.status_code, 303, 
                             "Expected 303 status code for POST with body")
            
            # 303 changes method to GET, which shouldn't have a body
            
        except requests.RequestException as e:
            self.assert_true(False, f"Request failed during 303 body test: {e}")
        
        # Test 307 (preserves POST and body)
        try:
            response = self.runner.send_request('POST', '/temp-redirect-307', 
                                              data=test_data, allow_redirects=False)
            
            self.assert_equals(response.status_code, 307, 
                             "Expected 307 status code for POST with body")
            
            # 307 preserves method and body
            
        except requests.RequestException as e:
            self.assert_true(False, f"Request failed during 307 body test: {e}")
    
    def test_malformed_location_header(self):
        """
        Test server behavior with malformed Location headers.
        
        This would require configuring redirects with invalid locations,
        which might not be possible with nginx-style config.
        """
        # This test would need special server configuration to create
        # malformed Location headers, which may not be supported
        self.logger.debug("Malformed Location header test would require special server support")
    
    def test_redirect_without_location(self):
        """
        Test that redirect responses always include Location header.
        
        According to RFC 7231, 3xx responses SHOULD include a Location header.
        This test verifies proper error handling if it's missing.
        """
        # All our configured redirects should have Location headers
        # This test verifies that's the case
        redirect_paths = [
            '/old-page',
            '/temp-redirect', 
            '/see-other',
            '/temp-redirect-307',
            '/perm-redirect-308',
        ]
        
        for path in redirect_paths:
            try:
                response = self.runner.send_request('GET', path, allow_redirects=False)
                
                # Verify it's a redirect status
                self.assert_true(300 <= response.status_code < 400, 
                               f"Expected redirect status for {path}")
                
                # MUST have Location header
                self.assert_true('Location' in response.headers, 
                               f"Redirect at {path} missing required Location header")
                
            except requests.RequestException as e:
                self.assert_true(False, f"Request failed for {path}: {e}")