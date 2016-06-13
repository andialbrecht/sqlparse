# -*- coding: utf-8 -*-
#
# Copyright (C) 2016 Andi Albrecht, albrecht.andi@gmail.com
#
# This module is part of python-sqlparse and is released under
# the BSD License: http://www.opensource.org/licenses/bsd-license.php

"""SQL Lexer"""

# This code is based on the SqlLexer in pygments.
# http://pygments.org/
# It's separated from the rest of pygments to increase performance
# and to allow some customizations.

from sqlparse import tokens
from sqlparse.keywords import SQL_REGEX
from sqlparse.compat import StringIO, string_types, u
from sqlparse.utils import consume


class Lexer(object):
    """Lexer
    Empty class. Leaving for back-support
    """

    @staticmethod
    def get_tokens(text, encoding=None):
        """
        Return an iterable of (tokentype, value) pairs generated from
        `text`. If `unfiltered` is set to `True`, the filtering mechanism
        is bypassed even if filters are defined.

        Also preprocess the text, i.e. expand tabs and strip it if
        wanted and applies registered filters.

        Split ``text`` into (tokentype, text, row, col) pairs.

        ``stack`` is the inital stack (default: ``['root']``)
        """
        if isinstance(text, string_types):
            text = u(text, encoding)
        elif isinstance(text, StringIO):
            text = u(text.read(), encoding)

        iterable = enumerate(text)
        row = 1
        col = 0
        for pos, char in iterable:
            for rexmatch, action in SQL_REGEX:
                m = rexmatch(text, pos)
                if not m:
                    continue

                value = m.group()

                if isinstance(action, tokens._TokenType):
                    yield action, m.group(), row, col
                elif callable(action):
                    ttype, val = action(m.group())
                    yield ttype, val, row, col

                nl_rindex = value.rfind('\n')
                if nl_rindex >= 0:
                    row += value.count('\n')
                    col = len(value) - nl_rindex - 1
                else:
                    col += len(value)

                consume(iterable, m.end() - pos - 1)
                break
            else:
                yield tokens.Error, char, row, col
                if char == '\n':
                    row += 1
                    col = 0
                else:
                    col += 1


def tokenize(sql, encoding=None):
    """Tokenize sql.

    Tokenize *sql* using the :class:`Lexer` and return a 2-tuple stream
    of ``(token type, value, row, col)`` items.
    """
    return Lexer().get_tokens(sql, encoding)
