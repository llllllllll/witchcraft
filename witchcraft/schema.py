from functools import partial

import sqlalchemy as sa

db_version = 0


metadata = sa.MetaData()

version = sa.Table(
    'version',
    metadata,
    sa.Column('version', sa.Integer, primary_key=True),
)


def check_version(conn):
    """Check the db schema version.

    Parameters
    ----------
    conn : sa.Connection
        The connection to check the schema of.

    Returns
    -------
    incorrect_version : int or None
        The version in the database if it is not correct, otherwise None.
    """
    actual_version = conn.scalar(sa.select((version.c.version,)))
    return actual_version if actual_version != db_version else None

tracks = sa.Table(
    'tracks',
    metadata,
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('title', sa.String, nullable=False),
    sa.Column('path', sa.String, nullable=False),
)

albums = sa.Table(
    'albums',
    metadata,
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('title', sa.String, nullable=False)
)

artists = sa.Table(
    'artists',
    metadata,
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('name', sa.String, unique=True),
)

genres = sa.Table(
    'genres',
    metadata,
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('genre', sa.String, unique=True, nullable=False),
)

labels = sa.Table(
    'labels',
    metadata,
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('label', sa.String, unique=True, nullable=False),
)

album_contents = sa.Table(
    'album_contents',
    metadata,
    sa.Column('album_id', sa.ForeignKey(albums.c.id)),
    sa.Column('track_id', sa.ForeignKey(tracks.c.id)),
    sa.Column('track_number', sa.SmallInteger),
)

track_genres = sa.Table(
    'track_genres',
    metadata,
    sa.Column('track_id', sa.ForeignKey(tracks.c.id)),
    sa.Column('genre_id', sa.ForeignKey(genres.c.id)),
)

track_artists = sa.Table(
    'track_artists',
    metadata,
    sa.Column('track_id', sa.ForeignKey(tracks.c.id)),
    sa.Column('artist_id', sa.ForeignKey(artists.c.id)),
)

track_labels = sa.Table(
    'track_labels',
    metadata,
    sa.Column('track_id', sa.ForeignKey(tracks.c.id)),
    sa.Column('label_id', sa.ForeignKey(labels.c.id)),
)

# International Standard Recording Code
track_isrcs = sa.Table(
    'track_isrc',
    metadata,
    sa.Column('track_id', sa.ForeignKey(tracks.c.id)),
    sa.Column('isrc', sa.String, unique=True),
)

track_bpms = sa.Table(
    'track_bpm',
    metadata,
    sa.Column('track_id', sa.ForeignKey(tracks.c.id)),
    sa.Column('bpm', sa.SmallInteger),
)

track_dates = sa.Table(
    'track_dates',
    metadata,
    sa.Column('track_id', sa.ForeignKey(tracks.c.id)),
    sa.Column('date', sa.DateTime),
)

track_filetypes = sa.Table(
    'track_filetypes',
    metadata,
    sa.Column('track_id', sa.ForeignKey(tracks.c.id), unique=True),
    sa.Column('filetype', sa.String),
)


def _new_id(conn, table):
    return conn.scalar(sa.select(
        (sa.sql.functions.coalesce(sa.sql.functions.max(table.c.id), -1) + 1,)
    ))


def _ensure(name_column, table, conn, name):
    ids = conn.execute(
        sa.select(
            (table.c.id,),
        ).where(table.c[name_column] == name),
    ).fetchall()
    assert len(ids) <= 1, 'too many matching entities'
    if not ids:
        new_id = _new_id(conn, table)
        conn.execute(
            table.insert([{
                'id': new_id,
                name_column: name,
            }]),
        )
    else:
        new_id = ids[0][0]

    return new_id


ensure_artist = partial(_ensure, 'name', artists)
ensure_album = partial(_ensure, 'title', albums)
ensure_genre = partial(_ensure, 'genre', genres)
ensure_label = partial(_ensure, 'label', labels)


def ensure_track(conn,
                 path,
                 album,
                 artists,
                 bpm,
                 date,
                 filetype,
                 genres,
                 isrc,
                 label,
                 title,
                 track_number):
    """Add a new track to the db if it is not already added.

    Returns
    -------
    track_id : int
        The track id number.
    added_new_track : bool
        Was this track just added to the database.
    """
    artist_ids = [ensure_artist(conn, artist) for artist in artists]
    album_id = ensure_album(conn, album)
    # try to see if we think this is in the db already.
    ids = conn.execute(
        sa.select(
            (tracks.c.id,),
        ).select_from(
            tracks.join(
                album_contents,
                album_contents.c.track_id == tracks.c.id,
            ).join(
                track_artists,
                track_artists.c.track_id == tracks.c.id,
            ),
        ).where(
            (tracks.c.title == title) &
            (albums.c.id == album_id) &
            track_artists.c.artist_id.in_(artist_ids)
        ).distinct()
    ).fetchall()
    assert len(ids) <= 1, 'too many matching tracks'
    added_new_track = not ids
    if added_new_track:
        new_id = _new_id(conn, tracks)
        conn.execute(
            tracks.insert([{
                'id': new_id,
                'title': title,
                'path': path,
            }]),
        )
        conn.execute(
            album_contents.insert([{
                'track_id': new_id,
                'album_id': album_id,
                'track_number': track_number,
            }]),
        )
        conn.execute(
            track_genres.insert([
                {'track_id': new_id, 'genre_id': ensure_genre(conn, genre)}
                for genre in genres
            ]),
        )
        conn.execute(
            track_artists.insert([
                {'track_id': new_id, 'artist_id': artist_id}
                for artist_id in artist_ids
            ]),
        )
        if label is not None:
            conn.execute(
                track_labels.insert([{
                    'track_id': new_id,
                    'label_id': ensure_label(conn, label),
                }]),
            )
        if isrc is not None:
            conn.execute(
                track_isrcs.insert([{
                    'track_id': new_id,
                    'isrc': isrc,
                }]),
            )
        if bpm is not None:
            conn.execute(
                track_bpms.insert([{
                    'track_id': new_id,
                    'bpm': bpm,
                }]),
            )
        if date is not None:
            conn.execute(
                track_dates.insert([{
                    'track_id': new_id,
                    'date': date,
                }]),
            )
        if filetype is not None:
            conn.execute(
                track_filetypes.insert([{
                    'track_id': new_id,
                    'filetype': filetype,
                }]),
            )
    else:
        new_id = ids[0][0]

    return new_id, added_new_track


def create_schema(conn):
    """Create the schema with the given connection.

    Parameters
    ----------
    conn : sa.Connection
        The connection to create the schema in.
    """
    metadata.create_all(conn)
    conn.execute(version.insert({'version': db_version}))
