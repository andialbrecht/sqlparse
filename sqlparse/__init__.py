# Copyright (C) 2008 Andi Albrecht, albrecht.andi@gmail.com
#
# This module is part of python-sqlparse and is released under
# the BSD License: http://www.opensource.org/licenses/bsd-license.php.

"""Parse SQL statements."""


__version__ = '0.1.4'


class SQLParseError(Exception):
    """Base class for exceptions in this module."""


# Setup namespace
from sqlparse import engine
from sqlparse import filters
from sqlparse import formatter


def parse(sql):
    """Parse sql and return a list of statements.

    *sql* is a single string containting one or more SQL statements.

    Returns a tuple of :class:`~sqlparse.sql.Statement` instances.
    """
    stack = engine.FilterStack()
    stack.full_analyze()
    return tuple(stack.run(sql))


def parsestream(stream):
    """Pares sql statements from file-like object.

    Returns a generator of Statement instances.
    """
    stack = engine.FilterStack()
    stack.full_analyze()
    return stack.run(stream)


def format(sql, **options):
    """Format *sql* according to *options*.

    Available options are documented in :ref:`formatting`.

    Returns the formatted SQL statement as string.
    """
    stack = engine.FilterStack()
    options = formatter.validate_options(options)
    stack = formatter.build_filter_stack(stack, options)
    stack.postprocess.append(filters.SerializerUnicode())
    return ''.join(stack.run(sql))


def split(sql):
    """Split *sql* into single statements.

    Returns a list of strings.
    """
    stack = engine.FilterStack()
    stack.split_statements = True
    return [unicode(stmt) for stmt in stack.run(sql)]

from sqlparse.engine.filter import StatementFilter
def split2(stream):
    splitter = StatementFilter()
    return list(splitter.process(None, stream))
