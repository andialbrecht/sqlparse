# -*- coding: utf-8 -*-
#
# Copyright (C) 2016 Andi Albrecht, albrecht.andi@gmail.com
#
# This module is part of python-sqlparse and is released under
# the BSD License: http://www.opensource.org/licenses/bsd-license.php

import re

from sqlparse import sql, tokens as T
from sqlparse.compat import u, text_type
from sqlparse.utils import split_unquoted_newlines


# --------------------------
# token process

class _CaseFilter(object):

    ttype = None

    def __init__(self, case=None):
        if case is None:
            case = 'upper'
        assert case in ['lower', 'upper', 'capitalize']
        self.convert = getattr(text_type, case)

    def process(self, stream):
        for ttype, value in stream:
            if ttype in self.ttype:
                value = self.convert(value)
            yield ttype, value


class KeywordCaseFilter(_CaseFilter):
    ttype = T.Keyword


class IdentifierCaseFilter(_CaseFilter):
    ttype = (T.Name, T.String.Symbol)

    def process(self, stream):
        for ttype, value in stream:
            if ttype in self.ttype and not value.strip()[0] == '"':
                value = self.convert(value)
            yield ttype, value


class TruncateStringFilter(object):

    def __init__(self, width, char):
        self.width = max(width, 1)
        self.char = u(char)

    def process(self, stream):
        for ttype, value in stream:
            if ttype is T.Literal.String.Single:
                if value[:2] == '\'\'':
                    inner = value[2:-2]
                    quote = u'\'\''
                else:
                    inner = value[1:-1]
                    quote = u'\''
                if len(inner) > self.width:
                    value = u''.join((quote, inner[:self.width], self.char,
                                      quote))
            yield ttype, value


# ----------------------
# statement process

class StripCommentsFilter(object):

    def _get_next_comment(self, tlist):
        # TODO(andi) Comment types should be unified, see related issue38
        token = tlist.token_next_by(i=sql.Comment, t=T.Comment)
        return token

    def _process(self, tlist):
        token = self._get_next_comment(tlist)
        while token:
            tidx = tlist.token_index(token)
            prev = tlist.token_prev(tidx, False)
            next_ = tlist.token_next(tidx, False)
            # Replace by whitespace if prev and next exist and if they're not
            # whitespaces. This doesn't apply if prev or next is a paranthesis.
            if (prev is not None and next_ is not None
                and not prev.is_whitespace() and not next_.is_whitespace()
                and not (prev.match(T.Punctuation, '(')
                         or next_.match(T.Punctuation, ')'))):
                tlist.tokens[tidx] = sql.Token(T.Whitespace, ' ')
            else:
                tlist.tokens.pop(tidx)
            token = self._get_next_comment(tlist)

    def process(self, stmt):
        [self.process(sgroup) for sgroup in stmt.get_sublists()]
        self._process(stmt)


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
            if token.ttype is T.Punctuation \
               and token.value == ',' \
               and last_nl is not None:
                tlist.tokens.remove(last_nl)
            if token.is_whitespace():
                last_nl = token
            else:
                last_nl = None
        return self._stripws_default(tlist)

    def _stripws_parenthesis(self, tlist):
        if tlist.tokens[1].is_whitespace():
            tlist.tokens.pop(1)
        if tlist.tokens[-2].is_whitespace():
            tlist.tokens.pop(-2)
        self._stripws_default(tlist)

    def process(self, stmt, depth=0):
        [self.process(sgroup, depth + 1)
         for sgroup in stmt.get_sublists()]
        self._stripws(stmt)
        if (
            depth == 0
            and stmt.tokens
            and stmt.tokens[-1].is_whitespace()
        ):
            stmt.tokens.pop(-1)


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
            t = tlist.token_next_match(i, T.Keyword, split_words,
                                       regex=True)
            if t and t.value.upper() == 'BETWEEN':
                t = _next_token(tlist.token_index(t) + 1)
                if t and t.value.upper() == 'AND':
                    t = _next_token(tlist.token_index(t) + 1)
            return t

        idx = 0
        token = _next_token(idx)
        added = set()
        while token:
            prev = tlist.token_prev(tlist.token_index(token), False)
            offset = 1
            if prev and prev.is_whitespace() and prev not in added:
                tlist.tokens.pop(tlist.token_index(prev))
                offset += 1
            uprev = u(prev)
            if (prev and (uprev.endswith('\n') or uprev.endswith('\r'))):
                nl = tlist.token_next(token)
            else:
                nl = self.nl()
                added.add(nl)
                tlist.insert_before(token, nl)
                offset += 1
            token = _next_token(tlist.token_index(nl) + offset)

    def _split_statements(self, tlist):
        idx = 0
        token = tlist.token_next_by_type(idx, (T.Keyword.DDL, T.Keyword.DML))
        while token:
            prev = tlist.token_prev(tlist.token_index(token), False)
            if prev and prev.is_whitespace():
                tlist.tokens.pop(tlist.token_index(prev))
            # only break if it's not the first token
            if prev:
                nl = self.nl()
                tlist.insert_before(token, nl)
            token = tlist.token_next_by_type(tlist.token_index(token) + 1,
                                             (T.Keyword.DDL, T.Keyword.DML))

    def _process(self, tlist):
        func_name = '_process_%s' % tlist.__class__.__name__.lower()
        func = getattr(self, func_name, self._process_default)
        func(tlist)

    def _process_where(self, tlist):
        token = tlist.token_next_match(0, T.Keyword, 'WHERE')
        try:
            tlist.insert_before(token, self.nl())
        except ValueError:  # issue121, errors in statement
            pass
        self.indent += 1
        self._process_default(tlist)
        self.indent -= 1

    def _process_having(self, tlist):
        token = tlist.token_next_match(0, T.Keyword, 'HAVING')
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
            tlist.token_next_match(0, T.Punctuation, '('))
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
        end = tlist.token_next_match(0, T.Keyword, 'END')
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
                if u(self._last_stmt).endswith('\n'):
                    nl = '\n'
                else:
                    nl = '\n\n'
                stmt.tokens.insert(
                    0, sql.Token(T.Whitespace, nl))
            if self._last_stmt != stmt:
                self._last_stmt = stmt


