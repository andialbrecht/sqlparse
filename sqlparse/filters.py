# -*- coding: utf-8 -*-

import re

from os.path  import abspath, join
from warnings import warn

from sqlparse import sql, tokens as T
from sqlparse.engine import FilterStack
from sqlparse.lexer import tokenize
from sqlparse.pipeline import Pipeline
from sqlparse.tokens import (Comment, Comparison, Keyword, Name, Punctuation,
                             String, Whitespace)
from sqlparse.utils import memoize_generator


# --------------------------
# token process

class _CaseFilter:

    ttype = None

    def __init__(self, case=None):
        if case is None:
            case = 'upper'
        assert case in ['lower', 'upper', 'capitalize']
        self.convert = getattr(unicode, case)

    def process(self, stack, stream):
        warn("Deprecated, use callable objects. This will be removed at 0.2.0",
             DeprecationWarning)

        for ttype, value in stream:
            if ttype in self.ttype:
                value = self.convert(value)
            yield ttype, value


class KeywordCaseFilter(_CaseFilter):
    ttype = T.Keyword


class IdentifierCaseFilter(_CaseFilter):
    ttype = (T.Name, T.String.Symbol)

    def process(self, stack, stream):
        warn("Deprecated, use callable objects. This will be removed at 0.2.0",
             DeprecationWarning)

        for ttype, value in stream:
            if ttype in self.ttype and not value.strip()[0] == '"':
                value = self.convert(value)
            yield ttype, value


class GetComments:
    """Get the comments from a stack"""
    def process(self, stack, stream):
        warn("Deprecated, use callable objects. This will be removed at 0.2.0",
             DeprecationWarning)

        for token_type, value in stream:
            if token_type in Comment:
                yield token_type, value


class StripComments:
    """Strip the comments from a stack"""
    def process(self, stack, stream):
        warn("Deprecated, use callable objects. This will be removed at 0.2.0",
             DeprecationWarning)

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
        warn("Deprecated, use callable objects. This will be removed at 0.2.0",
             DeprecationWarning)

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
#                if token_type in tokens.String.Symbol:

                    # Get path of file to include
                    path = join(self.dirpath, value[1:-1])

                    try:
                        f = open(path)
                        raw_sql = f.read()
                        f.close()

                    # There was a problem loading the include file
                    except IOError, err:
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
                        except ValueError, err:
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
        warn("Deprecated, use callable objects. This will be removed at 0.2.0",
             DeprecationWarning)

        [self.process(stack, sgroup) for sgroup in stmt.get_sublists()]
        self._process(stmt)


class StripWhitespaceFilter:

    def _stripws(self, tlist):
        func_name = '_stripws_%s' % tlist.__class__.__name__.lower()
        func = getattr(self, func_name, self._stripws_default)
        func(tlist)

    def _stripws_default(self, tlist):
        last_was_ws = False
        for token in tlist.tokens:
            if token.is_whitespace():
                if last_was_ws:
                    token.value = ''
                else:
                    token.value = ' '
            last_was_ws = token.is_whitespace()

    def _stripws_parenthesis(self, tlist):
        if tlist.tokens[1].is_whitespace():
            tlist.tokens.pop(1)
        if tlist.tokens[-2].is_whitespace():
            tlist.tokens.pop(-2)
        self._stripws_default(tlist)

    def process(self, stack, stmt, depth=0):
        warn("Deprecated, use callable objects. This will be removed at 0.2.0",
             DeprecationWarning)

        [self.process(stack, sgroup, depth + 1)
         for sgroup in stmt.get_sublists()]
        self._stripws(stmt)
        if depth == 0 and stmt.tokens[-1].is_whitespace():
            stmt.tokens.pop(-1)


