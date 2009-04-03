# -*- coding: utf-8 -*-

import itertools
import re
import types

from sqlparse import tokens as T


class Token(object):

    __slots__ = ('value', 'ttype')

    def __init__(self, ttype, value):
        self.value = value
        self.ttype = ttype

    def __str__(self):
        return unicode(self).encode('latin-1')

    def __repr__(self):
        short = self._get_repr_value()
        return '<%s \'%s\' at 0x%07x>' % (self._get_repr_name(),
                                          short, id(self))

    def __unicode__(self):
        return self.value

    def to_unicode(self):
        return unicode(self)

    def _get_repr_name(self):
        return str(self.ttype).split('.')[-1]

    def _get_repr_value(self):
        raw = unicode(self)
        if len(raw) > 7:
            short = raw[:6]+u'...'
        else:
            short = raw
        return re.sub('\s+', ' ', short)

    def match(self, ttype, values, regex=False):
        if self.ttype is not ttype:
            return False
        if values is None:
            return self.ttype is ttype
        if isinstance(values, basestring):
            values = [values]
        if regex:
            if self.ttype is T.Keyword:
                values = [re.compile(v, re.IGNORECASE) for v in values]
            else:
                values = [re.compile(v) for v in values]
            for pattern in values:
                if pattern.search(self.value):
                    return True
            return False
        else:
            if self.ttype is T.Keyword:
                return self.value.upper() in [v.upper() for v in values]
            else:
                return self.value in values

    def is_group(self):
        return False

    def is_whitespace(self):
        return self.ttype and self.ttype in T.Whitespace


class TokenList(Token):

    __slots__ = ('value', 'ttype', 'tokens')

    def __init__(self, tokens=None):
        if tokens is None:
            tokens = []
        self.tokens = tokens
        Token.__init__(self, None, None)

    def __unicode__(self):
        return ''.join(unicode(x) for x in self.flatten())

    def __str__(self):
        return unicode(self).encode('latin-1')

    def _get_repr_name(self):
        return self.__class__.__name__

    def _pprint_tree(self, max_depth=None, depth=0):
        """Pretty-print the object tree."""
        indent = ' '*(depth*2)
        for token in self.tokens:
            if token.is_group():
                pre = ' | '
            else:
                pre = ' | '
            print '%s%s%s \'%s\'' % (indent, pre, token._get_repr_name(),
                                     token._get_repr_value())
            if (token.is_group() and max_depth is not None
                and depth < max_depth):
                token._pprint_tree(max_depth, depth+1)

    def flatten(self):
        for token in self.tokens:
            if isinstance(token, TokenList):
                for item in token.flatten():
                    yield item
            else:
                yield token

    def is_group(self):
        return True

    def get_sublists(self):
        return [x for x in self.tokens if isinstance(x, TokenList)]

    def token_first(self, ignore_whitespace=True):
        for token in self.tokens:
            if ignore_whitespace and token.is_whitespace():
                continue
            return token
        return None

    def token_next_by_instance(self, idx, clss):
        if type(clss) not in (types.ListType, types.TupleType):
            clss = (clss,)
        if type(clss) is not types.TupleType:
            clss = tuple(clss)
        for token in self.tokens[idx:]:
            if isinstance(token, clss):
                return token
        return None

    def token_next_by_type(self, idx, ttypes):
        if not isinstance(ttypes, (types.TupleType, types.ListType)):
            ttypes = [ttypes]
        for token in self.tokens[idx:]:
            if token.ttype in ttypes:
                return token
        return None

    def token_next_match(self, idx, ttype, value, regex=False):
        if type(idx) != types.IntType:
            idx = self.token_index(idx)
        for token in self.tokens[idx:]:
            if token.match(ttype, value, regex):
                return token
        return None

    def token_not_matching(self, idx, funcs):
        for token in self.tokens[idx:]:
            passed = False
            for func in funcs:
                if func(token):
                   passed = True
                   break
            if not passed:
                return token
        return None

    def token_prev(self, idx, skip_ws=True):
        while idx != 0:
            idx -= 1
            if self.tokens[idx].is_whitespace() and skip_ws:
                continue
            return self.tokens[idx]

    def token_next(self, idx, skip_ws=True):
        while idx < len(self.tokens)-1:
            idx += 1
            if self.tokens[idx].is_whitespace() and skip_ws:
                continue
            return self.tokens[idx]

    def token_index(self, token):
        """Return list index of token."""
        return self.tokens.index(token)

    def tokens_between(self, start, end, exclude_end=False):
        """Return all tokens between (and including) start and end."""
        if exclude_end:
            offset = 0
        else:
            offset = 1
        return self.tokens[self.token_index(start):self.token_index(end)+offset]

    def group_tokens(self, grp_cls, tokens):
        """Replace tokens by instance of grp_cls."""
        idx = self.token_index(tokens[0])
        for t in tokens:
            self.tokens.remove(t)
        grp = grp_cls(tokens)
        self.tokens.insert(idx, grp)
        return grp

    def insert_before(self, where, token):
        self.tokens.insert(self.token_index(where), token)


