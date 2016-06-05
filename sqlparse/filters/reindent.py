# -*- coding: utf-8 -*-
#
# Copyright (C) 2016 Andi Albrecht, albrecht.andi@gmail.com
#
# This module is part of python-sqlparse and is released under
# the BSD License: http://www.opensource.org/licenses/bsd-license.php

from sqlparse import sql, tokens as T
from sqlparse.compat import text_type


class ReindentFilter(object):
    def __init__(self, width=2, char=' ', line_width=None, wrap_after=0):
        self.width = width
        self.char = char
        self.indent = 0
        self.offset = 0
        self.line_width = line_width
        self.wrap_after = wrap_after
        self._curr_stmt = None
        self._last_stmt = None

    def _flatten_up_to_token(self, token):
        """Yields all tokens up to token plus the next one."""
        # helper for _get_offset
        iterator = self._curr_stmt.flatten()
        for t in iterator:
            yield t
            if t == token:
                raise StopIteration

    def _get_offset(self, token):
        raw = ''.join(map(text_type, self._flatten_up_to_token(token)))
        line = raw.splitlines()[-1]
        # Now take current offset into account and return relative offset.
        full_offset = len(line) - len(self.char * (self.width * self.indent))
        return full_offset - self.offset

    def nl(self):
        # TODO: newline character should be configurable
        space = (self.char * ((self.indent * self.width) + self.offset))
        # Detect runaway indenting due to parsing errors
        if len(space) > 200:
            # something seems to be wrong, flip back
            self.indent = self.offset = 0
            space = (self.char * ((self.indent * self.width) + self.offset))
        ws = '\n' + space
        return sql.Token(T.Whitespace, ws)

    def _split_kwds(self, tlist):
        split_words = ('FROM', 'STRAIGHT_JOIN$', 'JOIN$', 'AND', 'OR',
                       'GROUP', 'ORDER', 'UNION', 'VALUES',
                       'SET', 'BETWEEN', 'EXCEPT', 'HAVING')

        def _next_token(i):
            t = tlist.token_next_by(m=(T.Keyword, split_words, True), idx=i)
            if t and t.value.upper() == 'BETWEEN':
                t = _next_token(tlist.token_index(t) + 1)
                if t and t.value.upper() == 'AND':
                    t = _next_token(tlist.token_index(t) + 1)
            return t

        idx = 0
        token = _next_token(idx)
        added = set()
        while token:
            prev = tlist.token_prev(token, skip_ws=False)
            offset = 1
            if prev and prev.is_whitespace() and prev not in added:
                tlist.tokens.pop(tlist.token_index(prev))
                offset += 1
            uprev = text_type(prev)
            if prev and (uprev.endswith('\n') or uprev.endswith('\r')):
                nl = tlist.token_next(token)
            else:
                nl = self.nl()
                added.add(nl)
                tlist.insert_before(token, nl)
                offset += 1
            token = _next_token(tlist.token_index(nl) + offset)

    def _split_statements(self, tlist):
        token = tlist.token_next_by(t=(T.Keyword.DDL, T.Keyword.DML))
        while token:
            prev = tlist.token_prev(token, skip_ws=False)
            if prev and prev.is_whitespace():
                tlist.tokens.pop(tlist.token_index(prev))
            # only break if it's not the first token
            if prev:
                nl = self.nl()
                tlist.insert_before(token, nl)
            token = tlist.token_next_by(t=(T.Keyword.DDL, T.Keyword.DML),
                                        idx=token)

    def _process(self, tlist):
        func_name = '_process_%s' % tlist.__class__.__name__.lower()
        func = getattr(self, func_name, self._process_default)
        func(tlist)

    def _process_where(self, tlist):
        token = tlist.token_next_by(m=(T.Keyword, 'WHERE'))
        try:
            tlist.insert_before(token, self.nl())
        except ValueError:  # issue121, errors in statement
            pass
        self.indent += 1
        self._process_default(tlist)
        self.indent -= 1

    def _process_having(self, tlist):
        token = tlist.token_next_by(m=(T.Keyword, 'HAVING'))
        try:
            tlist.insert_before(token, self.nl())
        except ValueError:  # issue121, errors in statement
            pass
        self.indent += 1
        self._process_default(tlist)
        self.indent -= 1

    def _process_parenthesis(self, tlist):
        first = tlist.token_next(0)
        indented = False
        if first and first.ttype in (T.Keyword.DML, T.Keyword.DDL):
            self.indent += 1
            tlist.tokens.insert(0, self.nl())
            indented = True
        num_offset = self._get_offset(
            tlist.token_next_by(m=(T.Punctuation, '(')))
        self.offset += num_offset
        self._process_default(tlist, stmts=not indented)
        if indented:
            self.indent -= 1
        self.offset -= num_offset

    def _process_identifierlist(self, tlist):
        identifiers = list(tlist.get_identifiers())
        if len(identifiers) > 1 and not tlist.within(sql.Function):
            first = list(identifiers[0].flatten())[0]
            if self.char == '\t':
                # when using tabs we don't count the actual word length
                # in spaces.
                num_offset = 1
            else:
                num_offset = self._get_offset(first) - len(first.value)
            self.offset += num_offset
            position = self.offset
            for token in identifiers[1:]:
                # Add 1 for the "," separator
                position += len(token.value) + 1
                if position > self.wrap_after:
                    tlist.insert_before(token, self.nl())
                    position = self.offset
            self.offset -= num_offset
        self._process_default(tlist)

    def _process_case(self, tlist):
        is_first = True
        num_offset = None
        case = tlist.tokens[0]
        outer_offset = self._get_offset(case) - len(case.value)
        self.offset += outer_offset
        for cond, value in tlist.get_cases():
            if is_first:
                tcond = list(cond[0].flatten())[0]
                is_first = False
                num_offset = self._get_offset(tcond) - len(tcond.value)
                self.offset += num_offset
                continue
            if cond is None:
                token = value[0]
            else:
                token = cond[0]
            tlist.insert_before(token, self.nl())
        # Line breaks on group level are done. Now let's add an offset of
        # 5 (=length of "when", "then", "else") and process subgroups.
        self.offset += 5
        self._process_default(tlist)
        self.offset -= 5
        if num_offset is not None:
            self.offset -= num_offset
        end = tlist.token_next_by(m=(T.Keyword, 'END'))
        tlist.insert_before(end, self.nl())
        self.offset -= outer_offset

    def _process_default(self, tlist, stmts=True, kwds=True):
        if stmts:
            self._split_statements(tlist)
        if kwds:
            self._split_kwds(tlist)
        [self._process(sgroup) for sgroup in tlist.get_sublists()]

    def process(self, stmt):
        if isinstance(stmt, sql.Statement):
            self._curr_stmt = stmt
        self._process(stmt)
        if isinstance(stmt, sql.Statement):
            if self._last_stmt is not None:
                if text_type(self._last_stmt).endswith('\n'):
                    nl = '\n'
                else:
                    nl = '\n\n'
                stmt.tokens.insert(
                    0, sql.Token(T.Whitespace, nl))
            if self._last_stmt != stmt:
                self._last_stmt = stmt
