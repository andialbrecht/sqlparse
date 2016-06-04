# -*- coding: utf-8 -*-
#
# Copyright (C) 2016 Andi Albrecht, albrecht.andi@gmail.com
#
# This module is part of python-sqlparse and is released under
# the BSD License: http://www.opensource.org/licenses/bsd-license.php

from sqlparse.sql import Statement, Token
from sqlparse import tokens as T


class StatementFilter(object):
    """Filter that split stream at individual statements"""

    def __init__(self):
        self._reset()

    def _reset(self):
        """Set the filter attributes to its default values"""
        self._in_declare = False
        self._in_dbldollar = False
        self._is_create = False
        self._begin_depth = 0

    def _change_splitlevel(self, ttype, value):
        """Get the new split level (increase, decrease or remain equal)"""
        # PostgreSQL
        if ttype == T.Name.Builtin \
           and value.startswith('$') and value.endswith('$'):

            # 2nd dbldollar found. $quote$ completed
            # decrease level
            if self._in_dbldollar:
                self._in_dbldollar = False
                return -1
            else:
                self._in_dbldollar = True
                return 1

        # if inside $$ everything inside is defining function character.
        # Nothing inside can create a new statement
        elif self._in_dbldollar:
            return 0

        # ANSI
        # if normal token return
        # wouldn't parenthesis increase/decrease a level?
        # no, inside a paranthesis can't start new statement
        if ttype not in T.Keyword:
            return 0

        # Everything after here is ttype = T.Keyword
        # Also to note, once entered an If statement you are done and basically
        # returning
        unified = value.upper()

        # can have nested declare inside of being...
        if unified == 'DECLARE' and self._is_create and self._begin_depth == 0:
            self._in_declare = True
            return 1

        if unified == 'BEGIN':
            self._begin_depth += 1
            if self._in_declare or self._is_create:
                # FIXME(andi): This makes no sense.
                return 1
            return 0

        if unified in ('END IF', 'END FOR', 'END WHILE'):
            return -1

        # Should this respect a preceeding BEGIN?
        # In CASE ... WHEN ... END this results in a split level -1.
        # Would having multiple CASE WHEN END and a Assigment Operator
        # cause the statement to cut off prematurely?
        if unified == 'END':
            self._begin_depth = max(0, self._begin_depth - 1)
            return -1

        # three keywords begin with CREATE, but only one of them is DDL
        # DDL Create though can contain more words such as "or replace"
        if ttype is T.Keyword.DDL and unified.startswith('CREATE'):
            self._is_create = True
            return 0

        if unified in ('IF', 'FOR', 'WHILE') \
           and self._is_create and self._begin_depth > 0:
            return 1

        # Default
        return 0

    def process(self, stream):
        """Process the stream"""
        consume_ws = False
        splitlevel = 0
        stmt = None
        stmt_tokens = []

        # Run over all stream tokens
        for ttype, value in stream:
            # Yield token if we finished a statement and there's no whitespaces
            # It will count newline token as a non whitespace. In this context
            # whitespace ignores newlines.
            # why don't multi line comments also count?
            if consume_ws and ttype not in (T.Whitespace, T.Comment.Single):
                stmt.tokens = stmt_tokens
                yield stmt

                # Reset filter and prepare to process next statement
                self._reset()
                consume_ws = False
                splitlevel = 0
                stmt = None

            # Create a new statement if we are not currently in one of them
            if stmt is None:
                stmt = Statement()
                stmt_tokens = []

            # Change current split level (increase, decrease or remain equal)
            splitlevel += self._change_splitlevel(ttype, value)

            # Append the token to the current statement
            stmt_tokens.append(Token(ttype, value))

            # Check if we get the end of a statement
            if splitlevel <= 0 and ttype is T.Punctuation and value == ';':
                consume_ws = True

        # Yield pending statement (if any)
        if stmt is not None:
            stmt.tokens = stmt_tokens
            yield stmt
