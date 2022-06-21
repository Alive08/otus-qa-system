import http
import socket
import socketserver
from threading import Thread
import json
import sys

HOST = 'localhost'
PORT = 2000

class SingleTCPHandler(socketserver.BaseRequestHandler):
    "One instance per connection.  Override handle(self) to customize action."
    def handle(self):
        # self.request is the client connection
        while True:
            data = self.request.recv(1024)  # clip input at 1Kb
            if not data:
                break
            text = data.decode('utf-8')
            # print(json.loads(text))
            self.request.send('OK'.encode('utf-8'))
        self.request.close()


class SimpleServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    # Ctrl-C will cleanly kill all spawned threads
    daemon_threads = True
    # much faster rebinding
    allow_reuse_address = True
    allow_reuse_port = True
    
    def __init__(self, server_address, RequestHandlerClass):
        socketserver.TCPServer.__init__(self, server_address, RequestHandlerClass)



def run_server(host='127.0.0.1', port=33333):
    sock = socket.socket()
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))
    sock.listen()
    while True:
        print(f"Listening on {host}:{port}")
        client_sock, addr = sock.accept()
        print('Connection from', addr)
        Thread(target=handle_client, args=(client_sock,)).start()

def handle_client(sock: socket.socket):
    print(f"Serving client {sock.getpeername()}")
    while True:
        received_data = sock.recv(4096)
        if not received_data:
            break
        print(received_data.decode())
        sock.sendall(received_data)

    print('Client disconnected:', sock.getpeername())
    sock.close()

if __name__ == '__main__':
    # run_server()
    server = SimpleServer((HOST, PORT), SingleTCPHandler)
    # terminate with Ctrl-C
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        sys.exit(0)
