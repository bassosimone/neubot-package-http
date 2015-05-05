#
# This file is part of Neubot <https://www.neubot.org/>.
#
# Neubot is free software. See AUTHORS and LICENSE for more
# information on the copying conditions.
#

""" HTTP messages """

class HTTPMessage(object):
    """ HTTP message object """

    def __init__(self):
        self.method = ""
        self.url = ""
        self.protocol = ""
        self.code = ""
        self.reason = ""
        self.headers = {}
        self.bodyv = []

    @staticmethod
    def request(method, url, protocol, headers):
        """ Constructs a request message """
        message = HTTPMessage()
        message.method = method
        message.url = url
        message.protocol = protocol
        message.headers = headers
        return message

    @staticmethod
    def response(protocol, code, reason, headers):
        """ Constructs a response message """
        message = HTTPMessage()
        message.protocol = protocol
        message.code = code
        message.reason = reason
        message.headers = headers
        return message

    def __getitem__(self, key):
        key = key.lower()
        if key not in self.headers:
            return ""
        return self.headers[key]

    def add_body_chunk(self, chunk):
        """ Add chunk to body """
        self.bodyv.append(chunk)

    def body_as_string(self, encoding=None):
        """ Return the body as string """
        binary = b"".join(self.bodyv)
        if encoding:
            return binary.decode(encoding)
        content_type = self["content-type"].lower()
        index = content_type.find("charset=")
        if index >= 0:
            encoding = content_type[index + len("charset="):].strip()
            return binary.decode(encoding)
        if content_type == "application/json":
            return binary.decode("utf-8")
        if content_type == "application/xml":
            return binary.decode("utf-8")
        return binary.decode("iso-8859-1")  # Default

    def body_as_bytes(self):
        """ Return the body as bytes """
        return b"".join(self.bodyv)
