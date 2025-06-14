#!/bin/bash
# This script intentionally generates errors while also producing valid output

# First output valid content to stdout
echo "Content-type: text/plain"
echo
echo "This line is valid"
echo "This is the error.cgi script output"

# Then generate some errors to stderr
echo "This is an error message" >&2
echo "Another error for testing" >&2

# Exit with error code
exit 1