import sqlalchemy as sa

from .parser import parse
from ..schema import (
    album_contents,
    albums,
    artists,
    track_artists,
    tracks,
)


def fuzzy(cs):
    """Make a string fuzzy in sql. This is so that querying for a subset of
    a name finds the full result.
    """
    return '%{}%'.format(cs)


def compile_query(query):
    """"Compile a Query object into sql and flags to ``mpv``.

    Parameters
    ----------
    query : Query
        The query to compile.

    Returns
    -------
    select : sa.sql.Select
        The select to execute which will return the paths to the tracks
        selected by the query.
    extra_args : list[str]
        The extra arguments to pass to ``mpv``.
    """
    from_obj = tracks
    where = True

    if query.on is not None:
        # ``on`` clauses turn into a join against the ``albums`` table
        # through the ``album_contents`` table.
        from_obj = from_obj.join(
            albums,
        ).join(
            album_contents,
            album_contents.c.track_id == tracks.id,
        )
        where = sa.and_(
            where,
            albums.c.title.like(fuzzy(query.on)),
        )

    if query.by is not None:
        # ``by`` clauses turn into a join against the ``artists`` table
        # through the ``track_artists`` table. An on clause will match
        # tracks even if the author is not the sole author.
        from_obj = from_obj.join(
            track_artists,
            track_artists.c.track_id == tracks.c.id,
        ).join(
            artists,
            track_artists.c.artist_id == artists.c.id,
        )
        where = sa.and_(
            where,
            artists.c.name.like(fuzzy(query.by)),
        )

    # The title names get converted into filters against the title of the
    # track. The special title '.' means match all tracks.
    where = sa.and_(
        where,
        sa.or_(*(
            True if title == '.' else tracks.c.title.like(fuzzy(title))
            for title in query.titles
        )),
    )

    select = sa.select((
        tracks.c.path,
    )).select_from(
        from_obj,
    ).where(
        where,
    )

    # shuffle is implemented in mpv so forward this argument along.
    extra_args = ['--shuffle'] if query.shuffle else []

    # ``and_`` and ``or_`` clauses add their extra_args to the ``extra_args``.
    # This may not totally be correct with unioning queries but we can deal
    # with that later.
    if query.and_:
        and_, new_extras = compile_query(query.and_)
        extra_args.extend(new_extras)
        select = select.intersect(and_)
    if query.or_:
        or_, new_extras = compile_query(query.or_)
        extra_args.extend(new_extras)
        select = select.union(or_)

    return select, extra_args


def compile(source):
    """Compile a witchcraft ql query into sql and flags to ``mpv``.

    Parameters
    ----------
    source : str
        The query to compile.

    Returns
    -------
    select : sa.sql.Select
        The select to execute which will return the paths to the tracks
        selected by the query.
    extra_args : list[str]
        The extra arguments to pass to ``mpv``.

    """
    return compile_query(parse(source))
