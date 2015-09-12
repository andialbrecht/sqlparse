# -*- coding: utf-8 -*-
#
# Copyright (C) 2016 Andi Albrecht, albrecht.andi@gmail.com
#
# This module is part of python-sqlparse and is released under
# the BSD License: http://www.opensource.org/licenses/bsd-license.php

import re

from sqlparse import sql, tokens as T
from sqlparse.compat import text_type
from sqlparse.utils import split_unquoted_newlines


# --------------------------
# token process

class _CaseFilter(object):
    ttype = None

    def __init__(self, case=None):
        case = case or 'upper'
        self.convert = getattr(text_type, case)

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


class TruncateStringFilter(object):
    def __init__(self, width, char):
        self.width = width
        self.char = char

    def process(self, stream):
        for ttype, value in stream:
            if ttype != T.Literal.String.Single:
                yield ttype, value
                continue

            if value[:2] == "''":
                inner = value[2:-2]
                quote = "''"
            else:
                inner = value[1:-1]
                quote = "'"

            if len(inner) > self.width:
                value = ''.join((quote, inner[:self.width], self.char, quote))
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
            prev = tlist.token_prev(tidx, skip_ws=False)
            next_ = tlist.token_next(tidx, skip_ws=False)
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


class SpacesAroundOperatorsFilter:
    whitelist = (sql.Identifier, sql.Comparison, sql.Where)

    def _process(self, tlist):
        def next_token(idx):
            # HACK: distinguish between real wildcard from multiplication operator
            return tlist.token_next_by_type(idx, (T.Operator, T.Comparison, T.Wildcard))
        idx = 0
        token = next_token(idx)
        while token:
            idx = tlist.token_index(token)
            if idx > 0 and tlist.tokens[idx - 1].ttype != T.Whitespace:
                tlist.tokens.insert(idx, sql.Token(T.Whitespace, ' '))  # insert before
                idx += 1
            if idx < len(tlist.tokens) - 1:
                if token.ttype == T.Wildcard and tlist.tokens[idx + 1].match(T.Punctuation, ','):
                    pass  # this must have been a real wildcard, not multiplication
                elif tlist.tokens[idx + 1].ttype != T.Whitespace:
                    tlist.tokens.insert(idx + 1, sql.Token(T.Whitespace, ' '))

            idx += 1
            token = next_token(idx)

        for sgroup in tlist.get_sublists():
            self._process(sgroup)

    def process(self, stack, stmt):
        self._process(stmt)


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


