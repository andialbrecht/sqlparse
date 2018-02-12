# -*- coding: utf-8 -*-

"""Tests sqlparse.parse()."""

import pytest

import sqlparse
from sqlparse import sql, tokens as T
from sqlparse.compat import StringIO, text_type


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_parse_tokenize(sql_dialect):
    s = 'select * from foo;'
    stmts = sqlparse.parse(s, sql_dialect=sql_dialect)
    assert len(stmts) == 1
    assert str(stmts[0]) == s


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_parse_multistatement(sql_dialect):
    sql1 = 'select * from foo;'
    sql2 = 'select * from bar;'
    stmts = sqlparse.parse(sql1 + sql2, sql_dialect=sql_dialect)
    assert len(stmts) == 2
    assert str(stmts[0]) == sql1
    assert str(stmts[1]) == sql2


@pytest.mark.parametrize(['s', 'sql_dialect'],
                         [('select\n*from foo;', None),
                          ('select\r\n*from foo', None),
                          ('select\r*from foo', None),
                          ('select\r\n*from foo\n', None),
                          ('select\n*from foo;', 'TransactSQL'),
                          ('select\r\n*from foo', 'TransactSQL'),
                          ('select\r*from foo', 'TransactSQL'),
                          ('select\r\n*from foo\n', 'TransactSQL')
                          ])
def test_parse_newlines(s, sql_dialect):
    p = sqlparse.parse(s, sql_dialect=sql_dialect)[0]
    assert str(p) == s


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_parse_within(sql_dialect):
    s = 'foo(col1, col2)'
    p = sqlparse.parse(s, sql_dialect=sql_dialect)[0]
    col1 = p.tokens[0].tokens[1].tokens[1].tokens[0]
    assert col1.within(sql.Function)


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_parse_child_of(sql_dialect):
    s = '(col1, col2)'
    p = sqlparse.parse(s, sql_dialect=sql_dialect)[0]
    assert p.tokens[0].tokens[1].is_child_of(p.tokens[0])
    s = 'select foo'
    p = sqlparse.parse(s, sql_dialect=sql_dialect)[0]
    assert not p.tokens[2].is_child_of(p.tokens[0])
    assert p.tokens[2].is_child_of(p)


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_parse_has_ancestor(sql_dialect):
    s = 'foo or (bar, baz)'
    p = sqlparse.parse(s, sql_dialect=sql_dialect)[0]
    baz = p.tokens[-1].tokens[1].tokens[-1]
    assert baz.has_ancestor(p.tokens[-1].tokens[1])
    assert baz.has_ancestor(p.tokens[-1])
    assert baz.has_ancestor(p)


@pytest.mark.parametrize(['s', 'sql_dialect'], [('.5', None),
                                                ('.51', None),
                                                ('1.5', None),
                                                ('12.5', None),
                                                ('.5', 'TransactSQL'),
                                                ('.51', 'TransactSQL'),
                                                ('1.5', 'TransactSQL'),
                                                ('12.5', 'TransactSQL')
                                                ])
def test_parse_float(s, sql_dialect):
    t = sqlparse.parse(s, sql_dialect=sql_dialect)[0].tokens
    assert len(t) == 1
    assert t[0].ttype is sqlparse.tokens.Number.Float


@pytest.mark.parametrize('s, holder', [
    ('select * from foo where user = ?', '?'),
    ('select * from foo where user = :1', ':1'),
    ('select * from foo where user = :name', ':name'),
    ('select * from foo where user = %s', '%s'),
    ('select * from foo where user = $a', '$a')])
