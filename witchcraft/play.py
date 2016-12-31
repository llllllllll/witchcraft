import os

from . import ql


def select(conn, query):
    """Exectute a query and return the paths to the tracks to be played.

    Parameters
    ----------
    conn : sa.engine.Connection
        The connection to the metadata database.
    query : string
        The witchcraft ql query to run against the database.

    Return
    ------
    paths : iterable[str]
        The paths to the tracks that match the query.
    """
    select, extra_args = ql.compile(query)
    return [p[0] for p in conn.execute(select).fetchall()]


def play(conn, query):
    """Launch mpv with the results of the query.

    Parameters
    ----------
    conn : sa.engine.Connection
        The connection to the metadata database.
    query : string
        The witchcraft ql query to run against the database.

    Notes
    -----
    This function never returns.
    """
    select, extra_args = ql.compile(query)
    paths = [p[0] for p in conn.execute(select).fetchall()]

    if not paths:
        # nothing to play, mpv doesn't want an empty path list
        return

    os.execvp('mpv', ['mpv', '--no-video'] + extra_args + paths)