class AlignedIndentFilter:
    join_words = r'((LEFT\s+|RIGHT\s+|FULL\s+)?(INNER\s+|OUTER\s+|STRAIGHT\s+)?|(CROSS\s+|NATURAL\s+)?)?JOIN\b'
    split_words = (
        'FROM',
        join_words, 'ON',
        'WHERE', 'AND', 'OR',
        'GROUP', 'HAVING', 'LIMIT',
        'ORDER', 'UNION', 'VALUES',
        'SET', 'BETWEEN', 'EXCEPT',
        )

    def __init__(self, char=' ', line_width=None):
        self.char = char
        self._max_kwd_len = len('select')

    def newline(self):
        return sql.Token(T.Newline, '\n')

    def whitespace(self, chars=0, newline_before=False, newline_after=False):
        return sql.Token(
            T.Whitespace,
            (str(self.newline()) if newline_before else '') + self.char * chars + (str(self.newline()) if newline_after else ''))

    def _process_statement(self, tlist, base_indent=0):
        if tlist.tokens[0].is_whitespace() and base_indent == 0:
            tlist.tokens.pop(0)

        # process the main query body
        return self._process(sql.TokenList(tlist.tokens), base_indent=base_indent)

    def _process_parenthesis(self, tlist, base_indent=0):
        if not tlist.token_next_match(0, T.DML, 'SELECT'):
            # if this isn't a subquery, don't re-indent
            return tlist

        sub_indent = base_indent + self._max_kwd_len + 2  # add two for the space and parens
        tlist.insert_after(tlist.tokens[0], self.whitespace(sub_indent, newline_before=True))
        # de-indent the last parenthesis
        tlist.insert_before(tlist.tokens[-1], self.whitespace(sub_indent - 1, newline_before=True))

        # process the inside of the parantheses
        tlist.tokens = (
            [tlist.tokens[0]] +
            self._process(sql.TokenList(tlist._groupable_tokens), base_indent=sub_indent).tokens +
            [tlist.tokens[-1]]
            )
        return tlist

    def _process_identifierlist(self, tlist, base_indent=0):
        # columns being selected
        new_tokens = []
        identifiers = filter(lambda t: t.ttype not in (T.Punctuation, T.Whitespace, T.Newline), tlist.tokens)
        for i, token in enumerate(identifiers):
            if i > 0:
                new_tokens.append(self.newline())
                new_tokens.append(self.whitespace(self._max_kwd_len + base_indent + 1))
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
        end_token = tlist.token_next_match(0, T.Keyword, 'END')
        cases.append((None, [end_token]))

        condition_width = max(len(' '.join(map(str, cond))) for cond, value in cases if cond)
        for i, (cond, value) in enumerate(cases):
            if cond is None:  # else or end
                stmt = value[0]
                line = value
            else:
                stmt = cond[0]
                line = cond + value
            if i > 0:
                tlist.insert_before(stmt, self.whitespace(base_offset + case_offset - len(str(stmt))))
            if cond:
                tlist.insert_after(cond[-1], self.whitespace(condition_width - len(' '.join(map(str, cond)))))

            if i < len(cases) - 1:
                # if not the END add a newline
                tlist.insert_after(line[-1], self.newline())

    def _process_substatement(self, tlist, base_indent=0):
        def _next_token(i):
            t = tlist.token_next_match(i, T.Keyword, self.split_words, regex=True)
            # treat "BETWEEN x and y" as a single statement
            if t and t.value.upper() == 'BETWEEN':
                t = _next_token(tlist.token_index(t) + 1)
                if t and t.value.upper() == 'AND':
                    t = _next_token(tlist.token_index(t) + 1)
            return t

        idx = 0
        token = _next_token(idx)
        while token:
            if token.match(T.Keyword, self.join_words, regex=True):
                # joins are a special case. we only consider the first word of the join as the aligner
                token_indent = len(token.value.split()[0])
            else:
                token_indent = len(str(token))
            tlist.insert_before(token, self.whitespace(self._max_kwd_len - token_indent + base_indent, newline_before=True))
            next_idx = tlist.token_index(token) + 1
            token = _next_token(next_idx)

        # process any sub-sub statements
        for sgroup in tlist.get_sublists():
            prev_token = tlist.token_prev(tlist.token_index(sgroup))
            indent_offset = 0
            if prev_token and prev_token.match(T.Keyword, 'BY'):
                # HACK: make "group by" and "order by" indents work. these are longer than _max_kwd_len.
                # TODO: generalize this
                indent_offset = 3
            self._process(sgroup, base_indent=base_indent + indent_offset)
        return tlist

    def _process(self, tlist, base_indent=0, verbose=False):
        token_name = tlist.__class__.__name__.lower()
        func_name = '_process_%s' % token_name
        func = getattr(self, func_name, self._process_substatement)
        if verbose:
            print func.__name__, token_name, str(tlist)
        return func(tlist, base_indent=base_indent)

    def process(self, stack, stmt):
        self._process(stmt)


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
            elif token.is_group() and type(token) not in self.keep_together:
                token.tokens = self._process(token, token.tokens)
            else:
                val = text_type(token)
                if len(self.line) + len(val) > self.width:
                    match = re.search(r'^ +', self.line)
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
        raw = text_type(stmt)
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

        has_nl = len(text_type(stmt).strip().splitlines()) > 1
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
