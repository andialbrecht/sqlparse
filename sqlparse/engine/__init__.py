# Copyright (C) 2008 Andi Albrecht, albrecht.andi@gmail.com
#
# This module is part of python-sqlparse and is released under
# the BSD License: http://www.opensource.org/licenses/bsd-license.php.

"""filter"""

from sqlparse import lexer
from sqlparse.engine import grouping
from sqlparse.engine.filter import StatementFilter

# XXX remove this when cleanup is complete
Filter = object


class FilterStack(object):

    default_grouping_funcs = [
        grouping.group_comments,
        grouping.group_brackets,
        grouping.group_functions,
        grouping.group_where,
        grouping.group_case,
        grouping.group_identifier,
        grouping.group_order,
        grouping.group_typecasts,
        grouping.group_as,
        grouping.group_aliased,
        grouping.group_assignment,
        grouping.group_comparison,
        grouping.align_comments,
        grouping.group_identifier_list,
        grouping.group_if,
        grouping.group_for,
        grouping.group_foreach,
        grouping.group_begin
    ]

    def __init__(
        self,
        pre_processes=[],
        stmt_processes=[],
        post_processes=[],
        grouping_funcs=default_grouping_funcs
    ):
        self.pre_processes = pre_processes
        self.stmt_processes = stmt_processes
        self.post_processes = post_processes
        self.grouping_funcs = grouping_funcs
        self.split_statements = False
        self._grouping = False

    def _flatten(self, stream):
        for token in stream:
            if token.is_group():
                for t in self._flatten(token.tokens):
                    yield t
            else:
                yield token

    def enable_grouping(self):
        self._grouping = True

    def full_analyze(self):
        self.enable_grouping()

    def run(self, sql, encoding=None):
        stream = lexer.tokenize(sql, encoding)
        # Process token stream
        if self.pre_processes:
            for filter_ in self.pre_processes:
                stream = filter_.process(self, stream)

        if (self.stmt_processes or self.post_processes or self.split_statements
            or self._grouping):
            splitter = StatementFilter()
            stream = splitter.process(self, stream)

        if self._grouping:

            def _group(stream):
                for stmt in stream:
                    grouping.group(stmt, self.grouping_funcs)
                    yield stmt
            stream = _group(stream)

        if self.stmt_processes:

            def _run1(stream):
                ret = []
                for stmt in stream:
                    for filter_ in self.stmt_processes:
                        filter_.process(self, stmt)
                    ret.append(stmt)
                return ret
            stream = _run1(stream)

        if self.post_processes:

            def _run2(stream):
                for stmt in stream:
                    stmt.tokens = list(self._flatten(stmt.tokens))
                    for filter_ in self.post_processes:
                        stmt = filter_.process(self, stmt)
                    yield stmt
            stream = _run2(stream)

        return stream
