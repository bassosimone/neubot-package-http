#
# This file is part of Neubot <https://www.neubot.org/>.
#
# Neubot is free software. See AUTHORS and LICENSE for more
# information on the copying conditions.
#

""" HTTP writer """

import logging
import os

def _compose(first_line, headers, bounded_body, filep, after, size):
    """ Compose a generic HTTP message """

    logging.debug("> %s", first_line)
    yield first_line + "\r\n"

    ischunked = headers.get("Transfer-Encoding", "").lower() == "chunked"

    if not ischunked:
        tot = 0
        if bounded_body:
            tot += len(bounded_body)
        if filep:
            filep.seek(0, os.SEEK_END)
            tot += filep.tell()
            filep.seek(0, os.SEEK_SET)
        if after:
            tot += len(after)
        headers["Content-Length"] = tot

    for name, value in headers.items():
        if value is not None:
            logging.debug("> %s: %s", name, value)
            header = "%s: %s\r\n" % (name, value)
            yield header
    yield "\r\n"

    if bounded_body:
        if ischunked:
            yield compose_chunk(bounded_body)
        else:
            yield bounded_body
    while filep:
        data = filep.read(size)
        if not data:
            break
        if ischunked:
            yield compose_chunk(data)
        else:
            yield data
    if after:
        if ischunked:
            yield compose_chunk(after)
        else:
            yield after

def compose_response(code, reason, headers, body):
    """ Compose an HTTP response with bounded body """
    return _compose("HTTP/1.1 %s %s" % (code, reason),
                    headers, body, None, None, 0)

def compose_response_filep(code, reason, headers, filep, size=65536):
    """ Compose an HTTP response reading body from filep """
    return _compose("HTTP/1.1 %s %s" % (code, reason),
                    headers, None, filep, None, size)

def compose_response_error(code, reason):
    """ Compose an HTTP error message """
    body = """\
        <HTML>
         <HEAD>
          <TITLE>%(code)s %(reason)s</TITLE>
         <HEAD>
         <BODY>
          <P>Error occurred: %(code)s %(reason)s</P>
         </BODY>
        </HTML>
        """ % locals()
    return compose_response(code, reason, {
        "Content-Type": "text/html",
    }, body)

def compose_headers(code, reason, headers):
    """ Compose headers of HTTP response """
    return compose_response(code, reason, headers, None)

def compose_response_redirect(target):
    """ Compose a redirect response """
    body = """\
        <HTML>
         <HEAD>
          <TITLE>Redirected to: %(target)s</TITLE>
         <HEAD>
         <BODY>
          <P>Redirected to: %(target)s</P>
         </BODY>
        </HTML>
        """ % locals()
    return compose_response("302", "Found", {
        "Location": target
    }, body)

def compose_chunk(chunk):
    """ Compose a body chunk """
    logging.debug("> %x", len(chunk))
    pre = "%x\r\n" % len(chunk)
    yield pre
    logging.debug("> {%d bytes}", len(chunk))
    yield chunk
    logging.debug(">")
    yield "\r\n"

def compose_last_chunk():
    """ Compose last chunk """
    yield "0\r\n\r\n"
