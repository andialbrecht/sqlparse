# -*- coding: utf-8 -*-

import sqlparse
from sqlparse import sql
from sqlparse import tokens as T

from tests.utils import TestCaseBase


class TestGrouping(TestCaseBase):

    def test_parenthesis(self):
        s ='select (select (x3) x2) and (y2) bar'
        parsed = sqlparse.parse(s)[0]
        self.ndiffAssertEqual(s, str(parsed))
        self.assertEqual(len(parsed.tokens), 9)
        self.assert_(isinstance(parsed.tokens[2], sql.Parenthesis))
        self.assert_(isinstance(parsed.tokens[-3], sql.Parenthesis))
        self.assertEqual(len(parsed.tokens[2].tokens), 7)
        self.assert_(isinstance(parsed.tokens[2].tokens[3], sql.Parenthesis))
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
        self.ndiffAssertEqual(s, parsed.to_unicode())
        self.assert_(isinstance(parsed.tokens[2], sql.Identifier))
        self.assert_(isinstance(parsed.tokens[6], sql.Identifier))
        self.assert_(isinstance(parsed.tokens[8], sql.Where))
        s = 'select * from foo where foo.id = 1'
        parsed = sqlparse.parse(s)[0]
        self.ndiffAssertEqual(s, parsed.to_unicode())
        self.assert_(isinstance(parsed.tokens[-1].tokens[-1].tokens[0],
                                sql.Identifier))
        s = 'select * from (select "foo"."id" from foo)'
        parsed = sqlparse.parse(s)[0]
        self.ndiffAssertEqual(s, parsed.to_unicode())
        self.assert_(isinstance(parsed.tokens[-1].tokens[3], sql.Identifier))

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

    def test_where(self):
        s = 'select * from foo where bar = 1 order by id desc'
        p = sqlparse.parse(s)[0]
        self.ndiffAssertEqual(s, p.to_unicode())
        self.assertTrue(len(p.tokens), 16)
        s = 'select x from (select y from foo where bar = 1) z'
        p = sqlparse.parse(s)[0]
        self.ndiffAssertEqual(s, p.to_unicode())
        self.assertTrue(isinstance(p.tokens[-3].tokens[-2], sql.Where))

    def test_typecast(self):
        s = 'select foo::integer from bar'
        p = sqlparse.parse(s)[0]
        self.ndiffAssertEqual(s, p.to_unicode())
        self.assertEqual(p.tokens[2].get_typecast(), 'integer')
        self.assertEqual(p.tokens[2].get_name(), 'foo')
        s = 'select (current_database())::information_schema.sql_identifier'
        p = sqlparse.parse(s)[0]
        self.ndiffAssertEqual(s, p.to_unicode())
        self.assertEqual(p.tokens[2].get_typecast(),
                         'information_schema.sql_identifier')

    def test_alias(self):
        s = 'select foo as bar from mytable'
        p = sqlparse.parse(s)[0]
        self.ndiffAssertEqual(s, p.to_unicode())
        self.assertEqual(p.tokens[2].get_real_name(), 'foo')
        self.assertEqual(p.tokens[2].get_alias(), 'bar')
        s = 'select foo from mytable t1'
        p = sqlparse.parse(s)[0]
        self.ndiffAssertEqual(s, p.to_unicode())
        self.assertEqual(p.tokens[6].get_real_name(), 'mytable')
        self.assertEqual(p.tokens[6].get_alias(), 't1')
        s = 'select foo::integer as bar from mytable'
        p = sqlparse.parse(s)[0]
        self.ndiffAssertEqual(s, p.to_unicode())
        self.assertEqual(p.tokens[2].get_alias(), 'bar')
        s = ('SELECT DISTINCT '
             '(current_database())::information_schema.sql_identifier AS view')
        p = sqlparse.parse(s)[0]
        self.ndiffAssertEqual(s, p.to_unicode())
        self.assertEqual(p.tokens[4].get_alias(), 'view')

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
        self.assertEqual(len(p.tokens[0].get_parameters()), 2)


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
