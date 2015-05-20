#
# This file is part of Neubot <https://www.neubot.org/>.
#
# Neubot is free software. See AUTHORS and LICENSE for more
# information on the copying conditions.
#

""" File handler """

import logging
import mimetypes
import os

from . import writer

class FileHandler(object):
    """ File handler class """

    def __init__(self, rootdir, default_file):
        logging.debug("fh: user specified rootdir: %s", rootdir)
        rootdir = os.path.abspath(os.path.realpath(os.path.abspath(rootdir)))
        logging.debug("fh: absolute rootdir is: %s", rootdir)
        self._rootdir = rootdir
        self._default_file = default_file

    def resolve_path(self, path):
        """ Safely maps HTTP path to filesystem path """

        logging.debug("fh: rootdir %s", self._rootdir)
        logging.debug("fh: original path %s", path)

        path = os.sep.join([self._rootdir, path])
        path = os.path.abspath(path)             # Process "../"s
        path = os.path.realpath(path)            # Resolve symlinks
        path = os.path.abspath(path)             # Just in case

        logging.debug("fh: normalized path %s", path)

        if not path.startswith(self._rootdir):
            return

        return path

    @staticmethod
    def guess_mimetype(path):
        """ Guess mimetype of the file at path """
        mimetype, encoding = mimetypes.guess_type(path)
        if not mimetype:
            mimetype = "text/plain"
        return mimetype, encoding

    def serve_filep(self, connection, request, path, filep):
        """ Serve the content of a file """

        mimetype, encoding = self.guess_mimetype(path)

        logging.debug("fh: sending '%s' (i.e., '%s')", request.url, path)

        connection.write(writer.compose_filep(200, "Ok", {
            "Content-Type": mimetype,
            "Content-Encoding": encoding,  # if encoding is None
                                           # it is filtered out
        }, filep))

    def serve_file(self, connection, request, path):
        """ Serve the file at path """

        if not os.path.isfile(path):
            connection.write(writer.compose_error(404, "Not Found"))
            return

        logging.debug("fh: url mapped to existing file: %s", path)

        try:
            filep = open(path, "rb")
        except (OSError, IOError):
            connection.write(writer.compose_error(404, "Not Found"))
            return

        self.serve_filep(connection, request, path, filep)

    def serve_directory(self, connection, request, path):
        """ Serve the directory at path """
        path = os.sep.join([path, self._default_file])
        logging.debug("fh: url isdir; trying with: %s", path)
        self.serve_file(connection, request, path)

    def __call__(self, connection, request):
        """ Process HTTP request for file resources """

        if not self._rootdir:
            logging.warning("fh: rootdir is not set")
            connection.write(writer.compose_error(403, "Forbidden"))
            return

        logging.debug("fh: requested to serve: %s", request.url)

        path = self.resolve_path(request.url)
        if not path:
            connection.write(writer.compose_error(403, "Forbidden"))
            return

        logging.debug("fh: url mapped to: %s", path)

        if os.path.isdir(path):
            self.serve_directory(connection, request, path)
        else:
            self.serve_file(connection, request, path)
