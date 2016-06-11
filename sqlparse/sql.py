# -*- coding: utf-8 -*-
#
# Copyright (C) 2016 Andi Albrecht, albrecht.andi@gmail.com
#
# This module is part of python-sqlparse and is released under
# the BSD License: http://www.opensource.org/licenses/bsd-license.php

"""This module contains classes representing syntactical elements of SQL."""
from __future__ import print_function

import re

from sqlparse import tokens as T
from sqlparse.compat import string_types, text_type, unicode_compatible
from sqlparse.utils import imt, remove_quotes


@unicode_compatible
class Token(object):
    """Base class for all other classes in this module.

    It represents a single token and has two instance attributes:
    ``value`` is the unchange value of the token and ``ttype`` is
    the type of the token.
    """

    __slots__ = ('value', 'ttype', 'parent', 'normalized', 'is_keyword')

    def __init__(self, ttype, value):
        value = text_type(value)
        self.value = value
        self.ttype = ttype
        self.parent = None
        self.is_keyword = ttype in T.Keyword
        self.normalized = value.upper() if self.is_keyword else value

    def __str__(self):
        return self.value

    def __repr__(self):
        cls = self._get_repr_name()
        value = self._get_repr_value()
        return "<{cls} '{value}' at 0x{id:2X}>".format(id=id(self), **locals())

    def _get_repr_name(self):
        return str(self.ttype).split('.')[-1]

    def _get_repr_value(self):
        raw = text_type(self)
        if len(raw) > 7:
            raw = raw[:6] + '...'
        return re.sub(r'\s+', ' ', raw)

    def flatten(self):
        """Resolve subgroups."""
        yield self

    def match(self, ttype, values, regex=False):
        """Checks whether the token matches the given arguments.

        *ttype* is a token type. If this token doesn't match the given token
        type.
        *values* is a list of possible values for this token. The values
        are OR'ed together so if only one of the values matches ``True``
        is returned. Except for keyword tokens the comparison is
        case-sensitive. For convenience it's ok to pass in a single string.
        If *regex* is ``True`` (default is ``False``) the given values are
        treated as regular expressions.
        """
        type_matched = self.ttype is ttype
        if not type_matched or values is None:
            return type_matched

        if isinstance(values, string_types):
            values = (values,)

        if regex:
            # TODO: Add test for regex with is_keyboard = false
            flag = re.IGNORECASE if self.is_keyword else 0
            values = (re.compile(v, flag) for v in values)

            for pattern in values:
                if pattern.search(self.normalized):
                    return True
            return False

        if self.is_keyword:
            values = (v.upper() for v in values)

        return self.normalized in values

    def is_group(self):
        """Returns ``True`` if this object has children."""
        return False

    def is_whitespace(self):
        """Return ``True`` if this token is a whitespace token."""
        return self.ttype in T.Whitespace

    def within(self, group_cls):
        """Returns ``True`` if this token is within *group_cls*.

        Use this method for example to check if an identifier is within
        a function: ``t.within(sql.Function)``.
        """
        parent = self.parent
        while parent:
            if isinstance(parent, group_cls):
                return True
            parent = parent.parent
        return False

    def is_child_of(self, other):
        """Returns ``True`` if this token is a direct child of *other*."""
        return self.parent == other

    def has_ancestor(self, other):
        """Returns ``True`` if *other* is in this tokens ancestry."""
        parent = self.parent
        while parent:
            if parent == other:
                return True
            parent = parent.parent
        return False


