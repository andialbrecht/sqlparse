# -*- coding: utf-8 -*-

from tests.utils import TestCaseBase

import sqlparse


class TestFormat(TestCaseBase):

    def test_keywordcase(self):
        sql = 'select * from bar; -- select foo\n'
        res = sqlparse.format(sql, keyword_case='upper')
        self.ndiffAssertEqual(res, 'SELECT * FROM bar; -- select foo\n')
        res = sqlparse.format(sql, keyword_case='capitalize')
        self.ndiffAssertEqual(res, 'Select * From bar; -- select foo\n')
        res = sqlparse.format(sql.upper(), keyword_case='lower')
        self.ndiffAssertEqual(res, 'select * from BAR; -- SELECT FOO\n')
        self.assertRaises(sqlparse.SQLParseError, sqlparse.format, sql,
                          keyword_case='foo')

    def test_identifiercase(self):
        sql = 'select * from bar; -- select foo\n'
        res = sqlparse.format(sql, identifier_case='upper')
        self.ndiffAssertEqual(res, 'select * from BAR; -- select foo\n')
        res = sqlparse.format(sql, identifier_case='capitalize')
        self.ndiffAssertEqual(res, 'select * from Bar; -- select foo\n')
        res = sqlparse.format(sql.upper(), identifier_case='lower')
        self.ndiffAssertEqual(res, 'SELECT * FROM bar; -- SELECT FOO\n')
        self.assertRaises(sqlparse.SQLParseError, sqlparse.format, sql,
                          identifier_case='foo')
        sql = 'select * from "foo"."bar"'
        res = sqlparse.format(sql, identifier_case="upper")
        self.ndiffAssertEqual(res, 'select * from "FOO"."BAR"')

    def test_strip_comments_single(self):
        sql = 'select *-- statement starts here\nfrom foo'
        res = sqlparse.format(sql, strip_comments=True)
        self.ndiffAssertEqual(res, 'select * from foo')
        sql = 'select * -- statement starts here\nfrom foo'
        res = sqlparse.format(sql, strip_comments=True)
        self.ndiffAssertEqual(res, 'select * from foo')
        sql = 'select-- foo\nfrom -- bar\nwhere'
        res = sqlparse.format(sql, strip_comments=True)
        self.ndiffAssertEqual(res, 'select from where')

    def test_strip_comments_multi(self):
        sql = '/* sql starts here */\nselect'
        res = sqlparse.format(sql, strip_comments=True)
        self.ndiffAssertEqual(res, 'select')
        sql = '/* sql starts here */ select'
        res = sqlparse.format(sql, strip_comments=True)
        self.ndiffAssertEqual(res, 'select')
        sql = '/*\n * sql starts here\n */\nselect'
        res = sqlparse.format(sql, strip_comments=True)
        self.ndiffAssertEqual(res, 'select')
        sql = 'select (/* sql starts here */ select 2)'
        res = sqlparse.format(sql, strip_comments=True)
        self.ndiffAssertEqual(res, 'select (select 2)')

    def test_strip_ws(self):
        f = lambda sql: sqlparse.format(sql, strip_whitespace=True)
        s = 'select\n* from      foo\n\twhere  ( 1 = 2 )\n'
        self.ndiffAssertEqual(f(s), 'select * from foo where (1 = 2)')
        s = 'select -- foo\nfrom    bar\n'
        self.ndiffAssertEqual(f(s), 'select -- foo\nfrom bar')


class TestFormatReindent(TestCaseBase):

    def test_stmts(self):
        f = lambda sql: sqlparse.format(sql, reindent=True)
        s = 'select foo; select bar'
        self.ndiffAssertEqual(f(s), 'select foo;\n\nselect bar')
        s = 'select foo'
        self.ndiffAssertEqual(f(s), 'select foo')
        s = 'select foo; -- test\n select bar'
        self.ndiffAssertEqual(f(s), 'select foo; -- test\n\nselect bar')

    def test_keywords(self):
        f = lambda sql: sqlparse.format(sql, reindent=True)
        s = 'select * from foo union select * from bar;'
        self.ndiffAssertEqual(f(s), '\n'.join(['select *',
                                               'from foo',
                                               'union',
                                               'select *',
                                               'from bar;']))

    def test_parenthesis(self):
        f = lambda sql: sqlparse.format(sql, reindent=True)
        s = 'select count(*) from (select * from foo);'
        self.ndiffAssertEqual(f(s),
                              '\n'.join(['select count(*)',
                                         'from',
                                         '  (select *',
                                         '   from foo);',
                                         ])
                              )

    def test_where(self):
        f = lambda sql: sqlparse.format(sql, reindent=True)
        s = 'select * from foo where bar = 1 and baz = 2 or bzz = 3;'
        self.ndiffAssertEqual(f(s), ('select *\nfrom foo\n'
                                     'where bar = 1\n'
                                     '  and baz = 2\n'
                                     '  or bzz = 3;'))
        s = 'select * from foo where bar = 1 and (baz = 2 or bzz = 3);'
        self.ndiffAssertEqual(f(s), ('select *\nfrom foo\n'
                                     'where bar = 1\n'
                                     '  and (baz = 2\n'
                                     '       or bzz = 3);'))

    def test_join(self):
        f = lambda sql: sqlparse.format(sql, reindent=True)
        s = 'select * from foo join bar on 1 = 2'
        self.ndiffAssertEqual(f(s), '\n'.join(['select *',
                                               'from foo',
                                               'join bar on 1 = 2']))
        s = 'select * from foo inner join bar on 1 = 2'
        self.ndiffAssertEqual(f(s), '\n'.join(['select *',
                                               'from foo',
                                               'inner join bar on 1 = 2']))
        s = 'select * from foo left outer join bar on 1 = 2'
        self.ndiffAssertEqual(f(s), '\n'.join(['select *',
                                               'from foo',
                                               'left outer join bar on 1 = 2']
                                              ))

    def test_identifier_list(self):
        f = lambda sql: sqlparse.format(sql, reindent=True)
        s = 'select foo, bar, baz from table1, table2 where 1 = 2'
        self.ndiffAssertEqual(f(s), '\n'.join(['select foo,',
                                               '       bar,',
                                               '       baz',
                                               'from table1,',
                                               '     table2',
                                               'where 1 = 2']))

    def test_case(self):
        f = lambda sql: sqlparse.format(sql, reindent=True)
        s = 'case when foo = 1 then 2 when foo = 3 then 4 else 5 end'
        self.ndiffAssertEqual(f(s), '\n'.join(['case when foo = 1 then 2',
                                               '     when foo = 3 then 4',
                                               '     else 5',
                                               'end']))