# FIXME: Doesn't work
class RightMarginFilter(object):

    keep_together = (
        # sql.TypeCast, sql.Identifier, sql.Alias,
    )

    def __init__(self, width=79):
        self.width = width
        self.line = ''

    def _process(self, group, stream):
        for token in stream:
            if token.is_whitespace() and '\n' in token.value:
                if token.value.endswith('\n'):
                    self.line = ''
                else:
                    self.line = token.value.splitlines()[-1]
            elif (token.is_group()
                  and token.__class__ not in self.keep_together):
                token.tokens = self._process(token, token.tokens)
            else:
                val = u(token)
                if len(self.line) + len(val) > self.width:
                    match = re.search('^ +', self.line)
                    if match is not None:
                        indent = match.group()
                    else:
                        indent = ''
                    yield sql.Token(T.Whitespace, '\n%s' % indent)
                    self.line = indent
                self.line += val
            yield token

    def process(self, group):
        # return
        # group.tokens = self._process(group, group.tokens)
        raise NotImplementedError

# ---------------------------
# postprocess

class SerializerUnicode(object):

    def process(self, stmt):
        raw = u(stmt)
        lines = split_unquoted_newlines(raw)
        res = '\n'.join(line.rstrip() for line in lines)
        return res


class OutputFilter(object):
    varname_prefix = ''

    def __init__(self, varname='sql'):
        self.varname = self.varname_prefix + varname
        self.count = 0

    def _process(self, stream, varname, has_nl):
        raise NotImplementedError

    def process(self, stmt):
        self.count += 1
        if self.count > 1:
            varname = '%s%d' % (self.varname, self.count)
        else:
            varname = self.varname

        has_nl = len(u(stmt).strip().splitlines()) > 1
        stmt.tokens = self._process(stmt.tokens, varname, has_nl)
        return stmt


class OutputPythonFilter(OutputFilter):
    def _process(self, stream, varname, has_nl):
        # SQL query asignation to varname
        if self.count > 1:
            yield sql.Token(T.Whitespace, '\n')
        yield sql.Token(T.Name, varname)
        yield sql.Token(T.Whitespace, ' ')
        yield sql.Token(T.Operator, '=')
        yield sql.Token(T.Whitespace, ' ')
        if has_nl:
            yield sql.Token(T.Operator, '(')
        yield sql.Token(T.Text, "'")

        # Print the tokens on the quote
        for token in stream:
            # Token is a new line separator
            if token.is_whitespace() and '\n' in token.value:
                # Close quote and add a new line
                yield sql.Token(T.Text, " '")
                yield sql.Token(T.Whitespace, '\n')

                # Quote header on secondary lines
                yield sql.Token(T.Whitespace, ' ' * (len(varname) + 4))
                yield sql.Token(T.Text, "'")

                # Indentation
                after_lb = token.value.split('\n', 1)[1]
                if after_lb:
                    yield sql.Token(T.Whitespace, after_lb)
                continue

            # Token has escape chars
            elif "'" in token.value:
                token.value = token.value.replace("'", "\\'")

            # Put the token
            yield sql.Token(T.Text, token.value)

        # Close quote
        yield sql.Token(T.Text, "'")
        if has_nl:
            yield sql.Token(T.Operator, ')')


class OutputPHPFilter(OutputFilter):
    varname_prefix = '$'

    def _process(self, stream, varname, has_nl):
        # SQL query asignation to varname (quote header)
        if self.count > 1:
            yield sql.Token(T.Whitespace, '\n')
        yield sql.Token(T.Name, varname)
        yield sql.Token(T.Whitespace, ' ')
        if has_nl:
            yield sql.Token(T.Whitespace, ' ')
        yield sql.Token(T.Operator, '=')
        yield sql.Token(T.Whitespace, ' ')
        yield sql.Token(T.Text, '"')

        # Print the tokens on the quote
        for token in stream:
            # Token is a new line separator
            if token.is_whitespace() and '\n' in token.value:
                # Close quote and add a new line
                yield sql.Token(T.Text, ' ";')
                yield sql.Token(T.Whitespace, '\n')

                # Quote header on secondary lines
                yield sql.Token(T.Name, varname)
                yield sql.Token(T.Whitespace, ' ')
                yield sql.Token(T.Operator, '.=')
                yield sql.Token(T.Whitespace, ' ')
                yield sql.Token(T.Text, '"')

                # Indentation
                after_lb = token.value.split('\n', 1)[1]
                if after_lb:
                    yield sql.Token(T.Whitespace, after_lb)
                continue

            # Token has escape chars
            elif '"' in token.value:
                token.value = token.value.replace('"', '\\"')

            # Put the token
            yield sql.Token(T.Text, token.value)

        # Close quote
        yield sql.Token(T.Text, '"')
        yield sql.Token(T.Punctuation, ';')