@unicode_compatible
class TokenList(Token):
    """A group of tokens.

    It has an additional instance attribute ``tokens`` which holds a
    list of child-tokens.
    """

    __slots__ = 'tokens'

    def __init__(self, tokens=None):
        self.tokens = tokens or []
        super(TokenList, self).__init__(None, text_type(self))

    def __str__(self):
        return ''.join(token.value for token in self.flatten())

    def __iter__(self):
        return iter(self.tokens)

    def __getitem__(self, item):
        return self.tokens[item]

    def _get_repr_name(self):
        return type(self).__name__

    def _pprint_tree(self, max_depth=None, depth=0, f=None):
        """Pretty-print the object tree."""
        ind = ' ' * (depth * 2)
        for idx, token in enumerate(self.tokens):
            pre = ' +-' if token.is_group() else ' | '
            cls = token._get_repr_name()
            value = token._get_repr_value()
            print("{ind}{pre}{idx} {cls} '{value}'".format(**locals()), file=f)

            if token.is_group() and (max_depth is None or depth < max_depth):
                token._pprint_tree(max_depth, depth + 1, f)

    def get_token_at_offset(self, offset):
        """Returns the token that is on position offset."""
        idx = 0
        for token in self.flatten():
            end = idx + len(token.value)
            if idx <= offset < end:
                return token
            idx = end

    def flatten(self):
        """Generator yielding ungrouped tokens.

        This method is recursively called for all child tokens.
        """
        for token in self.tokens:
            if token.is_group():
                for item in token.flatten():
                    yield item
            else:
                yield token

    def is_group(self):
        return True

    def get_sublists(self):
        for token in self.tokens:
            if token.is_group():
                yield token

    @property
    def _groupable_tokens(self):
        return self.tokens

    def _token_matching(self, funcs, start=0, end=None, reverse=False):
        """next token that match functions"""
        if start is None:
            return None

        if not isinstance(start, int):
            start = self.token_index(start) + 1

        if not isinstance(funcs, (list, tuple)):
            funcs = (funcs,)

        if reverse:
            iterable = reversed(self.tokens[end:start - 1])
        else:
            iterable = self.tokens[start:end]

        for token in iterable:
            for func in funcs:
                if func(token):
                    return token

    def token_first(self, skip_ws=True, skip_cm=False):
        """Returns the first child token.

        If *ignore_whitespace* is ``True`` (the default), whitespace
        tokens are ignored.

        if *ignore_comments* is ``True`` (default: ``False``), comments are
        ignored too.
        """
        # this on is inconsistent, using Comment instead of T.Comment...
        funcs = lambda tk: not ((skip_ws and tk.is_whitespace()) or
                                (skip_cm and imt(tk, i=Comment)))
        return self._token_matching(funcs)

    def token_next_by(self, i=None, m=None, t=None, idx=0, end=None):
        funcs = lambda tk: imt(tk, i, m, t)
        return self._token_matching(funcs, idx, end)

    def token_not_matching(self, idx, funcs):
        funcs = (funcs,) if not isinstance(funcs, (list, tuple)) else funcs
        funcs = [lambda tk: not func(tk) for func in funcs]
        return self._token_matching(funcs, idx)

    def token_matching(self, idx, funcs):
        return self._token_matching(funcs, idx)

    def token_prev(self, idx, skip_ws=True, skip_cm=False):
        """Returns the previous token relative to *idx*.

        If *skip_ws* is ``True`` (the default) whitespace tokens are ignored.
        ``None`` is returned if there's no previous token.
        """
        funcs = lambda tk: not ((skip_ws and tk.is_whitespace()) or
                                (skip_cm and imt(tk, t=T.Comment)))
        return self._token_matching(funcs, idx, reverse=True)

    def token_next(self, idx, skip_ws=True, skip_cm=False):
        """Returns the next token relative to *idx*.

        If *skip_ws* is ``True`` (the default) whitespace tokens are ignored.
        ``None`` is returned if there's no next token.
        """
        funcs = lambda tk: not ((skip_ws and tk.is_whitespace()) or
                                (skip_cm and imt(tk, t=T.Comment)))
        return self._token_matching(funcs, idx)

    def token_index(self, token, start=0):
        """Return list index of token."""
        start = start if isinstance(start, int) else self.token_index(start)
        return start + self.tokens[start:].index(token)

    def tokens_between(self, start, end, include_end=True):
        """Return all tokens between (and including) start and end.

        If *include_end* is ``False`` (default is ``True``) the end token
        is excluded.
        """
        start_idx = self.token_index(start)
        end_idx = include_end + self.token_index(end)
        return self.tokens[start_idx:end_idx]

    def group_tokens(self, grp_cls, tokens, skip_ws=False, extend=False):
        """Replace tokens by an instance of *grp_cls*."""

        while skip_ws and tokens and tokens[-1].is_whitespace():
            tokens = tokens[:-1]

        left = tokens[0]
        idx = self.token_index(left)

        if extend and isinstance(left, grp_cls):
            grp = left
            grp.tokens.extend(tokens[1:])
        else:
            grp = grp_cls(tokens)

        for token in tokens:
            token.parent = grp

        # Improve performance. LOOP(list.remove()) is O(n**2) operation
        self.tokens = [token for token in self.tokens if token not in tokens]

        self.tokens.insert(idx, grp)
        grp.parent = self
        return grp

    def insert_before(self, where, token):
        """Inserts *token* before *where*."""
        self.tokens.insert(self.token_index(where), token)

    def insert_after(self, where, token, skip_ws=True):
        """Inserts *token* after *where*."""
        next_token = self.token_next(where, skip_ws=skip_ws)
        if next_token is None:
            self.tokens.append(token)
        else:
            self.insert_before(next_token, token)

    def has_alias(self):
        """Returns ``True`` if an alias is present."""
        return self.get_alias() is not None

    def get_alias(self):
        """Returns the alias for this identifier or ``None``."""

        # "name AS alias"
        kw = self.token_next_by(m=(T.Keyword, 'AS'))
        if kw is not None:
            return self._get_first_name(kw, keywords=True)

        # "name alias" or "complicated column expression alias"
        if len(self.tokens) > 2 and self.token_next_by(t=T.Whitespace):
            return self._get_first_name(reverse=True)

    def get_name(self):
        """Returns the name of this identifier.

        This is either it's alias or it's real name. The returned valued can
        be considered as the name under which the object corresponding to
        this identifier is known within the current statement.
        """
        return self.get_alias() or self.get_real_name()

    def get_real_name(self):
        """Returns the real name (object name) of this identifier."""
        # a.b
        dot = self.token_next_by(m=(T.Punctuation, '.'))
        return self._get_first_name(dot)

    def get_parent_name(self):
        """Return name of the parent object if any.

        A parent object is identified by the first occuring dot.
        """
        dot = self.token_next_by(m=(T.Punctuation, '.'))
        prev_ = self.token_prev(dot)
        return remove_quotes(prev_.value) if prev_ is not None else None

    def _get_first_name(self, idx=None, reverse=False, keywords=False):
        """Returns the name of the first token with a name"""

        if idx and not isinstance(idx, int):
            idx = self.token_index(idx) + 1

        tokens = self.tokens[idx:] if idx else self.tokens
        tokens = reversed(tokens) if reverse else tokens
        types = [T.Name, T.Wildcard, T.String.Symbol]

        if keywords:
            types.append(T.Keyword)

        for token in tokens:
            if token.ttype in types:
                return remove_quotes(token.value)
            elif isinstance(token, (Identifier, Function)):
                return token.get_name()


