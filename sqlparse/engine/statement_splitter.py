#
# Copyright (C) 2009-2020 the sqlparse authors and contributors
# <see AUTHORS file>
#
# This module is part of python-sqlparse and is released under
# the BSD License: https://opensource.org/licenses/BSD-3-Clause

from sqlparse import sql, tokens as T


class StatementSplitter:
    """Filter that split stream at individual statements"""

    def __init__(self):
        self._reset()

    def _reset(self):
        """Set the filter attributes to its default values"""
        self._case_depth = 0
        self._stmt_start = True
        self._begin_depth = 0

        self.consume_ws = False
        self.tokens = []
        self.level = 0

    def _change_splitlevel(self, ttype, value):
        """Get the new split level (increase, decrease or remain equal)"""

        # parenthesis increase/decrease a level
        if ttype is T.Punctuation and value == '(':
            return 1
        elif ttype is T.Punctuation and value == ')':
            return -1
        elif ttype is T.Punctuation and value == ';' and self._stmt_start:
                self._begin_depth = max(0, self._begin_depth - 1)
                self._begin_depth -= 1
                return -1
        elif ttype not in T.Keyword:  # if normal token return
            return 0

        # Everything after here is ttype = T.Keyword
        # Also to note, once entered an If statement you are done and basically
        # returning
        unified = value.upper()

        if unified == 'BEGIN' and not self._stmt_start:
            self._begin_depth += 1
            return 1

        if self._stmt_start:
            self._stmt_start = False

        # BEGIN and CASE/WHEN both end with END
        if unified == 'END':
            if not self._case_depth:
                self._begin_depth = max(0, self._begin_depth - 1)
            else:
                self._case_depth = max(0, self._case_depth - 1)
            return -1

        if unified in ('IF', 'FOR', 'WHILE', 'CASE'):
            if unified == 'CASE':
                self._case_depth += 1
            if self._begin_depth > 0:
                return 1

        if unified in ('END IF', 'END FOR', 'END WHILE', 'END CASE'):
            if self._begin_depth > 0:
                return -1

        # Default
        return 0

    def process(self, stream):
        """Process the stream"""
        EOS_TTYPE = T.Whitespace, T.Comment.Single

        # Run over all stream tokens
        sb = ""
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
            if (self.level <= 0 and ttype is T.Punctuation and value == ';') \
                    or (ttype is T.Keyword and value.split()[0] == 'GO'):
                self.consume_ws = True

        # Yield pending statement (if any)
        if self.tokens and not all(t.is_whitespace for t in self.tokens):
            yield sql.Statement(self.tokens)
