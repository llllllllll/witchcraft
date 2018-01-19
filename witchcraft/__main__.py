import os

import click

_version_msg = """\
witchcraft {version}
Copyright (C) 2016 Joe Jevnik
License GPLv2+: GNU GPL version 2 or later <http://gnu.org/licenses/gpl.html>
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law."""


@click.group()
@click.option(
    '--music-home',
    default=os.path.expanduser('~/.witchcraft'),
    envvar='WITCHCRAFT_MUSIC_HOME',
    type=click.Path(file_okay=False, writable=True, resolve_path=True),
    help='The top level directory where music is stored',
)
@click.option(
    '--db-name',
    default='.metadata.db',
    envvar='WITCHCRAFT_DB_NAME',
    type=str,
    help='The name of the metatadata database relative to the music home',
)
@click.option(
    '--verbose/--quiet',
    default=True,
    help='Print additional information while running?',
)
@click.pass_context
def main(ctx, music_home, db_name, verbose):
    """Utilities for managing the storage of songs and albums.
    """
    os.makedirs(music_home, exist_ok=True)
    ctx.obj = {
        'music_home': music_home,
        'db_name': db_name,
        'verbose': verbose,
    }


def _connect_db(ctx):
    import sqlalchemy as sa

    from witchcraft.schema import check_version, db_version, create_schema

    path = os.path.join(ctx.obj['music_home'], ctx.obj['db_name'])
    eng = sa.create_engine('sqlite:///' + path)
    if not os.path.exists(path):
        create_schema(eng)

    version = check_version(eng)
    if version is not None:
        ctx.fail(
            'invalid version, witchraft=%s, db=%s' % (
                db_version,
                version,
            ),
        )
    return eng.connect()


@main.command()
def version():
    """Print version, copyright, and license information.
    """
    from witchcraft import __version__

    click.echo(_version_msg.format(version=__version__))


@main.command()
@click.argument('query', nargs=-1)
@click.pass_context
def play(ctx, query):
    """Execute a witchcraft query and launch mpv with the results.
    """
    from witchcraft.play import play

    try:
        play(
            ctx.obj['music_home'],
            _connect_db(ctx),
            ' '.join(query),
        )
    except ValueError as e:
        ctx.fail(str(e))


@main.command()
@click.argument('query', nargs=-1)
@click.pass_context
def select(ctx, query):
    """Execute a witchcraft query and print the paths to all tracks that match
    the query.
    """
    from witchcraft.play import select

    try:
        paths = select(
            ctx.obj['music_home'],
            _connect_db(ctx),
            ' '.join(query),
        )
    except ValueError as e:
        ctx.fail(str(e))

    for path in paths:
        print(path)


@main.command(context_settings={
    'ignore_unknown_options': True,
    'allow_interspersed_args': False,
})
@click.argument('query', nargs=-1, type=click.UNPROCESSED)
@click.pass_context
def completions(ctx, query):
    """Generate completion suggestions for a potentially unfinished query.
    """
    if not query:
        completions = main.commands.keys()
    elif query[0] in ('play', 'select'):
        from witchcraft.ql import completions as get_completions
        try:
            completions = get_completions(
                _connect_db(ctx),
                ' '.join(query[1:]),
            )
        except ValueError as e:
            ctx.fail(str(e))
    elif len(query) == 1:
        last_part = query[-1]
        if last_part.startswith('-'):
            completions = [
                opt for param in main.params for opt in param.opts
                if opt.startswith(last_part)
            ]
        else:
            completions = [
                k for k in main.commands.keys() if k.startswith(last_part)
            ]
    else:
        last_part = query[-1]
        if last_part.startswith('-'):
            command = main.commands[query[0]]
            completions = [
                opt for param in command.params for opt in param.opts
                if opt.startswith(last_part)
            ]
        else:
            completions = []

    for completion in sorted(completions):
        print(completion)


@main.command('unpack-album')
@click.argument(
    'paths',
    type=click.Path(exists=True, dir_okay=False, writable=True),
    nargs=-1,  # beatport makes you download each song as a different file
)
@click.option(
    '-s',
    '--source',
    required=True,
    type=click.Choice(['bandcamp', 'amazon']),
    help='Where did you buy the album from?',
)
@click.option(
    '--album',
    default=None,
    type=str,
    help='The name of the album. For some sources this can be inferred.'
)
@click.option(
    '--artist',
    default=None,
    type=str,
    help='The name of the artist. For some sources this can be inferred.'
    ' Multiple artists may be passed comma delimited.',
)
@click.pass_context
def unpack_album(ctx, paths, source, album, artist):
    """Unpack an album and store it in canonical form.
    """
    from witchcraft.unpack import unpack

    try:
        with _connect_db(ctx) as conn:
            unpack(
                source,
                ctx.obj['music_home'],
                conn,
                album,
                artist,
                paths,
                verbose=ctx.obj['verbose'],
            )
    except ValueError as e:
        ctx.fail(str(e))


@main.command()
@click.argument(
    'path',
    nargs=-1,
    type=click.Path(file_okay=True, dir_okay=True, resolve_path=True),
)
@click.option(
    '--album',
    default=None,
    type=str,
    help='The name of the album. If not provided this will be read out of the'
    " file's tags.",
)
@click.option(
    '--artist',
    default=None,
    type=str,
    help='The name of the artist. If not provided this will be read out of the'
    " file's tags. Multiple artists may be passed comma delimited.",
)
@click.option(
    '--title',
    default=None,
    type=str,
    help='The title of the track. If not provided this will be read out of the'
    " file's tags. This may not be passed when ingesting a directory.",
)
@click.option(
    '--ignore-failures/--no-ignore-failures',
    default=True,
    help='Ignore files that fail to parse.',
)
@click.pass_context
def ingest(ctx, path, album, artist, title, ignore_failures):
    """Ingest a file or director into the witchcraft database.
    """
    paths = path
    for path in paths:
        if os.path.isdir(path):
            from witchcraft.ingest import ingest_recursive

            if title is not None:
                ctx.fail('cannot pass --title when ingesting a single file')

            def ingest(**kwargs):
                del kwargs['title']
                ingest_recursive(**kwargs)

        else:
            from witchcraft.ingest import ingest_file as ingest

        try:
            with _connect_db(ctx) as conn:
                ingest(
                    music_home=ctx.obj['music_home'],
                    conn=conn,
                    path=path,
                    artists=artist if artist is None else artist.split(','),
                    album=album,
                    title=title,
                    verbose=ctx.obj['verbose'],
                    ignore_failures=ignore_failures,
                )
        except ValueError as e:
            ctx.fail(str(e))


if __name__ == '__main__':
    main()
