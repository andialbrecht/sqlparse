# -*- coding: utf-8 -*-

# Tests splitting functions.

import unittest

from tests.utils import load_file, TestCaseBase

import sqlparse


class SQLSplitTest(TestCaseBase):
    """Tests sqlparse.sqlsplit()."""

    _sql1 = 'select * from foo;'
    _sql2 = 'select * from bar;'

    def test_split_semicolon(self):
        sql2 = 'select * from foo where bar = \'foo;bar\';'
        stmts = sqlparse.parse(''.join([self._sql1, sql2]))
        self.assertEqual(len(stmts), 2)
        self.ndiffAssertEqual(unicode(stmts[0]), self._sql1)
        self.ndiffAssertEqual(unicode(stmts[1]), sql2)

    def test_split_backslash(self):
        stmts = sqlparse.parse(r"select '\\'; select '\''; select '\\\'';")
        self.assertEqual(len(stmts), 3)

    def test_create_function(self):
        sql = load_file('function.sql')
        stmts = sqlparse.parse(sql)
        self.assertEqual(len(stmts), 1)
        self.ndiffAssertEqual(unicode(stmts[0]), sql)

    def test_create_function_psql(self):
        sql = load_file('function_psql.sql')
        stmts = sqlparse.parse(sql)
        self.assertEqual(len(stmts), 1)
        self.ndiffAssertEqual(unicode(stmts[0]), sql)

    def test_create_function_psql3(self):
        sql = load_file('function_psql3.sql')
        stmts = sqlparse.parse(sql)
        self.assertEqual(len(stmts), 1)
        self.ndiffAssertEqual(unicode(stmts[0]), sql)

    def test_create_function_psql2(self):
        sql = load_file('function_psql2.sql')
        stmts = sqlparse.parse(sql)
        self.assertEqual(len(stmts), 1)
        self.ndiffAssertEqual(unicode(stmts[0]), sql)

    def test_dashcomments(self):
        sql = load_file('dashcomment.sql')
        stmts = sqlparse.parse(sql)
        self.assertEqual(len(stmts), 3)
        self.ndiffAssertEqual(''.join(unicode(q) for q in stmts), sql)

    def test_dashcomments_eol(self):
        stmts = sqlparse.parse('select foo; -- comment\n')
        self.assertEqual(len(stmts), 1)
        stmts = sqlparse.parse('select foo; -- comment\r')
        self.assertEqual(len(stmts), 1)
        stmts = sqlparse.parse('select foo; -- comment\r\n')
        self.assertEqual(len(stmts), 1)
        stmts = sqlparse.parse('select foo; -- comment')
        self.assertEqual(len(stmts), 1)

    def test_begintag(self):
        sql = load_file('begintag.sql')
        stmts = sqlparse.parse(sql)
        self.assertEqual(len(stmts), 3)
        self.ndiffAssertEqual(''.join(unicode(q) for q in stmts), sql)

    def test_begintag_2(self):
        sql = load_file('begintag_2.sql')
        stmts = sqlparse.parse(sql)
        self.assertEqual(len(stmts), 1)
        self.ndiffAssertEqual(''.join(unicode(q) for q in stmts), sql)

    def test_dropif(self):
        sql = 'DROP TABLE IF EXISTS FOO;\n\nSELECT * FROM BAR;'
        stmts = sqlparse.parse(sql)
        self.assertEqual(len(stmts), 2)
        self.ndiffAssertEqual(''.join(unicode(q) for q in stmts), sql)

    def test_comment_with_umlaut(self):
        sql = (u'select * from foo;\n'
               u'-- Testing an umlaut: ä\n'
               u'select * from bar;')
        stmts = sqlparse.parse(sql)
        self.assertEqual(len(stmts), 2)
        self.ndiffAssertEqual(''.join(unicode(q) for q in stmts), sql)

    def test_comment_end_of_line(self):
        sql = ('select * from foo; -- foo\n'
               'select * from bar;')
        stmts = sqlparse.parse(sql)
        self.assertEqual(len(stmts), 2)
        self.ndiffAssertEqual(''.join(unicode(q) for q in stmts), sql)
        # make sure the comment belongs to first query
        self.ndiffAssertEqual(unicode(stmts[0]), 'select * from foo; -- foo\n')

    def test_casewhen(self):
        sql = ('SELECT case when val = 1 then 2 else null end as foo;\n'
               'comment on table actor is \'The actor table.\';')
        stmts = sqlparse.split(sql)
        self.assertEqual(len(stmts), 2)

    def test_cursor_declare(self):
        sql = ('DECLARE CURSOR "foo" AS SELECT 1;\n'
               'SELECT 2;')
        stmts = sqlparse.split(sql)
        self.assertEqual(len(stmts), 2)

    def test_if_function(self):  # see issue 33
        # don't let IF as a function confuse the splitter
        sql = ('CREATE TEMPORARY TABLE tmp '
               'SELECT IF(a=1, a, b) AS o FROM one; '
               'SELECT t FROM two')
        stmts = sqlparse.split(sql)
        self.assertEqual(len(stmts), 2)

    def test_split_stream(self):
        import types
        from cStringIO import StringIO

        stream = StringIO("SELECT 1; SELECT 2;")
        stmts = sqlparse.parsestream(stream)
        self.assertEqual(type(stmts), types.GeneratorType)
        self.assertEqual(len(list(stmts)), 2)

    def test_encoding_parsestream(self):
        from cStringIO import StringIO
        stream = StringIO("SELECT 1; SELECT 2;")
        stmts = list(sqlparse.parsestream(stream))
        self.assertEqual(type(stmts[0].tokens[0].value), unicode)


def test_split_simple():
    stmts = sqlparse.split('select * from foo; select * from bar;')
    assert len(stmts) == 2
    assert stmts[0] == 'select * from foo;'
    assert stmts[1] == 'select * from bar;'
