import logging
import re
import selectors
import socket
from argparse import ArgumentParser
from collections import namedtuple
from http import HTTPStatus
from urllib.parse import parse_qs, urlencode, urlparse

parser = ArgumentParser()
parser.add_argument('--host', default='0.0.0.0')
parser.add_argument('--port', type=int, default=9000)
args = parser.parse_args()

Header = namedtuple('Header', ('name', 'value'))

HOST, PORT = args.host, args.port
BUFF_SIZE = 4096

selector = selectors.DefaultSelector()

logger = None


def init_logger(name):
    LOG_FORMAT = '{asctime} [{levelname}] [{name}] [{funcName}] > {message}'
    logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT, style='{', )
    return logging.getLogger(name)


def find_http_status(code):
    """Find HTTP status by its code"""

    for status in HTTPStatus:
        if status.value == code:
            return status


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
    client_socket.setblocking(False)
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

    request = sock.recv(BUFF_SIZE)

    if request:
        logger.debug("Got request from %s:%s", *client_addr)

        response = generate_response(request, client_addr)

        logger.debug("Sending response to %s:%s", *client_addr)
        sock.sendall(response)

        if HTTPStatus.BAD_REQUEST.phrase in response.decode():
            logger.debug("Got %s from %s:%s",
                         HTTPStatus.BAD_REQUEST.phrase, *client_addr)
            close(sock)
            return

        if "Connection: close" in response.decode():
            close(sock)

    else:
        logger.debug("Client %s:%s has disconnected", *client_addr)
        close(sock)


def parse_post(headers, body):
    ''' We handle only trivial case here - only text form data'''

    if 'application/x-www-form-urlencoded' in headers['content-type']:
        return parse_qs(body)

    if 'multipart/form-data' in headers['content-type']:
        boundary = headers['content-type'].split('; boundary=', 1)[1]
        pattern = f"\-*{boundary}\-*"
        form_data = [part.strip() for part in re.split(pattern, body)]
        params = {}
        for part in form_data:
            # ex: 'Content-Disposition: form-data; name="status"\r\n\r\n500\r\n'
            param = re.match(r'.+name\=\"(.+)\"\s+(\S+)\s*', part)
            if param:
                params.update([param.groups()])
        if params:
            return parse_qs(urlencode(params))


def parse_request(request):
    """Parse client's request"""

    startline: str = request.decode().split('\n', 1)[0]

    # minimal sanity check
    try:
        method, url, schema = startline.split()
        assert 'HTTP' in schema
    except:
        return {
            'status': HTTPStatus.BAD_REQUEST,
            'schema': 'HTTP/1.1',
            'headers': {'Connection': 'close'}
        }

    try:
        assert method in ('GET', 'POST')
    except AssertionError:
        return {
            'status': HTTPStatus.NOT_IMPLEMENTED,
            'schema': schema,
            'headers': {'Connection': 'close'}
        }

    raw_headers, body = request.decode().split('\r\n\r\n', 1)

    headers = {}

    for header in raw_headers.split('\r\n'):
        header = header.split(': ', 1)
        if len(header) == 2:
            header = Header(*header)
            headers[header.name.lower()] = header.value

    url_parsed = urlparse(url)
    qs_parsed = None

    if method == 'GET':
        qs_parsed = parse_qs(url_parsed.query)

    elif method == 'POST' and headers.get('content-type'):
        qs_parsed = parse_post(headers, body)

    try:
        code = int(qs_parsed['status'][0])
    except:
        code = 200

    status = find_http_status(code)
    if not status:
        status = HTTPStatus.OK

    return {
        'status': status,
        'schema': schema,
        'method': method,
        'url': url,
        'url_parsed': url_parsed,
        'qs_parsed': qs_parsed,
        'headers': headers
    }


def generate_headers(request):
    '''Generate response headers'''

    headers = {}

    if 'keep-alive' in request['headers'].values():
        headers.update({"Connection": "keep-alive"})
    else:
        headers.update({"Connection": "close"})

    headers.update({"Content-Type": "text/html"})

    return '\n'.join([f"{k}: {v}" for k, v in headers.items()])


def generate_content(request, client_addr):
    '''Generate response content'''

    content = []
    status = request['status']

    content.append("<h4>Request source: {}:{}</h4>".format(*client_addr))

    if request.get('method'):
        content.append(f"<h4>Request method: {request['method']}</h4>")

    content.append(f"<h4>Response status: {status.value} {status.phrase}</h4>")

    if request.get('headers'):
        content.append("<h3>Request headers:</h3>")
        content.extend([f"<h4>{k.capitalize()}: {v}</h4>" for k,
                        v in request['headers'].items()])

    if request.get('qs_parsed'):
        content.append("<h3>Request parameters:</h3>")
        content.extend([f"<h4>{k}: {v}</h4>" for k,
                        v in request['qs_parsed'].items()])

    return ''.join(content)


def generate_startline(request):
    '''Generate response start line'''

    return f"{request['schema']} {request['status'].value} {request['status'].phrase}\n"


def generate_response(request, client_addr):
    '''Generate response'''

    parsed_request = parse_request(request)

    startline = generate_startline(parsed_request)
    body = generate_content(parsed_request, client_addr)
    headers = generate_headers(parsed_request)
    headers += f"\nContent-length: {len(body)}\n\n"

    return (startline + headers + body).encode()


def event_loop():
    '''Run event loop based on selectors functionality'''

    while True:
        for key, mask in selector.select():  # key: SelectorKey, events: selectors.EVENT_READ
            callback = key.data
            sock = key.fileobj
            callback(sock, mask)


def main():

    global logger
    logger = init_logger('ECHO')
    server(HOST, PORT)
    event_loop()


if __name__ == '__main__':

    main()
