# -*- coding: utf-8 -*-

"""Tests sqlparse function."""

import pytest

from tests.utils import TestCaseBase

import sqlparse
import sqlparse.sql

from sqlparse import tokens as T


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
        stmts = sqlparse.parse(sql1 + sql2)
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

    def test_modulo_not_placeholder(self):
        tokens = list(sqlparse.lexer.tokenize('x %3'))
        self.assertEqual(tokens[2][0], sqlparse.tokens.Operator)

    def test_access_symbol(self):  # see issue27
        t = sqlparse.parse('select a.[foo bar] as foo')[0].tokens
        self.assert_(isinstance(t[-1], sqlparse.sql.Identifier))
        self.assertEqual(t[-1].get_name(), 'foo')
        self.assertEqual(t[-1].get_real_name(), '[foo bar]')
        self.assertEqual(t[-1].get_parent_name(), 'a')

    def test_square_brackets_notation_isnt_too_greedy(self):  # see issue153
        t = sqlparse.parse('[foo], [bar]')[0].tokens
        self.assert_(isinstance(t[0], sqlparse.sql.IdentifierList))
        self.assertEqual(len(t[0].tokens), 4)
        self.assertEqual(t[0].tokens[0].get_real_name(), '[foo]')
        self.assertEqual(t[0].tokens[-1].get_real_name(), '[bar]')

    def test_keyword_like_identifier(self):  # see issue47
        t = sqlparse.parse('foo.key')[0].tokens
        self.assertEqual(len(t), 1)
        self.assert_(isinstance(t[0], sqlparse.sql.Identifier))

    def test_function_parameter(self):  # see issue94
        t = sqlparse.parse('abs(some_col)')[0].tokens[0].get_parameters()
        self.assertEqual(len(t), 1)
        self.assert_(isinstance(t[0], sqlparse.sql.Identifier))

    def test_function_param_single_literal(self):
        t = sqlparse.parse('foo(5)')[0].tokens[0].get_parameters()
        self.assertEqual(len(t), 1)
        self.assert_(t[0].ttype is T.Number.Integer)

    def test_nested_function(self):
        t = sqlparse.parse('foo(bar(5))')[0].tokens[0].get_parameters()
        self.assertEqual(len(t), 1)
        self.assert_(type(t[0]) is sqlparse.sql.Function)


def test_quoted_identifier():
    t = sqlparse.parse('select x.y as "z" from foo')[0].tokens
    assert isinstance(t[2], sqlparse.sql.Identifier)
    assert t[2].get_name() == 'z'
    assert t[2].get_real_name() == 'y'


@pytest.mark.parametrize('name', [
    'foo',
    '_foo',
])
def test_valid_identifier_names(name):  # issue175
    t = sqlparse.parse(name)[0].tokens
    assert isinstance(t[0], sqlparse.sql.Identifier)


def test_psql_quotation_marks():  # issue83
    # regression: make sure plain $$ work
    t = sqlparse.split("""
    CREATE OR REPLACE FUNCTION testfunc1(integer) RETURNS integer AS $$
          ....
    $$ LANGUAGE plpgsql;
    CREATE OR REPLACE FUNCTION testfunc2(integer) RETURNS integer AS $$
          ....
    $$ LANGUAGE plpgsql;""")
    assert len(t) == 2
    # make sure $SOMETHING$ works too
    t = sqlparse.split("""
    CREATE OR REPLACE FUNCTION testfunc1(integer) RETURNS integer AS $PROC_1$
          ....
    $PROC_1$ LANGUAGE plpgsql;
    CREATE OR REPLACE FUNCTION testfunc2(integer) RETURNS integer AS $PROC_2$
          ....
    $PROC_2$ LANGUAGE plpgsql;""")
    assert len(t) == 2


def test_double_precision_is_builtin():
    sql = 'DOUBLE PRECISION'
    t = sqlparse.parse(sql)[0].tokens
    assert (len(t) == 1
            and t[0].ttype == sqlparse.tokens.Name.Builtin
            and t[0].value == 'DOUBLE PRECISION')


