import socket

HOST, PORT = '', 8080

listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

listen_socket.bind((HOST, PORT))
listen_socket.listen(1)

print 'Serving HTTP on port %s ...' % PORT

while True:
    client_connection, client_address = listen_socket.accept()
    
    request = client_connection.recv(1024)
    
    http_response = """\
HTTP/1.1 200 OK
Content-Type: text/html

<html>
<body>
<h1>Hello, World!</h1>
<p>This is a Python 2.7 socket-only server.</p>
</body>
</html>
"""
    
    client_connection.sendall(http_response)
    client_connection.close()
