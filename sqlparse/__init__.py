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


def parse(sql, encoding=None):
    """Parse sql and return a list of statements.

    :param sql: A string containting one or more SQL statements.
    :param encoding: The encoding of the statement (optional).
    :returns: A tuple of :class:`~sqlparse.sql.Statement` instances.
    """
    stream = parse_stream(sql, encoding)

    return tuple(stream)


def parse_stream(stream, encoding=None):
    """Parses sql statements from file-like object.

    :param stream: A file-like object.
    :param encoding: The encoding of the stream contents (optional).
    :returns: A generator of :class:`~sqlparse.sql.Statement` instances.
    """
    stream = _tokenize(stream, encoding)
    statements = split2(stream)
    create_table_stack = engine.FilterStack(
        stmt_processes=[filters.MysqlCreateStatementFilter()],
        grouping_funcs=[grouping.group_brackets]
    )
    default_stack = engine.FilterStack()
    for statement in statements:
        if _is_create_table_statement(statement):
            stack = create_table_stack
        else:
            stack = default_stack
        stack.enable_grouping()
        yield list(stack.run(unicode(statement), encoding))[0]


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
    stack.post_processes.append(filters.SerializerUnicode())
    return ''.join(stack.run(sql, encoding))


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
    stack = engine.FilterStack()
    stack.split_statements = True
    return [unicode(stmt).strip() for stmt in stack.run(sql, encoding)]


from sqlparse.engine.filter import StatementFilter


def split2(stream):
    splitter = StatementFilter()
    return list(splitter.process(None, stream))
