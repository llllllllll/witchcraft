from collections import deque
from itertools import islice


class PeekableIterator:
    """An iterator that can peek at the next ``n`` elements without
    consuming them.

    Parameters
    ----------
    stream : iterator
        The underlying iterator to pull from.

    Notes
    -----
    Peeking at ``n`` items will pull that many values into memory until
    they have been consumed with ``next``.

    The underlying iterator should not be consumed while the
    ``PeekableIterator`` is in use.
    """
    def __init__(self, stream):
        self._stream = iter(stream)
        self._peeked = deque()

    def __iter__(self):
        return self

    def __next__(self):
        try:
            return self._peeked.popleft()
        except IndexError:
            return next(self._stream)

    def peek(self, n=1):
        """Return the next ``n`` elements of the iterator without consuming
        them.

        Parameters
        ----------
        n : int

        Returns
        -------
        peeked : tuple
            The next ``elements``

        Examples
        --------
        >>> it = PeekableIterator(iter((1, 2, 3, 4)))
        >>> it.peek(2)
        (1, 2)
        >>> next(it)
        1
        >>> it.peek(1)
        (2,)
        >>> next(it)
        2
        >>> next(it)
        3
        """
        peeked = tuple(islice(self, None, n))
        put = self._peeked.append
        for item in peeked:
            put(item)
        return peeked

    def consume_peeked(self, n=None):
        if n is None:
            self._peeked.clear()
        else:
            for _ in range(n):
                self._peeked.popleft()

    def lookahead_iter(self):
        """Return an iterator that yields the next element and then consumes
        it.

        This is particularly useful for ``takewhile`` style functions where
        you want to break when some predicate is matched but not consume the
        element that failed the predicate.

        Examples
        --------
        >>> it = PeekableIterator(iter((1, 2, 3)))
        >>> for n in it.lookahead_iter():
        ...     if n == 2:
        ...         break
        >>> next(it)
        2
        """
        while True:
            yield from self.peek(1)
            try:
                next(self)
            except StopIteration:
                break
