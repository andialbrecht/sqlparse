# -*- coding: utf-8 -*-
#
# Copyright (C) 2016 Andi Albrecht, albrecht.andi@gmail.com
#
# This module is part of python-sqlparse and is released under
# the BSD License: http://www.opensource.org/licenses/bsd-license.php

from sqlparse import sql, tokens as T


class AlignedIndentFilter(object):
    join_words = (r'((LEFT\s+|RIGHT\s+|FULL\s+)?'
                  r'(INNER\s+|OUTER\s+|STRAIGHT\s+)?|'
                  r'(CROSS\s+|NATURAL\s+)?)?JOIN\b')
    split_words = ('FROM',
                   join_words, 'ON',
                   'WHERE', 'AND', 'OR',
                   'GROUP', 'HAVING', 'LIMIT',
                   'ORDER', 'UNION', 'VALUES',
                   'SET', 'BETWEEN', 'EXCEPT')

    def __init__(self, char=' ', line_width=None):
        self.char = char
        self._max_kwd_len = len('select')

    def newline(self):
        return sql.Token(T.Newline, '\n')

    def whitespace(self, chars=0, newline_before=False, newline_after=False):
        return sql.Token(T.Whitespace, ('\n' if newline_before else '') +
                         self.char * chars + ('\n' if newline_after else ''))

    def _process_statement(self, tlist, base_indent=0):
        if tlist.tokens[0].is_whitespace() and base_indent == 0:
            tlist.tokens.pop(0)

        # process the main query body
        return self._process(sql.TokenList(tlist.tokens),
                             base_indent=base_indent)

    def _process_parenthesis(self, tlist, base_indent=0):
        if not tlist.token_next_by(m=(T.DML, 'SELECT')):
            # if this isn't a subquery, don't re-indent
            return tlist

        # add two for the space and parens
        sub_indent = base_indent + self._max_kwd_len + 2
        tlist.insert_after(tlist.tokens[0],
                           self.whitespace(sub_indent, newline_before=True))
        # de-indent the last parenthesis
        tlist.insert_before(tlist.tokens[-1],
                            self.whitespace(sub_indent - 1,
                                            newline_before=True))

        # process the inside of the parantheses
        tlist.tokens = (
            [tlist.tokens[0]] +
            self._process(sql.TokenList(tlist._groupable_tokens),
                          base_indent=sub_indent).tokens +
            [tlist.tokens[-1]]
        )
        return tlist

    def _process_identifierlist(self, tlist, base_indent=0):
        # columns being selected
        new_tokens = []
        identifiers = list(filter(
            lambda t: t.ttype not in (T.Punctuation, T.Whitespace, T.Newline),
            tlist.tokens))
        for i, token in enumerate(identifiers):
            if i > 0:
                new_tokens.append(self.newline())
                new_tokens.append(
                    self.whitespace(self._max_kwd_len + base_indent + 1))
            new_tokens.append(token)
            if i < len(identifiers) - 1:
                # if not last column in select, add a comma seperator
                new_tokens.append(sql.Token(T.Punctuation, ','))
        tlist.tokens = new_tokens

        # process any sub-sub statements (like case statements)
        for sgroup in tlist.get_sublists():
            self._process(sgroup, base_indent=base_indent)
        return tlist

    def _process_case(self, tlist, base_indent=0):
        base_offset = base_indent + self._max_kwd_len + len('case ')
        case_offset = len('when ')
        cases = tlist.get_cases(skip_ws=True)
        # align the end as well
        end_token = tlist.token_next_by(m=(T.Keyword, 'END'))
        cases.append((None, [end_token]))

        condition_width = max(
            len(' '.join(map(str, cond))) for cond, value in cases if cond)
        for i, (cond, value) in enumerate(cases):
            if cond is None:  # else or end
                stmt = value[0]
                line = value
            else:
                stmt = cond[0]
                line = cond + value
            if i > 0:
                tlist.insert_before(stmt, self.whitespace(
                    base_offset + case_offset - len(str(stmt))))
            if cond:
                tlist.insert_after(cond[-1], self.whitespace(
                    condition_width - len(' '.join(map(str, cond)))))

            if i < len(cases) - 1:
                # if not the END add a newline
                tlist.insert_after(line[-1], self.newline())

    def _next_token(self, tlist, idx=0):
        split_words = T.Keyword, self.split_words, True
        token = tlist.token_next_by(m=split_words, idx=idx)
        # treat "BETWEEN x and y" as a single statement
        if token and token.value.upper() == 'BETWEEN':
            token = self._next_token(tlist, token)
            if token and token.value.upper() == 'AND':
                token = self._next_token(tlist, token)
        return token

    def _split_kwds(self, tlist, base_indent=0):
        token = self._next_token(tlist)
        while token:
            # joins are special case. only consider the first word as aligner
            if token.match(T.Keyword, self.join_words, regex=True):
                token_indent = len(token.value.split()[0])
            else:
                token_indent = len(str(token))
            tlist.insert_before(token, self.whitespace(
                self._max_kwd_len - token_indent + base_indent,
                newline_before=True))
            next_idx = tlist.token_index(token) + 1
            token = self._next_token(tlist, next_idx)

    def _process_default(self, tlist, base_indent=0):
        self._split_kwds(tlist, base_indent)
        # process any sub-sub statements
        for sgroup in tlist.get_sublists():
            prev_token = tlist.token_prev(tlist.token_index(sgroup))
            indent_offset = 0
            # HACK: make "group/order by" work. Longer than _max_kwd_len.
            if prev_token and prev_token.match(T.Keyword, 'BY'):
                # TODO: generalize this
                indent_offset = 3
            self._process(sgroup, base_indent=base_indent + indent_offset)
        return tlist

    def _process(self, tlist, base_indent=0):
        func_name = '_process_{cls}'.format(cls=type(tlist).__name__)
        func = getattr(self, func_name.lower(), self._process_default)
        return func(tlist, base_indent=base_indent)

    def process(self, stmt):
        self._process(stmt)
        return stmt
