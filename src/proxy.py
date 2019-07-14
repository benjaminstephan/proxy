import socket
import threading

from proxyconf import conf


class ProxyServer:

    def __init__(self):
        # Create a TCP socket
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # the SO_REUSEADDR flag tells the kernel to reuse a local socket in TIME_WAIT state,
        # without waiting for its natural timeout to expire.
        self.serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # bind the socket to given host and port
        self.serverSocket.bind((conf['HOST'], conf['PORT']))

        self.serverSocket.listen()

    def handle_connections(self):
        while True:
            # Accept connections
            connection, client_address = self.serverSocket.accept()

            # Create a thread for every client
            proxy_thread = ProxyThread(connection, client_address)
            proxy_thread.run()


class ProxyThread(threading.Thread):

    def __init__(self, client_connection, client_address):
        threading.Thread.__init__(self)

        self.client_connection = client_connection
        self.client_address = client_address

        # The entire python program exists once all non daemon threads exited
        # so making the proxy threads daemons leads to them exiting once the main thread
        # finishes execution
        self.daemon = True

    def run(self):
        print('[*] Starting Proxy Thread')
        self.request = self.get_request()
        if self.request:
            self.url, self.port = self.get_url_and_port_from_http_request()
            self.target_connection = self.connect_to_target_server()
            self.send_request_to_target_server()
            self.return_response_to_client()
            self.close_connections()
        print('[*] Exiting Proxy Thread')

    def get_request(self):
        request = self.client_connection.recv(4096)
        print('[*] Request is: {}'.format(request))
        return request

    def get_url_and_port_from_http_request(self):
        """ Gets URL and PORT from the request. In case no port is specified the default HTTP port 80 is used. It also
        cleans the URL to make it usable for socket connections.
        """
        first_line = self.request.split(b'\n')[0]
        url = first_line.split(b' ')[1]

        # find and remove http://
        http_pos = url.find(b'://')
        if http_pos >= 0:
            url = url[(http_pos + 3):]

        # find and remove / as otherwise no socket connection can be established
        url = url.split(b'/')[0]

        # find and handle port
        url_parts = url.split(b':')
        if len(url_parts) > 1:
            url = url_parts[0]
            port = int(url_parts[1])
        else:
            # use default http port if not specified
            port = 80

        print('[*] The URL is: {}'.format(url))
        print('[*] The port is: {}'.format(port))
        return url, port

    def connect_to_target_server(self):
        target_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        target_connection.connect((self.url, self.port))
        return target_connection

    def send_request_to_target_server(self):
        self.target_connection.send(self.request)

    def return_response_to_client(self):
        while True:
            data = self.target_connection.recv(4096)
            print('[*] Response from target server is: {} \n Sending to Client'.format(str(data)))
            if len(data):
                self.client_connection.send(data)  # send to browser/client
            else:
                break

    def close_connections(self):
        self.client_connection.close()
        self.target_connection.close()


if __name__ == '__main__':
    proxyServer = ProxyServer()
    proxyServer.handle_connections()
