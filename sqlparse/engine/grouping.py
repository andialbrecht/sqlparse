# -*- coding: utf-8 -*-

import itertools

from sqlparse import sql
from sqlparse import tokens as T

try:
    next
except NameError:  # Python < 2.6
    next = lambda i: i.next()


def _group_left_right(tlist, ttype, value, cls,
                      check_right=lambda t: True,
                      check_left=lambda t: True,
                      include_semicolon=False):
    [_group_left_right(sgroup, ttype, value, cls, check_right,
                       include_semicolon) for sgroup in tlist.get_sublists()
     if not isinstance(sgroup, cls)]
    idx = 0
    token = tlist.token_next_match(idx, ttype, value)
    while token:
        right = tlist.token_next(tlist.token_index(token))
        left = tlist.token_prev(tlist.token_index(token))
        if right is None or not check_right(right):
            token = tlist.token_next_match(tlist.token_index(token) + 1,
                                           ttype, value)
        elif left is None or not check_right(left):
            token = tlist.token_next_match(tlist.token_index(token) + 1,
                                           ttype, value)
        else:
            if include_semicolon:
                sright = tlist.token_next_match(tlist.token_index(right),
                                                T.Punctuation, ';')
                if sright is not None:
                    # only overwrite "right" if a semicolon is actually
                    # present.
                    right = sright
            tokens = tlist.tokens_between(left, right)[1:]
            if not isinstance(left, cls):
                new = cls([left])
                new_idx = tlist.token_index(left)
                tlist.tokens.remove(left)
                tlist.tokens.insert(new_idx, new)
                left = new
            left.tokens.extend(tokens)
            for t in tokens:
                tlist.tokens.remove(t)
            token = tlist.token_next_match(tlist.token_index(left) + 1,
                                           ttype, value)


def _group_matching(tlist, start_ttype, start_value, end_ttype, end_value,
                    cls, include_semicolon=False, recurse=False):
    def _find_matching(i, tl, stt, sva, ett, eva):
        depth = 1
        for n in xrange(i, len(tl.tokens)):
            t = tl.tokens[n]
            if t.match(stt, sva):
                depth += 1
            elif t.match(ett, eva):
                depth -= 1
                if depth == 1:
                    return t
        return None
    [_group_matching(sgroup, start_ttype, start_value, end_ttype, end_value,
                     cls, include_semicolon) for sgroup in tlist.get_sublists()
     if recurse]
    if isinstance(tlist, cls):
        idx = 1
    else:
        idx = 0
    token = tlist.token_next_match(idx, start_ttype, start_value)
    while token:
        tidx = tlist.token_index(token)
        end = _find_matching(tidx, tlist, start_ttype, start_value,
                             end_ttype, end_value)
        if end is None:
            idx = tidx + 1
        else:
            if include_semicolon:
                next_ = tlist.token_next(tlist.token_index(end))
                if next_ and next_.match(T.Punctuation, ';'):
                    end = next_
            group = tlist.group_tokens(cls, tlist.tokens_between(token, end))
            _group_matching(group, start_ttype, start_value,
                            end_ttype, end_value, cls, include_semicolon)
            idx = tlist.token_index(group) + 1
        token = tlist.token_next_match(idx, start_ttype, start_value)


def group_if(tlist):
    _group_matching(tlist, T.Keyword, 'IF', T.Keyword, 'END IF', sql.If, True)


def group_for(tlist):
    _group_matching(tlist, T.Keyword, 'FOR', T.Keyword, 'END LOOP',
                    sql.For, True)


def group_as(tlist):

    def _right_valid(token):
        # Currently limited to DML/DDL. Maybe additional more non SQL reserved
        # keywords should appear here (see issue8).
        return not token.ttype in (T.DML, T.DDL)
    _group_left_right(tlist, T.Keyword, 'AS', sql.Identifier,
                      check_right=_right_valid)


def group_assignment(tlist):
    _group_left_right(tlist, T.Assignment, ':=', sql.Assignment,
                      include_semicolon=True)


def group_comparison(tlist):

    def _parts_valid(token):
        return (token.ttype in (T.String.Symbol, T.Name, T.Number,
                                T.Number.Integer, T.Literal,
                                T.Literal.Number.Integer)
                or isinstance(token, (sql.Identifier,)))
    _group_left_right(tlist, T.Operator.Comparison, None, sql.Comparison,
                      check_left=_parts_valid, check_right=_parts_valid)


def group_case(tlist):
    _group_matching(tlist, T.Keyword, 'CASE', T.Keyword, 'END', sql.Case,
                    include_semicolon=True, recurse=True)


def group_identifier(tlist):
    def _consume_cycle(tl, i):
        # TODO: Usage of Wildcard token is ambivalent here.
        x = itertools.cycle((
            lambda y: (y.match(T.Punctuation, '.')
                       or y.ttype is T.Operator
                       or y.ttype is T.Wildcard),
            lambda y: (y.ttype in (T.String.Symbol,
                                   T.Name,
                                   T.Wildcard,
                                   T.Literal.Number.Integer))))
        for t in tl.tokens[i:]:
            if next(x)(t):
                yield t
            else:
                raise StopIteration

    def _next_token(tl, i):
        # chooses the next token. if two tokens are found then the
        # first is returned.
        t1 = tl.token_next_by_type(i, (T.String.Symbol, T.Name))
        t2 = tl.token_next_by_instance(i, sql.Function)
        if t1 and t2:
            i1 = tl.token_index(t1)
            i2 = tl.token_index(t2)
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
                           tlist.token_index(token) + 1))
        if not (len(identifier_tokens) == 1
                and isinstance(identifier_tokens[0], sql.Function)):
            group = tlist.group_tokens(sql.Identifier, identifier_tokens)
            idx = tlist.token_index(group) + 1
        else:
            idx += 1
        token = _next_token(tlist, idx)


