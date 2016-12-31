import operator as op

from .iterator import PeekableIterator
from .lexer import (
    And,
    By,
    Comma,
    Name,
    On,
    Or,
    Shuffle,
    lex,
)


class BadParse(Exception):
    """Signals that the lexeme stream did not match the grammar.

    Parameters
    ----------
    lexeme : Lexeme
        The lexeme that triggered the failure.
    msg : str
        A message about why this is invalid.
    """
    def __init__(self, lexeme, msg):
        self.lexeme = lexeme
        self.msg = msg


def expect(stream, type_, *types):
    """Pull the next lexeme out of the stream and assert that it is of one of
    the expected types.

    Parameters
    ----------
    stream : PeekableIterator[Lexeme]
        The lexeme stream.
    *types
        The types to expect. This cannot be empty.

    Returns
    -------
    lexeme : Lexeme
        The next lexeme in the stream if it is of one of the valid types.

    Raises
    ------
    BadParse
        Raised when the next lexeme in the stream is not one of the expected
        types.
    """
    lexeme = next(stream)
    types = (type_,) + types
    if not isinstance(lexeme, type_):
        raise BadParse(
            lexeme,
            'unexpected lexeme %r, expected %s' % (
                lexeme.string,
                ('one of %s' % tuple(map(op.attrgetter('__name__'), types)))
                if len(types) > 1 else
                type_.__name__,
            ),
        )
    return lexeme


def accept(stream, handlers):
    """Peek at the next iterable in the stream and call an optional function
    on the stream if it matches.

    Parameters
    ----------
    stream : PeekableIterator[Lexeme]
        The lexeme stream.
    handler : dict[type, callable[PeekableIterator[Lexeme]]]
        A mapping from Lexeme types to a handler function to apply to the
        stream if the next lexeme is of the given type. If the next lexeme is
        not handled, it will not be consumed from the stream.
    """
    next_ = stream.peek()
    if not next_:
        return

    try:
        f = handlers[type(next_[0])]
    except KeyError:
        pass
    else:
        next(stream)
        f(stream)


class Query:
    """A query to run against the database.

    Parameters
    ----------
    titles : iterable[str]
        The patterns for the titles of the tracks.
    on : str
        The pattern for the album to select from.
    by : str
        The patterns for the artist to select from
    shuffle : bool
        Should the tracks be shuffled?
    and_ : Query or None
        The query to intersect with.
    or_ : Query or None
        The query to union with.
    """
    def __init__(self, titles, on, by, shuffle, and_, or_):
        self.titles = titles
        self.on = on
        self.by = by
        self.shuffle = shuffle
        self.and_ = and_
        self.or_ = or_

    @classmethod
    def parse(cls, stream):
        """Parse a query from a stream of Lexemes.

        A query is of the form:

        .. code-bock::

           Name {, Name} [on Name] [by Name] [shuffle] [and Query] [or Query]

        where ``[...]`` means optional and ``{...}`` means repeatable (can be
        empty).

        Parameters
        ----------
        stream : PeekableIterator[Lexeme]
            The stream to consume from.

        Returns
        -------
        query : Query
            The parsed query.

        Raises
        ------
        BadParse
            Raised when the lexemes in the stream don't match the grammar for
            a Query.

        """
        # we require at least one Name for the titles
        titles = [expect(stream, Name).string]

        def parse_titles(iterable):
            """Append the new title and check for more comma delimited titles.
            """
            titles.append(expect(stream, Name).string)
            accept(stream, {Comma: parse_titles})

        # parse any extra titles
        accept(stream, {Comma: parse_titles})

        on = None
        by = None
        shuffle = False
        and_ = None
        or_ = None

        def parse_on(stream):
            """Parse an ``on`` clause. If we haven't already added a ``by``,
            check for a ``by`` clause.
            """
            nonlocal on

            on = expect(stream, Name).string
            if by is None:
                accept(stream, {By: parse_by})

        def parse_by(stream):
            """Parse a ``by`` clause. If we haven't already added an ``on``,
            check for a ``on`` clause.
            """
            nonlocal by
            by = expect(stream, Name).string
            if on is None:
                accept(stream, {On: parse_on})

        # parse the ``on`` and ``by`` in any order
        accept(stream, {On: parse_on, By: parse_by})

        def parse_shuffle(stream):
            """Parse the ``shuffle`` modifier.
            """
            nonlocal shuffle
            shuffle = True

        accept(stream, {Shuffle: parse_shuffle})

        def parse_and(stream):
            """Parse an ``and`` clause.
            """
            nonlocal and_
            and_ = Query.parse(stream)

        def parse_or(stream):
            """Parse an ``or`` clause.
            """
            nonlocal or_
            or_ = Query.parse(stream)

        # optionally check for an ``and`` or an ``or``
        accept(stream, {And: parse_and, Or: parse_or})

        return cls(titles, on, by, shuffle, and_, or_)


def parse(source):
    """Parse a witchcraft ql query string into a Query object.

    Parameters
    ----------
    source : str
        The source to parse into a Query.

    Returns
    -------
    query : Query
        The parsed query.

    Raises
    ------
    ValueError
        Raised when the source is not a valid query.
    """
    stream = PeekableIterator(lex(source))
    try:
        query = Query.parse(stream)
        if stream.peek():
            # we have more tokens in the stream after the full parse
            lexeme = next(stream)
            raise BadParse(lexeme, 'unexpected lexeme %r' % lexeme.string)
    except BadParse as e:
        raise ValueError(
            'parse error at %d: %s\n%s\n%s^' % (
                e.lexeme.col_offset,
                e.msg,
                source,
                ' ' * e.lexeme.col_offset,
            ),
        )

    return query