class Statement(TokenList):
    """Represents a SQL statement."""

    def get_type(self):
        """Returns the type of a statement.

        The returned value is a string holding an upper-cased reprint of
        the first DML or DDL keyword. If the first token in this group
        isn't a DML or DDL keyword "UNKNOWN" is returned.

        Whitespaces and comments at the beginning of the statement
        are ignored.
        """
        first_token = self.token_first(skip_cm=True)
        if first_token is None:
            # An "empty" statement that either has not tokens at all
            # or only whitespace tokens.
            return 'UNKNOWN'

        elif first_token.ttype in (T.Keyword.DML, T.Keyword.DDL):
            return first_token.normalized

        elif first_token.ttype == T.Keyword.CTE:
            # The WITH keyword should be followed by either an Identifier or
            # an IdentifierList containing the CTE definitions;  the actual
            # DML keyword (e.g. SELECT, INSERT) will follow next.
            token = self.token_next(first_token, skip_ws=True)
            if isinstance(token, (Identifier, IdentifierList)):
                dml_keyword = self.token_next(token, skip_ws=True)

                if dml_keyword.ttype == T.Keyword.DML:
                    return dml_keyword.normalized

        # Hmm, probably invalid syntax, so return unknown.
        return 'UNKNOWN'


class Identifier(TokenList):
    """Represents an identifier.

    Identifiers may have aliases or typecasts.
    """

    def is_wildcard(self):
        """Return ``True`` if this identifier contains a wildcard."""
        token = self.token_next_by(t=T.Wildcard)
        return token is not None

    def get_typecast(self):
        """Returns the typecast or ``None`` of this object as a string."""
        marker = self.token_next_by(m=(T.Punctuation, '::'))
        next_ = self.token_next(marker, False)
        return next_.value if next_ else None

    def get_ordering(self):
        """Returns the ordering or ``None`` as uppercase string."""
        ordering = self.token_next_by(t=T.Keyword.Order)
        return ordering.normalized if ordering else None

    def get_array_indices(self):
        """Returns an iterator of index token lists"""

        for token in self.tokens:
            if isinstance(token, SquareBrackets):
                # Use [1:-1] index to discard the square brackets
                yield token.tokens[1:-1]


