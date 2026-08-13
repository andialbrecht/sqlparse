#
# Copyright (C) 2009-2020 the sqlparse authors and contributors
# <see AUTHORS file>
#
# This module is part of python-sqlparse and is released under
# the BSD License: https://opensource.org/licenses/BSD-3-Clause

import re

from sqlparse import sql
from sqlparse import tokens as T
from sqlparse.utils import indent, offset

# The line boundaries str.splitlines() recognizes. Used only to tell whether a
# token value can possibly affect the line count, never to split.
HAS_LINE_BREAK = re.compile('[\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029]')


class _Unreachable(Exception):
    """*token* is not reachable from *group* by walking parents."""


def _tokens_before(group, token):
    """Yields the tokens of *group* that precede *token*, closest one first.

    Groups are yielded whole rather than descended into, so ``str()`` on the
    result still spells the preceding text but does not visit a leaf that the
    caller may not need to look at.
    """
    # Record where *token* sits inside each of its ancestors, up to *group*.
    ancestry = []
    node = token
    while node is not group:
        parent = node.parent
        try:
            ancestry.append((parent.tokens, parent.tokens.index(node)))
        except (AttributeError, ValueError):
            # *token* is not reachable from *group* -- StripCommentsFilter, for
            # one, splices in a replacement token whose parent is unset. The
            # backwards walk cannot answer this, so say so and let the caller
            # fall back to flattening the statement.
            raise _Unreachable from None
        node = parent

    for siblings, tidx in ancestry:
        for idx in range(tidx - 1, -1, -1):
            yield siblings[idx]


