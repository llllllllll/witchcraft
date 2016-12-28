witchcraft
==========

Local music directory management utilities.

Purpose
-------

To make it easier to manage the storage and playback of tracks and albums that I
have purchased from various online retailers.

By making it easier to manage my local music library I will be more likely to
purchase music and support the artists that make the music I love.

Implemented
-----------

- metadata database
- ingest a single file
- unpack and ingest bandcamp zipfiles
- primitive query language support


Witchcraft Query Language
-------------------------

I really want to add a bunch of features but right now queries are of the form:

.. code-block::

   <name> [on <album>] [by <artist>]

- ``<name>`` is interpreted as a substring search on the result set. The special
  form ``.`` is like ``select *``; however, ``*`` is not used because I don't
  want to escape queries.
- ``on <album>`` filters the result set based on the album name.
- ``by <artist>`` filters the result set based on the artist name.

TODO
----

- better compiler / querying features
  - sorted
  - unions
- provide overrides for more metadata in the ``ingest`` entry point.
- add more unpackers for different vendors.

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
