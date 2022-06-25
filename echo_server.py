import selectors
import socket
from argparse import ArgumentParser
from http import HTTPStatus
from urllib.parse import parse_qs, urlparse

parser = ArgumentParser()
parser.add_argument('--host', default='0.0.0.0')
parser.add_argument('--port', type=int, default=9999)
args = parser.parse_args()

HOST, PORT = args.host, args.port

selector = selectors.DefaultSelector()


def server(host, port):
    server_socket = socket.socket(
        socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(
        socket.SOL_SOCKET, socket.SO_REUSEADDR, socket.SO_REUSEPORT)
    server_socket.setblocking(False)
    server_socket.bind((host, port))
    server_socket.listen()
    print(f'Start listening at {server_socket.getsockname()}')

    selector.register(fileobj=server_socket,
                      events=selectors.EVENT_READ, data=accept)


def accept(sock: socket.socket, mask):
    client_socket, addrinfo = sock.accept()
    print(f'Accepted connection from {addrinfo}')

    selector.register(fileobj=client_socket,
                      events=selectors.EVENT_READ, data=reply)


def reply(sock: socket.socket, mask):
    request = sock.recv(4096)
    peer = ':'.join(map(str, sock.getpeername())).encode()
    if request:
        request += peer
        sock.sendall(generate_response(request))
    print(f'Closing connection from {sock.getpeername()}')
    selector.unregister(sock)
    sock.close()


def parse_request(request):
    headers = request.decode().split('\n')
    try:
        method, url, schema = headers.pop(0).split()
    except:
        return f"HTTP/1.1 {HTTPStatus.INTERNAL_SERVER_ERROR.value} {HTTPStatus.INTERNAL_SERVER_ERROR.phrase}\n\n"
    url_parsed = urlparse(url)
    qs_parsed = parse_qs(url_parsed.query)
    return {
        'schema': schema,
        'method': method,
        'url': url,
        'url_parsed': url_parsed,
        'qs_parsed': qs_parsed,
        'headers': headers
    }


def find_http_status(code):
    for status in HTTPStatus:
        if status.value == code:
            return status


def get_http_status(request):
    try:
        code = request['qs_parsed'].get('status')
    except:
        code = None
    if code:
        try:
            code = int(code[0])
        except:
            code = None
    status = find_http_status(code)
    if not status:
        status = HTTPStatus.OK
    return status


def generate_headers(request):
    status = get_http_status(request)
    return f"{request['schema']} {status.value} {status.phrase}\n\n"


def generate_content(request):
    content = []
    status = get_http_status(request)
    content.append('<html><body>')
    content.append(f"<h4>Request method: {request['method']}</h4>")
    content.append(f"<h4>Request source: {request['headers'].pop()}<h4>")
    content.append(f"<h4>Response status: {status.value} {status.phrase}</h4>")
    content.append("<h3>Request headers:</h3>")
    content.extend([f"<h4>{h}</h4>" for h in request['headers']])
    content.append('</body></html>')
    return ''.join(content)


def generate_response(request):
    parsed_request = parse_request(request)
    if HTTPStatus.INTERNAL_SERVER_ERROR.phrase in parsed_request:
        return parsed_request.encode()
    headers = generate_headers(parsed_request)
    body = generate_content(parsed_request)
    return (headers + body).encode()


def event_loop():
    while True:

        events = selector.select()  # key: SelectorKey, events: selectors.EVENT_READ

        for key, mask in events:
            key.data(key.fileobj, mask)


if __name__ == '__main__':
    server(HOST, PORT)
    event_loop()
