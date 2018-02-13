# -*- coding: utf-8 -*-
#
# Copyright (C) 2016 Andi Albrecht, albrecht.andi@gmail.com
#
# This module is part of python-sqlparse and is released under
# the BSD License: https://opensource.org/licenses/BSD-3-Clause

"""SQL Lexer"""

# This code is based on the SqlLexer in pygments.
# http://pygments.org/
# It's separated from the rest of pygments to increase performance
# and to allow some customizations.

from sqlparse import tokens
from sqlparse.compat import bytes_type, text_type, file_types
from sqlparse.exceptions import SQLParseError
from sqlparse.keywords import get_sql_regex_tokens_map, SQL_REGEX_WITH_DIALECT
from sqlparse.utils import consume


class Lexer(object):
    """Lexer
    Empty class. Leaving for backwards-compatibility
    """

    @staticmethod
    def get_tokens(text, encoding=None, **options):
        """
        Return an iterable of (tokentype, value) pairs generated from
        `text`. If `unfiltered` is set to `True`, the filtering mechanism
        is bypassed even if filters are defined.

        Also preprocess the text, i.e. expand tabs and strip it if
        wanted and applies registered filters.

        Split ``text`` into (tokentype, text) pairs.

        ``stack`` is the initial stack (default: ``['root']``)
        """
        if isinstance(text, file_types):
            text = text.read()

        if isinstance(text, text_type):
            pass
        elif isinstance(text, bytes_type):
            if encoding:
                text = text.decode(encoding)
            else:
                try:
                    text = text.decode('utf-8')
                except UnicodeDecodeError:
                    text = text.decode('unicode-escape')
        else:
            raise TypeError(u"Expected text or file-like object, got {!r}".
                            format(type(text)))

        iterable = enumerate(text)
        SQL_REGEX = get_sql_regex_tokens_map(**options)
        for pos, char in iterable:
            for rexmatch, action in SQL_REGEX:
                m = rexmatch(text, pos)

                if not m:
                    continue
                elif isinstance(action, tokens._TokenType):
                    yield action, m.group()
                elif callable(action):
                    yield action(m.group())
                consume(iterable, m.end() - pos - 1)
                break
            else:
                yield tokens.Error, char


def tokenize(sql, encoding=None, **options):
    """Tokenize sql.

    Tokenize *sql* using the :class:`Lexer` and return a 2-tuple stream
    of ``(token type, value)`` items.
    """
    validate_options(**options)
    return Lexer().get_tokens(sql, encoding, **options)


def validate_options(**options):
    """Validate options.
    """
    sql_dialect = options.get('sql_dialect')

    if sql_dialect and sql_dialect not in SQL_REGEX_WITH_DIALECT:
        raise SQLParseError('Invalid value for sql_dialect: '
                            '{0!r}'.format(sql_dialect))

    additional_keywords = options.get('additional_keywords')

    if additional_keywords:
        if not isinstance(additional_keywords, list):
            raise SQLParseError('additional_keywords: '
                                '{0!r} must be a list'.format(
                                    additional_keywords))
