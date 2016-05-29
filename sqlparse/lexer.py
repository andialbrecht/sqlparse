# -*- coding: utf-8 -*-

# Copyright (C) 2008 Andi Albrecht, albrecht.andi@gmail.com
#
# This module is part of python-sqlparse and is released under
# the BSD License: http://www.opensource.org/licenses/bsd-license.php.

"""SQL Lexer"""

# This code is based on the SqlLexer in pygments.
# http://pygments.org/
# It's separated from the rest of pygments to increase performance
# and to allow some customizations.

import re

from sqlparse import tokens
from sqlparse.keywords import SQL_REGEX
from sqlparse.compat import StringIO, string_types, text_type, range
from sqlparse.utils import consume


class Lexer(object):
    encoding = 'utf-8'
    flags = re.IGNORECASE | re.UNICODE

    def __init__(self):
        self._tokens = {}

        for state in SQL_REGEX:
            self._tokens[state] = []

            for tdef in SQL_REGEX[state]:
                rex = re.compile(tdef[0], self.flags).match
                new_state = None
                if len(tdef) > 2:
                    # Only Multiline comments
                    if tdef[2] == '#pop':
                        new_state = -1
                    elif tdef[2] in SQL_REGEX:
                        new_state = (tdef[2],)
                self._tokens[state].append((rex, tdef[1], new_state))

    def get_tokens(self, text):
        """
        Return an iterable of (tokentype, value) pairs generated from
        `text`. If `unfiltered` is set to `True`, the filtering mechanism
        is bypassed even if filters are defined.

        Also preprocess the text, i.e. expand tabs and strip it if
        wanted and applies registered filters.

        Split ``text`` into (tokentype, text) pairs.

        ``stack`` is the inital stack (default: ``['root']``)
        """
        statestack = ['root', ]
        statetokens = self._tokens['root']

        if isinstance(text, string_types):
            text = StringIO(text)

        text = text.read()
        if not isinstance(text, text_type):
            try:
                text = text.decode(self.encoding)
            except UnicodeDecodeError:
                text = text.decode('unicode-escape')

        iterable = iter(range(len(text)))

        for pos in iterable:
            for rexmatch, action, new_state in statetokens:
                m = rexmatch(text, pos)

                if not m:
                    continue
                elif isinstance(action, tokens._TokenType):
                    yield action, m.group()
                elif callable(action):
                    yield action(m.group())

                if isinstance(new_state, tuple):
                    for state in new_state:
                        # fixme: multiline-comments not stackable
                        if not (state == 'multiline-comments'
                                and statestack[-1] == 'multiline-comments'):
                            statestack.append(state)
                elif isinstance(new_state, int):
                    del statestack[new_state:]
                statetokens = self._tokens[statestack[-1]]

                consume(iterable, m.end() - pos - 1)
                break
            else:
                yield tokens.Error, text[pos]


def tokenize(sql, encoding=None):
    """Tokenize sql.

    Tokenize *sql* using the :class:`Lexer` and return a 2-tuple stream
    of ``(token type, value)`` items.
    """
    lexer = Lexer()
    if encoding is not None:
        lexer.encoding = encoding
    return lexer.get_tokens(sql)
