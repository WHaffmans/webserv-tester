
# Contributing to Webserv Tester

## 📋 Feature Implementation
List of features to implement, in priority order:
- Add a file where user can specify a list of tests to ignore (for the server feature he don't want to implement).
- Add more RFC references to tests
- Add 2 test modes: strict (RFC/nginx-like) and permissive (subject/correction)
- Improve test coverage
- Refactor test framework

## ✏️ Writing New Tests

1. Create a new test class in `tests_suites/` or add to an existing one
2. Test methods must start with `test_`
3. Use assertions provided by the TestCase class
4. Group related tests in the same class

Example test:

```python
from core.test_case import TestCase

class MyTests(TestCase):
    """
    Tests specific to the configuration in test.conf:
    location / {
        index index.html;
        methods GET POST;
    }
    """

    def test_my_feature(self):
        """Test description here."""
        response = self.runner.send_request('GET', '/my-endpoint')
        self.assert_equals(response.status_code, 200)
        self.assert_true('Content-Type' in response.headers)
```