class IdentifierList(TokenList):
    """A list of :class:`~sqlparse.sql.Identifier`\'s."""

    def get_identifiers(self):
        """Returns the identifiers.

        Whitespaces and punctuations are not included in this generator.
        """
        for token in self.tokens:
            if not (token.is_whitespace() or token.match(T.Punctuation, ',')):
                yield token


class Parenthesis(TokenList):
    """Tokens between parenthesis."""
    M_OPEN = T.Punctuation, '('
    M_CLOSE = T.Punctuation, ')'

    @property
    def _groupable_tokens(self):
        return self.tokens[1:-1]


class SquareBrackets(TokenList):
    """Tokens between square brackets"""
    M_OPEN = T.Punctuation, '['
    M_CLOSE = T.Punctuation, ']'

    @property
    def _groupable_tokens(self):
        return self.tokens[1:-1]


class Assignment(TokenList):
    """An assignment like 'var := val;'"""


class If(TokenList):
    """An 'if' clause with possible 'else if' or 'else' parts."""
    M_OPEN = T.Keyword, 'IF'
    M_CLOSE = T.Keyword, 'END IF'


class For(TokenList):
    """A 'FOR' loop."""
    M_OPEN = T.Keyword, ('FOR', 'FOREACH')
    M_CLOSE = T.Keyword, 'END LOOP'


class Comparison(TokenList):
    """A comparison used for example in WHERE clauses."""

    @property
    def left(self):
        return self.tokens[0]

    @property
    def right(self):
        return self.tokens[-1]


class Comment(TokenList):
    """A comment."""

    def is_multiline(self):
        return self.tokens and self.tokens[0].ttype == T.Comment.Multiline


class Where(TokenList):
    """A WHERE clause."""
    M_OPEN = T.Keyword, 'WHERE'
    M_CLOSE = T.Keyword, ('ORDER', 'GROUP', 'LIMIT', 'UNION', 'EXCEPT',
                          'HAVING')


class Case(TokenList):
    """A CASE statement with one or more WHEN and possibly an ELSE part."""
    M_OPEN = T.Keyword, 'CASE'
    M_CLOSE = T.Keyword, 'END'

    def get_cases(self, skip_ws=False):
        """Returns a list of 2-tuples (condition, value).

        If an ELSE exists condition is None.
        """
        CONDITION = 1
        VALUE = 2

        ret = []
        mode = CONDITION

        for token in self.tokens:
            # Set mode from the current statement
            if token.match(T.Keyword, 'CASE'):
                continue

            elif skip_ws and token.ttype in T.Whitespace:
                continue

            elif token.match(T.Keyword, 'WHEN'):
                ret.append(([], []))
                mode = CONDITION

            elif token.match(T.Keyword, 'THEN'):
                mode = VALUE

            elif token.match(T.Keyword, 'ELSE'):
                ret.append((None, []))
                mode = VALUE

            elif token.match(T.Keyword, 'END'):
                mode = None

            # First condition without preceding WHEN
            if mode and not ret:
                ret.append(([], []))

            # Append token depending of the current mode
            if mode == CONDITION:
                ret[-1][0].append(token)

            elif mode == VALUE:
                ret[-1][1].append(token)

        # Return cases list
        return ret


class Function(TokenList):
    """A function or procedure call."""

    def get_parameters(self):
        """Return a list of parameters."""
        parenthesis = self.tokens[-1]
        for token in parenthesis.tokens:
            if imt(token, i=IdentifierList):
                return token.get_identifiers()
            elif imt(token, i=(Function, Identifier), t=T.Literal):
                return [token, ]
        return []


class Begin(TokenList):
    """A BEGIN/END block."""
    M_OPEN = T.Keyword, 'BEGIN'
    M_CLOSE = T.Keyword, 'END'
