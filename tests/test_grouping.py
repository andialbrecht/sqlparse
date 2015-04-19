# -*- coding: utf-8 -*-

import pytest

import sqlparse
from sqlparse import sql
from sqlparse import tokens as T

from tests.utils import TestCaseBase


class TestGrouping(TestCaseBase):

    def test_parenthesis(self):
        s = 'select (select (x3) x2) and (y2) bar'
        parsed = sqlparse.parse(s)[0]
        self.ndiffAssertEqual(s, str(parsed))
        self.assertEqual(len(parsed.tokens), 7)
        self.assert_(isinstance(parsed.tokens[2], sql.Parenthesis))
        self.assert_(isinstance(parsed.tokens[-1], sql.Identifier))
        self.assertEqual(len(parsed.tokens[2].tokens), 5)
        self.assert_(isinstance(parsed.tokens[2].tokens[3], sql.Identifier))
        self.assert_(isinstance(parsed.tokens[2].tokens[3].tokens[0], sql.Parenthesis))
        self.assertEqual(len(parsed.tokens[2].tokens[3].tokens), 3)

    def test_comments(self):
        s = '/*\n * foo\n */   \n  bar'
        parsed = sqlparse.parse(s)[0]
        self.ndiffAssertEqual(s, unicode(parsed))
        self.assertEqual(len(parsed.tokens), 2)

    def test_assignment(self):
        s = 'foo := 1;'
        parsed = sqlparse.parse(s)[0]
        self.assertEqual(len(parsed.tokens), 1)
        self.assert_(isinstance(parsed.tokens[0], sql.Assignment))
        s = 'foo := 1'
        parsed = sqlparse.parse(s)[0]
        self.assertEqual(len(parsed.tokens), 1)
        self.assert_(isinstance(parsed.tokens[0], sql.Assignment))

    def test_identifiers(self):
        s = 'select foo.bar from "myscheme"."table" where fail. order'
        parsed = sqlparse.parse(s)[0]
        self.ndiffAssertEqual(s, unicode(parsed))
        self.assert_(isinstance(parsed.tokens[2], sql.Identifier))
        self.assert_(isinstance(parsed.tokens[6], sql.Identifier))
        self.assert_(isinstance(parsed.tokens[8], sql.Where))
        s = 'select * from foo where foo.id = 1'
        parsed = sqlparse.parse(s)[0]
        self.ndiffAssertEqual(s, unicode(parsed))
        self.assert_(isinstance(parsed.tokens[-1].tokens[-1].tokens[0],
                                sql.Identifier))
        s = 'select * from (select "foo"."id" from foo)'
        parsed = sqlparse.parse(s)[0]
        self.ndiffAssertEqual(s, unicode(parsed))
        self.assert_(isinstance(parsed.tokens[-1].tokens[3], sql.Identifier))

        s = "INSERT INTO `test` VALUES('foo', 'bar');"
        parsed = sqlparse.parse(s)[0]
        types = [l.ttype for l in parsed.tokens if not l.is_whitespace()]
        self.assertEquals(types, [T.DML, T.Keyword, None,
                                  T.Keyword, None, T.Punctuation])

        s = "select 1.0*(a+b) as col, sum(c)/sum(d) from myschema.mytable"
        parsed = sqlparse.parse(s)[0]
        self.assertEqual(len(parsed.tokens), 7)
        self.assert_(isinstance(parsed.tokens[2], sql.IdentifierList))
        self.assertEqual(len(parsed.tokens[2].tokens), 4)
        identifiers = list(parsed.tokens[2].get_identifiers())
        self.assertEqual(len(identifiers), 2)
        self.assertEquals(identifiers[0].get_alias(), u"col")

    def test_identifier_wildcard(self):
        p = sqlparse.parse('a.*, b.id')[0]
        self.assert_(isinstance(p.tokens[0], sql.IdentifierList))
        self.assert_(isinstance(p.tokens[0].tokens[0], sql.Identifier))
        self.assert_(isinstance(p.tokens[0].tokens[-1], sql.Identifier))

    def test_identifier_name_wildcard(self):
        p = sqlparse.parse('a.*')[0]
        t = p.tokens[0]
        self.assertEqual(t.get_name(), '*')
        self.assertEqual(t.is_wildcard(), True)

    def test_identifier_invalid(self):
        p = sqlparse.parse('a.')[0]
        self.assert_(isinstance(p.tokens[0], sql.Identifier))
        self.assertEqual(p.tokens[0].has_alias(), False)
        self.assertEqual(p.tokens[0].get_name(), None)
        self.assertEqual(p.tokens[0].get_real_name(), None)
        self.assertEqual(p.tokens[0].get_parent_name(), 'a')

    def test_identifier_as_invalid(self):  # issue8
        p = sqlparse.parse('foo as select *')[0]
        self.assert_(len(p.tokens), 5)
        self.assert_(isinstance(p.tokens[0], sql.Identifier))
        self.assertEqual(len(p.tokens[0].tokens), 1)
        self.assertEqual(p.tokens[2].ttype, T.Keyword)

    def test_identifier_function(self):
        p = sqlparse.parse('foo() as bar')[0]
        self.assert_(isinstance(p.tokens[0], sql.Identifier))
        self.assert_(isinstance(p.tokens[0].tokens[0], sql.Function))
        p = sqlparse.parse('foo()||col2 bar')[0]
        self.assert_(isinstance(p.tokens[0], sql.Identifier))
        self.assert_(isinstance(p.tokens[0].tokens[0], sql.Function))

    def test_identifier_extended(self):  # issue 15
        p = sqlparse.parse('foo+100')[0]
        self.assert_(isinstance(p.tokens[0], sql.Identifier))
        p = sqlparse.parse('foo + 100')[0]
        self.assert_(isinstance(p.tokens[0], sql.Identifier))
        p = sqlparse.parse('foo*100')[0]
        self.assert_(isinstance(p.tokens[0], sql.Identifier))

    def test_identifier_list(self):
        p = sqlparse.parse('a, b, c')[0]
        self.assert_(isinstance(p.tokens[0], sql.IdentifierList))
        p = sqlparse.parse('(a, b, c)')[0]
        self.assert_(isinstance(p.tokens[0].tokens[1], sql.IdentifierList))

    def test_identifier_list_case(self):
        p = sqlparse.parse('a, case when 1 then 2 else 3 end as b, c')[0]
        self.assert_(isinstance(p.tokens[0], sql.IdentifierList))
        p = sqlparse.parse('(a, case when 1 then 2 else 3 end as b, c)')[0]
        self.assert_(isinstance(p.tokens[0].tokens[1], sql.IdentifierList))

    def test_identifier_list_other(self):  # issue2
        p = sqlparse.parse("select *, null, 1, 'foo', bar from mytable, x")[0]
        self.assert_(isinstance(p.tokens[2], sql.IdentifierList))
        l = p.tokens[2]
        self.assertEqual(len(l.tokens), 13)

    def test_identifier_list_with_inline_comments(self):  # issue163
        p = sqlparse.parse('foo /* a comment */, bar')[0]
        self.assert_(isinstance(p.tokens[0], sql.IdentifierList))
        self.assert_(isinstance(p.tokens[0].tokens[0], sql.Identifier))
        self.assert_(isinstance(p.tokens[0].tokens[3], sql.Identifier))

    def test_where(self):
        s = 'select * from foo where bar = 1 order by id desc'
        p = sqlparse.parse(s)[0]
        self.ndiffAssertEqual(s, unicode(p))
        self.assertTrue(len(p.tokens), 16)
        s = 'select x from (select y from foo where bar = 1) z'
        p = sqlparse.parse(s)[0]
        self.ndiffAssertEqual(s, unicode(p))
        self.assertTrue(isinstance(p.tokens[-1].tokens[0].tokens[-2], sql.Where))

    def test_typecast(self):
        s = 'select foo::integer from bar'
        p = sqlparse.parse(s)[0]
        self.ndiffAssertEqual(s, unicode(p))
        self.assertEqual(p.tokens[2].get_typecast(), 'integer')
        self.assertEqual(p.tokens[2].get_name(), 'foo')
        s = 'select (current_database())::information_schema.sql_identifier'
        p = sqlparse.parse(s)[0]
        self.ndiffAssertEqual(s, unicode(p))
        self.assertEqual(p.tokens[2].get_typecast(),
                         'information_schema.sql_identifier')

    def test_alias(self):
        s = 'select foo as bar from mytable'
        p = sqlparse.parse(s)[0]
        self.ndiffAssertEqual(s, unicode(p))
        self.assertEqual(p.tokens[2].get_real_name(), 'foo')
        self.assertEqual(p.tokens[2].get_alias(), 'bar')
        s = 'select foo from mytable t1'
        p = sqlparse.parse(s)[0]
        self.ndiffAssertEqual(s, unicode(p))
        self.assertEqual(p.tokens[6].get_real_name(), 'mytable')
        self.assertEqual(p.tokens[6].get_alias(), 't1')
        s = 'select foo::integer as bar from mytable'
        p = sqlparse.parse(s)[0]
        self.ndiffAssertEqual(s, unicode(p))
        self.assertEqual(p.tokens[2].get_alias(), 'bar')
        s = ('SELECT DISTINCT '
             '(current_database())::information_schema.sql_identifier AS view')
        p = sqlparse.parse(s)[0]
        self.ndiffAssertEqual(s, unicode(p))
        self.assertEqual(p.tokens[4].get_alias(), 'view')

    def test_alias_case(self):  # see issue46
        p = sqlparse.parse('CASE WHEN 1 THEN 2 ELSE 3 END foo')[0]
        self.assertEqual(len(p.tokens), 1)
        self.assertEqual(p.tokens[0].get_alias(), 'foo')

    def test_alias_returns_none(self):  # see issue185
        p = sqlparse.parse('foo.bar')[0]
        self.assertEqual(len(p.tokens), 1)
        self.assertEqual(p.tokens[0].get_alias(), None)

    def test_idlist_function(self):  # see issue10 too
        p = sqlparse.parse('foo(1) x, bar')[0]
        self.assert_(isinstance(p.tokens[0], sql.IdentifierList))

    def test_comparison_exclude(self):
        # make sure operators are not handled too lazy
        p = sqlparse.parse('(=)')[0]
        self.assert_(isinstance(p.tokens[0], sql.Parenthesis))
        self.assert_(not isinstance(p.tokens[0].tokens[1], sql.Comparison))
        p = sqlparse.parse('(a=1)')[0]
        self.assert_(isinstance(p.tokens[0].tokens[1], sql.Comparison))
        p = sqlparse.parse('(a>=1)')[0]
        self.assert_(isinstance(p.tokens[0].tokens[1], sql.Comparison))

    def test_function(self):
        p = sqlparse.parse('foo()')[0]
        self.assert_(isinstance(p.tokens[0], sql.Function))
        p = sqlparse.parse('foo(null, bar)')[0]
        self.assert_(isinstance(p.tokens[0], sql.Function))
        self.assertEqual(len(list(p.tokens[0].get_parameters())), 2)

    def test_function_not_in(self):  # issue183
        p = sqlparse.parse('in(1, 2)')[0]
        self.assertEqual(len(p.tokens), 2)
        self.assertEqual(p.tokens[0].ttype, T.Keyword)
        self.assert_(isinstance(p.tokens[1], sql.Parenthesis))

    def test_varchar(self):
        p = sqlparse.parse('"text" Varchar(50) NOT NULL')[0]
        self.assert_(isinstance(p.tokens[2], sql.Function))


