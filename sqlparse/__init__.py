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

# Deprecated in 0.1.5. Will be removed in 0.2.0
from sqlparse.exceptions import SQLParseError


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
    stream = _tokenize(stream, encoding)
    statements = split2(stream)

    default_stack = engine.FilterStack()
    for statement in statements:
        if _is_create_table_statement(statement) and dialect is 'mysql':
            stack = engine.FilterStack(
                stmtprocess=[filters.MysqlCreateStatementFilter()],
                grouping_funcs=[grouping.group_brackets]
            )
        else:
            stack = default_stack
        stack.enable_grouping()
        yield stack.run(statement)


def format(sql, **options):
    """Format *sql* according to *options*.

    Available options are documented in :ref:`formatting`.

    In addition to the formatting options this function accepts the
    keyword "encoding" which determines the encoding of the statement.

    :returns: The formatted SQL statement as string.
    """
    options = formatter.validate_options(options)
    encoding = options.pop('encoding', None)
    stream = _tokenize(sql, encoding)
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


def _tokenize(sql, encoding):
    return lexer.tokenize(sql, encoding)


def _is_create_table_statement(statement):
    if statement.get_type() == 'CREATE':
        first_keyword_token = statement.token_first()
        first_keyword_token_index = statement.token_index(first_keyword_token)
        second_keyword_token = statement.token_next_by_type(
            first_keyword_token_index+1,
            T.Keyword
        )
        if second_keyword_token and second_keyword_token.normalized == 'TABLE':
            return True
    return False


def split(sql, encoding=None):
    """Split *sql* into single statements.

    :param sql: A string containting one or more SQL statements.
    :param encoding: The encoding of the statement (optional).
    :returns: A list of strings.
    """
    stream = _tokenize(sql, encoding)
    splitter = StatementFilter()
    stream = splitter.process(None, stream)
    return [unicode(stmt).strip() for stmt in stream]


from sqlparse.engine.filter import StatementFilter


def split2(stream):
    splitter = StatementFilter()
    return list(splitter.process(None, stream))