def test_parse_placeholder(s, holder):
    t = sqlparse.parse(s)[0].tokens[-1].tokens
    assert t[-1].ttype is sqlparse.tokens.Name.Placeholder
    assert t[-1].value == holder


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_parse_modulo_not_placeholder(sql_dialect):
    tokens = list(sqlparse.lexer.tokenize('x %3', sql_dialect=sql_dialect))
    assert tokens[2][0] == sqlparse.tokens.Operator


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_parse_access_symbol(sql_dialect):
    # see issue27
    t = sqlparse.parse('select a.[foo bar] as foo',
                       sql_dialect=sql_dialect)[0].tokens
    assert isinstance(t[-1], sql.Identifier)
    assert t[-1].get_name() == 'foo'
    assert t[-1].get_real_name() == '[foo bar]'
    assert t[-1].get_parent_name() == 'a'


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_parse_square_brackets_notation_isnt_too_greedy(sql_dialect):
    # see issue153
    t = sqlparse.parse('[foo], [bar]', sql_dialect=sql_dialect)[0].tokens
    assert isinstance(t[0], sql.IdentifierList)
    assert len(t[0].tokens) == 4
    assert t[0].tokens[0].get_real_name() == '[foo]'
    assert t[0].tokens[-1].get_real_name() == '[bar]'


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_parse_keyword_like_identifier(sql_dialect):
    # see issue47
    t = sqlparse.parse('foo.key', sql_dialect=sql_dialect)[0].tokens
    assert len(t) == 1
    assert isinstance(t[0], sql.Identifier)


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_parse_function_parameter(sql_dialect):
    # see issue94
    t = sqlparse.parse('abs(some_col)',
                       sql_dialect=sql_dialect)[0].tokens[0].get_parameters()
    assert len(t) == 1
    assert isinstance(t[0], sql.Identifier)


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_parse_function_param_single_literal(sql_dialect):
    t = sqlparse.parse('foo(5)',
                       sql_dialect=sql_dialect)[0].tokens[0].get_parameters()
    assert len(t) == 1
    assert t[0].ttype is T.Number.Integer


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_parse_nested_function(sql_dialect):
    t = sqlparse.parse('foo(bar(5))',
                       sql_dialect=sql_dialect)[0].tokens[0].get_parameters()
    assert len(t) == 1
    assert type(t[0]) is sql.Function


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_quoted_identifier(sql_dialect):
    t = sqlparse.parse('select x.y as "z" from foo',
                       sql_dialect=sql_dialect)[0].tokens
    assert isinstance(t[2], sql.Identifier)
    assert t[2].get_name() == 'z'
    assert t[2].get_real_name() == 'y'


@pytest.mark.parametrize('name', [
    'foo', '_foo',  # issue175
    '1_data',  # valid MySQL table name, see issue337
])
def test_valid_identifier_names(name):
    t = sqlparse.parse(name)[0].tokens
    assert isinstance(t[0], sql.Identifier)
    assert t[0].get_name() == name


def test_psql_quotation_marks():
    # issue83

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
    s = 'DOUBLE PRECISION'
    t = sqlparse.parse(s)[0].tokens
    assert len(t) == 1
    assert t[0].ttype == sqlparse.tokens.Name.Builtin
    assert t[0].value == 'DOUBLE PRECISION'


def test_tsql_variable_and_builtin():
    s = 'DECLARE @my_var int;'
    t = sqlparse.parse(s, sql_dialect='TransactSQL')[0].tokens
    assert len(t) == 6
    assert t[2].ttype == sqlparse.tokens.Name.Variable
    assert t[2].value == '@my_var'

    s = 'SELECT @@Version;'
    t = sqlparse.parse(s, sql_dialect='TransactSQL')[0].tokens
    assert len(t) == 4
    assert t[2].ttype == sqlparse.tokens.Name.Builtin
    assert t[2].value == '@@Version'


@pytest.mark.parametrize('ph', ['?', ':1', ':foo', '%s', '%(foo)s'])
def test_placeholder(ph):
    p = sqlparse.parse(ph)[0].tokens
    assert len(p) == 1
    assert p[0].ttype is T.Name.Placeholder


@pytest.mark.parametrize(['num', 'sql_dialect'],
                         [('6.67428E-8', None),
                          ('1.988e33', None),
                          ('1e-12', None),
                          ('6.67428E-8', 'TransactSQL'),
                          ('1.988e33', 'TransactSQL'),
                          ('1e-12', 'TransactSQL')
                          ])