class TestStatement(TestCaseBase):

    def test_get_type(self):
        f = lambda sql: sqlparse.parse(sql)[0]
        self.assertEqual(f('select * from foo').get_type(), 'SELECT')
        self.assertEqual(f('update foo').get_type(), 'UPDATE')
        self.assertEqual(f(' update foo').get_type(), 'UPDATE')
        self.assertEqual(f('\nupdate foo').get_type(), 'UPDATE')
        self.assertEqual(f('foo').get_type(), 'UNKNOWN')
        # Statements that have a whitespace after the closing semicolon
        # are parsed as two statements where later only consists of the
        # trailing whitespace.
        self.assertEqual(f('\n').get_type(), 'UNKNOWN')


def test_identifier_with_operators():  # issue 53
    p = sqlparse.parse('foo||bar')[0]
    assert len(p.tokens) == 1
    assert isinstance(p.tokens[0], sql.Identifier)
    # again with whitespaces
    p = sqlparse.parse('foo || bar')[0]
    assert len(p.tokens) == 1
    assert isinstance(p.tokens[0], sql.Identifier)


def test_identifier_with_op_trailing_ws():
    # make sure trailing whitespace isn't grouped with identifier
    p = sqlparse.parse('foo || bar ')[0]
    assert len(p.tokens) == 2
    assert isinstance(p.tokens[0], sql.Identifier)
    assert p.tokens[1].ttype is T.Whitespace


