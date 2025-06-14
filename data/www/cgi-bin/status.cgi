#!/bin/sh

# Get status from query string (default to 200)
STATUS=$(echo "$QUERY_STRING" | grep -oE "status=[0-9]+" | cut -d= -f2)
if [ -z "$STATUS" ]; then
  STATUS=200
fi

# Send status and headers
echo "Status: $STATUS"
echo "Content-Type: text/plain"
echo ""

# Send content
echo "CGI Status Test"
echo "Returned status code: $STATUS"