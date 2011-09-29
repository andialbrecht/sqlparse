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

    def test_float(self):
        t = sqlparse.parse('.5')[0].tokens
        self.assertEqual(len(t), 1)
        self.assert_(t[0].ttype is sqlparse.tokens.Number.Float)
        t = sqlparse.parse('.51')[0].tokens
        self.assertEqual(len(t), 1)
        self.assert_(t[0].ttype is sqlparse.tokens.Number.Float)
        t = sqlparse.parse('1.5')[0].tokens
        self.assertEqual(len(t), 1)
        self.assert_(t[0].ttype is sqlparse.tokens.Number.Float)
        t = sqlparse.parse('12.5')[0].tokens
        self.assertEqual(len(t), 1)
        self.assert_(t[0].ttype is sqlparse.tokens.Number.Float)

    def test_placeholder(self):
        def _get_tokens(sql):
            return sqlparse.parse(sql)[0].tokens[-1].tokens
        t = _get_tokens('select * from foo where user = ?')
        self.assert_(t[-1].ttype is sqlparse.tokens.Name.Placeholder)
        self.assertEqual(t[-1].value, '?')
        t = _get_tokens('select * from foo where user = :1')
        self.assert_(t[-1].ttype is sqlparse.tokens.Name.Placeholder)
        self.assertEqual(t[-1].value, ':1')
        t = _get_tokens('select * from foo where user = :name')
        self.assert_(t[-1].ttype is sqlparse.tokens.Name.Placeholder)
        self.assertEqual(t[-1].value, ':name')
        t = _get_tokens('select * from foo where user = %s')
        self.assert_(t[-1].ttype is sqlparse.tokens.Name.Placeholder)
        self.assertEqual(t[-1].value, '%s')
        t = _get_tokens('select * from foo where user = $a')
        self.assert_(t[-1].ttype is sqlparse.tokens.Name.Placeholder)
        self.assertEqual(t[-1].value, '$a')

    def test_access_symbol(self):  # see issue27
        t = sqlparse.parse('select a.[foo bar] as foo')[0].tokens
        self.assert_(isinstance(t[-1], sqlparse.sql.Identifier))
        self.assertEqual(t[-1].get_name(), 'foo')
        self.assertEqual(t[-1].get_real_name(), '[foo bar]')
        self.assertEqual(t[-1].get_parent_name(), 'a')

    def test_keyword_like_identifier(self):  # see issue47
        t = sqlparse.parse('foo.key')[0].tokens
        self.assertEqual(len(t), 1)
        self.assert_(isinstance(t[0], sqlparse.sql.Identifier))
