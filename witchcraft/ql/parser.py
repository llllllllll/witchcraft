from .iterator import PeekableIterator
from .lexer import (
    And,
    By,
    Comma,
    Name,
    On,
    Or,
    Ordered,
    Shuffle,
    lex,
)


class BadParse(Exception):
    """Signals that the lexeme stream did not match the grammar.

    Parameters
    ----------
    lexeme : Lexeme or None
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
    try:
        lexeme = next(stream)
    except StopIteration:
        raise BadParse(
            None,
            'unexpected end of lexeme stream',
        )

    types = (type_,) + types
    if not isinstance(lexeme, type_):
        raise BadParse(
            lexeme,
            '%s, expected %s' % (
                lexeme.unexpected(),
                (
                    'one of {%r}' % ', '.join(
                        tp.__name__.lower() for tp in types
                    )
                )
                if len(types) > 1 else
                type_.__name__.lower(),
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


def parse_names(stream):
    """Parse a comma delimited list of names.

    Parameters
    ----------
    stream : PeekableIterator[Lexeme]
        The stream of lexeme.

    Returns
    -------
    names : list[str] or None
        The comma delimited list of names or None if '.' is in the list.
    """
    names = [expect(stream, Name).string]

    def parse_more_names(iterable):
        """Append the new names and check for more comma delimited names
        """
        names.append(expect(stream, Name).string)
        accept(stream, {Comma: parse_more_names})

    # parse any extra names
    accept(stream, {Comma: parse_more_names})
    return names


class Query:
    """A query to run against the database.

    Parameters
    ----------
    titles : iterable[str]
        The patterns for the titles of the tracks.
    on : iterable[str]
        The patterns for the albums to select from.
    ordered : bool
        Should the results be ordered by their appearance on this album.
    by : iterable[str]
        The patterns for the artists to select from
    shuffle : bool
        Should the tracks be shuffled?
    and_ : Query or None
        The query to intersect with.
    or_ : Query or None
        The query to union with.
    """
    def __init__(self, titles, on, ordered, by, shuffle, and_, or_):
        self.titles = titles
        self.on = on
        self.ordered = ordered
        self.by = by
        self.shuffle = shuffle
        self.and_ = and_
        self.or_ = or_

    @classmethod
    def parse(cls, stream):
        """Parse a query from a stream of Lexemes.

        A query is of the form:

        .. code-bock::

           Name {, Name}
           [on Name] {, Name} [ordered]
           [by Name] {, Name}
           [shuffle]
           [and Query]
           [or Query]

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
        titles = parse_names(stream)
        on = None
        by = None
        ordered = False
        shuffle = False
        and_ = None
        or_ = None

        def parse_on(stream):
            """Parse an ``on`` clause. If we haven't already added a ``by``,
            check for a ``by`` clause.
            """
            nonlocal on

            on = parse_names(stream)

            def parse_ordered(stream):
                nonlocal ordered
                ordered = True

            accept(stream, {Ordered: parse_ordered})

            if by is None:
                accept(stream, {By: parse_by})

        def parse_by(stream):
            """Parse a ``by`` clause. If we haven't already added an ``on``,
            check for a ``on`` clause.
            """
            nonlocal by
            by = parse_names(stream)
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

        return cls(titles, on, ordered, by, shuffle, and_, or_)


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
            # we have more tokens in the stream after the full parse, it must
            # not be an ``And`` or ``Or`` or we wouldn't have gotten here
            expect(stream, And, Or)
            raise AssertionError('Query should have consumed an and or or')
    except BadParse as e:
        raise ValueError(
            'parse error%s: %s%s%s' % (
                (' at %d' % e.lexeme.col_offset)
                if e.lexeme is not None else
                '',
                e.msg,
                ('\n' + source) if source else '',
                '\n%s^' % (' ' * e.lexeme.col_offset)
                if e.lexeme is not None else
                '',
            ),
        )

    return query
