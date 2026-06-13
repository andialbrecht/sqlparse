#
# Copyright (C) 2009-2020 the sqlparse authors and contributors
# <see AUTHORS file>
#
# This module is part of python-sqlparse and is released under
# the BSD License: https://opensource.org/licenses/BSD-3-Clause

from sqlparse import sql
from sqlparse import tokens as T


class OutputFilter:
    varname_prefix = ''

    def __init__(self, varname='sql'):
        self.varname = self.varname_prefix + varname
        self.count = 0

    def _process(self, stream, varname, has_nl):
        raise NotImplementedError

    def process(self, stmt):
        self.count += 1
        if self.count > 1:
            varname = f'{self.varname}{self.count}'
        else:
            varname = self.varname

        has_nl = len(str(stmt).strip().splitlines()) > 1
        stmt.tokens = self._process(stmt.tokens, varname, has_nl)
        return stmt


def _generate_assignment_header(varname, has_nl, count, quote_char, assign_op='='):
    """Generate the variable assignment header tokens.

    Yields the tokens that start a variable assignment line:
        varname = '   (Python)
        varname  = "   (PHP)

    Args:
        varname: Variable name string
        has_nl: Whether the SQL has newlines
        count: Statement count (for blank line before subsequent statements)
        quote_char: Single quote (') for Python, double quote (") for PHP
        assign_op: Assignment operator ('=' or '.=')
    """
    if count > 1:
        yield sql.Token(T.Whitespace, '\n')
    yield sql.Token(T.Name, varname)
    yield sql.Token(T.Whitespace, ' ')
    yield sql.Token(T.Operator, assign_op)
    yield sql.Token(T.Whitespace, ' ')
    yield sql.Token(T.Text, quote_char)


def _generate_continuation_header(varname, quote_char, assign_op='=', indent_padding=0):
    """Generate the continuation line header tokens after a newline.

    Yields the tokens for a continuation line when the SQL has newlines:
        '     (Python - with optional indent padding)
        varname .= "  (PHP)

    Args:
        varname: Variable name string
        quote_char: Quote character for the new line
        assign_op: Assignment operator for continuation ('=' or '.=')
        indent_padding: Number of spaces for Python-style continuation padding
    """
    yield sql.Token(T.Text, f' {quote_char}')
    yield sql.Token(T.Whitespace, '\n')
    if assign_op == '.=':
        # PHP-style: re-assign with .=
        yield sql.Token(T.Name, varname)
        yield sql.Token(T.Whitespace, ' ')
        yield sql.Token(T.Operator, '.=')
        yield sql.Token(T.Whitespace, ' ')
    else:
        # Python-style: continuation with padding
        yield sql.Token(T.Whitespace, ' ' * indent_padding)
    yield sql.Token(T.Text, quote_char)


class OutputPythonFilter(OutputFilter):
    _quote_char = "'"
    _escape_char = "'"
    _escape_replacement = "\\'"

    def _process(self, stream, varname, has_nl):
        # Variable assignment header (without trailing quote — we add it below)
        if self.count > 1:
            yield sql.Token(T.Whitespace, '\n')
        yield sql.Token(T.Name, varname)
        yield sql.Token(T.Whitespace, ' ')
        yield sql.Token(T.Operator, '=')
        yield sql.Token(T.Whitespace, ' ')
        if has_nl:
            yield sql.Token(T.Operator, '(')

        yield sql.Token(T.Text, self._quote_char)

        # Print the tokens within the quote
        continuation_padding = len(varname) + 4
        for token in stream:
            if token.is_whitespace and '\n' in token.value:
                # Close current quote and start continuation line
                yield from _generate_continuation_header(
                    varname, self._quote_char, '=',
                    indent_padding=continuation_padding)

                # Indentation after the newline
                after_lb = token.value.split('\n', 1)[1]
                if after_lb:
                    yield sql.Token(T.Whitespace, after_lb)
                continue

            # Escape the quote character within token values
            if self._escape_char in token.value:
                token.value = token.value.replace(
                    self._escape_char, self._escape_replacement)

            yield sql.Token(T.Text, token.value)

        # Close quote
        yield sql.Token(T.Text, self._quote_char)
        if has_nl:
            yield sql.Token(T.Operator, ')')


class OutputPHPFilter(OutputFilter):
    varname_prefix = '$'
    _quote_char = '"'
    _escape_char = '"'
    _escape_replacement = '\\"'

    def _process(self, stream, varname, has_nl):
        # Variable assignment header
        if self.count > 1:
            yield sql.Token(T.Whitespace, '\n')
        yield sql.Token(T.Name, varname)
        yield sql.Token(T.Whitespace, ' ')
        if has_nl:
            # Extra space for alignment with continuation .= lines
            yield sql.Token(T.Whitespace, ' ')
        yield sql.Token(T.Operator, '=')
        yield sql.Token(T.Whitespace, ' ')
        yield sql.Token(T.Text, self._quote_char)

        # Print the tokens within the quote
        for token in stream:
            if token.is_whitespace and '\n' in token.value:
                # Close current quote with semicolon and start continuation
                yield sql.Token(T.Text, ' ";')
                yield sql.Token(T.Whitespace, '\n')

                # PHP continuation line: $varname .= "
                yield sql.Token(T.Name, varname)
                yield sql.Token(T.Whitespace, ' ')
                yield sql.Token(T.Operator, '.=')
                yield sql.Token(T.Whitespace, ' ')
                yield sql.Token(T.Text, self._quote_char)

                # Indentation after the newline
                after_lb = token.value.split('\n', 1)[1]
                if after_lb:
                    yield sql.Token(T.Whitespace, after_lb)
                continue

            # Escape the quote character within token values
            if self._escape_char in token.value:
                token.value = token.value.replace(
                    self._escape_char, self._escape_replacement)

            yield sql.Token(T.Text, token.value)

        # Close quote
        yield sql.Token(T.Text, self._quote_char)
        yield sql.Token(T.Punctuation, ';')
