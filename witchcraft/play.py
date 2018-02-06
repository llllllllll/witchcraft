import os

from . import ql


def _select_with_args(music_home, conn, query):
    """Exectute a query and return the paths to the tracks to be played.

    Parameters
    ----------
    music_home : str
        The root directory for witchcraft music.
    conn : sa.engine.Connection
        The connection to the metadata database.
    query : string
        The witchcraft ql query to run against the database.

    Return
    ------
    paths : iterable[str]
        The paths to the tracks that match the query.
    """
    return [
        os.path.join(music_home, p[0])
        for select in ql.compile(query)
        for p in conn.execute(select).fetchall()
    ]


def select(music_home, conn, query):
    """Exectute a query and return the paths to the tracks to be played.

    Parameters
    ----------
    music_home : str
        The root directory for witchcraft music.
    conn : sa.engine.Connection
        The connection to the metadata database.
    query : string
        The witchcraft ql query to run against the database.

    Return
    ------
    paths : iterable[str]
        The paths to the tracks that match the query.
    """
    return _select_with_args(music_home, conn, query)


def play(music_home, conn, query):
    """Launch mpv with the results of the query.

    Parameters
    ----------
    music_home : str
        The root directory for witchcraft music.
    conn : sa.engine.Connection
        The connection to the metadata database.
    query : string
        The witchcraft ql query to run against the database.

    Notes
    -----
    This function never returns.
    """
    paths = list(_select_with_args(music_home, conn, query))

    if not paths:
        # nothing to play, mpv doesn't want an empty path list
        return

    os.execvp('mpv', ['mpv', '--no-video'] + paths)
