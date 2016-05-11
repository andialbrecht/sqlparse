# -*- coding: utf-8 -*-

import itertools

from sqlparse import sql
from sqlparse import tokens as T
from sqlparse.utils import recurse, imt, find_matching

M_ROLE = (T.Keyword, ('null', 'role'))
M_SEMICOLON = (T.Punctuation, ';')

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
                sright = tlist.token_next_by(m=M_SEMICOLON, idx=right)
                right = sright or right  # only overwrite if a semicolon present.
            tokens = tlist.tokens_between(left, right)
            token = tlist.group_tokens(cls, tokens, extend=True)
        token = tlist.token_next_by(m=m, idx=token)


def _group_matching(tlist, cls):
    """Groups Tokens that have beginning and end. ie. parenthesis, brackets.."""
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


def group_identifier(tlist):
    def _consume_cycle(tl, i):
        # TODO: Usage of Wildcard token is ambivalent here.
        x = itertools.cycle((
            lambda y: (y.match(T.Punctuation, '.')
                       or y.ttype in (T.Operator,
                                      T.Wildcard,
                                      T.Name)
                       or isinstance(y, sql.SquareBrackets)),
            lambda y: (y.ttype in (T.String.Symbol,
                                   T.Name,
                                   T.Wildcard,
                                   T.Literal.String.Single,
                                   T.Literal.Number.Integer,
                                   T.Literal.Number.Float)
                       or isinstance(y, (sql.Parenthesis,
                                         sql.SquareBrackets,
                                         sql.Function)))))
        for t in tl.tokens[i:]:
            # Don't take whitespaces into account.
            if t.ttype is T.Whitespace:
                yield t
                continue
            if next(x)(t):
                yield t
            else:
                if isinstance(t, sql.Comment) and t.is_multiline():
                    yield t
                if t.ttype is T.Keyword.Order:
                    yield t
                return

    def _next_token(tl, i):
        # chooses the next token. if two tokens are found then the
        # first is returned.
        t1 = tl.token_next_by_type(
            i, (T.String.Symbol, T.Name, T.Literal.Number.Integer,
                T.Literal.Number.Float))

        i1 = tl.token_index(t1, start=i) if t1 else None
        t2_end = None if i1 is None else i1 + 1
        t2 = tl.token_next_by_instance(i, (sql.Function, sql.Parenthesis),
                                       end=t2_end)

        if t1 and t2:
            i2 = tl.token_index(t2, start=i)
            if i1 > i2:
                return t2
            else:
                return t1
        elif t1:
            return t1
        else:
            return t2

    # bottom up approach: group subgroups first
    [group_identifier(sgroup) for sgroup in tlist.get_sublists()
     if not isinstance(sgroup, sql.Identifier)]

    # real processing
    idx = 0
    token = _next_token(tlist, idx)
    while token:
        identifier_tokens = [token] + list(
            _consume_cycle(tlist,
                           tlist.token_index(token, start=idx) + 1))
        # remove trailing whitespace
        if identifier_tokens and identifier_tokens[-1].ttype is T.Whitespace:
            identifier_tokens = identifier_tokens[:-1]
        if not (len(identifier_tokens) == 1
                and (isinstance(identifier_tokens[0], (sql.Function,
                                                       sql.Parenthesis))
                     or identifier_tokens[0].ttype in (
                    T.Literal.Number.Integer, T.Literal.Number.Float))):
            group = tlist.group_tokens(sql.Identifier, identifier_tokens)
            idx = tlist.token_index(group, start=idx) + 1
        else:
            idx += 1
        token = _next_token(tlist, idx)


@recurse(sql.IdentifierList)
def group_identifier_list(tlist):
    # Allowed list items
    fend1_funcs = [lambda t: isinstance(t, (sql.Identifier, sql.Function,
                                            sql.Case)),
                   lambda t: t.is_whitespace(),
                   lambda t: t.ttype == T.Name,
                   lambda t: t.ttype == T.Wildcard,
                   lambda t: t.match(T.Keyword, 'null'),
                   lambda t: t.match(T.Keyword, 'role'),
                   lambda t: t.ttype == T.Number.Integer,
                   lambda t: t.ttype == T.String.Single,
                   lambda t: t.ttype == T.Name.Placeholder,
                   lambda t: t.ttype == T.Keyword,
                   lambda t: isinstance(t, sql.Comparison),
                   lambda t: isinstance(t, sql.Comment),
                   lambda t: t.ttype == T.Comment.Multiline,
                   ]
    tcomma = tlist.token_next_match(0, T.Punctuation, ',')
    start = None
    while tcomma is not None:
        # Go back one idx to make sure to find the correct tcomma
        idx = tlist.token_index(tcomma)
        before = tlist.token_prev(idx)
        after = tlist.token_next(idx)
        # Check if the tokens around tcomma belong to a list
        bpassed = apassed = False
        for func in fend1_funcs:
            if before is not None and func(before):
                bpassed = True
            if after is not None and func(after):
                apassed = True
        if not bpassed or not apassed:
            # Something's wrong here, skip ahead to next ","
            start = None
            tcomma = tlist.token_next_match(idx + 1,
                                            T.Punctuation, ',')
        else:
            if start is None:
                start = before
            after_idx = tlist.token_index(after, start=idx)
            next_ = tlist.token_next(after_idx)
            if next_ is None or not next_.match(T.Punctuation, ','):
                # Reached the end of the list
                tokens = tlist.tokens_between(start, after)
                group = tlist.group_tokens(sql.IdentifierList, tokens)
                start = None
                tcomma = tlist.token_next_match(tlist.token_index(group) + 1,
                                                T.Punctuation, ',')
            else:
                tcomma = next_


def group_brackets(tlist):
    _group_matching(tlist, sql.SquareBrackets)


def group_parenthesis(tlist):
    _group_matching(tlist, sql.Parenthesis)


@recurse(sql.Comment)
def group_comments(tlist):
    idx = 0
    token = tlist.token_next_by_type(idx, T.Comment)
    while token:
        tidx = tlist.token_index(token)
        end = tlist.token_not_matching(tidx + 1,
                                       [lambda t: t.ttype in T.Comment,
                                        lambda t: t.is_whitespace()])
        if end is None:
            idx = tidx + 1
        else:
            eidx = tlist.token_index(end)
            grp_tokens = tlist.tokens_between(token,
                                              tlist.token_prev(eidx, False))
            group = tlist.group_tokens(sql.Comment, grp_tokens)
            idx = tlist.token_index(group)
        token = tlist.token_next_by_type(idx, T.Comment)


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


@recurse(sql.Identifier, sql.Function, sql.Case)
def group_aliased(tlist):
    clss = (sql.Identifier, sql.Function, sql.Case)
    idx = 0
    token = tlist.token_next_by_instance(idx, clss)
    while token:
        next_ = tlist.token_next(tlist.token_index(token))
        if next_ is not None and isinstance(next_, clss):
            if not next_.value.upper().startswith('VARCHAR'):
                grp = tlist.tokens_between(token, next_)[1:]
                token.tokens.extend(grp)
                for t in grp:
                    tlist.tokens.remove(t)
        idx = tlist.token_index(token) + 1
        token = tlist.token_next_by_instance(idx, clss)


def group_typecasts(tlist):
    _group_left_right(tlist, (T.Punctuation, '::'), sql.Identifier)


@recurse(sql.Function)
def group_functions(tlist):
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


def group(tlist):
    for func in [
        group_comments,
        group_brackets,
        group_parenthesis,
        group_functions,
        group_where,
        group_case,
        group_identifier,
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
