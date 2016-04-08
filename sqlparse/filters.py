# -*- coding: utf-8 -*-

import re

from os.path import abspath, join

from sqlparse import sql, tokens as T
from sqlparse.compat import u, text_type
from sqlparse.engine import FilterStack
from sqlparse.pipeline import Pipeline
from sqlparse.tokens import (Comment, Comparison, Keyword, Name, Punctuation,
                             String, Whitespace)
from sqlparse.utils import memoize_generator
from sqlparse.utils import split_unquoted_newlines


# --------------------------
# token process

class _CaseFilter:

    ttype = None

    def __init__(self, case=None):
        if case is None:
            case = 'upper'
        assert case in ['lower', 'upper', 'capitalize']
        self.convert = getattr(text_type, case)

    def process(self, stack, stream):
        for ttype, value in stream:
            if ttype in self.ttype:
                value = self.convert(value)
            yield ttype, value


class KeywordCaseFilter(_CaseFilter):
    ttype = T.Keyword


class IdentifierCaseFilter(_CaseFilter):
    ttype = (T.Name, T.String.Symbol)

    def process(self, stack, stream):
        for ttype, value in stream:
            if ttype in self.ttype and not value.strip()[0] == '"':
                value = self.convert(value)
            yield ttype, value


class TruncateStringFilter:

    def __init__(self, width, char):
        self.width = max(width, 1)
        self.char = u(char)

    def process(self, stack, stream):
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


class GetComments:
    """Get the comments from a stack"""
    def process(self, stack, stream):
        for token_type, value in stream:
            if token_type in Comment:
                yield token_type, value


class StripComments:
    """Strip the comments from a stack"""
    def process(self, stack, stream):
        for token_type, value in stream:
            if token_type not in Comment:
                yield token_type, value


def StripWhitespace(stream):
    "Strip the useless whitespaces from a stream leaving only the minimal ones"
    last_type = None
    has_space = False
    ignore_group = frozenset((Comparison, Punctuation))

    for token_type, value in stream:
        # We got a previous token (not empty first ones)
        if last_type:
            if token_type in Whitespace:
                has_space = True
                continue

        # Ignore first empty spaces and dot-commas
        elif token_type in (Whitespace, Whitespace.Newline, ignore_group):
            continue

        # Yield a whitespace if it can't be ignored
        if has_space:
            if not ignore_group.intersection((last_type, token_type)):
                yield Whitespace, ' '
            has_space = False

        # Yield the token and set its type for checking with the next one
        yield token_type, value
        last_type = token_type


class IncludeStatement:
    """Filter that enable a INCLUDE statement"""

    def __init__(self, dirpath=".", maxrecursive=10, raiseexceptions=False):
        if maxrecursive <= 0:
            raise ValueError('Max recursion limit reached')

        self.dirpath = abspath(dirpath)
        self.maxRecursive = maxrecursive
        self.raiseexceptions = raiseexceptions

        self.detected = False

    @memoize_generator
    def process(self, stack, stream):
        # Run over all tokens in the stream
        for token_type, value in stream:
            # INCLUDE statement found, set detected mode
            if token_type in Name and value.upper() == 'INCLUDE':
                self.detected = True
                continue

            # INCLUDE statement was found, parse it
            elif self.detected:
                # Omit whitespaces
                if token_type in Whitespace:
                    continue

                # Found file path to include
                if token_type in String.Symbol:
                    # Get path of file to include
                    path = join(self.dirpath, value[1:-1])

                    try:
                        f = open(path)
                        raw_sql = f.read()
                        f.close()

                    # There was a problem loading the include file
                    except IOError as err:
                        # Raise the exception to the interpreter
                        if self.raiseexceptions:
                            raise

                        # Put the exception as a comment on the SQL code
                        yield Comment, u'-- IOError: %s\n' % err

                    else:
                        # Create new FilterStack to parse readed file
                        # and add all its tokens to the main stack recursively
                        try:
                            filtr = IncludeStatement(self.dirpath,
                                                     self.maxRecursive - 1,
                                                     self.raiseexceptions)

                        # Max recursion limit reached
                        except ValueError as err:
                            # Raise the exception to the interpreter
                            if self.raiseexceptions:
                                raise

                            # Put the exception as a comment on the SQL code
                            yield Comment, u'-- ValueError: %s\n' % err

                        stack = FilterStack()
                        stack.preprocess.append(filtr)

                        for tv in stack.run(raw_sql):
                            yield tv

                    # Set normal mode
                    self.detected = False

                # Don't include any token while in detected mode
                continue

            # Normal token
            yield token_type, value


