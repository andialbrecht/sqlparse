# -*- coding: utf-8 -*-
#
# Copyright (C) 2016 Andi Albrecht, albrecht.andi@gmail.com
#
# This module is part of python-sqlparse and is released under
# the BSD License: http://www.opensource.org/licenses/bsd-license.php

from sqlparse import sql
from sqlparse import tokens as T
from sqlparse.utils import recurse, imt, find_matching

M_ROLE = (T.Keyword, ('null', 'role'))
M_SEMICOLON = (T.Punctuation, ';')
M_COMMA = (T.Punctuation, ',')

T_NUMERICAL = (T.Number, T.Number.Integer, T.Number.Float)
T_STRING = (T.String, T.String.Single, T.String.Symbol)
T_NAME = (T.Name, T.Name.Placeholder)


def _group_left_right(tlist, m, cls,
                      valid_left=lambda t: t is not None,
                      valid_right=lambda t: t is not None,
                      semicolon=False):
    """Groups together tokens that are joined by a middle token. ie. x < y"""
    [_group_left_right(sgroup, m, cls, valid_left, valid_right, semicolon)
     for sgroup in tlist.get_sublists() if not isinstance(sgroup, cls)]

    token = tlist.token_next_by(m=m)
    while token:
        left, right = tlist.token_prev(token), tlist.token_next(token)

        if valid_left(left) and valid_right(right):
            if semicolon:
                # only overwrite if a semicolon present.
                sright = tlist.token_next_by(m=M_SEMICOLON, idx=right)
                right = sright or right
            tokens = tlist.tokens_between(left, right)
            token = tlist.group_tokens(cls, tokens, extend=True)
        token = tlist.token_next_by(m=m, idx=token)


def _group_matching(tlist, cls):
    """Groups Tokens that have beginning and end."""
    idx = 1 if imt(tlist, i=cls) else 0

    token = tlist.token_next_by(m=cls.M_OPEN, idx=idx)
    while token:
        end = find_matching(tlist, token, cls.M_OPEN, cls.M_CLOSE)
        if end is not None:
            token = tlist.group_tokens(cls, tlist.tokens_between(token, end))
            _group_matching(token, cls)
        token = tlist.token_next_by(m=cls.M_OPEN, idx=token)


def group_if(tlist):
    _group_matching(tlist, sql.If)


def group_for(tlist):
    _group_matching(tlist, sql.For)


def group_foreach(tlist):
    _group_matching(tlist, sql.For)


def group_begin(tlist):
    _group_matching(tlist, sql.Begin)


def group_as(tlist):
    lfunc = lambda tk: not imt(tk, t=T.Keyword) or tk.value == 'NULL'
    rfunc = lambda tk: not imt(tk, t=(T.DML, T.DDL))
    _group_left_right(tlist, (T.Keyword, 'AS'), sql.Identifier,
                      valid_left=lfunc, valid_right=rfunc)


def group_assignment(tlist):
    _group_left_right(tlist, (T.Assignment, ':='), sql.Assignment,
                      semicolon=True)


def group_comparison(tlist):
    I_COMPERABLE = (sql.Parenthesis, sql.Function, sql.Identifier)
    T_COMPERABLE = T_NUMERICAL + T_STRING + T_NAME

    func = lambda tk: imt(tk, t=T_COMPERABLE, i=I_COMPERABLE) or (
        imt(tk, t=T.Keyword) and tk.value.upper() == 'NULL')

    _group_left_right(tlist, (T.Operator.Comparison, None), sql.Comparison,
                      valid_left=func, valid_right=func)


def group_case(tlist):
    _group_matching(tlist, sql.Case)


@recurse(sql.Identifier)
def group_identifier(tlist):
    T_IDENT = (T.String.Symbol, T.Name)

    token = tlist.token_next_by(t=T_IDENT)
    while token:
        token = tlist.group_tokens(sql.Identifier, [token, ])
        token = tlist.token_next_by(t=T_IDENT, idx=token)


def group_period(tlist):
    lfunc = lambda tk: imt(tk, i=(sql.SquareBrackets, sql.Identifier),
                           t=(T.Name, T.String.Symbol,))

    rfunc = lambda tk: imt(tk, i=(sql.SquareBrackets, sql.Function),
                           t=(T.Name, T.String.Symbol, T.Wildcard))

    _group_left_right(tlist, (T.Punctuation, '.'), sql.Identifier,
                      valid_left=lfunc, valid_right=rfunc)


def group_arrays(tlist):
    token = tlist.token_next_by(i=sql.SquareBrackets)
    while token:
        prev = tlist.token_prev(idx=token)
        if imt(prev, i=(sql.SquareBrackets, sql.Identifier, sql.Function),
               t=(T.Name, T.String.Symbol,)):
            tokens = tlist.tokens_between(prev, token)
            token = tlist.group_tokens(sql.Identifier, tokens, extend=True)
        token = tlist.token_next_by(i=sql.SquareBrackets, idx=token)


