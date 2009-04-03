# Copyright (C) 2008 Andi Albrecht, albrecht.andi@gmail.com
#
# This module is part of python-sqlparse and is released under
# the BSD License: http://www.opensource.org/licenses/bsd-license.php.

"""This module contains classes that represent SQL dialects."""

from tokens import *


class Dialect(object):
    """Base class for SQL dialect implementations."""

    def handle_token(self, tokentype, text):
        """Handle a token.

        Arguments:
          tokentype: A token type.
          text: Text representation of the token.

        Returns:
          A tuple of three items: tokentype, text, splitlevel.
          splitlevel is either -1, 0 or 1 and describes an identation level.
        """
        raise NotImplementedError

    def reset(self):
        """Reset Dialect state."""
        pass


class DefaultDialect(Dialect):

    def __init__(self):
        self._in_declare = False
        self._stmt_type = None

    def get_statement_type(self):
        return self._stmt_type

    def set_statement_type(self, type_):
        self._stmt_type = type_

    def handle_token(self, tokentype, text):
        if not tokentype == Keyword:
            return tokentype, text, 0
        unified = text.upper()
        if unified == 'DECLARE':
            self._in_declare = True
            return tokentype, text, 1
        if unified == 'BEGIN':
            if self._in_declare:
                return tokentype, text, 0
            return tokentype, text, 0
        if unified == 'END':
            return tokentype, text, -1
        # TODO: Use a constant here
        if unified in ('IF', 'FOR') and self._stmt_type == 6:
            return tokentype, text, 1
        return tokentype, text, 0

    def reset(self):
        self._in_declare = False


class PSQLDialect(DefaultDialect):

    def __init__(self):
        super(PSQLDialect, self).__init__()
        self._in_dbldollar = False

    def handle_token(self, tokentype, text):
        if (tokentype == Name.Builtin
            and text.startswith('$') and text.endswith('$')):
            if self._in_dbldollar:
                self._in_dbldollar = False
                return tokentype, text, -1
            else:
                self._in_dbldollar = True
                return tokentype, text, 1
        elif self._in_dbldollar:
            return tokentype, text, 0
        else:
            return super(PSQLDialect, self).handle_token(tokentype, text)

    def reset(self):
        self._dollar_started = False
        self._in_dbldollar = False
