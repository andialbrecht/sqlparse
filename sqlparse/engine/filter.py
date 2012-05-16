# -*- coding: utf-8 -*-

from sqlparse.sql import Statement, Token
from sqlparse import tokens as T


def statementFilter(stream):
    "Filter that split stream at individual statements"

    # init
    statementFilter._in_declare = False
    statementFilter._in_dbldollar = False
    statementFilter._is_create = False
    statementFilter._begin_depth = 0

    def _change_splitlevel(ttype, value):
        "Get the new split level (increase, decrease or remain equal)"
        # PostgreSQL
        if (ttype == T.Name.Builtin
        and value.startswith('$') and value.endswith('$')):
            if statementFilter._in_dbldollar:
                statementFilter._in_dbldollar = False
                return -1

            statementFilter._in_dbldollar = True
            return 1

        elif statementFilter._in_dbldollar:
            return 0

        # ANSI
        if ttype not in T.Keyword:
            return 0

        unified = value.upper()

        if unified == 'DECLARE' and statementFilter._is_create:
            statementFilter._in_declare = True
            return 1

        if unified == 'BEGIN':
            statementFilter._begin_depth += 1
            if statementFilter._in_declare or statementFilter._is_create:
                # FIXME(andi): This makes no sense.
                return 1
            return 0

        if unified == 'END':
            # Should this respect a preceeding BEGIN?
            # In CASE ... WHEN ... END this results in a split level -1.
            statementFilter._begin_depth = max(0, statementFilter._begin_depth - 1)
            return -1

        if ttype is T.Keyword.DDL and unified.startswith('CREATE'):
            statementFilter._is_create = True
            return 0

        if (unified in ('IF', 'FOR')
            and statementFilter._is_create and statementFilter._begin_depth > 0):
            return 1

        # Default
        return 0

    # Process the stream
    consume_ws = False
    splitlevel = 0
    stmt = None
    stmt_tokens = []

    # Run over all stream tokens
    for ttype, value in stream:
        # Yield token if we finished a statement and there's no whitespaces
        if consume_ws and ttype not in (T.Whitespace, T.Comment.Single):
            stmt.tokens = stmt_tokens
            yield stmt

            # Reset filter and prepare to process next statement
            _in_declare = False
            _in_dbldollar = False
            _is_create = False
            _begin_depth = 0

            consume_ws = False
            splitlevel = 0
            stmt = None

        # Create a new statement if we are not currently in one of them
        if stmt == None:
            stmt = Statement()
            stmt_tokens = []

        # Change current split level (increase, decrease or remain equal)
        splitlevel += _change_splitlevel(ttype, value)

        # Append the token to the current statement
        stmt_tokens.append(Token(ttype, value))

        # Check if we get the end of a statement
        if splitlevel <= 0 and ttype is T.Punctuation and value == ';':
            consume_ws = True

    # Yield pending statement (if any)
    if stmt:
        stmt.tokens = stmt_tokens
        yield stmt