@recurse(sql.Identifier)
def group_operator(tlist):
    I_CYCLE = (sql.SquareBrackets, sql.Parenthesis, sql.Function,
               sql.Identifier,)  # sql.Operation)
    # wilcards wouldn't have operations next to them
    T_CYCLE = T_NUMERICAL + T_STRING + T_NAME  # + T.Wildcard
    func = lambda tk: imt(tk, i=I_CYCLE, t=T_CYCLE)

    token = tlist.token_next_by(t=(T.Operator, T.Wildcard))
    while token:
        left, right = tlist.token_prev(token), tlist.token_next(token)

        if func(left) and func(right):
            token.ttype = T.Operator
            tokens = tlist.tokens_between(left, right)
            # token = tlist.group_tokens(sql.Operation, tokens)
            token = tlist.group_tokens(sql.Identifier, tokens)

        token = tlist.token_next_by(t=(T.Operator, T.Wildcard), idx=token)


@recurse(sql.IdentifierList)
def group_identifier_list(tlist):
    I_IDENT_LIST = (sql.Function, sql.Case, sql.Identifier, sql.Comparison,
                    sql.IdentifierList)  # sql.Operation
    T_IDENT_LIST = (T_NUMERICAL + T_STRING + T_NAME +
                    (T.Keyword, T.Comment, T.Wildcard))

    func = lambda t: imt(t, i=I_IDENT_LIST, m=M_ROLE, t=T_IDENT_LIST)
    token = tlist.token_next_by(m=M_COMMA)

    while token:
        before, after = tlist.token_prev(token), tlist.token_next(token)

        if func(before) and func(after):
            tokens = tlist.tokens_between(before, after)
            token = tlist.group_tokens(sql.IdentifierList, tokens, extend=True)
        token = tlist.token_next_by(m=M_COMMA, idx=token)


def group_brackets(tlist):
    _group_matching(tlist, sql.SquareBrackets)


def group_parenthesis(tlist):
    _group_matching(tlist, sql.Parenthesis)


@recurse(sql.Comment)
def group_comments(tlist):
    token = tlist.token_next_by(t=T.Comment)
    while token:
        end = tlist.token_not_matching(
            token, lambda tk: imt(tk, t=T.Comment) or tk.is_whitespace())
        if end is not None:
            end = tlist.token_prev(end, False)
            tokens = tlist.tokens_between(token, end)
            token = tlist.group_tokens(sql.Comment, tokens)

        token = tlist.token_next_by(t=T.Comment, idx=token)


@recurse(sql.Where)
def group_where(tlist):
    token = tlist.token_next_by(m=sql.Where.M_OPEN)
    while token:
        end = tlist.token_next_by(m=sql.Where.M_CLOSE, idx=token)

        if end is None:
            tokens = tlist.tokens_between(token, tlist._groupable_tokens[-1])
        else:
            tokens = tlist.tokens_between(
                token, tlist.tokens[tlist.token_index(end) - 1])

        token = tlist.group_tokens(sql.Where, tokens)
        token = tlist.token_next_by(m=sql.Where.M_OPEN, idx=token)


@recurse()
def group_aliased(tlist):
    I_ALIAS = (sql.Parenthesis, sql.Function, sql.Case, sql.Identifier,
               )  # sql.Operation)

    token = tlist.token_next_by(i=I_ALIAS, t=T.Number)
    while token:
        next_ = tlist.token_next(token)
        if imt(next_, i=sql.Identifier):
            tokens = tlist.tokens_between(token, next_)
            token = tlist.group_tokens(sql.Identifier, tokens, extend=True)
        token = tlist.token_next_by(i=I_ALIAS, t=T.Number, idx=token)


def group_typecasts(tlist):
    _group_left_right(tlist, (T.Punctuation, '::'), sql.Identifier)


@recurse(sql.Function)
def group_functions(tlist):
    has_create = False
    has_table = False
    for tmp_token in tlist.tokens:
        if tmp_token.value == 'CREATE':
            has_create = True
        if tmp_token.value == 'TABLE':
            has_table = True
    if has_create and has_table:
        return
    token = tlist.token_next_by(t=T.Name)
    while token:
        next_ = tlist.token_next(token)
        if imt(next_, i=sql.Parenthesis):
            tokens = tlist.tokens_between(token, next_)
            token = tlist.group_tokens(sql.Function, tokens)
        token = tlist.token_next_by(t=T.Name, idx=token)


def group_order(tlist):
    """Group together Identifier and Asc/Desc token"""
    token = tlist.token_next_by(t=T.Keyword.Order)
    while token:
        prev = tlist.token_prev(token)
        if imt(prev, i=sql.Identifier, t=T.Number):
            tokens = tlist.tokens_between(prev, token)
            token = tlist.group_tokens(sql.Identifier, tokens)
        token = tlist.token_next_by(t=T.Keyword.Order, idx=token)


@recurse()
def align_comments(tlist):
    token = tlist.token_next_by(i=sql.Comment)
    while token:
        before = tlist.token_prev(token)
        if isinstance(before, sql.TokenList):
            tokens = tlist.tokens_between(before, token)
            token = tlist.group_tokens(sql.TokenList, tokens, extend=True)
        token = tlist.token_next_by(i=sql.Comment, idx=token)


def group(stmt):
    for func in [
        group_comments,
        group_brackets,
        group_parenthesis,
        group_functions,
        group_where,
        group_case,
        group_period,
        group_arrays,
        group_identifier,
        group_operator,
        group_order,
        group_typecasts,
        group_as,
        group_aliased,
        group_assignment,
        group_comparison,
        align_comments,
        group_identifier_list,
        group_if,
        group_for,
        group_foreach,
        group_begin,
    ]:
        func(stmt)
    return stmt
