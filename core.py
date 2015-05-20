#
# This file is part of Neubot <https://www.neubot.org/>.
#
# Neubot is free software. See AUTHORS and LICENSE for more
# information on the copying conditions.
#

""" Core API of this module """

import asyncore
import logging
import socket

from .outqueue import HTTPOutputQueue
from .parser import HTTPParser

from . import writer

class HTTPRequestHandler(object):
    """ HTTP request handler """

    def on_request(self, connection, request):
        """ Call when headers are received """

    def on_data(self, connection, request, chunk):
        """ Called when data is received """

    def on_end(self, connection, request):
        """ Called at end of request """

class BodyReceiverHandler(HTTPRequestHandler):
    """ Handler that expects to receive a body """

    def on_request(self, connection, request):
        """ Send '100 Continue' if this is expected by client """
        if request["expect"].lower() == "100-continue":
            connection.write(writer.compose_headers("100", "Continue", {}))

class NotFoundHandler(HTTPRequestHandler):
    """ '404 Not Found' handler """

    def on_end(self, connection, _):
        connection.write(writer.compose_error("404", "Not Found"))

class HTTPRequestDispatcher(asyncore.dispatcher):
    """ HTTP request dispatcher """

    def __init__(self, server, sock=None, mapx=None):
        asyncore.dispatcher.__init__(self, sock, mapx)
        self._handler = HTTPRequestHandler()
        self._parser = HTTPParser()
        self._queue = HTTPOutputQueue()
        self._server = server

    def handle_read(self):
        data = self.recv(65535)
        logging.debug("http: received %d bytes", len(data))
        if data:
            self._parser.feed(data)
        else:
            self._parser.eof()
        result = self._parser.parse()
        while result:
            self._emit(result)
            result = self._parser.parse()

    def _emit(self, event):
        """ Emit the specified event """
        if event[0] == "request":
            self._handler = self._server.route(event[1])
            self._handler.on_request(self, event[1])
        elif event[0] == "data":
            self._handler.on_data(self, event[1], event[2])
        elif event[0] == "end":
            self._handler.on_end(self, event[1])
        else:
            raise RuntimeError

    def write(self, data):
        """ Write bytes, str or generator to socket """
        self._queue.insert_data(data)

    def writable(self):
        return bool(self._queue)

    def handle_write(self):
        chunk = self._queue.get_next_chunk()
        if chunk:
            chunk = chunk[self.send(chunk):]
            if chunk:
                self.reinsert_partial_chunk(chunk)

class HTTPServer(asyncore.dispatcher):
    """ HTTP server """

    def __init__(self, file_handler=None):
        asyncore.dispatcher.__init__(self)
        self._routes = {}
        self._file_handler = file_handler

    def add_route(self, url, generator):
        """ Add a route """
        self._routes[url] = generator

    def route(self, request):
        """ Route request """

        url = request.url
        logging.debug("http: router received url: %s", url)
        index = url.find("?")
        if index >= 0:
            url = url[:index]
            logging.debug("http: router url without query: %s", url)

        if url in self._routes:
            return self._routes[url]()
        if self._file_handler:
            return self._file_handler()
        return NotFoundHandler()

    def handle_accept(self):
        result = self.accept()
        if not result:
            return
        sock = result[0]
        HTTPRequestDispatcher(self, sock)

def listen(settings):
    """ Listen for HTTP requests """

    settings.setdefault("backlog", 128)
    settings.setdefault("family", socket.AF_INET)
    settings.setdefault("hostname", "")
    settings.setdefault("port", 8080)
    settings.setdefault("routes", {})
    settings.setdefault("file_handler", None)

    epnt = settings["hostname"], int(settings["port"])

    server = HTTPServer(settings["file_handler"])
    for key in settings["routes"]:
        server.add_route(key, settings["routes"][key])
    server.create_socket(settings["family"], socket.SOCK_STREAM)
    server.set_reuse_addr()
    server.bind(epnt)
    server.listen(settings["backlog"])