def test_scientific_numbers(num, sql_dialect):
    p = sqlparse.parse(num, sql_dialect=sql_dialect)[0].tokens
    assert len(p) == 1
    assert p[0].ttype is T.Number.Float


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_single_quotes_are_strings(sql_dialect):
    p = sqlparse.parse("'foo'",
                       sql_dialect=sql_dialect)[0].tokens
    assert len(p) == 1
    assert p[0].ttype is T.String.Single


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_double_quotes_are_identifiers(sql_dialect):
    p = sqlparse.parse('"foo"', sql_dialect=sql_dialect)[0].tokens
    assert len(p) == 1
    assert isinstance(p[0], sql.Identifier)


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_single_quotes_with_linebreaks(sql_dialect):
    # issue118
    p = sqlparse.parse("'f\nf'",
                       sql_dialect=sql_dialect)[0].tokens
    assert len(p) == 1
    assert p[0].ttype is T.String.Single


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_sqlite_identifiers(sql_dialect):
    # Make sure we still parse sqlite/Transact SQL style escapes
    p = sqlparse.parse('[col1],[col2]',
                       sql_dialect=sql_dialect)[0].tokens
    id_names = [id_.get_name() for id_ in p[0].get_identifiers()]
    assert len(p) == 1
    assert isinstance(p[0], sql.IdentifierList)
    assert id_names == ['[col1]', '[col2]']

    p = sqlparse.parse('[col1]+[col2]',
                       sql_dialect=sql_dialect)[0]
    types = [tok.ttype for tok in p.flatten()]
    assert types == [T.Name, T.Operator, T.Name]


def test_simple_1d_array_index():
    p = sqlparse.parse('col[1]')[0].tokens
    assert len(p) == 1
    assert p[0].get_name() == 'col'
    indices = list(p[0].get_array_indices())
    assert len(indices) == 1  # 1-dimensional index
    assert len(indices[0]) == 1  # index is single token
    assert indices[0][0].value == '1'


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
    # array indices aren't grouped with built-ins, but make sure we can extract
    # identifier names
    p = sqlparse.parse('x int, y int[], z int')[0]
    names = [x.get_name() for x in p.get_sublists()
             if isinstance(x, sql.Identifier)]
    assert names == ['x', 'y', 'z']


@pytest.mark.parametrize(['s', 'sql_dialect'],
                         [('select 1 -- foo', None),
                          ('select 1 # foo', None),
                          ('select 1 -- foo', 'TransactSQL')])
def test_single_line_comments(s, sql_dialect):
    # see issue178
    p = sqlparse.parse(s, sql_dialect=sql_dialect)[0]
    assert len(p.tokens) == 5
    assert p.tokens[-1].ttype == T.Comment.Single


