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
import sys

from sqlparse import tokens
from sqlparse.keywords import SQL_REGEX
from sqlparse.compat import StringIO, string_types, with_metaclass, text_type


class LexerMeta(type):
    """
    Metaclass for Lexer, creates the self._tokens attribute from
    self.tokens on the first instantiation.
    """

    def _process_state(cls, unprocessed, processed, state):
        assert type(state) is str, "wrong state name %r" % state
        assert state[0] != '#', "invalid state name %r" % state
        if state in processed:
            return processed[state]
        tokenlist = processed[state] = []
        rflags = cls.flags
        for tdef in unprocessed[state]:

            assert type(tdef) is tuple, "wrong rule def %r" % tdef

            try:
                rex = re.compile(tdef[0], rflags).match
            except Exception as err:
                raise ValueError(("uncompilable regex %r in state"
                                  " %r of %r: %s"
                                  % (tdef[0], state, cls, err)))

            assert type(tdef[1]) is tokens._TokenType or callable(tdef[1]), \
                ('token type must be simple type or callable, not %r'
                 % (tdef[1],))

            if len(tdef) == 2:
                new_state = None
            else:
                tdef2 = tdef[2]
                if isinstance(tdef2, str):
                    # an existing state
                    if tdef2 == '#pop':
                        new_state = -1
                    elif tdef2 in unprocessed:
                        new_state = (tdef2,)
                    elif tdef2 == '#push':
                        new_state = tdef2
                    elif tdef2[:5] == '#pop:':
                        new_state = -int(tdef2[5:])
                    else:
                        assert False, 'unknown new state %r' % tdef2
                elif isinstance(tdef2, tuple):
                    # push more than one state
                    for state in tdef2:
                        assert (state in unprocessed or
                                state in ('#pop', '#push')), \
                            'unknown new state ' + state
                    new_state = tdef2
                else:
                    assert False, 'unknown new state def %r' % tdef2
            tokenlist.append((rex, tdef[1], new_state))
        return tokenlist

    def process_tokendef(cls):
        cls._all_tokens = {}
        cls._tmpname = 0
        processed = cls._all_tokens[cls.__name__] = {}
        for state in SQL_REGEX:
            cls._process_state(SQL_REGEX, processed, state)
        return processed

    def __call__(cls, *args, **kwds):
        if not hasattr(cls, '_tokens'):
            cls._all_tokens = {}
            cls._tmpname = 0
            if hasattr(cls, 'token_variants') and cls.token_variants:
                # don't process yet
                pass
            else:
                cls._tokens = cls.process_tokendef()

        return type.__call__(cls, *args, **kwds)


class _Lexer(object):

    encoding = 'utf-8'
    flags = re.IGNORECASE | re.UNICODE

    def __init__(self):
        self.filters = []

    def _decode(self, text):
        if sys.version_info[0] == 3:
            if isinstance(text, str):
                return text
        if self.encoding == 'guess':
            try:
                text = text.decode('utf-8')
                if text.startswith(u'\ufeff'):
                    text = text[len(u'\ufeff'):]
            except UnicodeDecodeError:
                text = text.decode('latin1')
        else:
            try:
                text = text.decode(self.encoding)
            except UnicodeDecodeError:
                text = text.decode('unicode-escape')
        return text

    def get_tokens(self, text):
        """
        Return an iterable of (tokentype, value) pairs generated from
        `text`. If `unfiltered` is set to `True`, the filtering mechanism
        is bypassed even if filters are defined.

        Also preprocess the text, i.e. expand tabs and strip it if
        wanted and applies registered filters.
        """
        if isinstance(text, string_types):
            if sys.version_info[0] < 3 and isinstance(text, text_type):
                text = StringIO(text.encode('utf-8'))
                self.encoding = 'utf-8'
            else:
                text = StringIO(text)

        def streamer():
            for i, t, v in self.get_tokens_unprocessed(text):
                yield t, v
        stream = streamer()
        return stream

    def get_tokens_unprocessed(self, stream):
        """
        Split ``text`` into (tokentype, text) pairs.

        ``stack`` is the inital stack (default: ``['root']``)
        """
        pos = 0
        tokendefs = self._tokens  # see __call__, pylint:disable=E1101
        statestack = ['root', ]
        statetokens = tokendefs[statestack[-1]]
        known_names = {}

        text = stream.read()
        text = self._decode(text)

        while 1:
            for rexmatch, action, new_state in statetokens:
                m = rexmatch(text, pos)
                if m:
                    value = m.group()
                    if value in known_names:
                        yield pos, known_names[value], value
                    elif type(action) is tokens._TokenType:
                        yield pos, action, value
                    elif hasattr(action, '__call__'):
                        ttype, value = action(value)
                        known_names[value] = ttype
                        yield pos, ttype, value
                    else:
                        for item in action(self, m):
                            yield item
                    pos = m.end()
                    if new_state is not None:
                        # state transition
                        if isinstance(new_state, tuple):
                            for state in new_state:
                                if state == '#pop':
                                    statestack.pop()
                                elif state == '#push':
                                    statestack.append(statestack[-1])
                                elif (
                                    # Ugly hack - multiline-comments
                                    # are not stackable
                                    state != 'multiline-comments'
                                    or not statestack
                                    or statestack[-1] != 'multiline-comments'
                                ):
                                    statestack.append(state)
                        elif isinstance(new_state, int):
                            # pop
                            del statestack[new_state:]
                        elif new_state == '#push':
                            statestack.append(statestack[-1])
                        else:
                            assert False, "wrong state def: %r" % new_state
                        statetokens = tokendefs[statestack[-1]]
                    break
            else:
                try:
                    if text[pos] == '\n':
                        # at EOL, reset state to "root"
                        pos += 1
                        statestack = ['root']
                        statetokens = tokendefs['root']
                        yield pos, tokens.Text, u'\n'
                        continue
                    yield pos, tokens.Error, text[pos]
                    pos += 1
                except IndexError:
                    break


class Lexer(with_metaclass(LexerMeta, _Lexer)):
    pass


def tokenize(sql, encoding=None):
    """Tokenize sql.

    Tokenize *sql* using the :class:`Lexer` and return a 2-tuple stream
    of ``(token type, value)`` items.
    """
    lexer = Lexer()
    if encoding is not None:
        lexer.encoding = encoding
    return lexer.get_tokens(sql)
