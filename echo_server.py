import http
import socket
import selectors
import json
import sys
from argparse import ArgumentParser

parser = ArgumentParser()
parser.add_argument('--host', default='0.0.0.0')
parser.add_argument('--port', type=int, default=9999)
args = parser.parse_args()

HOST, PORT = args.host, args.port

selector = selectors.DefaultSelector()

def server(host, port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # IPv4 / TCP
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, socket.SO_REUSEPORT) # reuse addr and port for faster restart
    server_socket.bind((host, port))
    server_socket.listen()
    print(f'Start listening at {server_socket.getsockname()}')

    selector.register(fileobj=server_socket, events=selectors.EVENT_READ, data=accept)


def accept(sock: socket.socket, mask):
    client_socket, addrinfo = sock.accept()
    print(f'Accepted connection from {addrinfo}')

    selector.register(fileobj=client_socket, events=selectors.EVENT_READ, data=reply)
 

def reply(sock: socket.socket, mask):
    print(mask)
    request = sock.recv(4096)
    if request:
        sock.send(prepare_response(request))
    else:
        selector.unregister(sock)
        print(f'Closing connection from {sock.getpeername()}')
        sock.close()
        


def parse_request(request):
    print(request.decode())
    return request


def prepare_response(request):
    return parse_request(request)


def event_loop():
    while True:
        
        events = selector.select() # key: SelectorKey, events

        for key, mask in events:
            # print(key, event)
            callback = key.data
            callback(key.fileobj, mask)


if __name__ == '__main__':
    server(HOST, PORT)
    event_loop()
