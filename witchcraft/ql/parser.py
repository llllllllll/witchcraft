from itertools import chain

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


class _QueryParser:
    """State manager for parsing a query. Users should consume this through
    :meth:`.Query.parse`.

    Parameters
    ----------
    stream : PeekableIterator[Lexeme]
        The stream of lexemes to parse.
    """
    def __init__(self, stream):
        self.stream = stream
        self.skipped_lexeme_types = set()

    @property
    def have_more(self):
        return bool(self.stream.peek())

    def expect(self, type_, *types):
        """Pull the next lexeme out of the stream and assert that it is of one
        of the expected types.

        Parameters
        ----------
        *types
            The types to expect. This cannot be empty.

        Returns
        -------
        lexeme : Lexeme
            The next lexeme in the stream if it is of one of the valid types.

        Raises
        ------
        BadParse
            Raised when the next lexeme in the stream is not one of the
            expected types.
        """
        try:
            lexeme = next(self.stream)
        except StopIteration:
            raise BadParse(
                None,
                'unexpected end of lexeme stream',
            )

        types = (type_,) + types
        if not isinstance(lexeme, type_):
            skipped_lexeme_types = self.skipped_lexeme_types.copy()
            self.skipped_lexeme_types.clear()
            multiple_types = len(types) > 1
            raise BadParse(
                lexeme,
                '%s:%sexpected %s' % (
                    lexeme.unexpected(),
                    '\n' if multiple_types else ' ',
                    (
                        'one of {%s}' % ', '.join(sorted(
                            repr(tp.__name__.lower())
                            for tp in set(chain(types, skipped_lexeme_types))
                        ))
                    )
                    if multiple_types else
                    type_.__name__.lower(),
                ),
            )
        return lexeme

    def accept(self, handlers):
        """Peek at the next iterable in the stream and call an optional function
        on the stream if it matches.

        Parameters
        ----------
        handler : dict[type, callable[None]]
            A mapping from Lexeme types to a handler function to call if the
            next lexeme is of the given type. If the next lexeme is not
            handled, it will not be consumed from the stream.
        """
        stream = self.stream
        next_ = stream.peek()
        if not next_:
            return

        try:
            f = handlers[type(next_[0])]
        except KeyError:
            self.skipped_lexeme_types |= handlers.keys()
        else:
            next(stream)
            f()

    def parse_names(self):
        """Parse a comma delimited list of names.

        Returns
        -------
        names : list[str] or None
            The comma delimited list of names or None if '.' is in the list.
        """
        names = [self.expect(Name).string]

        def parse_more_names():
            """Append the new names and check for more comma delimited names
            """
            names.append(self.expect(Name).string)
            self.accept({Comma: parse_more_names})

        # parse any extra names
        self.accept({Comma: parse_more_names})
        return names

    def parse(self):
        titles = self.parse_names()
        on = None
        by = None
        ordered = False
        shuffle = False
        and_ = None
        or_ = None

        def parse_on():
            """Parse an ``on`` clause. If we haven't already added a ``by``,
            check for a ``by`` clause.
            """
            nonlocal on

            on = self.parse_names()

            def parse_ordered():
                nonlocal ordered
                ordered = True

            self.accept({Ordered: parse_ordered})

            if by is None:
                self.accept({By: parse_by})

        def parse_by():
            """Parse a ``by`` clause. If we haven't already added an ``on``,
            check for a ``on`` clause.
            """
            nonlocal by
            by = self.parse_names()
            if on is None:
                self.accept({On: parse_on})

        # parse the ``on`` and ``by`` in any order
        self.accept({On: parse_on, By: parse_by})

        def parse_shuffle():
            """Parse the ``shuffle`` modifier.
            """
            nonlocal shuffle
            shuffle = True

        self.accept({Shuffle: parse_shuffle})

        def parse_and():
            """Parse an ``and`` clause.
            """
            nonlocal and_
            and_ = _QueryParser(self.stream).parse()

        def parse_or():
            """Parse an ``or`` clause.
            """
            nonlocal or_
            or_ = _QueryParser(self.stream).parse()

        # optionally check for an ``and`` or an ``or``
        self.accept({And: parse_and, Or: parse_or})

        return Query(titles, on, ordered, by, shuffle, and_, or_)


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

        Notes
        -----
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
        """
        parser = _QueryParser(stream)
        query = parser.parse()
        if parser.have_more:
            # we have more tokens in the stream after the full parse, it must
            # not be an ``And`` or ``Or`` or we wouldn't have gotten here
            parser.expect(And, Or)
            raise AssertionError('Query should have consumed an and or or')
        return query


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
    try:
        query = Query.parse(PeekableIterator(lex(source)))
    except BadParse as e:
        indicator = '>>> '
        raise ValueError(
            'parse error%s: %s\n%s%s' % (
                (' at column %d' % e.lexeme.col_offset)
                if e.lexeme is not None else
                '',
                e.msg,
                ('\n%s%s' % (indicator, source)) if source else '',
                '\n%s^' % (' ' * (e.lexeme.col_offset + len(indicator)))
                if e.lexeme is not None else
                '',
            ),
        )

    return query
