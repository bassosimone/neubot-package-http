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
        self._method = ""
        self._url = ""
        self._protocol = ""
        self._code = ""
        self._reason = ""
        self._headers = {}
        self._bodyv = []

    @property
    def method(self):
        """ Get method """
        return self._method

    @property
    def url(self):
        """ Get url """
        return self._url

    @property
    def protocol(self):
        """ Get protocol """
        return self._protocol

    @property
    def code(self):
        """ Get code """
        return self._code

    @property
    def reason(self):
        """ Get reason """
        return self._reason

    @staticmethod
    def request(method, url, protocol, headers):
        """ Constructs a request message """
        # pylint: disable = protected-access
        message = HTTPMessage()
        message._method = method
        message._url = url
        message._protocol = protocol
        message._headers = headers
        return message

    @staticmethod
    def response(protocol, code, reason, headers):
        """ Constructs a response message """
        # pylint: disable = protected-access
        message = HTTPMessage()
        message._protocol = protocol
        message._code = code
        message._reason = reason
        message._headers = headers
        return message

    def __getitem__(self, key):
        key = key.lower()
        if key not in self._headers:
            return ""
        return self._headers[key]

    @property
    def headers(self):
        return self._headers.copy()

    def add_body_chunk(self, chunk):
        """ Add chunk to body """
        self._bodyv.append(chunk)

    def body_as_string(self, encoding=None):
        """ Return the body as string """
        binary = b"".join(self._bodyv)
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
        return b"".join(self._bodyv)
