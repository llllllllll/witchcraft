import os
import re
from tempfile import TemporaryDirectory

import click

from .ingest import ingest_file, ensure_album_dir

@object.__new__
class unpack:
    """The album unpacker dispatcher.
    """
    _map = {}

    def register(self, source, *, infer_album, infer_artist):
        def _(f):
            self._map[source] = f, infer_album, infer_artist
            return f
        return _

    def __call__(self,
                 source,
                 music_home,
                 conn,
                 album,
                 artist,
                 paths,
                 verbose):
        """Unpack an album.

        Parameters
        ----------
        source : str
            Where did this album come from?
        music_home : str
            The absolute path to the music home directory.
        conn : sa.Connection
            The connection to the metadata db.
        album : str or None
            The album name or None if it should be inferred.
        artist : str or None
            The artist name or None if it should be inferred.
        paths : list[str]
            The paths that make up this album.
        verbose : bool
            Print information about the status of the job.

        Raises
        ------
        ValueError
            Raised when the source has not been registered.
            Raised when album or artist is None and the source cannot infer
            this information.
        """
        try:
            f, infer_album, infer_artist = self._map[source]
        except KeyError:
            raise ValueError('unknown source: %r' % source)
        if album is None and not infer_album:
            raise ValueError(
                'cannot infer album name for %r sourced paths' % source,
            )
        if artist is None and not infer_artist:
            raise ValueError(
                'cannot infer artist name for %r sourced paths' % source,
            )
        return f(music_home, conn, album, artist, paths, verbose)


@unpack.register('bandcamp', infer_album=True, infer_artist=True)
def _unpack_bandcamp(music_home, conn, album, artist, paths, verbose):
    """Unpacker for bandcamp zipfiles.

    This can only infer the artist or album name if the file is in the form:
    ``'{artist} - {album}.zip'`` which is how it comes from bandcamp.
    """
    from zipfile import ZipFile

    if not paths:
        if verbose:
            click.echo('no albums to unpack')
        return

    try:
        path, = paths
    except ValueError:
        raise ValueError('bandcamp source expects exactly one file')

    if album is None or artist is None:
        filename = os.path.basename(os.path.splitext(path)[0])
        match = re.match(r'(.*) - (.*)', filename)
        if match is None:
            raise ValueError(
                'failed to infer artist or album name from file path %r' %
                path,
            )
        album = album if album is not None else match.group(2)
        artist = artist if artist is not None else match.group(1)

    with ZipFile(path) as zf, TemporaryDirectory() as tmpdir:
        for archivename in zf.namelist():
            if archivename == 'cover.jpg':
                path = os.path.join(
                    ensure_album_dir(music_home, album, artist),
                    archivename,
                )
                with open(path, 'wb') as f:
                    f.writelines(zf.open(archivename).readlines())
                continue

            ingest_file(
                music_home=music_home,
                conn=conn,
                path=zf.extract(archivename, path=tmpdir),
                verbose=verbose,
            )