class Statement(TokenList):

    __slots__ = ('value', 'ttype', 'tokens')

    def get_type(self):
        first_token = self.token_first()
        if first_token.ttype in (T.Keyword.DML, T.Keyword.DDL):
            return first_token.value.upper()
        else:
            return 'UNKNOWN'


class Identifier(TokenList):

    __slots__ = ('value', 'ttype', 'tokens')

    def has_alias(self):
        return self.get_alias() is not None

    def get_alias(self):
        kw = self.token_next_match(0, T.Keyword, 'AS')
        if kw is not None:
            alias = self.token_next(self.token_index(kw))
            if alias is None:
                return None
        else:
            next_ = self.token_next(0)
            if next_ is None or not isinstance(next_, Identifier):
                return None
            alias = next_
        if isinstance(alias, Identifier):
            return alias.get_name()
        else:
            return alias.to_unicode()

    def get_name(self):
        alias = self.get_alias()
        if alias is not None:
            return alias
        return self.get_real_name()

    def get_real_name(self):
        return self.token_next_by_type(0, T.Name).value

    def get_typecast(self):
        marker = self.token_next_match(0, T.Punctuation, '::')
        if marker is None:
            return None
        next_ = self.token_next(self.token_index(marker), False)
        if next_ is None:
            return None
        return next_.to_unicode()


class IdentifierList(TokenList):

    __slots__ = ('value', 'ttype', 'tokens')

    def get_identifiers(self):
        return [x for x in self.tokens if isinstance(x, Identifier)]


class Parenthesis(TokenList):
    __slots__ = ('value', 'ttype', 'tokens')


class Assignment(TokenList):
    __slots__ = ('value', 'ttype', 'tokens')

class If(TokenList):
    __slots__ = ('value', 'ttype', 'tokens')

class For(TokenList):
    __slots__ = ('value', 'ttype', 'tokens')

class Comparsion(TokenList):
    __slots__ = ('value', 'ttype', 'tokens')

class Comment(TokenList):
    __slots__ = ('value', 'ttype', 'tokens')

class Where(TokenList):
    __slots__ = ('value', 'ttype', 'tokens')


class Case(TokenList):

    __slots__ = ('value', 'ttype', 'tokens')

    def get_cases(self):
        """Returns a list of 2-tuples (condition, value).

        If an ELSE exists condition is None.
        """
        ret = []
        in_condition = in_value = False
        for token in self.tokens:
            if token.match(T.Keyword, 'WHEN'):
                ret.append(([], []))
                in_condition = True
                in_value = False
            elif token.match(T.Keyword, 'ELSE'):
                ret.append((None, []))
                in_condition = False
                in_value = True
            elif token.match(T.Keyword, 'THEN'):
                in_condition = False
                in_value = True
            elif token.match(T.Keyword, 'END'):
                in_condition = False
                in_value = False
            if in_condition:
                ret[-1][0].append(token)
            elif in_value:
                ret[-1][1].append(token)
        return ret

def _group_left_right(tlist, ttype, value, cls,
                      check_right=lambda t: True,
                      include_semicolon=False):
#    [_group_left_right(sgroup, ttype, value, cls, check_right,
#                       include_semicolon) for sgroup in tlist.get_sublists()
#     if not isinstance(sgroup, cls)]
    idx = 0
    token = tlist.token_next_match(idx, ttype, value)
    while token:
        right = tlist.token_next(tlist.token_index(token))
        left = tlist.token_prev(tlist.token_index(token))
        if (right is None or not check_right(right)
            or left is None):
            token = tlist.token_next_match(tlist.token_index(token)+1,
                                           ttype, value)
        else:
            if include_semicolon:
                right = tlist.token_next_match(tlist.token_index(right),
                                               T.Punctuation, ';')
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
            token = tlist.token_next_match(tlist.token_index(left)+1,
                                           ttype, value)

def _group_matching(tlist, start_ttype, start_value, end_ttype, end_value,
                    cls, include_semicolon=False, recurse=False):
    def _find_matching(i, tl, stt, sva, ett, eva):
        depth = 1
        for t in tl.tokens[i:]:
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
            idx = tidx+1
        else:
            if include_semicolon:
                next_ = tlist.token_next(tlist.token_index(end))
                if next_ and next_.match(T.Punctuation, ';'):
                    end = next_
            group = tlist.group_tokens(cls, tlist.tokens_between(token, end))
            _group_matching(group, start_ttype, start_value,
                            end_ttype, end_value, cls, include_semicolon)
            idx = tlist.token_index(group)+1
        token = tlist.token_next_match(idx, start_ttype, start_value)

def group_if(tlist):
    _group_matching(tlist, T.Keyword, 'IF', T.Keyword, 'END IF', If, True)

def group_for(tlist):
    _group_matching(tlist, T.Keyword, 'FOR', T.Keyword, 'END LOOP', For, True)

def group_as(tlist):
    _group_left_right(tlist, T.Keyword, 'AS', Identifier)

def group_assignment(tlist):
    _group_left_right(tlist, T.Assignment, ':=', Assignment,
                      include_semicolon=True)

