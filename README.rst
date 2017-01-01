witchcraft
==========

Local music directory management utilities.

Purpose
-------

To make it easier to manage the storage and playback of tracks and albums that I
have purchased from various online retailers.

By making it easier to manage my local music library I will be more likely to
purchase music and support the artists that make the music I love.

Design
------

Witchcraft is split into two parts:

1. ingestion and management of audio files and metadata
2. querying for playback


Ingestion
~~~~~~~~~

Witchcraft manages the storage and metadata for all of your tracks. Witchcraft
provides tools for loading tracks into the database and extracting or adding
metadata to a track.

Right now there are a couple of ways to add data to the witchcraft db:

- ``$ witchcraft ingest``: Load a file or directory into the witchcraft db.
  If a directory is given, it will be recursively walked looking for audio
  files. By default, this will read the metadata out of the file to populate the
  database; however, because many vendors do not properly tag their files, you
  may explicitly pass this information on the command line.
- ``$ witchcraft unpack-album``: Unpack and ingest an album in the form that is
  was provided by some music vendor. Right now this only supports reading the
  zipfiles provided by `bandcamp <https://bandcamp.com/>`_, but we plan to support other
  vendors.


Querying for Playback
---------------------

Why store metadata about tracks if you don't want to use it?

Witchcraft comes with a query language designed for reading the witchcraft db to
quickly select tracks to listen to. The goal is to describe the music you want
to hear with some query and let witchcraft find all of the tracks that match the
criteria. The queries can look for specific artists, albums, track names, or
more.


Witchcraft Query Language
-------------------------

Witchcraft queries allow you to quickly search your music library for tracks
that match some given criteria. The query language has explicitly been designed
to be easy to type on the command line **without** escaping anything.

The witchcraft query language uses queries of the form:

.. code-block::

   $ witchcraft [play|select]
                <title>{, <title>}
                [on <album>]{, <album>} [ordered]
                [by <artist>]{, <artist>}
                [shuffle]
                [and <query>
                [or <query>]

- ``$witchcraft play`` will launch ``mpv`` with the tracks that match the query.
- ``$witchcraft select`` will print the paths to the tracks that match the
  query.
- ``<title>`` filters the result set based on the title of the track. The
  special title ``.`` means select all tracks. Tracks will be sorted in the
  order they are matched by the given title patterns.
- ``on <album>`` filters the result set based on the album name. Tracks will be
  sorted in the order they are matched by the album patterns.
- ``ordered`` plays tracks in the order they appear on the the matched albums.
- ``by <artist>`` filters the result set based on the artist name. Tracks will
  be sorted in the order they are matched by the artist patterns.
- ``shuffle`` marks that the tracks should be played in random order.
- ``and <query`` intersects the results of this query with another query.
- ``or <query`` unions the results of this query with another query.


Note: The keywords ``on``, ``by``, ``shuffle``, ``and``, and ``or`` cannot be
used as a title, album, or artist. These can be escaped with a ``:`` like:

.. code-block::

   $ witchcraft play :on by :shuffle

This will play the track titled ``on`` by the artist ``shuffle``.

TODO
----

ingestion
~~~~~~~~~

- add key metadata field
- provide overrides for more metadata in the ``ingest`` entry point.
- add more unpackers for different vendors.
- add migration utility for the witchcraft db

witchcraft ql
~~~~~~~~~~~~~

- query for more metadata types like genre, bpm, or key.

Name
----

The name is from the track Witchcraft on the Shinigami EP by Sorrow. No real
reason, just love that song and the name seemed to fit the idea of a query
language for music.

License
-------

``witchcraft`` is free software, available under the terms of the `GNU General
Public License, version 3 or later <http://gnu.org/licenses/gpl.html>`_. For
more information, see ``LICENSE``.