# ----------------------
# statement process

class StripCommentsFilter:

    def _get_next_comment(self, tlist):
        # TODO(andi) Comment types should be unified, see related issue38
        token = tlist.token_next_by_instance(0, sql.Comment)
        if token is None:
            token = tlist.token_next_by_type(0, T.Comment)
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

    def process(self, stack, stmt):
        [self.process(stack, sgroup) for sgroup in stmt.get_sublists()]
        self._process(stmt)


class StripWhitespaceFilter:

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

    def process(self, stack, stmt, depth=0):
        [self.process(stack, sgroup, depth + 1)
         for sgroup in stmt.get_sublists()]
        self._stripws(stmt)
        if (
            depth == 0
            and stmt.tokens
            and stmt.tokens[-1].is_whitespace()
        ):
            stmt.tokens.pop(-1)


class ReindentFilter:

    def __init__(self, width=2, char=' ', line_width=None):
        self.width = width
        self.char = char
        self.indent = 0
        self.offset = 0
        self.line_width = line_width
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
            for token in identifiers[1:]:
                tlist.insert_before(token, self.nl())
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

    def process(self, stack, stmt):
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


# FIXME: Doesn't work ;)
class RightMarginFilter:

    keep_together = (
        # sql.TypeCast, sql.Identifier, sql.Alias,
    )

    def __init__(self, width=79):
        self.width = width
        self.line = ''

    def _process(self, stack, group, stream):
        for token in stream:
            if token.is_whitespace() and '\n' in token.value:
                if token.value.endswith('\n'):
                    self.line = ''
                else:
                    self.line = token.value.splitlines()[-1]
            elif (token.is_group()
                  and token.__class__ not in self.keep_together):
                token.tokens = self._process(stack, token, token.tokens)
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

    def process(self, stack, group):
        return
        group.tokens = self._process(stack, group, group.tokens)


class InfoCreateTable(object):
    # sqlparse outputs some tokens as Keyword type at places where they are names
    ALLOWED_KEYWORD_AS_NAME = set((
        'data',
        'source',
        'type',
    ))

    def process(self, stack, stream):
        class St:
            create = 0
            table = 1
            table_name = 2
            create_table_open_paren = 3
            column_name = 4
            column_type = 5
            column_ignore_rest = 6
            ignore_rest = 7
            finished = 8
            ignore_remaining_statement = 9

        state = St.create
        error = ''
        parens = 0

        for token_type, value in StripWhitespace(stream):

            # Ignore comments
            if token_type in (Comment, Whitespace):
                continue

            if state == St.create:
                table_name = ''
                columns = {} # index => (name, type)
                column_names = set()
                column = None

                if token_type in Keyword and value.upper() == 'CREATE':
                    state = St.table
                else:
                    error = 'Not a CREATE statement'
            elif state == St.table:
                if token_type in Keyword and value.upper() == 'TABLE':
                    state = St.table_name
                else:
                    error = 'Not a CREATE TABLE statement'
            elif state == St.table_name:
                if token_type in Name:
                    state = St.create_table_open_paren
                    table_name += value
                else:
                    error = 'No table name given'
            elif state == St.create_table_open_paren:
                if token_type in Punctuation:
                    if value == '(':
                        state = St.column_name
                    elif value == '.':
                        table_name += '.'
                        state = St.table_name

                if state == St.create_table_open_paren:
                    error = 'No opening paren for CREATE TABLE'
            elif state == St.column_name:
                if token_type in Name or (token_type in Keyword and value.lower() in InfoCreateTable.ALLOWED_KEYWORD_AS_NAME):
                    column = [self._to_column_name(value), None, None]
                    state = St.column_type
                elif token_type in Keyword:
                    state = St.ignore_rest
                else:
                    error = 'No column name given'
            elif state == St.column_type:
                if token_type in Name:
                    column[1] = value
                    state = St.column_ignore_rest
                else:
                    error = 'No column type given'
            elif state == St.ignore_rest:
                if token_type in Punctuation:
                    if value == '(':
                        parens += 1
                    elif value == ')':
                        if parens == 0: # closes 'CREATE TABLE ('
                            state = St.finished
                        else:
                            parens -= 1
                    elif value == ',' and parens == 0:
                        state = St.column_name
            elif state == St.column_ignore_rest:
                if token_type in Punctuation and parens == 0: # ignore anything in parens
                    add_column = False

                    if value == '(':
                        parens += 1
                    elif value == ')':
                        if parens == 0: # closes 'CREATE TABLE ('
                            state = St.finished

                            add_column = True
                        else: # pragma: no cover
                            error = 'Logic error (end of column declaration #1)'
                    elif value == ',':
                        add_column = True

                        state = St.column_name

                    if add_column:
                        if column[0] in column_names:
                            error = 'Duplicate column name: %s' % column[0]
                        else:
                            column_names.add(column[0])
                            # Store column index, name and type
                            columns[len(columns)] = tuple(column)

                        column = None
                elif token_type in Keyword and parens == 0:
                    keyword_value = value.upper()
                    if keyword_value in ('NULL', 'NOT NULL'):
                        column[2] = keyword_value
                elif token_type in Punctuation and parens > 0:
                    # ignore anything in parens
                    if value == '(':
                        parens += 1
                    elif value == ')':
                        parens -= 1

                # else ignore until comma or end of statement
            elif state == St.finished:
                # Finished one CREATE TABLE statement, yield result and try to parse next statement
                # (after semicolon)
                yield (table_name, columns)

                if token_type in Punctuation and value == ';':
                    state = St.create
                else:
                    state = St.ignore_remaining_statement
            elif state == St.ignore_remaining_statement:
                # Ignore until semicolon
                if token_type in Punctuation and value == ';':
                    state = St.create
            else: # pragma: no cover
                error = 'Unknown state %r' % state

            if error:
                raise ValueError('%s (token_type: %r, value: %r, column: %r)' % (error, token_type, value, column))

        if not error:
            if state == St.finished: # no more tokens after ')'
                yield (table_name, columns)

            if state not in (St.create, St.finished, St.ignore_remaining_statement):
                error = 'Unexpected end state %r (token_type: %r, value: %r, column: %r)' % (state, token_type, value, column)

        if error:
            raise ValueError(error)

    @staticmethod
    def _to_column_name(token_value):
        return token_value.strip(u'`´')


