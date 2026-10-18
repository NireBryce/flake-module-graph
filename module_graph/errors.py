"""The one exception the package raises for a mistake in what it was given."""


class ModuleGraphError(Exception):
    """A document, layout file, filter or template the tool can't use. The
    message says what and where, without the `error: ` the command line
    adds; nothing in the package exits the process itself."""
