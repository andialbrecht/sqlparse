# -*- coding: utf-8 -*-

from sqlparse import sql
from sqlparse import tokens as T
from sqlparse.utils import recurse, imt

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
        tidx = tlist.token_index(token)
        left, right = tlist.token_prev(tidx), tlist.token_next(tidx)

        if valid_left(left) and valid_right(right):
            if semicolon:
                sright = tlist.token_next_by(m=M_SEMICOLON, idx=tidx + 1)
                right = sright or right  # only overwrite if a semicolon present.
            # Luckily, this leaves the position of `token` intact.
            token = tlist.group_tokens_between(cls, left, right, extend=True)
        token = tlist.token_next_by(m=m, idx=tidx + 1)


def _group_matching(tlist, cls):
    """Groups Tokens that have beginning and end. ie. parenthesis, brackets.."""
    idx = 1 if imt(tlist, i=cls) else 0

    opens = []

    while True:
        try:
            token = tlist.tokens[idx]
        except IndexError:
            break

        if token.match(*cls.M_OPEN):
            opens.append(idx)
        elif token.match(*cls.M_CLOSE):
            try:
                open_idx = opens.pop()
            except IndexError:
                break
            tlist.group_tokens_between(cls, open_idx, idx)
            idx = open_idx

        idx += 1


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
        tidx = tlist.token_index(token)
        token = tlist.group_tokens_between(sql.Identifier, tidx, tidx)
        token = tlist.token_next_by(t=T_IDENT, idx=tidx + 1)


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
        prev = tlist.token_prev(idx=tlist.token_index(token))
        if imt(prev, i=(sql.SquareBrackets, sql.Identifier, sql.Function),
               t=(T.Name, T.String.Symbol,)):
            token = tlist.group_tokens_between(sql.Identifier, prev, token, extend=True)
        token = tlist.token_next_by(i=sql.SquareBrackets, idx=tlist.token_index(token) + 1)


@recurse(sql.Identifier)
def group_operator(tlist):
    I_CYCLE = (sql.SquareBrackets, sql.Parenthesis, sql.Function,
               sql.Identifier,)  # sql.Operation)
    # wilcards wouldn't have operations next to them
    T_CYCLE = T_NUMERICAL + T_STRING + T_NAME  # + T.Wildcard
    func = lambda tk: imt(tk, i=I_CYCLE, t=T_CYCLE)

    token = tlist.token_next_by(t=(T.Operator, T.Wildcard))
    while token:
        left, right = tlist.token_prev(tlist.token_index(token)), tlist.token_next(tlist.token_index(token))

        if func(left) and func(right):
            token.ttype = T.Operator
            # token = tlist.group_tokens_between(sql.Operation, left, right)
            token = tlist.group_tokens_between(sql.Identifier, left, right)

        token = tlist.token_next_by(t=(T.Operator, T.Wildcard), idx=tlist.token_index(token) + 1)


@recurse(sql.IdentifierList)
def group_identifier_list(tlist):
    I_IDENT_LIST = (sql.Function, sql.Case, sql.Identifier, sql.Comparison,
                    sql.IdentifierList)  # sql.Operation
    T_IDENT_LIST = (T_NUMERICAL + T_STRING + T_NAME +
                    (T.Keyword, T.Comment, T.Wildcard))

    func = lambda t: imt(t, i=I_IDENT_LIST, m=M_ROLE, t=T_IDENT_LIST)

    tidx, token = tlist.token_idx_next_by(m=M_COMMA)
    while token:
        before_idx, before = tlist.token_idx_prev(tidx)
        after = tlist.token_next(tidx)

        if func(before) and func(after):
            tidx = before_idx
            token = tlist.group_tokens_between(sql.IdentifierList, tidx, after, extend=True)

        tidx, token = tlist.token_idx_next_by(m=M_COMMA, idx=tidx + 1)


def group_brackets(tlist):
    _group_matching(tlist, sql.SquareBrackets)


def group_parenthesis(tlist):
    _group_matching(tlist, sql.Parenthesis)


@recurse(sql.Comment)
def group_comments(tlist):
    token = tlist.token_next_by(t=T.Comment)
    while token:
        end = tlist.token_not_matching(
            tlist.token_index(token) + 1, lambda tk: imt(tk, t=T.Comment) or tk.is_whitespace())
        if end is not None:
            end = tlist.token_prev(tlist.token_index(end), False)
            token = tlist.group_tokens_between(sql.Comment, token, end)

        token = tlist.token_next_by(t=T.Comment, idx=tlist.token_index(token) + 1)


@recurse(sql.Where)
def group_where(tlist):
    token = tlist.token_next_by(m=sql.Where.M_OPEN)
    while token:
        end = tlist.token_next_by(m=sql.Where.M_CLOSE, idx=tlist.token_index(token) + 1)

        if end is None:
            end = tlist._groupable_tokens[-1]
        else:
            end = tlist.tokens[tlist.token_index(end) - 1]

        token = tlist.group_tokens_between(sql.Where, token, end)
        token = tlist.token_next_by(m=sql.Where.M_OPEN, idx=tlist.token_index(token) + 1)


@recurse()
def group_aliased(tlist):
    I_ALIAS = (sql.Parenthesis, sql.Function, sql.Case, sql.Identifier,
               )  # sql.Operation)

    tidx, token = tlist.token_idx_next_by(i=I_ALIAS, t=T.Number)
    while token:
        next_ = tlist.token_next(tidx)
        if imt(next_, i=sql.Identifier):
            token = tlist.group_tokens_between(sql.Identifier, tidx, next_, extend=True)
        tidx, token = tlist.token_idx_next_by(i=I_ALIAS, t=T.Number, idx=tidx + 1)


def group_typecasts(tlist):
    _group_left_right(tlist, (T.Punctuation, '::'), sql.Identifier)


@recurse(sql.Function)
def group_functions(tlist):
    has_create = False
    has_table = False
    for tmp_token in tlist.tokens:
        if tmp_token.value == u'CREATE':
            has_create = True
        if tmp_token.value == u'TABLE':
            has_table = True
    if has_create and has_table:
        return
    token = tlist.token_next_by(t=T.Name)
    while token:
        next_ = tlist.token_next(tlist.token_index(token))
        if imt(next_, i=sql.Parenthesis):
            token = tlist.group_tokens_between(sql.Function, token, next_)
        token = tlist.token_next_by(t=T.Name, idx=tlist.token_index(token) + 1)


def group_order(tlist):
    """Group together Identifier and Asc/Desc token"""
    token = tlist.token_next_by(t=T.Keyword.Order)
    while token:
        prev = tlist.token_prev(tlist.token_index(token))
        if imt(prev, i=sql.Identifier, t=T.Number):
            token = tlist.group_tokens_between(sql.Identifier, prev, token)
        token = tlist.token_next_by(t=T.Keyword.Order, idx=tlist.token_index(token) + 1)


@recurse()
def align_comments(tlist):
    token = tlist.token_next_by(i=sql.Comment)
    while token:
        before = tlist.token_prev(tlist.token_index(token))
        if isinstance(before, sql.TokenList):
            token = tlist.group_tokens_between(sql.TokenList, before, token, extend=True)
        token = tlist.token_next_by(i=sql.Comment, idx=tlist.token_index(token) + 1)


def group(tlist):
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
        func(tlist)
