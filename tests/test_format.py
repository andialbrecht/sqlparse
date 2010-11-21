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
        self.ndiffAssertEqual(res, 'select * from "foo"."bar"')

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
        self.assertRaises(sqlparse.SQLParseError, sqlparse.format, sql,
                          strip_comments=None)

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
        self.assertRaises(sqlparse.SQLParseError, sqlparse.format, s,
                          strip_whitespace=None)

    def test_outputformat(self):
        sql = 'select * from foo;'
        self.assertRaises(sqlparse.SQLParseError, sqlparse.format, sql,
                          output_format='foo')


class TestFormatReindent(TestCaseBase):

    def test_option(self):
        self.assertRaises(sqlparse.SQLParseError, sqlparse.format, 'foo',
                          reindent=2)
        self.assertRaises(sqlparse.SQLParseError, sqlparse.format, 'foo',
                          indent_tabs=2)
        self.assertRaises(sqlparse.SQLParseError, sqlparse.format, 'foo',
                          reindent=True, indent_width='foo')
        self.assertRaises(sqlparse.SQLParseError, sqlparse.format, 'foo',
                          reindent=True, indent_width=-12)

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

    def test_keywords_between(self):  # issue 14
        # don't break AND after BETWEEN
        f = lambda sql: sqlparse.format(sql, reindent=True)
        s = 'and foo between 1 and 2 and bar = 3'
        self.ndiffAssertEqual(f(s), '\n'.join(['',
                                               'and foo between 1 and 2',
                                               'and bar = 3']))

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
        s = 'select a.*, b.id from a, b'
        self.ndiffAssertEqual(f(s), '\n'.join(['select a.*,',
                                               '       b.id',
                                               'from a,',
                                               '     b']))

    def test_identifier_list_with_functions(self):
        f = lambda sql: sqlparse.format(sql, reindent=True)
        s = ("select 'abc' as foo, coalesce(col1, col2)||col3 as bar,"
             "col3 from my_table")
        self.ndiffAssertEqual(f(s), '\n'.join(
            ["select 'abc' as foo,",
             "       coalesce(col1, col2)||col3 as bar,",
             "       col3",
             "from my_table"]))

    def test_case(self):
        f = lambda sql: sqlparse.format(sql, reindent=True)
        s = 'case when foo = 1 then 2 when foo = 3 then 4 else 5 end'
        self.ndiffAssertEqual(f(s), '\n'.join(['case',
                                               '    when foo = 1 then 2',
                                               '    when foo = 3 then 4',
                                               '    else 5',
                                               'end']))

    def test_nested_identifier_list(self):  # issue4
        f = lambda sql: sqlparse.format(sql, reindent=True)
        s = '(foo as bar, bar1, bar2 as bar3, b4 as b5)'
        self.ndiffAssertEqual(f(s), '\n'.join(['(foo as bar,',
                                               ' bar1,',
                                               ' bar2 as bar3,',
                                               ' b4 as b5)']))

    def test_duplicate_linebreaks(self):  # issue3
        f = lambda sql: sqlparse.format(sql, reindent=True)
        s = 'select c1 -- column1\nfrom foo'
        self.ndiffAssertEqual(f(s), '\n'.join(['select c1 -- column1',
                                               'from foo']))
        s = 'select c1 -- column1\nfrom foo'
        r = sqlparse.format(s, reindent=True, strip_comments=True)
        self.ndiffAssertEqual(r, '\n'.join(['select c1',
                                            'from foo']))
        s = 'select c1\nfrom foo\norder by c1'
        self.ndiffAssertEqual(f(s), '\n'.join(['select c1',
                                               'from foo',
                                               'order by c1']))
        s = 'select c1 from t1 where (c1 = 1) order by c1'
        self.ndiffAssertEqual(f(s), '\n'.join(['select c1',
                                               'from t1',
                                               'where (c1 = 1)',
                                               'order by c1']))




class TestOutputFormat(TestCaseBase):

    def test_python(self):
        sql = 'select * from foo;'
        f = lambda sql: sqlparse.format(sql, output_format='python')
        self.ndiffAssertEqual(f(sql), "sql = 'select * from foo;'")
        f = lambda sql: sqlparse.format(sql, output_format='python',
                                        reindent=True)
        self.ndiffAssertEqual(f(sql), ("sql = ('select * '\n"
                                       "       'from foo;')"))

    def test_php(self):
        sql = 'select * from foo;'
        f = lambda sql: sqlparse.format(sql, output_format='php')
        self.ndiffAssertEqual(f(sql), '$sql = "select * from foo;";')
        f = lambda sql: sqlparse.format(sql, output_format='php',
                                        reindent=True)
        self.ndiffAssertEqual(f(sql), ('$sql = "select * ";\n'
                                       '$sql .= "from foo;";'))

    def test_sql(self):  # "sql" is an allowed option but has no effect
        sql = 'select * from foo;'
        f = lambda sql: sqlparse.format(sql, output_format='sql')
        self.ndiffAssertEqual(f(sql), 'select * from foo;')
