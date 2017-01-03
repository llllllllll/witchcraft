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
    return '%{}%'.format(cs.replace('.', '%'))


def pattern_order(column, patterns):
    """Create a clause suitable for use in an ``order by`` clause which will
    sort results in the order they are matched by the patterns.

    Parameters
    ----------
    column : sa.sql.ColumnClause
        The column being matched against.
    patterns : iterable[str]
        The patterns to search in order.

    Returns
    -------
    sa.sql.ColumnClause
        The clause used in an ``order by`` to enforce the given order.
    """
    return sa.case([
        (column.like(fuzzy(pattern)), n)
        for n, pattern in enumerate(patterns)
    ]).asc()


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

    # play tracks in the order they are matched by the title patterns
    order_by = []

    if query.on is not None and '.' not in query.on:
        # ``on`` clauses turn into a join against the ``albums`` table
        # through the ``album_contents`` table.
        from_obj = from_obj.join(
            album_contents,
            album_contents.c.track_id == tracks.c.id,
        ).join(
            albums,
            album_contents.c.album_id == albums.c.id,

        )
        where = sa.and_(
            where,
            sa.or_(*(
                albums.c.title.like(fuzzy(album)) for album in query.on
            )),
        )

        # order the tracks by the album pattern that matched them
        order_by.append(pattern_order(albums.c.title, query.on))

        if query.ordered:
            order_by.append(album_contents.c.track_number)

    if query.by is not None and '.' not in query.by:
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
            sa.or_(*(
                artists.c.name.like(fuzzy(artist)) for artist in query.by
            )),
        )

        # order the tracks by the artist pattern that matched them
        order_by.append(pattern_order(artists.c.name, query.by))

    # The title names get converted into filters against the title of the
    # track. The special title '.' means match all tracks.
    where = sa.and_(
        where,
        sa.or_(*(
            tracks.c.title.like(fuzzy(title))
            for title in query.titles
            if title != '.'
        )),
    )

    order_by.append(pattern_order(tracks.c.title, query.titles))

    select = sa.select((
        tracks.c.path,
    )).select_from(
        from_obj,
    ).where(
        where,
    ).order_by(*order_by)

    # shuffle is implemented in mpv so forward this argument along.
    extra_args = ['--shuffle'] if query.shuffle else []

    # ``and_`` and ``or_`` clauses add their extra_args to the ``extra_args``.
    # This may not totally be correct with unioning queries but we can deal
    # with that later.
    if query.and_:
        and_, new_extras = compile_query(query.and_)
        extra_args.extend(new_extras)
        select = select.alias().select().intersect(and_.alias().select())
    if query.or_:
        or_, new_extras = compile_query(query.or_)
        extra_args.extend(new_extras)
        select = select.alias().select().union(or_.alias().select())

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
