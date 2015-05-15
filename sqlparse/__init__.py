# Copyright (C) 2008 Andi Albrecht, albrecht.andi@gmail.com
#
# This module is part of python-sqlparse and is released under
# the BSD License: http://www.opensource.org/licenses/bsd-license.php.

"""Parse SQL statements."""


__version__ = '0.1.14'


# Setup namespace
from sqlparse import engine
from sqlparse import filters
from sqlparse import formatter
from sqlparse import lexer
from sqlparse import tokens as T
from sqlparse.engine import grouping
from sqlparse.parsers import SQLParser

# Deprecated in 0.1.5. Will be removed in 0.2.0
from sqlparse.exceptions import SQLParseError


def build_parsers():
    parsers = dict()
    for cls in SQLParser.__subclasses__():
        parsers[cls.dialect] = cls()
    return parsers


parsers = build_parsers()


def parse(sql, encoding=None, dialect=None):
    """Parse sql and return a list of statements.

    :param sql: A string containting one or more SQL statements.
    :param encoding: The encoding of the statement (optional).
    :param dialect: The sql engine dialect of the input sql statements.
    It only supports "mysql" right now. If dialect is not specified,
    The input sql will be parsed using the generic sql syntax. (optional)
    :returns: A tuple of :class:`~sqlparse.sql.Statement` instances.
    """
    stream = parsestream(sql, encoding, dialect)

    return tuple(stream)


def parsestream(stream, encoding=None, dialect=None):
    """Parses sql statements from file-like object.

    :param stream: A file-like object.
    :param encoding: The encoding of the stream contents (optional).
    :param dialect: The sql engine dialect of the input sql statements.
    It only supports "mysql" right now. (optional)
    :returns: A generator of :class:`~sqlparse.sql.Statement` instances.
    """
    parser = parsers.get(dialect)
    if parser is None:
        raise Exception("Unable to find parser to parse dialect ({0})."
                        .format(dialect))
    return parser.parse(stream, encoding)


def format(sql, **options):
    """Format *sql* according to *options*.

    Available options are documented in :ref:`formatting`.

    In addition to the formatting options this function accepts the
    keyword "encoding" which determines the encoding of the statement.

    :returns: The formatted SQL statement as string.
    """
    options = formatter.validate_options(options)
    encoding = options.pop('encoding', None)
    stream = lexer.tokenize(sql, encoding)
    stream = _format_pre_process(stream, options)
    stack = engine.FilterStack()
    stack = formatter.build_filter_stack(stack, options)
    stack.postprocess.append(filters.SerializerUnicode())
    statements = split2(stream)
    return ''.join(stack.run(statement) for statement in statements)


def _format_pre_process(stream, options):
    pre_processes = []
    if options.get('keyword_case', None):
        pre_processes.append(
            filters.KeywordCaseFilter(options['keyword_case']))

    if options.get('identifier_case', None):
        pre_processes.append(
            filters.IdentifierCaseFilter(options['identifier_case']))

    if options.get('truncate_strings', None) is not None:
        pre_processes.append(filters.TruncateStringFilter(
            width=options['truncate_strings'], char=options['truncate_char']))
    return _pre_process(stream, pre_processes)


def _pre_process(stream, pre_processes):
    if pre_processes:
        for pre_process in pre_processes:
            stream = pre_process.process(None, stream)
    return stream


def split(sql, encoding=None):
    """Split *sql* into single statements.

    :param sql: A string containting one or more SQL statements.
    :param encoding: The encoding of the statement (optional).
    :returns: A list of strings.
    """
    stream = lexer.tokenize(sql, encoding)
    splitter = StatementFilter()
    stream = splitter.process(None, stream)
    return [unicode(stmt).strip() for stmt in stream]


from sqlparse.engine.filter import StatementFilter


def split2(stream):
    splitter = StatementFilter()
    return list(splitter.process(None, stream))