def test_identifier_with_string_literals():
    p = sqlparse.parse('foo + \'bar\'')[0]
    assert len(p.tokens) == 1
    assert isinstance(p.tokens[0], sql.Identifier)


# This test seems to be wrong. It was introduced when fixing #53, but #111
# showed that this shouldn't be an identifier at all. I'm leaving this
# commented in the source for a while.
# def test_identifier_string_concat():
#     p = sqlparse.parse('\'foo\' || bar')[0]
#     assert len(p.tokens) == 1
#     assert isinstance(p.tokens[0], sql.Identifier)


def test_identifier_consumes_ordering():  # issue89
    p = sqlparse.parse('select * from foo order by c1 desc, c2, c3')[0]
    assert isinstance(p.tokens[-1], sql.IdentifierList)
    ids = list(p.tokens[-1].get_identifiers())
    assert len(ids) == 3
    assert ids[0].get_name() == 'c1'
    assert ids[0].get_ordering() == 'DESC'
    assert ids[1].get_name() == 'c2'
    assert ids[1].get_ordering() is None


def test_comparison_with_keywords():  # issue90
    # in fact these are assignments, but for now we don't distinguish them
    p = sqlparse.parse('foo = NULL')[0]
    assert len(p.tokens) == 1
    assert isinstance(p.tokens[0], sql.Comparison)
    assert len(p.tokens[0].tokens) == 5
    assert p.tokens[0].left.value == 'foo'
    assert p.tokens[0].right.value == 'NULL'
    # make sure it's case-insensitive
    p = sqlparse.parse('foo = null')[0]
    assert len(p.tokens) == 1
    assert isinstance(p.tokens[0], sql.Comparison)


