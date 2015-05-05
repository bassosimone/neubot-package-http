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

class HTTPRequestHandler(asyncore.dispatcher):
    """ HTTP request handler """

    def __init__(self, server, sock=None, mapx=None):
        asyncore.dispatcher.__init__(self, sock, mapx)
        self.server = server
        self.parser = HTTPParser()
        self.queue = HTTPOutputQueue()

    def handle_read(self):
        data = self.recv(65535)
        logging.debug("http: received %d bytes", len(data))
        if data:
            self.parser.feed(data)
        else:
            self.parser.eof()
        result = self.parser.parse()
        while result:
            self._emit(result)
            result = self.parser.parse()

    def _emit(self, event):
        """ Emit the specified event """
        if event[0] == "request":
            self.server.pre_check(self, event[1])
        elif event[0] == "data":
            event[1].add_body_chunk(event[2])
        elif event[0] == "end":
            self.server.route(self, event[1])
        else:
            raise RuntimeError

    def write(self, data):
        """ Write bytes, str or generator to socket """
        self.queue.insert_data(data)

    def writable(self):
        return bool(self.queue)

    def handle_write(self):
        chunk = self.queue.get_next_chunk()
        if chunk:
            chunk = chunk[self.send(chunk):]
            if chunk:
                self.reinsert_partial_chunk(chunk)

class HTTPServer(asyncore.dispatcher):
    """ HTTP server """

    def __init__(self, file_handler=None):
        asyncore.dispatcher.__init__(self)
        self.routes = {}
        self.file_handler = file_handler

    def add_route(self, url, generator):
        """ Add a route """
        self.routes[url] = generator

    @staticmethod
    def pre_check(connection, request):
        """ Pre check incoming request """
        if request["expect"].lower() == "100-continue":
            connection.write(writer.compose_headers("100", "Continue", {}))

    def route(self, connection, request):
        """ Route request """
        try:
            self._route(connection, request)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            logging.warning("unhandled exception", exc_info=1)
            connection.write(writer.compose_error("500",
                             "Internal Server Error"))

    def _route(self, connection, request):
        """ Internal route function """

        url = request.url
        logging.debug("http: router received url: %s", url)
        index = url.find("?")
        if index >= 0:
            url = url[:index]
            logging.debug("http: router url without query: %s", url)

        if url in self.routes:
            self.routes[url](connection, request)
        elif self.file_handler:
            self.file_handler(connection, request)
        else:
            connection.write(writer.compose_error("404", "Not Found"))

    def handle_accept(self):
        result = self.accept()
        if not result:
            return
        sock = result[0]
        HTTPRequestHandler(self, sock)

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
