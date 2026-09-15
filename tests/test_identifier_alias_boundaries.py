import pytest

import sqlparse
from sqlparse import sql


@pytest.mark.parametrize('newline', ['\n', '\r\n'])
@pytest.mark.parametrize('expression, alias, expected', [
    ('a', 'b', 'b'),
    ('a.b', 'c', 'c'),
    ('a.b.c', 'd', 'd'),
    ('"a"."b"', '"c"', 'c'),
    ('`a`.`b`', '`c`', 'c'),
    ('func(1)', 'z', 'z'),
    ('a.func(1)', 'z', 'z'),
    ('1', 'z', 'z'),
])
def test_newline_only_implicit_alias(newline, expression, alias, expected):
    text = 'SELECT ' + expression + newline + alias
    statement = sqlparse.parse(text)[0]
    identifier = statement.tokens[2]
    assert isinstance(identifier, sql.Identifier)
    assert identifier.get_alias() == expected
    assert identifier.has_alias()
    assert identifier.get_name() == expected
    assert str(statement) == text


@pytest.mark.parametrize('expression', [
    'a/*c*/.b[1]',
    'a/*c*/.',
    "a/*c*/->'b'",
    'a/*c*/.func(1)',
    'a/*c*/.b',
    'a./*c*/b[1]',
])
def test_comment_inside_expression_is_no_alias(expression):
    text = 'SELECT ' + expression
    statement = sqlparse.parse(text)[0]
    identifiers = [token for token in statement.tokens
                   if isinstance(token, sql.Identifier)]
    assert identifiers
    for identifier in identifiers:
        assert identifier.get_alias() is None
        assert not identifier.has_alias()
    assert str(statement) == text


@pytest.mark.parametrize('operator', ['->', '->>'])
@pytest.mark.parametrize('left_comment', ['', '/*left*/'])
@pytest.mark.parametrize('right_comment', ['/*right*/', '--right\n'])
@pytest.mark.parametrize('operand', ['b', '"b"', '`b`'])
@pytest.mark.parametrize('suffix', ['', ' z', '\nz', '/*alias*/z'])
def test_arrow_operand_and_alias_boundary(operator, left_comment,
                                          right_comment, operand, suffix):
    expression = 'a' + left_comment + operator + right_comment + operand
    text = 'SELECT ' + expression + suffix
    statement = sqlparse.parse(text)[0]
    identifier = statement.tokens[2]
    assert isinstance(identifier, sql.Identifier)
    assert str(identifier) == expression + suffix
    assert identifier.get_alias() == ('z' if suffix else None)
    assert identifier.has_alias() == bool(suffix)
    if suffix:
        assert identifier.get_name() == 'z'
    assert str(statement) == text


@pytest.mark.parametrize('expression', ['a.b[1]', 'a.func(1)'])
@pytest.mark.parametrize('alias', ['z', '"z"'])
def test_expression_alias_whitespace_control(expression, alias):
    text = 'SELECT ' + expression + ' ' + alias
    statement = sqlparse.parse(text)[0]
    identifier = statement.tokens[2]
    assert isinstance(identifier, sql.Identifier)
    assert identifier.get_alias() == 'z'
    assert identifier.has_alias()
    assert identifier.get_name() == 'z'
    assert str(statement) == text


@pytest.mark.parametrize('expression', [
    'a.b[1]', 'a/*c*/.b[1]', 'a.func(1)', 'a/*c*/.func(1)',
])
@pytest.mark.parametrize('gap', [' ', '\n', '/*d*/'])
@pytest.mark.parametrize('alias', ['z', '"z"'])
def test_indexed_and_qualified_function_alias_boundary(expression, gap, alias):
    text = 'SELECT ' + expression + gap + alias
    statement = sqlparse.parse(text)[0]
    identifier = statement.tokens[2]
    assert isinstance(identifier, sql.Identifier)
    assert str(identifier) == expression + gap + alias
    assert identifier.get_alias() == 'z'
    assert identifier.has_alias()
    assert identifier.get_name() == 'z'
    assert str(statement) == text
