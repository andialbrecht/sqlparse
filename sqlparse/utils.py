#
# Copyright (C) 2009-2020 the sqlparse authors and contributors
# <see AUTHORS file>
#
# This module is part of python-sqlparse and is released under
# the BSD License: https://opensource.org/licenses/BSD-3-Clause

import itertools
import re
from collections import deque
from contextlib import contextmanager

_UNQUOTED_TEXT = re.compile(r'[^\r\n\'"]+')
# Content of a quoted string. A backslash escapes the next character,
# except for a newline.
_STRING_CONTENT = {
    '"': re.compile(r'(?:[^"\\]|\\.)*'),
    "'": re.compile(r"(?:[^'\\]|\\.)*"),
}


def split_unquoted_newlines(stmt):
    """Split a string on all unquoted newlines.

    Unlike str.splitlines(), this will ignore CR/LF/CR+LF if the requisite
    character is inside of a string. A quote that is never closed is
    treated as plain text."""
    text = str(stmt)
    length = len(text)
    lines = []
    line_start = pos = 0
    # Searching the end of a string that is never closed scans up to some
    # position. Every later quote of the same kind before that position
    # can't be closed either, so remember it instead of scanning again.
    # Otherwise many unclosed quotes take quadratic time
    # (GHSA-3r5h-5jcg-gmgg).
    unclosed_before = {'"': 0, "'": 0}
    while pos < length:
        char = text[pos]
        if char in '\r\n':
            lines.append(text[line_start:pos])
            pos += 2 if text.startswith('\r\n', pos) else 1
            line_start = pos
        elif char in unclosed_before:
            if pos >= unclosed_before[char]:
                end = _STRING_CONTENT[char].match(text, pos + 1).end()
                if end < length and text[end] == char:
                    pos = end + 1
                    continue
                unclosed_before[char] = end
            pos += 1
        else:
            pos = _UNQUOTED_TEXT.match(text, pos).end()
    lines.append(text[line_start:])
    return lines


def remove_quotes(val):
    """Helper that removes surrounding quotes from strings."""
    if val is None:
        return
    if val[0] in ('"', "'", '`') and val[0] == val[-1]:
        val = val[1:-1]
    return val


def recurse(*cls):
    """Function decorator to help with recursion

    :param cls: Classes to not recurse over
    :return: function
    """
    def wrap(f):
        def wrapped_f(tlist):
            for sgroup in tlist.get_sublists():
                if not isinstance(sgroup, cls):
                    wrapped_f(sgroup)
            f(tlist)

        return wrapped_f

    return wrap


def imt(token, i=None, m=None, t=None):
    """Helper function to simplify comparisons Instance, Match and TokenType
    :param token:
    :param i: Class or Tuple/List of Classes
    :param m: Tuple of TokenType & Value. Can be list of Tuple for multiple
    :param t: TokenType or Tuple/List of TokenTypes
    :return:  bool
    """
    if token is None:
        return False
    if i and isinstance(token, i):
        return True
    if m:
        if isinstance(m, list):
            if any(token.match(*pattern) for pattern in m):
                return True
        elif token.match(*m):
            return True
    if t:
        if isinstance(t, list):
            if any(token.ttype in ttype for ttype in t):
                return True
        elif token.ttype in t:
            return True
    return False


def consume(iterator, n):
    """Advance the iterator n-steps ahead. If n is none, consume entirely."""
    deque(itertools.islice(iterator, n), maxlen=0)


@contextmanager
def offset(filter_, n=0):
    filter_.offset += n
    yield
    filter_.offset -= n


@contextmanager
def indent(filter_, n=1):
    filter_.indent += n
    yield
    filter_.indent -= n
