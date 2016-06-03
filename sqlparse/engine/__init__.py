# -*- coding: utf-8 -*-
#
# Copyright (C) 2016 Andi Albrecht, albrecht.andi@gmail.com
#
# This module is part of python-sqlparse and is released under
# the BSD License: http://www.opensource.org/licenses/bsd-license.php

"""filter"""

from sqlparse import lexer
from sqlparse.engine import grouping
from sqlparse.engine.filter import StatementFilter


class FilterStack(object):

    def __init__(self):
        self.preprocess = []
        self.stmtprocess = []
        self.postprocess = []
        self.split_statements = False
        self._grouping = False

    def enable_grouping(self):
        self._grouping = True

    def run(self, sql, encoding=None):
        stream = lexer.tokenize(sql, encoding)
        # Process token stream
        if self.preprocess:
            for filter_ in self.preprocess:
                stream = filter_.process(stream)

        if (self.stmtprocess or self.postprocess or
                self.split_statements or self._grouping):
            splitter = StatementFilter()
            stream = splitter.process(stream)

        if self._grouping:

            def _group(stream):
                for stmt in stream:
                    grouping.group(stmt)
                    yield stmt
            stream = _group(stream)

        if self.stmtprocess:

            def _run1(stream):
                ret = []
                for stmt in stream:
                    for filter_ in self.stmtprocess:
                        filter_.process(stmt)
                    ret.append(stmt)
                return ret
            stream = _run1(stream)

        if self.postprocess:

            def _run2(stream):
                for stmt in stream:
                    stmt.tokens = list(stmt.flatten())
                    for filter_ in self.postprocess:
                        stmt = filter_.process(stmt)
                    yield stmt
            stream = _run2(stream)

        return stream
