#
# Copyright (C) 2009-2020 the sqlparse authors and contributors
# <see AUTHORS file>
#
# This module is part of python-sqlparse and is released under
# the BSD License: https://opensource.org/licenses/BSD-3-Clause

"""Exceptions used in this package."""


class SQLParseError(Exception):
    """Base class for exceptions in this module."""


class RecursionLimitError(SQLParseError):
    """Raised when recursion or token limits are exceeded during parsing.

    This exception is raised as a protection against DoS attacks when parsing
    extremely complex or deeply nested SQL queries.
    """