class ColumnsSelect:
    """Get the columns names of a SELECT query"""
    def process(self, stack, stream):
        mode = 0
        oldValue = ""
        parenthesis = 0

        for token_type, value in stream:
            # Ignore comments
            if token_type in Comment:
                continue

            # We have not detected a SELECT statement
            if mode == 0:
                if token_type in Keyword and value == 'SELECT':
                    mode = 1

            # We have detected a SELECT statement
            elif mode == 1:
                if value == 'FROM':
                    if oldValue:
                        yield oldValue

                    mode = 3    # Columns have been checked

                elif value == 'AS':
                    oldValue = ""
                    mode = 2

                elif (token_type == Punctuation
                      and value == ',' and not parenthesis):
                    if oldValue:
                        yield oldValue
                    oldValue = ""

                elif token_type not in Whitespace:
                    if value == '(':
                        parenthesis += 1
                    elif value == ')':
                        parenthesis -= 1

                    oldValue += value

            # We are processing an AS keyword
            elif mode == 2:
                # We check also for Keywords because a bug in SQLParse
                if token_type == Name or token_type == Keyword:
                    yield value
                    mode = 1


# ---------------------------
# postprocess

class SerializerUnicode:

    def process(self, stack, stmt):
        raw = u(stmt)
        lines = split_unquoted_newlines(raw)
        res = '\n'.join(line.rstrip() for line in lines)
        return res


def Tokens2Unicode(stream):
    result = ""

    for _, value in stream:
        result += u(value)

    return result


class OutputFilter:
    varname_prefix = ''

    def __init__(self, varname='sql'):
        self.varname = self.varname_prefix + varname
        self.count = 0

    def _process(self, stream, varname, has_nl):
        raise NotImplementedError

    def process(self, stack, stmt):
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


class Limit:
    """Get the LIMIT of a query.

    If not defined, return -1 (SQL specification for no LIMIT query)
    """
    def process(self, stack, stream):
        index = 7
        stream = list(stream)
        stream.reverse()

        # Run over all tokens in the stream from the end
        for token_type, value in stream:
            index -= 1

#            if index and token_type in Keyword:
            if index and token_type in Keyword and value == 'LIMIT':
                return stream[4 - index][1]

        return -1


def compact(stream):
    """Function that return a compacted version of the stream"""
    pipe = Pipeline()

    pipe.append(StripComments())
    pipe.append(StripWhitespace)

    return pipe(stream)
