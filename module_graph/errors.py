"""The one exception the package raises for a mistake in what it was given."""


def unreadable(path, e):
    """A ModuleGraphError for a file that could not be read or written."""
    if isinstance(e, FileNotFoundError):
        return ModuleGraphError(f'{path}: no such file')
    if isinstance(e, UnicodeDecodeError):
        return ModuleGraphError(f'{path}: not UTF-8 text')
    return ModuleGraphError(f'{path}: {e.strerror or e}')


class ModuleGraphError(Exception):
    """A document, layout file, filter or template the tool can't use. The
    message says what and where, without the `error: ` the command line
    adds; nothing in the package exits the process itself."""
