# -*- coding: utf-8 -*-

from tests.utils import TestCaseBase

import sqlparse
from sqlparse import sql
from sqlparse import tokens as T


class RegressionTests(TestCaseBase):

    def test_issue9(self):
        # make sure where doesn't consume parenthesis
        p = sqlparse.parse('(where 1)')[0]
        self.assert_(isinstance(p, sql.Statement))
        self.assertEqual(len(p.tokens), 1)
        self.assert_(isinstance(p.tokens[0], sql.Parenthesis))
        prt = p.tokens[0]
        self.assertEqual(len(prt.tokens), 3)
        self.assertEqual(prt.tokens[0].ttype, T.Punctuation)
        self.assertEqual(prt.tokens[-1].ttype, T.Punctuation)

    def test_issue13(self):
        parsed = sqlparse.parse(("select 'one';\n"
                                 "select 'two\\'';\n"
                                 "select 'three';"))
        self.assertEqual(len(parsed), 3)
        self.assertEqual(str(parsed[1]).strip(), "select 'two\\'';")

    def test_issue26(self):
        # parse stand-alone comments
        p = sqlparse.parse('--hello')[0]
        self.assertEqual(len(p.tokens), 1)
        self.assert_(p.tokens[0].ttype is T.Comment.Single)
        p = sqlparse.parse('-- hello')[0]
        self.assertEqual(len(p.tokens), 1)
        self.assert_(p.tokens[0].ttype is T.Comment.Single)
        p = sqlparse.parse('--hello\n')[0]
        self.assertEqual(len(p.tokens), 1)
        self.assert_(p.tokens[0].ttype is T.Comment.Single)
        p = sqlparse.parse('--')[0]
        self.assertEqual(len(p.tokens), 1)
        self.assert_(p.tokens[0].ttype is T.Comment.Single)
        p = sqlparse.parse('--\n')[0]
        self.assertEqual(len(p.tokens), 1)
        self.assert_(p.tokens[0].ttype is T.Comment.Single)

    def test_issue34(self):
        t = sqlparse.parse("create")[0].token_first()
        self.assertEqual(t.match(T.Keyword.DDL, "create"), True)
        self.assertEqual(t.match(T.Keyword.DDL, "CREATE"), True)

    def test_issue35(self):
        # missing space before LIMIT
        sql = sqlparse.format("select * from foo where bar = 1 limit 1",
                              reindent=True)
        self.ndiffAssertEqual(sql, "\n".join(["select *",
                                              "from foo",
                                              "where bar = 1 limit 1"]))

    def test_issue38(self):
        sql = sqlparse.format("SELECT foo; -- comment",
                              strip_comments=True)
        self.ndiffAssertEqual(sql, "SELECT foo;")
        sql = sqlparse.format("/* foo */", strip_comments=True)
        self.ndiffAssertEqual(sql, "")

    def test_issue39(self):
        p = sqlparse.parse('select user.id from user')[0]
        self.assertEqual(len(p.tokens), 7)
        idt = p.tokens[2]
        self.assertEqual(idt.__class__, sql.Identifier)
        self.assertEqual(len(idt.tokens), 3)
        self.assertEqual(idt.tokens[0].match(T.Name, 'user'), True)
        self.assertEqual(idt.tokens[1].match(T.Punctuation, '.'), True)
        self.assertEqual(idt.tokens[2].match(T.Name, 'id'), True)

    def test_issue40(self):
        # make sure identifier lists in subselects are grouped
        p = sqlparse.parse(('SELECT id, name FROM '
                            '(SELECT id, name FROM bar) as foo'))[0]
        self.assertEqual(len(p.tokens), 7)
        self.assertEqual(p.tokens[2].__class__, sql.IdentifierList)
        self.assertEqual(p.tokens[-1].__class__, sql.Identifier)
        self.assertEqual(p.tokens[-1].get_name(), u'foo')
        sp = p.tokens[-1].tokens[0]
        self.assertEqual(sp.tokens[3].__class__, sql.IdentifierList)
        # make sure that formatting works as expected
        self.ndiffAssertEqual(
            sqlparse.format(('SELECT id, name FROM '
                             '(SELECT id, name FROM bar)'),
                            reindent=True),
            ('SELECT id,\n'
             '       name\n'
             'FROM\n'
             '  (SELECT id,\n'
             '          name\n'
             '   FROM bar)'))
        self.ndiffAssertEqual(
            sqlparse.format(('SELECT id, name FROM '
                             '(SELECT id, name FROM bar) as foo'),
                            reindent=True),
            ('SELECT id,\n'
             '       name\n'
             'FROM\n'
             '  (SELECT id,\n'
             '          name\n'
             '   FROM bar) as foo'))
