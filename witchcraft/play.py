import os

from . import ql


def play(conn, query):
    paths = [p[0] for p in conn.execute(ql.compile(query)).fetchall()]

    if not paths:
        # nothing to play, mpv doesn't want an empty path list
        return

    os.execvp('mpv', ['mpv', '--no-video'] + paths)
