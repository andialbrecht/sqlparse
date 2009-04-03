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
        self.assert_(isinstance(parsed.tokens[-1].tokens[2], Identifier))
        s = 'select * from (select "foo"."id" from foo)'
        parsed = sqlparse.parse(s)[0]
        self.ndiffAssertEqual(s, parsed.to_unicode())
        self.assert_(isinstance(parsed.tokens[-1].tokens[3], Identifier))

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
