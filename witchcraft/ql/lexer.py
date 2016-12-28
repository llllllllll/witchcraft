import re
from string import capwords


special_chars = frozenset(r'\.^$*+?{}()[]|')


class LexemeMeta(type):
    lexemes = []
    _code_counter = 0

    def __new__(cls, name, bases, dict_):
        if 'pattern' not in dict_:
            raise ValueError('Lexemes need to define a pattern')

        self = super().__new__(cls, name, bases, dict_)
        while chr(cls._code_counter) in special_chars:
            cls._code_counter += 1
        self.code = chr(cls._code_counter)
        cls._code_counter += 1

        if dict_['pattern'] is not None:
            cls.lexemes.append(self)

        return self


class Lexeme(metaclass=LexemeMeta):
    pattern = None

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
    pattern = None

    @classmethod
    def from_keyword(cls, keyword):
        return type(
            capwords(keyword),
            (cls,),
            {'pattern': re.compile(keyword)},
        )


And = Keyword.from_keyword('and')
Or = Keyword.from_keyword('or')
On = Keyword.from_keyword('on')
By = Keyword.from_keyword('by')


class Name(Lexeme):
    pattern = re.compile(r'[\.a-zA-Z0-0\-]+')


class Invalid(Lexeme):
    pattern = re.compile(r'\S+')


ignore = re.compile(r'\s+')


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
    col_offset = 0

    lexemes = LexemeMeta.lexemes
    while source:
        for lexeme in lexemes:
            match = lexeme.pattern.match(source)
            if match is None:
                continue
            yield lexeme(match.string[slice(*match.span())], col_offset)
            to_consume = match.end()
            col_offset += to_consume
            break
        else:
            match = ignore.match(source)
            assert match is not None, 'invalid lex state'
            to_consume = match.end()
            col_offset += to_consume

        source = source[to_consume:]