def group_identifier_list(tlist):
    for sgroup in tlist.get_sublists():
        if not isinstance(sgroup, sql.IdentifierList):
            group_identifier_list(sgroup)

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
                   lambda t: isinstance(t, sql.Comparison),
                   lambda t: isinstance(t, sql.Comment),
                   ]

    def group_identifierlist(start, after):
        """
        Create and group the identifiers list
        """
        tokens = tlist.tokens_between(start, after)
        return tlist.group_tokens(sql.IdentifierList, tokens)

    # Search for the first identifier list
    start = None
    tcomma = tlist.token_next_match(0, T.Punctuation, ',')

    while tcomma:
        before = tlist.token_prev(tcomma)
        after = tlist.token_next(tcomma)

        # Check if the tokens around tcomma belong to an identifier list
        bpassed = apassed = False
        for func in fend1_funcs:
            if before and func(before):
                bpassed = True
            if after and func(after):
                apassed = True

        # Both tokens around tcomma belong to a list
        if bpassed and apassed:
            # Set the start of the identifier list if not defined before
            if start == None:
                start = before

                # Check the next token
                next_ = tlist.token_next(after)
                while next_:
                    if next_.value != ',':
                        passed = False
                        for func in fend1_funcs:
                            if func(next_):
                                passed = True
                                break

                        if not passed:
                            break

                    after = next_
                    next_ = tlist.token_next(next_)

            # Reached the end of the list
            # Create and group the identifiers list
            tcomma = group_identifierlist(start, after)

        # Skip ahead to next identifier list
        start = None
        tcomma = tlist.token_next_match(tlist.token_index(tcomma) + 1,
                                        T.Punctuation, ',')

    # There's an open identifier list, create and group the identifiers list
    if start:
        group_identifierlist(start, after)


def group_parenthesis(tlist):
    _group_matching(tlist, T.Punctuation, '(', T.Punctuation, ')',
                    sql.Parenthesis)


def group_comments(tlist):
    [group_comments(sgroup) for sgroup in tlist.get_sublists()
     if not isinstance(sgroup, sql.Comment)]
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


def group_where(tlist):
    [group_where(sgroup) for sgroup in tlist.get_sublists()
     if not isinstance(sgroup, sql.Where)]
    idx = 0
    token = tlist.token_next_match(idx, T.Keyword, 'WHERE')
    stopwords = ('ORDER', 'GROUP', 'LIMIT', 'UNION')
    while token:
        tidx = tlist.token_index(token)
        end = tlist.token_next_match(tidx + 1, T.Keyword, stopwords)
        if end is None:
            end = tlist._groupable_tokens[-1]
        else:
            end = tlist.tokens[tlist.token_index(end) - 1]
        group = tlist.group_tokens(sql.Where,
                                   tlist.tokens_between(token, end),
                                   ignore_ws=True)
        idx = tlist.token_index(group)
        token = tlist.token_next_match(idx, T.Keyword, 'WHERE')


def group_aliased(tlist):
    clss = (sql.Identifier, sql.Function, sql.Case)
    [group_aliased(sgroup) for sgroup in tlist.get_sublists()
     if not isinstance(sgroup, clss)]
    idx = 0
    token = tlist.token_next_by_instance(idx, clss)
    while token:
        next_ = tlist.token_next(tlist.token_index(token))
        if next_ is not None and isinstance(next_, clss):
            grp = tlist.tokens_between(token, next_)[1:]
            token.tokens.extend(grp)
            for t in grp:
                tlist.tokens.remove(t)
        idx = tlist.token_index(token) + 1
        token = tlist.token_next_by_instance(idx, clss)


def group_typecasts(tlist):
    _group_left_right(tlist, T.Punctuation, '::', sql.Identifier)


def group_functions(tlist):
    [group_functions(sgroup) for sgroup in tlist.get_sublists()
     if not isinstance(sgroup, sql.Function)]
    idx = 0
    token = tlist.token_next_by_type(idx, T.Name)
    while token:
        next_ = tlist.token_next(token)
        if not isinstance(next_, sql.Parenthesis):
            idx = tlist.token_index(token) + 1
        else:
            func = tlist.group_tokens(sql.Function,
                                      tlist.tokens_between(token, next_))
            idx = tlist.token_index(func) + 1
        token = tlist.token_next_by_type(idx, T.Name)


def group(tlist):
    for func in [
            group_comments,
            group_parenthesis,
            group_functions,
            group_where,
            group_case,
            group_identifier,
            group_typecasts,
            group_as,
            group_aliased,
            group_assignment,
            group_comparison,
            group_identifier_list,
            group_if,
            group_for]:
        func(tlist)
