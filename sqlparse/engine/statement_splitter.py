#
# Copyright (C) 2009-2020 the sqlparse authors and contributors
# <see AUTHORS file>
#
# This module is part of python-sqlparse and is released under
# the BSD License: https://opensource.org/licenses/BSD-3-Clause

from sqlparse import sql
from sqlparse import tokens as T


class StatementSplitter:
    """Filter that split stream at individual statements"""

    def __init__(self):
        self._reset()

    def _reset(self):
        """Set the filter attributes to its default values"""
        self._block_stack = []
        self._parenthesis_level = 0
        self._unconfirmed_start = None
        self._is_create = False
        self._seen_begin = False

        self.consume_ws = False
        self.tokens = []
        self.level = 0

    def _handle_nested_block(self, unified):
        """Check for nested loop or control structures inside a block"""
        if unified == 'FOR':
            self._unconfirmed_start = 'FOR'
            return 0
        if unified == 'WHILE':
            self._unconfirmed_start = 'WHILE'
            return 0
        if unified in ('LOOP', 'DO'):
            if self._unconfirmed_start in ('FOR', 'WHILE'):
                self._block_stack.append(self._unconfirmed_start)
                self._unconfirmed_start = None
                return 1
            if unified == 'LOOP':
                self._block_stack.append('LOOP')
                return 1
        if unified in ('IF', 'CASE'):
            self._block_stack.append(unified)
            return 1
        return None

    def _handle_closing_keyword(self, unified):
        """Handle closing keywords for blocks"""
        if unified == 'END IF':
            if self._block_stack and self._block_stack[-1] == 'IF':
                self._block_stack.pop()
                return -1
        elif unified == 'END FOR':
            if self._block_stack and self._block_stack[-1] == 'FOR':
                self._block_stack.pop()
                return -1
        elif unified == 'END WHILE':
            if self._block_stack and self._block_stack[-1] == 'WHILE':
                self._block_stack.pop()
                return -1
        elif unified == 'END LOOP':
            if (self._block_stack and
                    self._block_stack[-1] in ('LOOP', 'FOR', 'WHILE')):
                self._block_stack.pop()
                return -1
        elif unified == 'END CASE':
            if self._block_stack and self._block_stack[-1] == 'CASE':
                self._block_stack.pop()
                return -1
        elif unified == 'END':
            if self._block_stack:
                self._block_stack.pop()
            return -1
        return 0

    def _change_splitlevel(self, ttype, value):
        """Get the new split level (increase, decrease or remain equal)"""

        # Semicolon resets unconfirmed loop starters
        # and handles standalone BEGIN;
        if ttype is T.Punctuation and value == ';':
            self._unconfirmed_start = None
            if self._seen_begin:
                self._seen_begin = False
                if self._block_stack and self._block_stack[-1] == 'BEGIN':
                    self._block_stack.pop()
                    return -1
            return 0

        # parenthesis increase/decrease a level
        if ttype is T.Punctuation and value == '(':
            self._parenthesis_level += 1
            return 1
        elif ttype is T.Punctuation and value == ')':
            self._parenthesis_level = max(0, self._parenthesis_level - 1)
            return -1
        elif ttype not in T.Keyword:  # if normal token return
            return 0

        # Everything after here is ttype = T.Keyword
        unified = value.upper()

        # DDL Create though can contain more words such as "or replace"
        if ttype is T.Keyword.DDL and unified.startswith('CREATE'):
            self._is_create = True
            return 0

        # Handle DECLARE block start (only for CREATE statements)
        if unified == 'DECLARE' and self._is_create and not self._block_stack:
            self._block_stack.append('DECLARE')
            return 1

        # Handle BEGIN block start
        if unified == 'BEGIN':
            self._seen_begin = True
            # Transition DECLARE to BEGIN if present
            if self._block_stack and self._block_stack[-1] == 'DECLARE':
                self._block_stack.pop()
                self._block_stack.append('BEGIN')
                return 0
            else:
                self._block_stack.append('BEGIN')
                return 1

        # Issue826: If we see a transaction keyword after BEGIN,
        # it's a transaction statement, not a block.
        if self._seen_begin and \
                (ttype is T.Keyword or ttype is T.Name) and \
                unified in ('TRANSACTION', 'WORK', 'TRAN',
                            'DISTRIBUTED', 'DEFERRED',
                            'IMMEDIATE', 'EXCLUSIVE'):
            self._seen_begin = False
            if self._block_stack and self._block_stack[-1] == 'BEGIN':
                self._block_stack.pop()
                return -1
            return 0

        # Inside a block, check for nested loop or control structures
        if 'BEGIN' in self._block_stack:
            res = self._handle_nested_block(unified)
            if res is not None:
                return res

        # Handle closing keywords
        return self._handle_closing_keyword(unified)

    def process(self, stream):
        """Process the stream"""
        EOS_TTYPE = T.Whitespace, T.Comment.Single

        # Run over all stream tokens
        for ttype, value in stream:
            # Yield token if we finished a statement and there's no whitespaces
            # It will count newline token as a non whitespace. In this context
            # whitespace ignores newlines.
            # why don't multi line comments also count?
            if self.consume_ws and ttype not in EOS_TTYPE:
                yield sql.Statement(self.tokens)

                # Reset filter and prepare to process next statement
                self._reset()

            # Change current split level (increase, decrease or remain equal)
            self.level += self._change_splitlevel(ttype, value)

            # Append the token to the current statement
            self.tokens.append(sql.Token(ttype, value))

            # Check if we get the end of a statement
            # Issue762: Allow GO (or "GO 2") as statement splitter.
            # When implementing a language toggle, it's not only to add
            # keywords it's also to change some rules, like this splitting
            # rule.
            # Issue809: Ignore semicolons inside BEGIN...END blocks, but handle
            # standalone BEGIN; as a transaction statement
            if ttype is T.Punctuation and value == ';':
                self._seen_begin = False
                # Split on semicolon if not inside a BEGIN...END block
                if self.level <= 0 and 'BEGIN' not in self._block_stack:
                    self.consume_ws = True
            elif ttype is T.Keyword and value.split()[0] == 'GO':
                self.consume_ws = True
            elif (ttype not in (T.Whitespace, T.Newline, T.Comment.Single,
                                T.Comment.Multiline)
                  and not (ttype is T.Keyword and value.upper() == 'BEGIN')):
                # Reset _seen_begin if we see a non-whitespace, non-comment
                # token but not for BEGIN itself (which just set the flag)
                self._seen_begin = False

        # Yield pending statement (if any)
        if self.tokens and not all(t.is_whitespace for t in self.tokens):
            yield sql.Statement(self.tokens)