@pytest.mark.parametrize('s', ['foo', '@foo', '#foo', '##foo'])
def test_names_and_special_names(s):
    # see issue192
    p = sqlparse.parse(s)[0]
    assert len(p.tokens) == 1
    assert isinstance(p.tokens[0], sql.Identifier)


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_get_token_at_offset(sql_dialect):
    p = sqlparse.parse('select * from dual', sql_dialect=sql_dialect)[0]
    #                   0123456789
    assert p.get_token_at_offset(0) == p.tokens[0]
    assert p.get_token_at_offset(1) == p.tokens[0]
    assert p.get_token_at_offset(6) == p.tokens[1]
    assert p.get_token_at_offset(7) == p.tokens[2]
    assert p.get_token_at_offset(8) == p.tokens[3]
    assert p.get_token_at_offset(9) == p.tokens[4]
    assert p.get_token_at_offset(10) == p.tokens[4]


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_pprint(sql_dialect):
    p = sqlparse.parse('select a0, b0, c0, d0, e0 from '
                       '(select * from dual) q0 where 1=1 and 2=2',
                       sql_dialect=sql_dialect)[0]
    output = StringIO()

    p._pprint_tree(f=output)
    pprint = '\n'.join([
        " 0 DML 'select'",
        " 1 Whitespace ' '",
        " 2 IdentifierList 'a0, b0...'",
        " |  0 Identifier 'a0'",
        " |  |  0 Name 'a0'",
        " |  1 Punctuation ','",
        " |  2 Whitespace ' '",
        " |  3 Identifier 'b0'",
        " |  |  0 Name 'b0'",
        " |  4 Punctuation ','",
        " |  5 Whitespace ' '",
        " |  6 Identifier 'c0'",
        " |  |  0 Name 'c0'",
        " |  7 Punctuation ','",
        " |  8 Whitespace ' '",
        " |  9 Identifier 'd0'",
        " |  |  0 Name 'd0'",
        " | 10 Punctuation ','",
        " | 11 Whitespace ' '",
        " | 12 Float 'e0'",
        " 3 Whitespace ' '",
        " 4 Keyword 'from'",
        " 5 Whitespace ' '",
        " 6 Identifier '(selec...'",
        " |  0 Parenthesis '(selec...'",
        " |  |  0 Punctuation '('",
        " |  |  1 DML 'select'",
        " |  |  2 Whitespace ' '",
        " |  |  3 Wildcard '*'",
        " |  |  4 Whitespace ' '",
        " |  |  5 Keyword 'from'",
        " |  |  6 Whitespace ' '",
        " |  |  7 Identifier 'dual'",
        " |  |  |  0 Name 'dual'",
        " |  |  8 Punctuation ')'",
        " |  1 Whitespace ' '",
        " |  2 Identifier 'q0'",
        " |  |  0 Name 'q0'",
        " 7 Whitespace ' '",
        " 8 Where 'where ...'",
        " |  0 Keyword 'where'",
        " |  1 Whitespace ' '",
        " |  2 Comparison '1=1'",
        " |  |  0 Integer '1'",
        " |  |  1 Comparison '='",
        " |  |  2 Integer '1'",
        " |  3 Whitespace ' '",
        " |  4 Keyword 'and'",
        " |  5 Whitespace ' '",
        " |  6 Comparison '2=2'",
        " |  |  0 Integer '2'",
        " |  |  1 Comparison '='",
        " |  |  2 Integer '2'",
        ""])
    assert output.getvalue() == pprint


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_wildcard_multiplication(sql_dialect):
    p = sqlparse.parse('select * from dual',
                       sql_dialect=sql_dialect)[0]
    assert p.tokens[2].ttype == T.Wildcard

    p = sqlparse.parse('select a0.* from dual a0',
                       sql_dialect=sql_dialect)[0]
    assert p.tokens[2][2].ttype == T.Wildcard

    p = sqlparse.parse('select 1 * 2 from dual',
                       sql_dialect=sql_dialect)[0]
    assert p.tokens[2][2].ttype == T.Operator


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_stmt_tokens_parents(sql_dialect):
    # see issue 226
    s = "CREATE TABLE test();"
    stmt = sqlparse.parse(s,
                          sql_dialect=sql_dialect)[0]
    for token in stmt.tokens:
        assert token.has_ancestor(stmt)


@pytest.mark.parametrize('sql, is_literal', [
    ('$$foo$$', True),
    ('$_$foo$_$', True),
    ('$token$ foo $token$', True),
    # don't parse inner tokens
    ('$_$ foo $token$bar$token$ baz$_$', True),
    ('$A$ foo $B$', False)  # tokens don't match
])
def test_dbldollar_as_literal(sql, is_literal):
    # see issue 277
    p = sqlparse.parse(sql)[0]
    if is_literal:
        assert len(p.tokens) == 1
        assert p.tokens[0].ttype == T.Literal
    else:
        for token in p.tokens:
            assert token.ttype != T.Literal


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_non_ascii(sql_dialect):
    _test_non_ascii = u"insert into test (id, name) values (1, 'тест');"

    s = _test_non_ascii
    stmts = sqlparse.parse(s, sql_dialect=sql_dialect)
    assert len(stmts) == 1
    statement = stmts[0]
    assert text_type(statement) == s
    assert statement._pprint_tree() is None

    s = _test_non_ascii.encode('utf-8')
    stmts = sqlparse.parse(s, 'utf-8', sql_dialect=sql_dialect)
    assert len(stmts) == 1
    statement = stmts[0]
    assert text_type(statement) == _test_non_ascii
    assert statement._pprint_tree() is None
