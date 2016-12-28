import re

from .lexer import (
    By,
    Name,
    On,
    lex,
)


query_form = re.compile(
    '({Name})'
    '(({By}{Name})({On}{Name})'
    '|({On}{Name})({By}{Name})'
    '|({On}{Name})'
    '|({By}{Name})'
    '|)'.format(
        Name=Name.code,
        By=By.code,
        On=On.code,
    ),
)


class Query:
    def __init__(self, match, lexemes):
        if match is None:
            raise ValueError('bad parse')

        groups = match.groups()
        lexemes = iter(lexemes)

        self.name = next(lexemes).string

        def nextname():
            next(lexemes)
            return next(lexemes).string

        if groups[2] is not None and groups[3] is not None:
            self.by = nextname()
            self.on = nextname()
        elif groups[4] is not None and groups[5] is not None:
            self.on = nextname()
            self.by = nextname()
        elif groups[6] is not None:
            self.on = nextname()
            self.by = None
        elif groups[7] is not None:
            self.by = nextname()
            self.on = None
        else:
            self.on = None
            self.by = None


def parse(source):
    lexemes = list(lex(source))
    qs = []
    while lexemes:
        match = query_form.match(''.join(lexeme.code for lexeme in lexemes))
        if match is None:
            col_offset = lexemes[0].col_offset
            raise ValueError(
                'parse error at %.2d:\n%s\n%s^' % (
                    col_offset,
                    source,
                    ' ' * col_offset,
                ),
            )
        consumed = match.end()
        qs.append(Query(match, lexemes[:consumed]))
        lexemes = lexemes[consumed:]

    return qs
