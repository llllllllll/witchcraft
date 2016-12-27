from itertools import chain
import os
import shutil

import click
import dateutil.parser
import taglib

from . import schema
from .utils import (
    normalize,
    normalize_genre,
    normalize_track_number,
    normalize_artist,
)


def log_writing_file(verbose, path, track_id):
    if verbose:
        click.echo('writing track id %.2d: %r' % (track_id, path))


def log_skipping_write(verbose, path, track_id):
    if verbose:
        click.echo(
            'not copying %r because it is already in the db as track %.2d' % (
                path,
                track_id,
            ),
        )


def _exactly_one_tag(tags, key, *, optional, normalize=normalize):
    if optional:
        values = tags.get(key)
    else:
        try:
            values = tags[key]
        except KeyError:
            raise KeyError('file tags missing required key %r' % key)

    if values is None:
        return None

    if len(values) != 1:
        raise ValueError(
            'track may only have one %s, got: %r' % (key.lower(), values),
        )
    return normalize(values[0])


def _album_dir(music_home, album, artist):
    """The path where this album will be stored.

    Parameters
    ----------
    music_home : str
        The root directory for witchcraft.
    album : str
        The name of the album.
    artist : str
        The name of the primary (first) artist on the album.

    Returns
    -------
    album_dir_path : str
        The path to directory to store tracks for this album.
    """
    return os.path.join(music_home, normalize(artist), normalize(album))


def ensure_album_dir(music_home, album, artist):
    """Make sure the directory for the given album has been created.

    Parameters
    ----------
    music_home : str
        The root directory for witchcraft.
    album : str
        The name of the album.
    artist : str
        The name of the primary (first) artist on the album.

    Returns
    -------
    album_dir_path : str
        The path to directory to store tracks for this album.
    """
    d = _album_dir(music_home, album, artist)
    os.makedirs(d, exist_ok=True)
    return d


def _inner_ingest_file(music_home,
                       conn,
                       path,
                       album,
                       artists,
                       title,
                       verbose):
    """Helper for ``ignore_failures``.

    See Also
    --------
    ingest_file
    """
    tags = taglib.File(path).tags

    if album is None:
        album = _exactly_one_tag(tags, 'ALBUM', optional=False)
    if artists is None:
        artists = list(chain.from_iterable(map(
            normalize_artist, tags['ARTIST'],
        )))
    if title is None:
        title = _exactly_one_tag(tags, 'TITLE', optional=False)

    track_number = _exactly_one_tag(
        tags,
        'TRACKNUMBER',
        optional=True,
        normalize=normalize_track_number,
    )

    new_path = '%s%s' % (
        os.path.join(
            ensure_album_dir(music_home, album, artists[0]),
            '%.2d-%s' % (track_number, title),
        ),
        os.path.splitext(path)[1],
    )

    track_id, added_new_track = schema.ensure_track(
        conn=conn,
        path=new_path,
        album=album,
        artists=artists,
        bpm=_exactly_one_tag(tags, 'BPM', optional=True, normalize=int),
        date=_exactly_one_tag(
            tags,
            'DATE',
            optional=True,
            normalize=dateutil.parser.parse,
        ),
        filetype=_exactly_one_tag(tags, 'FILETYPE', optional=True),
        genres=list(map(normalize_genre, tags.get('GENRES', []))),
        isrc=_exactly_one_tag(tags, 'ISRC', optional=True),
        label=_exactly_one_tag(tags, 'LABEL', optional=True),
        title=title,
        track_number=track_number,
    )
    if added_new_track:
        log_writing_file(verbose, new_path, track_id)
        shutil.copy(path, new_path)

    else:
        log_skipping_write(verbose, path, track_id)


def ingest_file(music_home,
                conn,
                path,
                album=None,
                artists=None,
                title=None,
                *,
                verbose,
                ignore_failures):
    """Ignest a file into the witchcraft database.

    Parameters
    ----------
    music_home : str
        The root directory for witchcraft music.
    conn : sa.Connection
        The connection to the metadata db.
    path : str
        The path to ingest
    album : str, optional
        The album name to use. If not provided, this will be read from the
        file's tags.
    artists : str, optional
        The list of artists to use. If not provided, this will be read from the
        file's tags.
    title : str, optional
        The track's title. If not provided, this will be read from the file's
        tags.
    verbose : bool
        Should extra information be printed
    ignore_failures : bool
        Should failures be ignored? If verbose, these will be logged.
    """
    try:
        _inner_ingest_file(
            music_home,
            conn,
            path,
            album,
            artists,
            title,
            verbose,
        )
    except Exception as e:
        if not ignore_failures:
            raise
        if verbose:
            click.echo('failed to load %r: %s, continuing' % (path, e))


def ingest_recursive(music_home,
                     conn,
                     path,
                     album=None,
                     artists=None,
                     *,
                     verbose,
                     ignore_failures):
    """Recursivly travel a directory and ingest all taggable files.

    Parameters
    ----------
    music_home : str
        The root directory for witchcraft music.
    conn : sa.Connection
        The connection to the metadata db.
    path : str
        The path to traverse.
    album : str, optional
        The album name to use. If not provided, this will be read from the
        file's tags.
    artists : str, optional
        The list of artists to use. If not provided, this will be read from the
        file's tags.
    verbose : bool
        Should extra information be printed?
    ignore_failures : bool
        Should failures be ignored? If verbose, these will be logged.
    """
    for direntry in os.scandir(path):
        if direntry.is_dir():
            ingest_recursive(
                music_home,
                conn,
                direntry.path,
                album=album,
                artists=artists,
                verbose=verbose,
                ignore_failures=ignore_failures,
            )
        try:
            taglib.File(direntry.path)
        except OSError:
            continue

        ingest_file(
            music_home,
            conn,
            direntry.path,
            album=album,
            artists=artists,
            verbose=verbose,
            ignore_failures=ignore_failures,
        )