def group_comparsion(tlist):
    _group_left_right(tlist, T.Operator, None, Comparsion)


def group_case(tlist):
    _group_matching(tlist, T.Keyword, 'CASE', T.Keyword, 'END', Case, True)


def group_identifier(tlist):
    def _consume_cycle(tl, i):
        x = itertools.cycle((lambda y: y.match(T.Punctuation, '.'),
                             lambda y: y.ttype in (T.String.Symbol, T.Name)))
        for t in tl.tokens[i:]:
            if x.next()(t):
                yield t
            else:
                raise StopIteration

    # bottom up approach: group subgroups first
    [group_identifier(sgroup) for sgroup in tlist.get_sublists()
     if not isinstance(sgroup, Identifier)]

    # real processing
    idx = 0
    token = tlist.token_next_by_type(idx, (T.String.Symbol, T.Name))
    while token:
        identifier_tokens = [token]+list(
            _consume_cycle(tlist,
                           tlist.token_index(token)+1))
        group = tlist.group_tokens(Identifier, identifier_tokens)
        idx = tlist.token_index(group)+1
        token = tlist.token_next_by_type(idx, (T.String.Symbol, T.Name))


def group_identifier_list(tlist):
    [group_identifier_list(sgroup) for sgroup in tlist.get_sublists()
     if not isinstance(sgroup, IdentifierList)]
    idx = 0
    token = tlist.token_next_by_instance(idx, Identifier)
    while token:
        tidx = tlist.token_index(token)
        end = tlist.token_not_matching(tidx+1,
                                       [lambda t: isinstance(t, Identifier),
                                        lambda t: t.is_whitespace(),
                                        lambda t: t.match(T.Punctuation,
                                                          ',')
                                        ])
        if end is None:
            idx = tidx + 1
        else:
            grp_tokens = tlist.tokens_between(token, end, exclude_end=True)
            while grp_tokens and (grp_tokens[-1].is_whitespace()
                                  or grp_tokens[-1].match(T.Punctuation, ',')):
                grp_tokens.pop()
            if len(grp_tokens) <= 1:
                idx = tidx + 1
            else:
                group = tlist.group_tokens(IdentifierList, grp_tokens)
                idx = tlist.token_index(group)
        token = tlist.token_next_by_instance(idx, Identifier)


def group_parenthesis(tlist):
    _group_matching(tlist, T.Punctuation, '(', T.Punctuation, ')', Parenthesis)

def group_comments(tlist):
    [group_comments(sgroup) for sgroup in tlist.get_sublists()
     if not isinstance(sgroup, Comment)]
    idx = 0
    token = tlist.token_next_by_type(idx, T.Comment)
    while token:
        tidx = tlist.token_index(token)
        end = tlist.token_not_matching(tidx+1,
                                       [lambda t: t.ttype in T.Comment,
                                        lambda t: t.is_whitespace()])
        if end is None:
            idx = tidx + 1
        else:
            eidx = tlist.token_index(end)
            grp_tokens = tlist.tokens_between(token,
                                              tlist.token_prev(eidx, False))
            group = tlist.group_tokens(Comment, grp_tokens)
            idx = tlist.token_index(group)
        token = tlist.token_next_by_type(idx, T.Comment)

def group_where(tlist):
    [group_where(sgroup) for sgroup in tlist.get_sublists()
     if not isinstance(sgroup, Where)]
    idx = 0
    token = tlist.token_next_match(idx, T.Keyword, 'WHERE')
    stopwords = ('ORDER', 'GROUP', 'LIMIT', 'UNION')
    while token:
        tidx = tlist.token_index(token)
        end = tlist.token_next_match(tidx+1, T.Keyword, stopwords)
        if end is None:
            end = tlist.tokens[-1]
        else:
            end = tlist.tokens[tlist.token_index(end)-1]
        group = tlist.group_tokens(Where, tlist.tokens_between(token, end))
        idx = tlist.token_index(group)
        token = tlist.token_next_match(idx, T.Keyword, 'WHERE')

def group_aliased(tlist):
    [group_aliased(sgroup) for sgroup in tlist.get_sublists()
     if not isinstance(sgroup, Identifier)]
    idx = 0
    token = tlist.token_next_by_instance(idx, Identifier)
    while token:
        next_ = tlist.token_next(tlist.token_index(token))
        if next_ is not None and isinstance(next_, Identifier):
            grp = tlist.tokens_between(token, next_)[1:]
            token.tokens.extend(grp)
            for t in grp:
                tlist.tokens.remove(t)
        idx = tlist.token_index(token)+1
        token = tlist.token_next_by_instance(idx, Identifier)


def group_typecasts(tlist):
    _group_left_right(tlist, T.Punctuation, '::', Identifier)


def group(tlist):
    for func in [group_parenthesis,
                 group_comments,
                 group_where,
                 group_case,
                 group_identifier,
                 group_typecasts,
                 group_as,
                 group_aliased,
                 group_assignment,
                 group_comparsion,
                 group_identifier_list,
                 group_if,
                 group_for,]:
        func(tlist)
