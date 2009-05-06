# -*- coding: utf-8 -*-

import sqlparse
from sqlparse import tokens as T
from sqlparse.engine.grouping import *

from tests.utils import TestCaseBase


class TestGrouping(TestCaseBase):

    def test_parenthesis(self):
        s ='x1 (x2 (x3) x2) foo (y2) bar'
        parsed = sqlparse.parse(s)[0]
        self.ndiffAssertEqual(s, str(parsed))
        self.assertEqual(len(parsed.tokens), 9)
        self.assert_(isinstance(parsed.tokens[2], Parenthesis))
        self.assert_(isinstance(parsed.tokens[-3], Parenthesis))
        self.assertEqual(len(parsed.tokens[2].tokens), 7)
        self.assert_(isinstance(parsed.tokens[2].tokens[3], Parenthesis))
        self.assertEqual(len(parsed.tokens[2].tokens[3].tokens), 3)

    def test_comments(self):
        s = '/*\n * foo\n */   \n  bar'
        parsed = sqlparse.parse(s)[0]
        self.ndiffAssertEqual(s, unicode(parsed))
        self.assertEqual(len(parsed.tokens), 2)

    def test_identifiers(self):
        s = 'select foo.bar from "myscheme"."table" where fail. order'
        parsed = sqlparse.parse(s)[0]
        self.ndiffAssertEqual(s, parsed.to_unicode())
        self.assert_(isinstance(parsed.tokens[2], Identifier))
        self.assert_(isinstance(parsed.tokens[6], Identifier))
        self.assert_(isinstance(parsed.tokens[8], Where))
        s = 'select * from foo where foo.id = 1'
        parsed = sqlparse.parse(s)[0]
        self.ndiffAssertEqual(s, parsed.to_unicode())
        self.assert_(isinstance(parsed.tokens[-1].tokens[-1].tokens[0],
                                Identifier))
        s = 'select * from (select "foo"."id" from foo)'
        parsed = sqlparse.parse(s)[0]
        self.ndiffAssertEqual(s, parsed.to_unicode())
        self.assert_(isinstance(parsed.tokens[-1].tokens[3], Identifier))

    def test_identifier_wildcard(self):
        p = sqlparse.parse('a.*, b.id')[0]
        self.assert_(isinstance(p.tokens[0], IdentifierList))
        self.assert_(isinstance(p.tokens[0].tokens[0], Identifier))
        self.assert_(isinstance(p.tokens[0].tokens[-1], Identifier))

    def test_identifier_name_wildcard(self):
        p = sqlparse.parse('a.*')[0]
        t = p.tokens[0]
        self.assertEqual(t.get_name(), '*')
        self.assertEqual(t.is_wildcard(), True)

    def test_indentifier_invalid(self):
        p = sqlparse.parse('a.')[0]
        self.assert_(isinstance(p.tokens[0], Identifier))
        self.assertEqual(p.tokens[0].has_alias(), False)
        self.assertEqual(p.tokens[0].get_name(), None)
        self.assertEqual(p.tokens[0].get_real_name(), None)
        self.assertEqual(p.tokens[0].get_parent_name(), 'a')

    def test_identifier_list(self):
        p = sqlparse.parse('a, b, c')[0]
        self.assert_(isinstance(p.tokens[0], IdentifierList))
        p = sqlparse.parse('(a, b, c)')[0]
        self.assert_(isinstance(p.tokens[0].tokens[1], IdentifierList))

    def test_identifier_list_case(self):
        p = sqlparse.parse('a, case when 1 then 2 else 3 end as b, c')[0]
        self.assert_(isinstance(p.tokens[0], IdentifierList))
        p = sqlparse.parse('(a, case when 1 then 2 else 3 end as b, c)')[0]
        self.assert_(isinstance(p.tokens[0].tokens[1], IdentifierList))

    def test_identifier_list_other(self):  # issue2
        p = sqlparse.parse("select *, null, 1, 'foo', bar from mytable, x")[0]
        self.assert_(isinstance(p.tokens[2], IdentifierList))
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
        self.assertTrue(isinstance(p.tokens[-3].tokens[-1], Where))

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



class TestStatement(TestCaseBase):

    def test_get_type(self):
        f = lambda sql: sqlparse.parse(sql)[0]
        self.assertEqual(f('select * from foo').get_type(), 'SELECT')
        self.assertEqual(f('update foo').get_type(), 'UPDATE')
        self.assertEqual(f(' update foo').get_type(), 'UPDATE')
        self.assertEqual(f('\nupdate foo').get_type(), 'UPDATE')
        self.assertEqual(f('foo').get_type(), 'UNKNOWN')
