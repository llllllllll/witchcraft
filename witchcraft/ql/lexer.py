import re
from string import capwords


class LexemeMeta(type):
    """A metaclass for collecting all of the lexeme definitons to build
    the lexer.

    Lexeme patterns will be checked in the order they defined.
    """
    lexeme_types = []

    def __new__(cls, name, bases, dict_):
        if 'pattern' not in dict_:
            raise ValueError('Lexemes need to define a pattern')

        self = super().__new__(cls, name, bases, dict_)
        if dict_['pattern'] is not None:
            cls.lexeme_types.append(self)

        return self


class Lexeme(metaclass=LexemeMeta):
    """A unit which will be paseed to the parser.

    Attributes
    ----------
    pattern : regex
        The regular expression that defines this lexeme.
    startcodes : iterable[any]
        The startcodes where this lexeme can be read.
    begins : any
        The startcode to enter after this lexeme is matched.
    col_offset : int
        The column offset where this lexeme appeared in the source string.
    string : str
        The string matching this lexeme's pattern.
    """
    default_startcode = 'default_startcode'

    pattern = None
    startcodes = default_startcode,
    begins = default_startcode

    def __init__(self, string, col_offset):
        self.col_offset = col_offset
        self.string = string

    def __repr__(self):
        return '{.__name__}({!r}, {})'.format(
            type(self),
            self.string,
            self.col_offset,
        )


class Keyword(Lexeme):
    """A lexeme that matches a fixed string that is otherwise a ``Name``.
    """
    pattern = None

    def __init__(self, string, col_offset):
        super().__init__(string.strip(), col_offset)

    @classmethod
    def from_keyword(cls, keyword):
        return type(
            capwords(keyword),
            (cls,),
            {'pattern': re.compile(keyword + r'(\s|$)')},
        )

    def unexpected(self):
        return 'unexpected %r' % type(self).__name__.lower()


And = Keyword.from_keyword('and')
Or = Keyword.from_keyword('or')
On = Keyword.from_keyword('on')
By = Keyword.from_keyword('by')
Ordered = Keyword.from_keyword('ordered')
Shuffle = Keyword.from_keyword('shuffle')


class Punctuation(Lexeme):
    """A lexeme that matches a fixed string that is not otherwise a ``Name``
    """
    pattern = None

    @classmethod
    def from_symbol(cls, name, symbol):
        return type(
            name,
            (cls,),
            {'pattern': re.compile(symbol)},
        )

Comma = Punctuation.from_symbol('Comma', ',')


class Name(Lexeme):
    """A name lexeme. Names are used to identify things like tracks or artists.

    Notes
    -----
    Keywords are checked first, if you want to use a keyword as a name it can
    be escaped with a colon like ``:on``.
    """
    pattern = re.compile(r':?[\.a-zA-Z0-0\-]+')

    def __init__(self, string, col_offset):
        super().__init__(
            # unescape the string
            string[1:] if string.startswith(':') else string,
            col_offset,
        )

    def unexpected(self):
        return 'unexpected %r: %r' % (type(self).__name__.lower(), self.string)


class Invalid(Lexeme):
    """An invalid token. This will trigger a parse error.
    """
    pattern = re.compile(r'\S+')

    def unexpected(self):
        return 'inavlid lexeme: %r' % self.string


class Ignore(Lexeme):
    """A special lexeme type that represents patterns to be ignored from the
    lexeme stream. Text that matches this pattern will not be yielded from
    :func:`.lex`.
    """
    pattern = re.compile(r'\s+')

    def unexpected(self):
        raise AssertionError('we should never get an Ignore lexeme')


def lex(source):
    """Turn the source of a query into a stream of Lexemes

    Parameters
    ----------
    src : str
        The input string.

    Yields
    ------
    lexeme : Lexeme
        Lexemes from the source input.
    """
    startcode = Lexeme.default_startcode
    col_offset = 0

    lexeme_types = LexemeMeta.lexeme_types
    while source:
        for lexeme_type in lexeme_types:
            if startcode not in lexeme_type.startcodes:
                continue

            match = lexeme_type.pattern.match(source)
            if match is None:
                # check the next lexeme type's pattern
                continue

            lexeme = lexeme_type(
                match.string[slice(*match.span())],
                col_offset,
            )
            if lexeme_type is not Ignore:
                # don't yield the Ignore lexeme
                yield lexeme

            to_consume = match.end()
            col_offset += to_consume
            startcode = lexeme.begins
            break
        else:
            raise ValueError(
                'invalid lexer state, no lexeme matched: %s' % source,
            )

        # advance the pointer into the source
        source = source[to_consume:]
