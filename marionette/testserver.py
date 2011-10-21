import json
import select
import socket

class TestServer(object):
    """ A test Marionette server which can be used to test the Marionette
        protocol.  Each request will trigger a canned response; see
        process_command().
    """

    TEST_URL = 'http://www.mozilla.org'
    TEST_CURRENT_WINDOW = 'window1'
    TEST_WINDOW_LIST = ['window1', 'window2', 'window3']
    TEST_EXECUTE_RETURN_VALUE = 10
    TEST_EXECUTE_SCRIPT = 'return 2 * 5;'
    TEST_EXECUTE_SCRIPT_ARGS = 'testing'
    TEST_FIND_ELEMENT = 'element1'
    TEST_FIND_ELEMENTS = ['element1', 'element2', 'element3']
    TEST_GET_TEXT = 'first name'
    TEST_GET_VALUE = 'Mozilla Firefox'

    def __init__(self, port):
        self.port = port

        self.srvsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.srvsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.srvsock.bind(("", port))
        self.srvsock.listen(5)
        self.descriptors = [self.srvsock]
        print 'TestServer started on port %s' % port

    def _recv_n_bytes(self, sock, n):
        """ Convenience method for receiving exactly n bytes from
            self.sock (assuming it's open and connected).
        """
        data = ''
        while len(data) < n:
            chunk = sock.recv(n - len(data))
            if chunk == '':
                break
            data += chunk
        return data

    def receive(self, sock):
        """ Receive the next complete response from the server, and return
            it as a dict.  Each response from the server is prepended by
            len(message) + ':'.
        """
        assert(sock)
        response = sock.recv(10)
        sep = response.find(':')
        if sep == -1:
            return None
        length = response[0:sep]
        response = response[sep + 1:]
        response += self._recv_n_bytes(sock, int(length) + 1 + len(length) - 10)
        print 'received', response
        return json.loads(response)

    def send(self, sock, msg):
        msg['from'] = 'marionette'
        data = json.dumps(msg)
        print 'sending %s' % data
        sock.send('%s:%s' % (len(data), data))

    def accept_new_connection(self):
        newsock, (remhost, remport) = self.srvsock.accept()
        self.descriptors.append( newsock )
        str = 'Client connected %s:%s\r\n' % (remhost, remport)
        print str
        self.send(newsock, {'from': 'root',
                            'applicationType': 'gecko',
                            'traits': []})

    def process_command(self, data):
        command = data['command']

        # canned responses for test messages
        responses = {
            'newSession': { 'value': 'a65bef90b145' },
            'deleteSession': { 'ok': True },
            'setScriptTimeout': { 'ok': True },
            'setSearchTimeout': { 'ok': True },
            'getWindow': { 'value': self.TEST_CURRENT_WINDOW },
            'getWindows': { 'values': self.TEST_WINDOW_LIST },
            'closeWindow': { 'ok': True },
            'switchToWindow': { 'ok': True },
            'getUrl' : { 'value': self.TEST_URL },
            'goUrl': { 'ok': True },
            'goBack': { 'ok': True },
            'goForward': { 'ok': True },
            'refresh': { 'ok': True },
            'executeScript': { 'value': self.TEST_EXECUTE_RETURN_VALUE },
            'executeAsyncScript': { 'value': self.TEST_EXECUTE_RETURN_VALUE },
            'findElement': { 'value': self.TEST_FIND_ELEMENT },
            'findElements': { 'values': self.TEST_FIND_ELEMENTS },
            'clickElement': { 'ok': True },
            'getElementText': { 'value': self.TEST_GET_TEXT },
            'sendKeysToElement': { 'ok': True },
            'getElementValue': { 'value': self.TEST_GET_VALUE },
            'clearElement': { 'ok': True },
            'isElementSelected': { 'value': True },
            'elementsEqual': { 'value': True },
            'isElementEnabled': { 'value': True },
            'isElementDisplayed': { 'value': True },
            'getElementAttribute': { 'value': self.TEST_GET_VALUE },
            'getSessionCapabilities': { 'value': {
                "cssSelectorsEnabled": True,
                "browserName": "firefox",
                "handlesAlerts": True,
                "javascriptEnabled": True,
                "nativeEvents": True,
                "platform": 'linux',
                "takeScreenshot": False,
                "version": "10.1"
                }
            },
            'getStatus': { 'value': {
                "os": {
                    "arch": "x86",
                    "name": "linux",
                    "version": "unknown"
                    },
                "build": {
                    "revision": "unknown",
                    "time": "unknown",
                    "version": "unknown"
                    }
                }
            }
        }

        if command in responses:
            response = responses[command]
        else:
            response = { 'error': 'unknown command' }

        if command not in ('newSession', 'getStatus') and 'session' not in data:
            response = { 'error': 'no session specified' }

        return response

    def run(self):
        while 1:
            # Await an event on a readable socket descriptor
            (sread, swrite, sexc) = select.select( self.descriptors, [], [] )
            # Iterate through the tagged read descriptors
            for sock in sread:
                # Received a connect to the server (listening) socket
                if sock == self.srvsock:
                    self.accept_new_connection()
                else:
                    # Received something on a client socket
                    try:
                        data = self.receive(sock)
                    except:
                        data = None
                    # Check to see if the peer socket closed
                    if data is None:
                        host,port = sock.getpeername()
                        str = 'Client disconnected %s:%s\r\n' % (host, port)
                        print str
                        sock.close
                        self.descriptors.remove(sock)
                    else:
                        if 'command' in data:
                            msg = self.process_command(data)
                        else:
                            msg = 'command: %s' % json.dumps(data)
                        self.send(sock, msg)


if __name__ == "__main__":
    server = TestServer(2626)
    server.run()
