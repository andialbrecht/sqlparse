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
        self._grouping = False

    def enable_grouping(self):
        self._grouping = True

    def run(self, sql, encoding=None):
        stream = lexer.tokenize(sql, encoding)
        # Process token stream
        for filter_ in self.preprocess:
            stream = filter_.process(stream)

        stream = StatementFilter().process(stream)

        # Output: Stream processed Statements
        for stmt in stream:
            if self._grouping:
                stmt = grouping.group(stmt)

            for filter_ in self.stmtprocess:
                filter_.process(stmt)

            for filter_ in self.postprocess:
                stmt = filter_.process(stmt)

            yield stmt
