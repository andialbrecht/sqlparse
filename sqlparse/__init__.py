# Copyright (C) 2008 Andi Albrecht, albrecht.andi@gmail.com
#
# This module is part of python-sqlparse and is released under
# the BSD License: http://www.opensource.org/licenses/bsd-license.php.

"""Parse SQL statements."""


__version__ = '0.1.15'


# Setup namespace
from sqlparse import engine
from sqlparse import filters
from sqlparse import formatter

# Deprecated in 0.1.5. Will be removed in 0.2.0
from sqlparse.exceptions import SQLParseError


def parse(sql, encoding=None):
    """Parse sql and return a list of statements.

    :param sql: A string containting one or more SQL statements.
    :param encoding: The encoding of the statement (optional).
    :returns: A tuple of :class:`~sqlparse.sql.Statement` instances.
    """
    return tuple(parsestream(sql, encoding))


def parsestream(stream, encoding=None):
    """Parses sql statements from file-like object.

    :param stream: A file-like object.
    :param encoding: The encoding of the stream contents (optional).
    :returns: A generator of :class:`~sqlparse.sql.Statement` instances.
    """
    stack = engine.FilterStack()
    stack.full_analyze()
    return stack.run(stream, encoding)


def format(sql, **options):
    """Format *sql* according to *options*.

    Available options are documented in :ref:`formatting`.

    In addition to the formatting options this function accepts the
    keyword "encoding" which determines the encoding of the statement.

    :returns: The formatted SQL statement as string.
    """
    encoding = options.pop('encoding', None)
    stack = engine.FilterStack()
    options = formatter.validate_options(options)
    stack = formatter.build_filter_stack(stack, options)
    stack.postprocess.append(filters.SerializerUnicode())
    return ''.join(stack.run(sql, encoding))


def split(sql, encoding=None):
    """Split *sql* into single statements.

    :param sql: A string containting one or more SQL statements.
    :param encoding: The encoding of the statement (optional).
    :returns: A list of strings.
    """
    stack = engine.FilterStack()
    stack.split_statements = True
    return [unicode(stmt).strip() for stmt in stack.run(sql, encoding)]


from sqlparse.engine.filter import StatementFilter


def split2(stream):
    splitter = StatementFilter()
    return list(splitter.process(None, stream))
