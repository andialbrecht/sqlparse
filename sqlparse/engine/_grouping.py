# -*- coding: utf-8 -*-

import re

from sqlparse.engine.filter import TokenFilter
from sqlparse import tokens as T

class _Base(object):

    __slots__ = ('to_unicode', 'to_str', '_get_repr_name')

    def __unicode__(self):
        return 'Unkown _Base object'

    def __str__(self):
        return unicode(self).encode('latin-1')

    def __repr__(self):
        raw = unicode(self)
        if len(raw) > 7:
            short = raw[:6]+u'...'
        else:
            short = raw
        short = re.sub('\s+', ' ', short)
        return '<%s \'%s\' at 0x%07x>' % (self._get_repr_name(),
                                          short, id(self))

    def _get_repr_name(self):
        return self.__class__.__name__

    def to_unicode(self):
        return unicode(self)

    def to_str(self):
        return str(self)


class Token(_Base):

    __slots__ = ('value', 'ttype')

    def __init__(self, ttype, value):
        self.value = value
        self.ttype = ttype

    def __unicode__(self):
        return self.value

    def _get_repr_name(self):
        return str(self.ttype).split('.')[-1]

    def match(self, ttype, values):
        if self.ttype is not ttype:
            return False
        if isinstance(values, basestring):
            values = [values]
        if self.ttype is T.Keyword:
            return self.value.upper() in [v.upper() for v in values]
        else:
            return self.value in values

    def is_group(self):
        return False

    def is_whitespace(self):
        return self.ttype and self.ttype is T.Whitespace


class _Group(Token):

    __slots__ = ('value', 'ttype', 'tokens')

    def __init__(self, tokens=None):
        super(_Group, self).__init__(None, None)
        if tokens is None:
            tokens = []
        self._tokens = tokens

    def _set_tokens(self, tokens):
        self._tokens = tokens
    def _get_tokens(self):
        if type(self._tokens) is not types.TupleType:
            self._tokens = tuple(self._tokens)
        return self._tokens
    tokens = property(fget=_get_tokens, fset=_set_tokens)

    def _get_repr_name(self):
        return self.__class__.__name__

    def _pprint_tree(self, depth=0):
        """Pretty-print the object tree."""
        indent = ' '*(depth*2)
        for token in self.tokens:
            print '%s%r' % (indent, token)
            if token.is_group():
                token._pprint_tree(depth+1)

    def __unicode__(self):
        return u''.join(unicode(t) for t in self.tokens)

    @property
    def subgroups(self):
        #return [x for x in self.tokens if isinstance(x, _Group)]
        for item in self.tokens:
            if item.is_group():
                yield item

    def is_group(self):
        return True


class Statement(_Group):
    __slots__ = ('value', 'ttype', '_tokens')


class Parenthesis(_Group):
    __slots__ = ('value', 'ttype', '_tokens')


class Where(_Group):
    __slots__ = ('value', 'ttype', '_tokens')


class CommentMulti(_Group):
    __slots__ = ('value', 'ttype', '_tokens')


class Identifier(_Group):
    __slots__ = ('value', 'ttype', '_tokens')


class TypeCast(_Group):
    __slots__ = ('value', 'ttype', '_tokens')

    @property
    def casted_object(self):
        return self.tokens[0]

    @property
    def casted_type(self):
        return self.tokens[-1]


class Alias(_Group):
    __slots__ = ('value', 'ttype', '_tokens')

    @property
    def aliased_object(self):
        return self.tokens[0]

    @property
    def alias(self):
        return self.tokens[-1]




# - Filter

