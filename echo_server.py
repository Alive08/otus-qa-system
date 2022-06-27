import logging
import selectors
import socket
from argparse import ArgumentParser
from http import HTTPStatus
from urllib.parse import parse_qs, urlparse

LOG_FORMAT = '{asctime} [{levelname}] [{name}] [{funcName}] > {message}'
logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT, style='{', )
logger = logging.getLogger('ECHO')

parser = ArgumentParser()
parser.add_argument('--host', default='0.0.0.0')
parser.add_argument('--port', type=int, default=9999)
args = parser.parse_args()

HOST, PORT = args.host, args.port

selector = selectors.DefaultSelector()


def server(host, port):
    """Run TCP server"""

    server_socket = socket.socket(
        socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(
        socket.SOL_SOCKET, socket.SO_REUSEADDR, socket.SO_REUSEPORT)
    server_socket.setblocking(False)
    server_socket.bind((host, port))
    server_socket.listen()
    logger.debug('Start listening at %s:%s', *server_socket.getsockname())

    selector.register(fileobj=server_socket,
                      events=selectors.EVENT_READ, data=accept)


def accept(sock: socket.socket, mask):
    """Accept the client connection,
    register the socket for events polling"""

    client_socket, addrinfo = sock.accept()
    logger.debug('Accepted connection from %s:%s', *addrinfo)
    logger.debug('Registering client socket %s:%s for READ events', *addrinfo)
    selector.register(fileobj=client_socket,
                      events=selectors.EVENT_READ, data=reply)


def close(sock: socket.socket):
    logger.debug('Unregistering client socket %s:%s', *sock.getpeername())
    selector.unregister(sock)
    logger.debug("Closing connection from %s:%s", *sock.getpeername())
    sock.close()


def reply(sock: socket.socket, mask):
    """Send reply to client"""

    client_addr = sock.getpeername()

    request = sock.recv(4096)
    peer = ':'.join(map(str, client_addr)).encode()
    if request:
        logger.debug("Got request from %s:%s", *client_addr)
        request += peer
        response = generate_response(request)
        logger.debug("Sending response to %s:%s", *client_addr)
        sock.sendall(response)
        if HTTPStatus.BAD_REQUEST.phrase in response.decode():
            logger.debug("Got %s from %s:%s",
                         HTTPStatus.BAD_REQUEST.phrase, *client_addr)
            close(sock)
        # if "Connection: close" in response.decode():
        #     close(sock)
    else:
        logger.debug("Client %s:%s has disconnected", *client_addr)
        close(sock)


def parse_request(request):
    """Parse client's request"""

    headers = request.decode().split('\n')

    # minimal sanity check
    try:
        method, url, schema = headers.pop(0).split()
        assert method in ('GET', 'POST', 'PUT', 'HEAD')
        assert 'HTTP' in schema
    except:
        return f"HTTP/1.1 {HTTPStatus.BAD_REQUEST.value} {HTTPStatus.BAD_REQUEST.phrase}\nConnection: close\n\n"

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
    """Find HTTP status by its code"""

    for status in HTTPStatus:
        if status.value == code:
            return status


def get_http_status(request):
    code = None
    try:
        code = request['qs_parsed'].get('status')[0]
    except:
        pass
    if code:
        try:
            code = int(code)
        except:
            pass
    status = find_http_status(code)
    if not status:
        status = HTTPStatus.OK
    return status


def generate_headers(request):
    headers = []
    status = get_http_status(request)
    headers.append(f"{request['schema']} {status.value} {status.phrase}")

    if any(['keep-alive' in h for h in request['headers']]):
        headers.append("Connection: keep-alive")
    else:
        headers.append("Connection: close")

    headers.append("Content-type: text/html")
    return '\n'.join(headers)


def generate_content(request):
    content = []
    status = get_http_status(request)
    content.append('<html><body>')
    content.append(f"<h4>Request method: {request['method']}</h4>")
    content.append(f"<h4>Request source: {request['headers'].pop()}</h4>")
    content.append(f"<h4>Response status: {status.value} {status.phrase}</h4>")
    content.append("<h3>Request headers:</h3>")
    content.extend([f"<h4>{h}</h4>" for h in request['headers']])
    content.append('</body></html>')
    return ''.join(content)


def generate_response(request):
    parsed_request = parse_request(request)

    if HTTPStatus.BAD_REQUEST.phrase in parsed_request:
        return parsed_request.encode()

    body = generate_content(parsed_request)
    headers = generate_headers(parsed_request)
    headers += f"\nContent-length: {len(body)}\n\n"

    return (headers + body).encode()


def event_loop():

    while True:
        for key, mask in selector.select():  # key: SelectorKey, events: selectors.EVENT_READ
            key.data(key.fileobj, mask)


def main():

    server(HOST, PORT)
    event_loop()


if __name__ == '__main__':

    main()