class ReindentFilter:
    def __init__(self, width=2, char=' ', wrap_after=0, n='\n',
                 comma_first=False, indent_after_first=False,
                 indent_columns=False, compact=False):
        self.n = n
        self.width = width
        self.char = char
        self.indent = 1 if indent_after_first else 0
        self.offset = 0
        self.wrap_after = wrap_after
        self.comma_first = comma_first
        self.indent_columns = indent_columns
        self.compact = compact
        self._curr_stmt = None
        self._last_stmt = None
        self._last_func = None

    def _flatten_up_to_token(self, token):
        """Yields all tokens up to token but excluding current."""
        if token.is_group:
            token = next(token.flatten())

        for t in self._curr_stmt.flatten():
            if t == token:
                break
            yield t

    @property
    def leading_ws(self):
        return self.offset + self.indent * self.width

    def _preceding_line(self, token):
        """Returns the last line of the text preceding *token*."""
        if (type(self)._flatten_up_to_token is not _ORIG_FLATTEN_UP_TO_TOKEN
                or '_flatten_up_to_token' in vars(self)):
            # _flatten_up_to_token has been replaced -- by a subclass, on this
            # class, or on this instance. Honour the replacement rather than the
            # equivalent-but-faster walk below.
            raw = ''.join(map(str, self._flatten_up_to_token(token)))
            return (raw or '\n').splitlines()[-1]

        if token.is_group:
            token = next(token.flatten())

        # Only the final line of the preceding text is ever used, so walk
        # backwards from *token* and stop once the text collected is guaranteed
        # to contain that whole line. Re-flattening the entire statement on
        # every call is what made reindenting quadratic in the token count.
        #
        # Two line boundaries are needed rather than one, because splitlines()
        # ignores a *trailing* boundary: "a\nb\n" ends on the line "b", so a
        # token ending in a break does not start a fresh line. Stopping after
        # the third token that holds a boundary guarantees two boundaries even
        # in the worst case, where a "\r\n" is split across a token edge and so
        # counts only once.
        chunks = []
        breaks = 0
        try:
            for t in _tokens_before(self._curr_stmt, token):
                value = str(t)
                chunks.append(value)
                if HAS_LINE_BREAK.search(value):
                    breaks += 1
                    if breaks == 3:
                        break
        except _Unreachable:
            # A token spliced in without a parent (StripCommentsFilter does
            # this) cannot be located by walking parents. Flatten instead.
            raw = ''.join(map(str, self._flatten_up_to_token(token)))
            return (raw or '\n').splitlines()[-1]
        chunks.reverse()

        return (''.join(chunks) or '\n').splitlines()[-1]

    def _get_offset(self, token):
        line = self._preceding_line(token)
        # Now take current offset into account and return relative offset.
        return len(line) - len(self.char * self.leading_ws)

    def nl(self, offset=0):
        return sql.Token(
            T.Whitespace,
            self.n + self.char * max(0, self.leading_ws + offset))

    def _next_token(self, tlist, idx=-1):
        split_words = ('FROM', 'STRAIGHT_JOIN$', 'JOIN$', 'AND', 'OR',
                       'GROUP BY', 'ORDER BY', 'UNION', 'VALUES',
                       'SET', 'BETWEEN', 'EXCEPT', 'HAVING', 'LIMIT')
        m_split = T.Keyword, split_words, True
        tidx, token = tlist.token_next_by(m=m_split, idx=idx)

        if token and token.normalized == 'BETWEEN':
            tidx, token = self._next_token(tlist, tidx)

            if token and token.normalized == 'AND':
                tidx, token = self._next_token(tlist, tidx)

        return tidx, token

    def _split_kwds(self, tlist):
        tidx, token = self._next_token(tlist)
        while token:
            pidx, prev_ = tlist.token_prev(tidx, skip_ws=False)
            uprev = str(prev_)

            if prev_ and prev_.is_whitespace:
                del tlist.tokens[pidx]
                tidx -= 1

            if not (uprev.endswith('\n') or uprev.endswith('\r')):
                tlist.insert_before(tidx, self.nl())
                tidx += 1

            tidx, token = self._next_token(tlist, tidx)

    def _split_statements(self, tlist):
        ttypes = T.Keyword.DML, T.Keyword.DDL
        tidx, token = tlist.token_next_by(t=ttypes)
        while token:
            pidx, prev_ = tlist.token_prev(tidx, skip_ws=False)
            if prev_ and prev_.is_whitespace:
                del tlist.tokens[pidx]
                tidx -= 1
            # only break if it's not the first token
            if prev_:
                tlist.insert_before(tidx, self.nl())
                tidx += 1
            tidx, token = tlist.token_next_by(t=ttypes, idx=tidx)

    def _process(self, tlist):
        func_name = f'_process_{type(tlist).__name__}'
        func = getattr(self, func_name.lower(), self._process_default)
        func(tlist)

    def _process_where(self, tlist):
        tidx, token = tlist.token_next_by(m=(T.Keyword, 'WHERE'))
        if not token:
            return
        # issue121, errors in statement fixed??
        tlist.insert_before(tidx, self.nl())
        with indent(self):
            self._process_default(tlist)

    def _process_parenthesis(self, tlist):
        ttypes = T.Keyword.DML, T.Keyword.DDL
        _, is_dml_dll = tlist.token_next_by(t=ttypes)
        fidx, first = tlist.token_next_by(m=sql.Parenthesis.M_OPEN)
        if first is None:
            return

        with indent(self, 1 if is_dml_dll else 0):
            tlist.tokens.insert(0, self.nl()) if is_dml_dll else None
            with offset(self, self._get_offset(first) + 1):
                self._process_default(tlist, not is_dml_dll)

    def _process_function(self, tlist):
        self._last_func = tlist[0]
        self._process_default(tlist)

    def _process_identifierlist(self, tlist):
        identifiers = list(tlist.get_identifiers())
        if self.indent_columns:
            first = next(identifiers[0].flatten())
            num_offset = 1 if self.char == '\t' else self.width
        else:
            first = next(identifiers.pop(0).flatten())
            num_offset = 1 if self.char == '\t' else self._get_offset(first)

        if not tlist.within(sql.Function) and not tlist.within(sql.Values):
            with offset(self, num_offset):
                position = 0
                for token in identifiers:
                    # Add 1 for the "," separator
                    position += len(token.value) + 1
                    if position > (self.wrap_after - self.offset):
                        adjust = 0
                        if self.comma_first:
                            adjust = -2
                            _, comma = tlist.token_prev(
                                tlist.token_index(token))
                            if comma is None:
                                continue
                            token = comma
                        tlist.insert_before(token, self.nl(offset=adjust))
                        if self.comma_first:
                            _, ws = tlist.token_next(
                                tlist.token_index(token), skip_ws=False)
                            if (ws is not None
                                    and ws.ttype is not T.Text.Whitespace):
                                tlist.insert_after(
                                    token, sql.Token(T.Whitespace, ' '))
                        position = 0
        else:
            # ensure whitespace
            for token in tlist:
                _, next_ws = tlist.token_next(
                    tlist.token_index(token), skip_ws=False)
                if token.value == ',' and not next_ws.is_whitespace:
                    tlist.insert_after(
                        token, sql.Token(T.Whitespace, ' '))

            end_at = self.offset + sum(len(i.value) + 1 for i in identifiers)
            adjusted_offset = 0
            if (self.wrap_after > 0
                    and end_at > (self.wrap_after - self.offset)
                    and self._last_func):
                adjusted_offset = -len(self._last_func.value) - 1

            with offset(self, adjusted_offset), indent(self):
                if adjusted_offset < 0:
                    tlist.insert_before(identifiers[0], self.nl())
                position = 0
                for token in identifiers:
                    # Add 1 for the "," separator
                    position += len(token.value) + 1
                    if (self.wrap_after > 0
                            and position > (self.wrap_after - self.offset)):
                        adjust = 0
                        tlist.insert_before(token, self.nl(offset=adjust))
                        position = 0
        self._process_default(tlist)

    def _process_case(self, tlist):
        iterable = iter(tlist.get_cases())
        cond, _ = next(iterable)
        first = next(cond[0].flatten())

        with offset(self, self._get_offset(tlist[0])):
            with offset(self, self._get_offset(first)):
                for cond, value in iterable:
                    str_cond = ''.join(str(x) for x in cond or [])
                    str_value = ''.join(str(x) for x in value)
                    end_pos = self.offset + 1 + len(str_cond) + len(str_value)
                    if (not self.compact and end_pos > self.wrap_after):
                        token = value[0] if cond is None else cond[0]
                        tlist.insert_before(token, self.nl())

                # Line breaks on group level are done. let's add an offset of
                # len "when ", "then ", "else "
                with offset(self, len("WHEN ")):
                    self._process_default(tlist)
            end_idx, end = tlist.token_next_by(m=sql.Case.M_CLOSE)
            if end_idx is not None and not self.compact:
                tlist.insert_before(end_idx, self.nl())

    def _process_values(self, tlist):
        tlist.insert_before(0, self.nl())
        tidx, token = tlist.token_next_by(i=sql.Parenthesis)
        first_token = token
        while token:
            ptidx, ptoken = tlist.token_next_by(m=(T.Punctuation, ','),
                                                idx=tidx)
            if ptoken:
                if self.comma_first:
                    adjust = -2
                    offset = self._get_offset(first_token) + adjust
                    tlist.insert_before(ptoken, self.nl(offset))
                else:
                    tlist.insert_after(ptoken,
                                       self.nl(self._get_offset(token)))
            tidx, token = tlist.token_next_by(i=sql.Parenthesis, idx=tidx)

    def _process_default(self, tlist, stmts=True):
        self._split_statements(tlist) if stmts else None
        self._split_kwds(tlist)
        for sgroup in tlist.get_sublists():
            self._process(sgroup)

    def process(self, stmt):
        self._curr_stmt = stmt
        self._process(stmt)

        if self._last_stmt is not None:
            nl = '\n' if str(self._last_stmt).endswith('\n') else '\n\n'
            stmt.tokens.insert(0, sql.Token(T.Whitespace, nl))

        self._last_stmt = stmt
        return stmt


# The shipped _flatten_up_to_token, captured so that _preceding_line can tell
# whether it is still in place and only then take its faster equivalent path.
_ORIG_FLATTEN_UP_TO_TOKEN = ReindentFilter._flatten_up_to_token
