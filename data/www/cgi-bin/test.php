#!/usr/local/bin/php-cgi
<?php
header("Content-Type: text/html");
?>
<!DOCTYPE html>
<html>
<head>
<title>PHP CGI Test</title>
</head>
<body>
<h1>PHP CGI Test</h1>
<p>This is a test of PHP CGI functionality.</p>
<p>SERVER_SOFTWARE: <?php echo $_SERVER['SERVER_SOFTWARE']; ?></p>
<p>REQUEST_METHOD: <?php echo $_SERVER['REQUEST_METHOD']; ?></p>
<p>SCRIPT_FILENAME: <?php echo $_SERVER['SCRIPT_FILENAME']; ?></p>
</body>
</html>