#
# This file is part of Neubot <https://www.neubot.org/>.
#
# Neubot is free software. See AUTHORS and LICENSE for more
# information on the copying conditions.
#

"""
 Neubot HTTP library.

 Example usage:

     import asyncore
     import json
     from neubot_scheduler import http

     class Simple(http.HTTPRequestHandler):
         ''' Handles /simple URL '''

         def on_end(self, connection, request):
             response = {
                 "method": request.method,
                 "url": request.url,
                 "protocol": request.protocol,
                 "headers": request.headers,
                 "body": request.body_as_string()
             }
             connection.write(http.writer.compose_response("200", "Ok", {
                 "Content-Type": "application/json",
             }, json.dumps(response, indent=4)))

     def main():
         ''' Main function '''
         http.listen({
             "routes": {
                 "/simple": Simple,
             }
         })
         asyncore.loop()

    main()
"""

__version__ = 2.0

from .file_handler import FileHandler
from .core import HTTPRequestHandler, listen
from . import writer
