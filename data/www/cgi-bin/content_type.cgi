#!/bin/sh
printf "Content-Type: application/json\r\n"
printf "\r\n"
printf '{"message": "This is a JSON response from CGI", "status": "success"}'