@pytest.mark.parametrize('ph', ['?', ':1', ':foo', '%s', '%(foo)s'])
def test_placeholder(ph):
    p = sqlparse.parse(ph)[0].tokens
    assert len(p) == 1
    assert p[0].ttype is T.Name.Placeholder


@pytest.mark.parametrize('num', ['6.67428E-8', '1.988e33', '1e-12'])
def test_scientific_numbers(num):
    p = sqlparse.parse(num)[0].tokens
    assert len(p) == 1
    assert p[0].ttype is T.Number.Float


def test_single_quotes_are_strings():
    p = sqlparse.parse("'foo'")[0].tokens
    assert len(p) == 1
    assert p[0].ttype is T.String.Single


def test_double_quotes_are_identifiers():
    p = sqlparse.parse('"foo"')[0].tokens
    assert len(p) == 1
    assert isinstance(p[0], sqlparse.sql.Identifier)


def test_single_quotes_with_linebreaks():  # issue118
    p = sqlparse.parse("'f\nf'")[0].tokens
    assert len(p) == 1
    assert p[0].ttype is T.String.Single


def test_sqlite_identifiers():
    # Make sure we still parse sqlite style escapes
    p = sqlparse.parse('[col1],[col2]')[0].tokens
    assert (len(p) == 1
            and isinstance(p[0], sqlparse.sql.IdentifierList)
            and [id.get_name() for id in p[0].get_identifiers()]
                    == ['[col1]', '[col2]'])

    p = sqlparse.parse('[col1]+[col2]')[0]
    types = [tok.ttype for tok in p.flatten()]
    assert types == [T.Name, T.Operator, T.Name]


def test_simple_1d_array_index():
    p = sqlparse.parse('col[1]')[0].tokens
    assert len(p) == 1
    assert p[0].get_name() == 'col'
    indices = list(p[0].get_array_indices())
    assert (len(indices) == 1  # 1-dimensional index
            and len(indices[0]) == 1  # index is single token
            and indices[0][0].value == '1')


def test_2d_array_index():
    p = sqlparse.parse('col[x][(y+1)*2]')[0].tokens
    assert len(p) == 1
    assert p[0].get_name() == 'col'
    assert len(list(p[0].get_array_indices())) == 2  # 2-dimensional index


def test_array_index_function_result():
    p = sqlparse.parse('somefunc()[1]')[0].tokens
    assert len(p) == 1
    assert len(list(p[0].get_array_indices())) == 1


def test_schema_qualified_array_index():
    p = sqlparse.parse('schem.col[1]')[0].tokens
    assert len(p) == 1
    assert p[0].get_parent_name() == 'schem'
    assert p[0].get_name() == 'col'
    assert list(p[0].get_array_indices())[0][0].value == '1'


def test_aliased_array_index():
    p = sqlparse.parse('col[1] x')[0].tokens
    assert len(p) == 1
    assert p[0].get_alias() == 'x'
    assert p[0].get_real_name() == 'col'
    assert list(p[0].get_array_indices())[0][0].value == '1'


def test_array_literal():
    # See issue #176
    p = sqlparse.parse('ARRAY[%s, %s]')[0]
    assert len(p.tokens) == 2
    assert len(list(p.flatten())) == 7


def test_typed_array_definition():
    # array indices aren't grouped with builtins, but make sure we can extract
    # indentifer names
    p = sqlparse.parse('x int, y int[], z int')[0]
    names = [x.get_name() for x in p.get_sublists()
             if isinstance(x, sqlparse.sql.Identifier)]
    assert names == ['x', 'y', 'z']


@pytest.mark.parametrize('sql', [
    'select 1 -- foo',
    'select 1 # foo'  # see issue178
])
def test_single_line_comments(sql):
    p = sqlparse.parse(sql)[0]
    assert len(p.tokens) == 5
    assert p.tokens[-1].ttype == T.Comment.Single