class ReindentFilter:
    """
    Filter that return a correctly indented version of the SQL string
    """

    def __init__(self, width=2, char=' ', line_width=None):
        self.width = width
        self.char = char
        self.indent = 0
        self.offset = 0
        self.line_width = line_width
        self._curr_stmt = None
        self._last_stmt = None

    def _get_offset(self, token):
        """
        Return the offset where the token should be indented
        """
        # Get last processed line (the current one) up to the next token
        all_ = list(self._curr_stmt.flatten())
        idx = all_.index(token)
        raw = ''.join(unicode(x) for x in all_[:idx + 1])
        line = raw.splitlines()[-1]

        # Now take current offset into account and return relative offset.
        full_offset = len(line) - len(self.char * self.width * self.indent)
        return full_offset - self.offset

    def _gentabs(self, offset):
        result = ''
        if self.char == '\t':
            tabs, offset = divmod(offset, self.width)
            result += self.char * tabs
        result += ' ' * offset

        return result

    def nl(self):
        """
        Return an indented new line token
        """
        # TODO: newline character should be configurable
        ws = '\n' + self._gentabs(self.indent * self.width + self.offset)
        return sql.Token(T.Whitespace, ws)

    def _split_kwds(self, tlist):
        """
        Split `tlist` by its keywords
        """
        split_words = ('FROM', 'JOIN$', 'AND', 'OR',
                       'GROUP', 'ORDER', 'UNION', 'VALUES',
                       'SET', 'BETWEEN')

        def _next_token(i):
            """
            Get next keyword where to split
            """
            # Search for the first keyword token
            t = tlist.token_next_match(i, T.Keyword, split_words, regex=True)

            # Use the BETWEEN ... AND ... struct as an unsplitable statement
            if t and t.value.upper() == 'BETWEEN':
                t = _next_token(tlist.token_index(t) + 1)
                if t and t.value.upper() == 'AND':
                    t = _next_token(tlist.token_index(t) + 1)

            # Return the token
            return t

        # Get first token
        token = _next_token(0)
        while token:
            offset = 1
            nl = None

            # Check if we have any token before
            prev = tlist.token_prev(tlist.token_index(token), False)
            if prev:
                # Previous token was a whitespace, increase offset
                if prev.is_whitespace():
                    tlist.tokens.pop(tlist.token_index(prev))
                    offset += 1

                # Previous token was a comment, add new line if necessary
                if isinstance(prev, sql.Comment):
                    prev = str(prev)
                    if prev.endswith('\n') or prev.endswith('\r'):
                        nl = tlist.token_next(token)

            # New line was not added, set it now
            if nl == None:
                nl = self.nl()
                tlist.insert_before(token, nl)

            # Add token now
            token = _next_token(tlist.token_index(nl) + offset)

    def _split_statements(self, tlist):
        """
        Split tlist on statements
        """
        # Search for the first statement
        token = tlist.token_next_by_type(0, (T.Keyword.DDL, T.Keyword.DML))

        while token:
            prev = tlist.token_prev(tlist.token_index(token), False)
            if prev:
                if prev.is_whitespace():
                    tlist.tokens.pop(tlist.token_index(prev))

                # only break if it's not the first token
                nl = self.nl()
                tlist.insert_before(token, nl)

            # Go to the next statement
            token = tlist.token_next_by_type(tlist.token_index(token) + 1,
                                             (T.Keyword.DDL, T.Keyword.DML))

    def _process(self, tlist):
        """
        Proxy to other methods based on `tlist` class
        """
        func_name = '_process_%s' % tlist.__class__.__name__.lower()
        func = getattr(self, func_name, self._process_default)
        func(tlist)

    def _process_where(self, tlist):
        """
        Process WHERE statement
        """
        # Look for the next WHERE keyword and add a new line
        token = tlist.token_next_match(0, T.Keyword, 'WHERE')
        tlist.insert_before(token, self.nl())

        # Indent and process the (indented) WHERE statement as usual
        self.indent += 1
        self._process_default(tlist)
        self.indent -= 1

    def _process_parenthesis(self, tlist):
        """
        Process parenthesis
        """
        # Omit the 'open parenthesis' token
        # and check if the next one require say us we should indent
        first = tlist.token_next(0)
        indented = first and first.ttype in (T.Keyword.DML, T.Keyword.DDL)

        # If we should indent, increase indent and add a new line
        if indented:
            self.indent += 1
            tlist.tokens.insert(0, self.nl())

        # Get indentation offset
        token = tlist.token_next_match(0, T.Punctuation, '(')
        num_offset = self._get_offset(token)

        # Increase indentation offset and process the statement as usual
        self.offset += num_offset
        self._process_default(tlist, stmts=not indented)
        self.offset -= num_offset

        # If we indented, decrease indent to previous state
        if indented:
            self.indent -= 1

    def _process_identifierlist(self, tlist):
        """
        Process an identifier list

        If there are more than an identifier, put each on a line
        """
        # Split the identifier list if we are not in a function
        if not tlist.within(sql.Function):
            # Get identifiers from the tlist
            identifiers = list(tlist.get_identifiers())

            # Split the identifier list if we have more than one identifier
            if len(identifiers) > 1:
                # Get first token
                first = list(identifiers[0].flatten())[0]

                # Increase offset the size of the first token
                num_offset = self._get_offset(first) - len(first.value)

                # Increase offset and insert new lines
                self.offset += num_offset
                offset = 0

                # Insert a new line between the tokens
                ignore = False
                for token in identifiers[1:]:
                    if not ignore:
                        tlist.insert_before(token, self.nl())
                    ignore = token.ttype

                    # Check identifiers offset
                    if token.ttype:
                        l = len(token.value)
                        if offset < l:
                            offset = l

                # Imsert another new line after comment tokens
                for token in tlist.tokens:
                    if isinstance(token, sql.Comment):
                        tlist.insert_after(token, self.nl())

                # Update identifiers offset
                if offset:
                    offset += 1

                    ignore = False
                    for token in identifiers:
                        if not ignore and not token.ttype:
                            prev = tlist.token_prev(token, False)
                            if prev:
                                if prev.ttype == T.Whitespace:
                                    value = prev.value

                                    spaces = 0
                                    while value and value[-1] == ' ':
                                        value = value[:-1]
                                        spaces += 1

                                    value += self._gentabs(spaces + offset)
                                    prev.value = value
                                else:
                                    ws = sql.Token(T.Whitespace,
                                                   self._gentabs(offset))
                                    tlist.insert_before(token, ws)

                            # Just first identifier
                            else:
                                ws = sql.Token(T.Whitespace, ' ' * offset)
                                tlist.insert_before(token, ws)

                        ignore = token.ttype

                # Decrease offset the size of the first token
                self.offset -= num_offset

        # Process the identifier list as usual
        self._process_default(tlist)

    def _process_case(self, tlist):
        """
        Process a CASE statement
        """
        # Increase the offset the size of the CASE keyword
        case = tlist.tokens[0]
        outer_offset = self._get_offset(case) - len(case.value)
        self.offset += outer_offset

        # Get the case conditions
        cases = tlist.get_cases()

        # Get and increase the offset the size of the condition selector
        cond, value = cases[0]
        tcond = list(cond[0].flatten())[0]
        num_offset = self._get_offset(tcond) - len(tcond.value)
        self.offset += num_offset

        # Insert a new line before each condition
        for cond, value in cases[1:]:
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

        # Decrease the offset the size of the condition selector
        self.offset -= num_offset

        # Insert a new line before the case END keyword
        end = tlist.token_next_match(0, T.Keyword, 'END')
        tlist.insert_before(end, self.nl())

        # Decrease the offset the size of the CASE keyword
        self.offset -= outer_offset

    def _process_default(self, tlist, stmts=True, kwds=True):
        """
        Generic processing of `tlist` statements
        """
        if stmts:
            self._split_statements(tlist)
        if kwds:
            self._split_kwds(tlist)

        for sgroup in tlist.get_sublists():
            self._process(sgroup)

    def process(self, stack, stmt):
        warn("Deprecated, use callable objects. This will be removed at 0.2.0",
             DeprecationWarning)

        # If we are processing a statement, set it as the current one
        if isinstance(stmt, sql.Statement):
            self._curr_stmt = stmt

        # Process the statement
        self._process(stmt)

        # If we are processing a statement, check if we should add a new line
        if isinstance(stmt, sql.Statement):
            if self._last_stmt:
                if unicode(self._last_stmt).endswith('\n'):
                    nl = '\n'
                else:
                    nl = '\n\n'

                stmt.tokens.insert(0, sql.Token(T.Whitespace, nl))

            # Set the statement as the current one
            self._last_stmt = stmt


