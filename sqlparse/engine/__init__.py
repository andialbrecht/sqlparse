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
        stmtprocess=None,
        postprocess=None,
        grouping_funcs=None
    ):
        self.stmtprocess = stmtprocess or []
        self.postprocess = postprocess or []
        self.grouping_funcs = grouping_funcs or self.default_grouping_funcs
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

    def run(self, statement):
        statement = self._group_token(statement)
        statement = self._process_statement(statement)
        statement = self._post_process_statement(statement)
        return statement


    def _group_token(self, statement):
        if self._grouping:
            grouping.group(statement, self.grouping_funcs)
        return statement

    def _process_statement(self, statement):
        if self.stmtprocess:
            for filter_ in self.stmtprocess:
                filter_.process(self, statement)
        return statement

    def _post_process_statement(self, statement):
        if self.postprocess:
            statement.tokens = list(self._flatten(statement.tokens))
            for filter_ in self.postprocess:
                statement = filter_.process(self, statement)
        return statement