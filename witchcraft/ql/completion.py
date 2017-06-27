import sqlalchemy as sa

from .lexer import Keyword
from .parser import CompletionClass, completion_class
from ..schema import (
    albums,
    artists,
    tracks,
)


_completers = {}


def register_completer(cls):
    def dec(f):
        _completers[cls] = f
        return f
    return dec


@register_completer(CompletionClass.keyword)
def complete_keyword(engine, lexeme):
    if lexeme is None:
        prefix = ''
    else:
        prefix = lexeme.string

    return [kw for kw in Keyword.keywords if kw.startswith(prefix)]


def _complete_sql(column, engine, lexeme):
    sel = sa.select([column])
    if lexeme is not None:
        sel = sel.where(column.like('%s%%' % lexeme.string))

    return [c for c, in engine.execute(sel).fetchall()]


@register_completer(CompletionClass.title)
def complete_title(engine, lexeme):
    return _complete_sql(tracks.c.title, engine, lexeme)


@register_completer(CompletionClass.artist)
def complete_artist(engine, lexeme):
    return _complete_sql(artists.c.name, engine, lexeme)


@register_completer(CompletionClass.album)
def complete_album(engine, lexeme):
    return _complete_sql(albums.c.title, engine, lexeme)


def completions(engine, source):
    """Generate a list of completions for the given partial query.

    Parameters
    ----------
    engine : sa.engine.Engine
    source : str
        The query to complete

    Returns
    -------
    completions : list[str]
        The potential completions.
    """
    cls, lexeme = completion_class(source)
    return _completers[cls](engine, lexeme)