def test_comparison_with_floats():  # issue145
    p = sqlparse.parse('foo = 25.5')[0]
    assert len(p.tokens) == 1
    assert isinstance(p.tokens[0], sql.Comparison)
    assert len(p.tokens[0].tokens) == 5
    assert p.tokens[0].left.value == 'foo'
    assert p.tokens[0].right.value == '25.5'


def test_comparison_with_parenthesis():  # issue23
    p = sqlparse.parse('(3 + 4) = 7')[0]
    assert len(p.tokens) == 1
    assert isinstance(p.tokens[0], sql.Comparison)
    comp = p.tokens[0]
    assert isinstance(comp.left, sql.Parenthesis)
    assert comp.right.ttype is T.Number.Integer


def test_comparison_with_strings():  # issue148
    p = sqlparse.parse('foo = \'bar\'')[0]
    assert len(p.tokens) == 1
    assert isinstance(p.tokens[0], sql.Comparison)
    assert p.tokens[0].right.value == '\'bar\''
    assert p.tokens[0].right.ttype == T.String.Single


@pytest.mark.parametrize('start', ['FOR', 'FOREACH'])
def test_forloops(start):
    p = sqlparse.parse('%s foo in bar LOOP foobar END LOOP' % start)[0]
    assert (len(p.tokens)) == 1
    assert isinstance(p.tokens[0], sql.For)


def test_nested_for():
    p = sqlparse.parse('FOR foo LOOP FOR bar LOOP END LOOP END LOOP')[0]
    assert len(p.tokens) == 1
    for1 = p.tokens[0]
    assert for1.tokens[0].value == 'FOR'
    assert for1.tokens[-1].value == 'END LOOP'
    for2 = for1.tokens[6]
    assert isinstance(for2, sql.For)
    assert for2.tokens[0].value == 'FOR'
    assert for2.tokens[-1].value == 'END LOOP'


def test_begin():
    p = sqlparse.parse('BEGIN foo END')[0]
    assert len(p.tokens) == 1
    assert isinstance(p.tokens[0], sql.Begin)


def test_nested_begin():
    p = sqlparse.parse('BEGIN foo BEGIN bar END END')[0]
    assert len(p.tokens) == 1
    outer = p.tokens[0]
    assert outer.tokens[0].value == 'BEGIN'
    assert outer.tokens[-1].value == 'END'
    inner = outer.tokens[4]
    assert inner.tokens[0].value == 'BEGIN'
    assert inner.tokens[-1].value == 'END'
    assert isinstance(inner, sql.Begin)


def test_aliased_column_without_as():
    p = sqlparse.parse('foo bar')[0].tokens
    assert len(p) == 1
    assert p[0].get_real_name() == 'foo'
    assert p[0].get_alias() == 'bar'

    p = sqlparse.parse('foo.bar baz')[0].tokens[0]
    assert p.get_parent_name() == 'foo'
    assert p.get_real_name() == 'bar'
    assert p.get_alias() == 'baz'


def test_qualified_function():
    p = sqlparse.parse('foo()')[0].tokens[0]
    assert p.get_parent_name() is None
    assert p.get_real_name() == 'foo'

    p = sqlparse.parse('foo.bar()')[0].tokens[0]
    assert p.get_parent_name() == 'foo'
    assert p.get_real_name() == 'bar'


def test_aliased_function_without_as():
    p = sqlparse.parse('foo() bar')[0].tokens[0]
    assert p.get_parent_name() is None
    assert p.get_real_name() == 'foo'
    assert p.get_alias() == 'bar'

    p = sqlparse.parse('foo.bar() baz')[0].tokens[0]
    assert p.get_parent_name() == 'foo'
    assert p.get_real_name() == 'bar'
    assert p.get_alias() == 'baz'


def test_aliased_literal_without_as():
    p = sqlparse.parse('1 foo')[0].tokens
    assert len(p) == 1
    assert p[0].get_alias() == 'foo'
