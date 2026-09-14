#
# Copyright (C) 2009-2020 the sqlparse authors and contributors
# <see AUTHORS file>
#
# This module is part of python-sqlparse and is released under
# the BSD License: https://opensource.org/licenses/BSD-3-Clause

import re

from sqlparse import tokens as T


class _CaseFilter:
    ttype = None

    def __init__(self, case=None):
        case = case or 'upper'
        self.convert = getattr(str, case)

    def process(self, stream):
        for ttype, value in stream:
            if ttype in self.ttype:
                value = self.convert(value)
            yield ttype, value


class KeywordCaseFilter(_CaseFilter):
    ttype = T.Keyword


class IdentifierCaseFilter(_CaseFilter):
    ttype = T.Name, T.String.Symbol

    def process(self, stream):
        for ttype, value in stream:
            if ttype in self.ttype and value.strip()[0] != '"':
                value = self.convert(value)
            yield ttype, value


class TruncateStringFilter:
    def __init__(self, width, char):
        self.width = width
        self.char = char

    def process(self, stream):
        for ttype, value in stream:
            if ttype != T.Literal.String.Single:
                yield ttype, value
                continue

            inner = value[1:-1]
            if len(inner) > self.width:
                # Keep doubled quotes and backslash escapes intact at the
                # truncation boundary, without exceeding the requested width.
                end = 0
                for match in re.finditer(r"''|\\.|.", inner, re.DOTALL):
                    if match.end() > self.width:
                        break
                    end = match.end()
                value = ''.join(("'", inner[:end], self.char, "'"))
            yield ttype, value