class StatementFilter(TokenFilter):

    def __init__(self):
        self._in_declare = False
        self._in_dbldollar = False
        self._is_create = False

    def _reset(self):
        self._in_declare = False
        self._in_dbldollar = False
        self._is_create = False

    def _change_splitlevel(self, ttype, value):
        # PostgreSQL
        if (ttype == T.Name.Builtin
            and value.startswith('$') and value.endswith('$')):
            if self._in_dbldollar:
                self._in_dbldollar = False
                return -1
            else:
                self._in_dbldollar = True
                return 1
        elif self._in_dbldollar:
            return 0

        # ANSI
        if ttype is not T.Keyword:
            return 0

        unified = value.upper()

        if unified == 'DECLARE':
            self._in_declare = True
            return 1

        if unified == 'BEGIN':
            if self._in_declare:
                return 0
            return 0

        if unified == 'END':
            return -1

        if ttype is T.Keyword.DDL and unified.startswith('CREATE'):
            self._is_create = True

        if unified in ('IF', 'FOR') and self._is_create:
            return 1

        # Default
        return 0

    def process(self, stack, stream):
        splitlevel = 0
        stmt = None
        consume_ws = False
        stmt_tokens = []
        for ttype, value in stream:
            # Before appending the token
            if (consume_ws and ttype is not T.Whitespace
                and ttype is not T.Comment.Single):
                consume_ws = False
                stmt.tokens = stmt_tokens
                yield stmt
                self._reset()
                stmt = None
                splitlevel = 0
            if stmt is None:
                stmt = Statement()
                stmt_tokens = []
            splitlevel += self._change_splitlevel(ttype, value)
            # Append the token
            stmt_tokens.append(Token(ttype, value))
            # After appending the token
            if (not splitlevel and ttype is T.Punctuation
                and value == ';'):
                consume_ws = True
        if stmt is not None:
            stmt.tokens = stmt_tokens
            yield stmt


class GroupFilter(object):

    def process(self, stream):
        pass


class GroupParenthesis(GroupFilter):
    """Group parenthesis groups."""

    def _finish_group(self, group):
        start = group[0]
        end = group[-1]
        tokens = list(self._process(group[1:-1]))
        return [start]+tokens+[end]

    def _process(self, stream):
        group = None
        depth = 0
        for token in stream:
            if token.is_group():
                token.tokens = self._process(token.tokens)
            if token.match(T.Punctuation, '('):
                if depth == 0:
                    group = []
                depth += 1
            if group is not None:
                group.append(token)
            if token.match(T.Punctuation, ')'):
                depth -= 1
                if depth == 0:
                    yield Parenthesis(self._finish_group(group))
                    group = None
                    continue
            if group is None:
                yield token

    def process(self, group):
        if not isinstance(group, Parenthesis):
            group.tokens = self._process(group.tokens)


class GroupWhere(GroupFilter):

    def _process(self, stream):
        group = None
        depth = 0
        for token in stream:
            if token.is_group():
                token.tokens = self._process(token.tokens)
            if token.match(T.Keyword, 'WHERE'):
                if depth == 0:
                    group = []
                depth += 1
            # Process conditions here? E.g. "A =|!=|in|is|... B"...
            elif (token.ttype is T.Keyword
                  and token.value.upper() in ('ORDER', 'GROUP',
                                              'LIMIT', 'UNION')):
                depth -= 1
                if depth == 0:
                    yield Where(group)
                    group = None
                if depth < 0:
                    depth = 0
            if group is not None:
                group.append(token)
            else:
                yield token
        if group is not None:
            yield Where(group)

    def process(self, group):
        if not isinstance(group, Where):
            group.tokens = self._process(group.tokens)


class GroupMultiComments(GroupFilter):
    """Groups Comment.Multiline and adds trailing whitespace up to first lb."""

    def _process(self, stream):
        new_tokens = []
        grp = None
        consume_ws = False
        for token in stream:
            if token.is_group():
                token.tokens = self._process(token.tokens)
            if token.ttype is T.Comment.Multiline:
                if grp is None:
                    grp = []
                    consume_ws = True
                grp.append(token)
            elif consume_ws and token.ttype is not T.Whitespace:
                yield CommentMulti(grp)
                grp = None
                consume_ws = False
                yield token
            elif consume_ws:
                lines = token.value.splitlines(True)
                grp.append(Token(T.Whitespace, lines[0]))
                if lines[0].endswith('\n'):
                    yield CommentMulti(grp)
                    grp = None
                    consume_ws = False
                    if lines[1:]:
                        yield Token(T.Whitespace, ''.join(lines[1:]))
            else:
                yield token

    def process(self, group):
        if not isinstance(group, CommentMulti):
            group.tokens = self._process(group.tokens)


