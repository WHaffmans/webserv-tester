#!/bin/sh
echo "Content-Type: text/plain"
echo "Set-Cookie: attr_cookie1=value1; Path=/; Expires=Wed, 21 Oct 2025 07:28:00 GMT; Secure; HttpOnly"
echo "Set-Cookie: attr_cookie2=value2; Path=/subpath; Max-Age=3600; SameSite=Strict"
echo ""
echo "Cookie Attributes Script"
echo "======================="
echo ""
echo "Set cookies with various attributes"
