# -*- coding: utf-8 -*-

"""Tests sqlparse function."""

from tests.utils import TestCaseBase

import sqlparse
import sqlparse.sql


class SQLParseTest(TestCaseBase):
    """Tests sqlparse.parse()."""

    def test_tokenize(self):
        sql = 'select * from foo;'
        stmts = sqlparse.parse(sql)
        self.assertEqual(len(stmts), 1)
        self.assertEqual(str(stmts[0]), sql)

    def test_multistatement(self):
        sql1 = 'select * from foo;'
        sql2 = 'select * from bar;'
        stmts = sqlparse.parse(sql1+sql2)
        self.assertEqual(len(stmts), 2)
        self.assertEqual(str(stmts[0]), sql1)
        self.assertEqual(str(stmts[1]), sql2)

    def test_newlines(self):
        sql = u'select\n*from foo;'
        p = sqlparse.parse(sql)[0]
        self.assertEqual(unicode(p), sql)
        sql = u'select\r\n*from foo'
        p = sqlparse.parse(sql)[0]
        self.assertEqual(unicode(p), sql)
        sql = u'select\r*from foo'
        p = sqlparse.parse(sql)[0]
        self.assertEqual(unicode(p), sql)
        sql = u'select\r\n*from foo\n'
        p = sqlparse.parse(sql)[0]
        self.assertEqual(unicode(p), sql)

    def test_within(self):
        sql = 'foo(col1, col2)'
        p = sqlparse.parse(sql)[0]
        col1 = p.tokens[0].tokens[1].tokens[1].tokens[0]
        self.assert_(col1.within(sqlparse.sql.Function))

    def test_child_of(self):
        sql = '(col1, col2)'
        p = sqlparse.parse(sql)[0]
        self.assert_(p.tokens[0].tokens[1].is_child_of(p.tokens[0]))
        sql = 'select foo'
        p = sqlparse.parse(sql)[0]
        self.assert_(not p.tokens[2].is_child_of(p.tokens[0]))
        self.assert_(p.tokens[2].is_child_of(p))

    def test_has_ancestor(self):
        sql = 'foo or (bar, baz)'
        p = sqlparse.parse(sql)[0]
        baz = p.tokens[-1].tokens[1].tokens[-1]
        self.assert_(baz.has_ancestor(p.tokens[-1].tokens[1]))
        self.assert_(baz.has_ancestor(p.tokens[-1]))
        self.assert_(baz.has_ancestor(p))