## class GroupIdentifier(GroupFilter):

##     def _process(self, stream):
##         buff = []
##         expect_dot = False
##         for token in stream:
##             if token.is_group():
##                 token.tokens = self._process(token.tokens)
##             if (token.ttype is T.String.Symbol or token.ttype is T.Name
##                 and not expect_dot):
##                 buff.append(token)
##                 expect_dot = True
##             elif expect_dot and token.match(T.Punctuation, '.'):
##                 buff.append(token)
##                 expect_dot = False
##             else:
##                 if expect_dot == False:
##                     # something's wrong, it ends with a dot...
##                     while buff:
##                         yield buff.pop(0)
##                     expect_dot = False
##                 elif buff:
##                     idt = Identifier()
##                     idt.tokens = buff
##                     yield idt
##                     buff = []
##                 yield token
##         if buff and expect_dot:
##             idt = Identifier()
##             idt.tokens = buff
##             yield idt
##             buff = []
##         while buff:
##             yield buff.pop(0)

##     def process(self, group):
##         if not isinstance(group, Identifier):
##             group.tokens = self._process(group.tokens)


class AddTypeCastFilter(GroupFilter):

    def _process(self, stream):
        buff = []
        expect_colon = False
        has_colons = False
        for token in stream:
            if token.is_group():
                token.tokens = self._process(token.tokens)
            if ((isinstance(token, Parenthesis)
                 or isinstance(token, Identifier))
                and not expect_colon):
                buff.append(token)
                expect_colon = True
            elif expect_colon and token.match(T.Punctuation, ':'):
                buff.append(token)
                has_colons = True
            elif (expect_colon
                  and (token.ttype in T.Name
                       or isinstance(token, Identifier))
                  ):
                if not has_colons:
                    while buff:
                        yield buff.pop(0)
                    yield token
                else:
                    buff.append(token)
                    grp = TypeCast()
                    grp.tokens = buff
                    buff = []
                    yield grp
                expect_colons = has_colons = False
            else:
                while buff:
                    yield buff.pop(0)
                yield token
        while buff:
            yield buff.pop(0)

    def process(self, group):
        if not isinstance(group, TypeCast):
            group.tokens = self._process(group.tokens)


class AddAliasFilter(GroupFilter):

    def _process(self, stream):
        buff = []
        search_alias = False
        lazy = False
        for token in stream:
            if token.is_group():
                token.tokens = self._process(token.tokens)
            if search_alias and (isinstance(token, Identifier)
                                 or token.ttype in (T.Name,
                                                    T.String.Symbol)
                                 or (lazy and not token.is_whitespace())):
                buff.append(token)
                search_alias = lazy = False
                grp = Alias()
                grp.tokens = buff
                buff = []
                yield grp
            elif (isinstance(token, (Identifier, TypeCast))
                or token.ttype in (T.Name, T.String.Symbol)):
                buff.append(token)
                search_alias = True
            elif search_alias and (token.is_whitespace()
                                   or token.match(T.Keyword, 'as')):
                buff.append(token)
                if token.match(T.Keyword, 'as'):
                    lazy = True
            else:
                while buff:
                    yield buff.pop(0)
                yield token
                search_alias = False
        while buff:
            yield buff.pop(0)

    def process(self, group):
        if not isinstance(group, Alias):
            group.tokens = self._process(group.tokens)


GROUP_FILTER = (GroupParenthesis(),
                GroupMultiComments(),
                GroupWhere(),
                GroupIdentifier(),
                AddTypeCastFilter(),
                AddAliasFilter(),
                )

import types
def group_tokens(group):
    def _materialize(g):
        if type(g.tokens) is not types.TupleType:
            g.tokens = tuple(g.tokens)
        for sg in g.subgroups:
            _materialize(sg)
    for groupfilter in GROUP_FILTER:
        groupfilter.process(group)
#    _materialize(group)
#    group.tokens = tuple(group.tokens)
#    for subgroup in group.subgroups:
#        group_tokens(subgroup)
