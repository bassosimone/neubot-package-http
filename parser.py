#
# This file is part of Neubot <https://www.neubot.org/>.
#
# Neubot is free software. See AUTHORS and LICENSE for more
# information on the copying conditions.
#

""" HTTP parser """

import logging

from .messages import HTTPMessage

class HTTPError(RuntimeError):
    """ Indicates a protocol error """

class HTTPParser(object):
    """ HTTP messages parser """

    def __init__(self):
        self._coro = self._coroutine()
        self._eof_flag = False
        self._incoming = []
        self._maxheaders = 128
        self._maxline = 32768

    def eof(self):
        """ Tell the parser we've hit EOF """
        logging.debug("* EOF")
        self._eof_flag = True

    def feed(self, data):
        """ Feed the parser with new data """
        self._incoming.append(data)

    def parse(self):
        """ Parse data previously bufferized """
        try:
            return next(self._coro)
        except StopIteration:
            return ()

    def _readline_internal(self, maxline):
        """ Read a line from the input buffer (implementation) """
        data = b"".join(self._incoming)
        pos = data.find(b"\r\n")
        if pos < 0:
            pos = data.find(b"\n")
            if pos == -1:
                if len(data) > maxline:
                    return -1, ""
                return 0, ""
            else:
                pos += 1
        else:
            pos += 2
        line = data[:pos]
        #
        # If I understand RFC2616 Sect. 2.2 correctly, <TEXT> must
        # be ISO-8859-1, otherwise it must be MIME encoded.
        #
        line = line.decode("iso-8859-1")
        self._incoming = [data[pos:]]
        return len(line), line

    def _readline(self):
        """ Read a line from input buffer (interface) """
        length, line = self._readline_internal(self._maxline)
        if length < 0:
            raise HTTPError
        if length == 0:
            return ""
        logging.debug("< %s", line.strip())
        return line

    def _read(self, desired):
        """ Read from the input buffer """
        data = b"".join(self._incoming)
        self._incoming = [data[desired:]]
        data = data[:desired]
        return data

    def _coroutine(self):
        """ Coroutine that process incoming data """
        while True:

            logging.debug("* FIRSTLINE")
            line = self._readline()
            while not line:
                yield ()
                line = self._readline()
            if self._eof_flag:
                return  # Reached final state
            line = line.strip()
            first_line = line.split(None, 3)
            if len(first_line) != 3:
                raise HTTPError

            if first_line[0].startswith("HTTP/"):
                isresponse = True
            elif first_line[2].startswith("HTTP/"):
                isresponse = False
            else:
                raise HTTPError

            logging.debug("* HEADERS")
            last_hdr = ""
            headers = {}
            while True:
                if len(headers) > self._maxheaders:
                    raise HTTPError
                line = self._readline()
                while not line:
                    yield ()
                    line = self._readline()
                line = line.strip()
                if not line:
                    break
                if last_hdr and line[0:1] in (" ", "\t"):
                    # Must be first branch so ":" can appear in folded lines
                    value = headers[last_hdr] + " " + line
                else:
                    pos = line.find(":")
                    if pos < 0:
                        raise HTTPError
                    last_hdr, value = line.split(":", 1)
                    last_hdr, value = last_hdr.strip().lower(), value.strip()
                headers[last_hdr] = value

            if isresponse:
                message = HTTPMessage.response(first_line[0], first_line[1],
                                               first_line[2], headers)
                yield ("response", message)
            else:
                message = HTTPMessage.request(first_line[0], first_line[1],
                                              first_line[2], headers)
                yield ("request", message)

            if headers.get("transfer-encoding") == "chunked":

                while True:

                    logging.debug("* CHUNK_LENGTH")
                    line = self._readline()
                    while not line:
                        yield ()
                        line = self._readline()
                    line = line.strip()
                    vector = line.split()
                    length = int(vector[0], 16)
                    if length < 0:
                        raise HTTPError
                    if length == 0:
                        break

                    logging.debug("* CHUNK")
                    while length > 0:
                        data = self._read(length)
                        if not data:
                            yield ()
                            continue
                        length -= len(data)
                        yield ("data", message, data)

                    logging.debug("* CHUNK_END")
                    line = self._readline()
                    while not line:
                        yield ()
                        line = self._readline()

                logging.debug("* TRAILERS")
                while True:
                    line = self._readline()
                    while not line:
                        yield ()
                        line = self._readline()
                    line = line.strip()
                    if not line:
                        break

                yield ("end", message)

            elif headers.get("content-length"):

                logging.debug("* BOUNDED_BODY")
                length = int(headers["content-length"])
                if length < 0:
                    raise HTTPError
                while length > 0:
                    data = self._read(length)
                    if not data:
                        yield ()
                        continue
                    length -= len(data)
                    yield ("data", message, data)
                yield ("end", message)

            elif isresponse and (first_line[1][0:1] == "1" or
                                 first_line[1] == "204" or
                                 first_line[1] == "304"):
                logging.debug("* 100_OR_2O4_OR_304")
                yield ("end", message)

            elif isresponse and (headers.get("connection") != "keep-alive" or
                                 first_line[0] == "HTTP/1.0"):
                logging.debug("* CONNECTION_CLOSE")
                while not self._eof_flag:
                    data = self._read(65535)
                    if not data:
                        yield ()
                        continue
                    length -= len(data)
                    yield ("data", message, data)
                yield ("end", message)
                return  # Reached final state

            elif isresponse and (first_line[1][0:1] == "1" or
                                 first_line[1] == "204" or
                                 first_line[1] == "304"):
                logging.debug("* RESPONSE_WITHOUT_BODY")
                yield ("end", message)

            elif not isresponse:
                logging.debug("* REQUEST_WITHOUT_BODY")
                yield ("end", message)

            else:
                raise RuntimeError
