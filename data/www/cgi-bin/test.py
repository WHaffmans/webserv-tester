#!/usr/bin/env python3
# filepath: data/www/cgi-bin/test.py
import cgi
import os
import sys

# Print the HTTP headers
print("Content-Type: text/html\r")
print("\r")  # Empty line to separate headers from body

# Start the HTML output
print("<html>")
print("<head>")
print("<title>Python CGI Test</title>")
print("</head>")
print("<body>")
print("<h1>Hello from test.py!</h1>")
print("<p>Received GET parameters:</p>")
print("<ul>")

# Parse any GET parameters
form = cgi.FieldStorage()
for key in form.keys():
    print("<li>{0}: {1}</li>".format(key, form.getvalue(key)))

print("</ul>")
print("</body>")
print("</html>")