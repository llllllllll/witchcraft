import sqlalchemy as sa

from .parser import parse
from ..schema import (
    album_contents,
    albums,
    artists,
    track_artists,
    tracks,
)


def compile_query(query):
    from_obj = tracks
    where = True

    if query.on is not None:
        from_obj = from_obj.join(
            albums,
        ).join(
            album_contents,
            album_contents.c.track_id == tracks.id,
        )
        where = sa.and_(
            where,
            albums.c.title.like('%{}%'.format(query.on)),
        )
    if query.by is not None:
        from_obj = from_obj.join(
            track_artists,
            track_artists.c.track_id == tracks.c.id,
        ).join(
            artists,
            track_artists.c.artist_id == artists.c.id,
        )
        where = sa.and_(
            where,
            artists.c.name.like('%{}%'.format(query.by)),
        )

    if query.name is not '.':
        where = sa.and_(
            where,
            tracks.c.title.like('%{}%'.format(query.name)),
        )

    return sa.select((
        tracks.c.path,
    )).select_from(
        from_obj,
    ).where(
        where,
    )


def compile(source):
    queries = parse(source)
    if len(queries) != 1:
        raise ValueError('only one query supported right now')
    return compile_query(queries[0])
