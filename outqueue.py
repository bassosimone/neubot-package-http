#
# This file is part of Neubot <https://www.neubot.org/>.
#
# Neubot is free software. See AUTHORS and LICENSE for more
# information on the copying conditions.
#

""" Output queue """

import collections

class OutputQueue(object):
    """ Output queue """

    def __init__(self, default_encoding="iso-8859-1"):
        self._queue = collections.deque()
        self._default_encoding = default_encoding

    def insert_data(self, data):
        """
         Insert data to be sent.

         The inserted element shall be an instance of `bytes`, an instance
         of `str`, or an iterator. In the latter case, the iterator shall
         return instances of `bytes`, instances of `str` or another iterator
         that shall return instances of `bytes`, of `str` or, in turn,
         another iterator to which the same restrictions apply.

         If the inserted element is empty, nothing is inserted in queue.
        """
        if data:
            self._queue.append(data)

    def reinsert_partial_chunk(self, chunk):
        """
         Reinsert partially sent chunk on the left side of the queue.

         The inserted element is coerced to memoryview.
        """
        self._queue.appendleft(memoryview(chunk))

    def get_next_chunk(self):
        """
         Extract element from the left side of the queue.

         Returns a memoryview that could be passed to send() and similar
         functions, or `None` when the queue is empty.
        """
        while self._queue:
            try:
                elem = next(self._queue[0])
            except StopIteration:
                self._queue.popleft()
            except TypeError:
                elem = self._queue.popleft()
                if elem:
                    try:
                        elem = memoryview(elem)
                    except TypeError:  # Deal with strings
                        elem = elem.encode(self._default_encoding)
                        elem = memoryview(elem)
                    return elem
            else:
                self._queue.appendleft(elem)

    def __bool__(self):
        return bool(self._queue)

    def __len__(self):
        return len(self._queue)