# FIXME: Doesn't work ;)
class RightMarginFilter:

    keep_together = (
#        sql.TypeCast, sql.Identifier, sql.Alias,
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
                  and not token.__class__ in self.keep_together):
                token.tokens = self._process(stack, token, token.tokens)
            else:
                val = unicode(token)
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
        warn("Deprecated, use callable objects. This will be removed at 0.2.0",
             DeprecationWarning)

        return
        group.tokens = self._process(stack, group, group.tokens)


class ColumnsSelect:
    """Get the columns names of a SELECT query"""
    def process(self, stack, stream):
        warn("Deprecated, use callable objects. This will be removed at 0.2.0",
             DeprecationWarning)

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
            elif mode in (1, 3):
                if value in ('FROM', 'WHERE', 'GROUP'):
                    if oldValue:
                        yield oldValue
                        oldValue = ""

                    break    # Columns have been checked

                elif value == 'AS':
                    oldValue = ""
                    mode = 2

                elif token_type in Whitespace:
                    mode = 3

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

                    if mode == 3:
                        oldValue = value
                        mode = 1
                    else:
                        oldValue += value

            # We are processing an AS keyword
            elif mode == 2:
                # We check also for Keywords because a bug in SQLParse
                if token_type == Name or token_type == Keyword:
                    yield value
                    mode = 1

        if oldValue:
            yield oldValue


# ---------------------------
# postprocess

class SerializerUnicode:

    def process(self, stack, stmt):
        warn("Deprecated, use callable objects. This will be removed at 0.2.0",
             DeprecationWarning)

        raw = unicode(stmt)
        add_nl = raw.endswith('\n')
        res = '\n'.join(line.rstrip() for line in raw.splitlines())
        if add_nl:
            res += '\n'
        return res


def Tokens2Unicode(stream):
    result = ""

    for _, value in stream:
        result += unicode(value)

    return result


class OutputFilter:
    varname_prefix = ''

    def __init__(self, varname='sql'):
        self.varname = self.varname_prefix + varname
        self.count = 0

    def _process(self, stream, varname, has_nl):
        raise NotImplementedError

    def process(self, stack, stmt):
        warn("Deprecated, use callable objects. This will be removed at 0.2.0",
             DeprecationWarning)

        self.count += 1
        if self.count > 1:
            varname = '%s%d' % (self.varname, self.count)
        else:
            varname = self.varname

        has_nl = len(unicode(stmt).strip().splitlines()) > 1
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
        warn("Deprecated, use callable objects. This will be removed at 0.2.0",
             DeprecationWarning)

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
