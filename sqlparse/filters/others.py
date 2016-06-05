# -*- coding: utf-8 -*-
#
# Copyright (C) 2016 Andi Albrecht, albrecht.andi@gmail.com
#
# This module is part of python-sqlparse and is released under
# the BSD License: http://www.opensource.org/licenses/bsd-license.php

from sqlparse import sql, tokens as T
from sqlparse.compat import text_type
from sqlparse.utils import split_unquoted_newlines


class StripCommentsFilter(object):
    @staticmethod
    def _process(tlist):
        def get_next_comment():
            # TODO(andi) Comment types should be unified, see related issue38
            return tlist.token_next_by(i=sql.Comment, t=T.Comment)

        token = get_next_comment()
        while token:
            prev = tlist.token_prev(token, skip_ws=False)
            next_ = tlist.token_next(token, skip_ws=False)
            # Replace by whitespace if prev and next exist and if they're not
            # whitespaces. This doesn't apply if prev or next is a paranthesis.
            if (prev is None or next_ is None or
                    prev.is_whitespace() or prev.match(T.Punctuation, '(') or
                    next_.is_whitespace() or next_.match(T.Punctuation, ')')):
                tlist.tokens.remove(token)
            else:
                tidx = tlist.token_index(token)
                tlist.tokens[tidx] = sql.Token(T.Whitespace, ' ')

            token = get_next_comment()

    def process(self, stmt):
        [self.process(sgroup) for sgroup in stmt.get_sublists()]
        StripCommentsFilter._process(stmt)
        return stmt


class StripWhitespaceFilter(object):
    def _stripws(self, tlist):
        func_name = '_stripws_%s' % tlist.__class__.__name__.lower()
        func = getattr(self, func_name, self._stripws_default)
        func(tlist)

    def _stripws_default(self, tlist):
        last_was_ws = False
        is_first_char = True
        for token in tlist.tokens:
            if token.is_whitespace():
                if last_was_ws or is_first_char:
                    token.value = ''
                else:
                    token.value = ' '
            last_was_ws = token.is_whitespace()
            is_first_char = False

    def _stripws_identifierlist(self, tlist):
        # Removes newlines before commas, see issue140
        last_nl = None
        for token in tlist.tokens[:]:
            if last_nl and token.ttype is T.Punctuation and token.value == ',':
                tlist.tokens.remove(last_nl)

            last_nl = token if token.is_whitespace() else None
        return self._stripws_default(tlist)

    def _stripws_parenthesis(self, tlist):
        if tlist.tokens[1].is_whitespace():
            tlist.tokens.pop(1)
        if tlist.tokens[-2].is_whitespace():
            tlist.tokens.pop(-2)
        self._stripws_default(tlist)

    def process(self, stmt, depth=0):
        [self.process(sgroup, depth + 1) for sgroup in stmt.get_sublists()]
        self._stripws(stmt)
        if depth == 0 and stmt.tokens and stmt.tokens[-1].is_whitespace():
            stmt.tokens.pop(-1)


class SpacesAroundOperatorsFilter(object):
    @staticmethod
    def _process(tlist):
        def next_token(idx=0):
            return tlist.token_next_by(t=(T.Operator, T.Comparison), idx=idx)

        token = next_token()
        while token:
            prev_ = tlist.token_prev(token, skip_ws=False)
            if prev_ and prev_.ttype != T.Whitespace:
                tlist.insert_before(token, sql.Token(T.Whitespace, ' '))

            next_ = tlist.token_next(token, skip_ws=False)
            if next_ and next_.ttype != T.Whitespace:
                tlist.insert_after(token, sql.Token(T.Whitespace, ' '))

            token = next_token(idx=token)

    def process(self, stmt):
        [self.process(sgroup) for sgroup in stmt.get_sublists()]
        SpacesAroundOperatorsFilter._process(stmt)
        return stmt


# ---------------------------
# postprocess

class SerializerUnicode(object):
    @staticmethod
    def process(stmt):
        raw = text_type(stmt)
        lines = split_unquoted_newlines(raw)
        return '\n'.join(line.rstrip() for line in lines)
