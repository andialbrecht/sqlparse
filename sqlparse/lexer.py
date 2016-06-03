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

import re

from sqlparse import tokens
from sqlparse.keywords import SQL_REGEX
from sqlparse.compat import StringIO, string_types, text_type
from sqlparse.utils import consume


class Lexer(object):
    flags = re.IGNORECASE | re.UNICODE

    def __init__(self):
        self._tokens = []

        for tdef in SQL_REGEX['root']:
            rex = re.compile(tdef[0], self.flags).match
            self._tokens.append((rex, tdef[1]))

    def get_tokens(self, text, encoding=None):
        """
        Return an iterable of (tokentype, value) pairs generated from
        `text`. If `unfiltered` is set to `True`, the filtering mechanism
        is bypassed even if filters are defined.

        Also preprocess the text, i.e. expand tabs and strip it if
        wanted and applies registered filters.

        Split ``text`` into (tokentype, text) pairs.

        ``stack`` is the inital stack (default: ``['root']``)
        """
        encoding = encoding or 'utf-8'

        if isinstance(text, string_types):
            text = StringIO(text)

        text = text.read()
        if not isinstance(text, text_type):
            try:
                text = text.decode(encoding)
            except UnicodeDecodeError:
                text = text.decode('unicode-escape')

        iterable = enumerate(text)
        for pos, char in iterable:
            for rexmatch, action in self._tokens:
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


def tokenize(sql, encoding=None):
    """Tokenize sql.

    Tokenize *sql* using the :class:`Lexer` and return a 2-tuple stream
    of ``(token type, value)`` items.
    """
    return Lexer().get_tokens(sql, encoding)
