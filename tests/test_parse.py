# -*- coding: utf-8 -*-

"""Tests sqlparse function."""

from tests.utils import TestCaseBase

import sqlparse


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
