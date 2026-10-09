import pytest

import sqlparse
from sqlparse import lexer, sql
from sqlparse import tokens as T

APPLY_OPERATORS = [
    'CROSS APPLY', 'OUTER APPLY', 'cross  apply', 'outer\tapply',
    'CrOsS\nApPlY', 'OuTeR\r\nApPlY',
]


@pytest.mark.parametrize('operator', APPLY_OPERATORS)
def test_apply_keyword(operator):
    assert list(lexer.tokenize(operator)) == [(T.Keyword, operator)]


@pytest.mark.parametrize('operator', ['CROSS APPLY', 'OUTER APPLY'])
@pytest.mark.parametrize('right', [
    'dbo.GetReports(d.DeptMgrID) r',
    'OPENJSON(d.payload) r',
    '(select d.DeptMgrID as id) r',
])
def test_apply_table_sources(operator, right):
    query = f'select * from Departments d {operator} {right}'
    statement = sqlparse.parse(query)[0]
    tokens = [token for token in statement if not token.is_whitespace]

    assert len(tokens) == 6
    assert isinstance(tokens[3], sql.Identifier)
    assert tokens[3].get_real_name() == 'Departments'
    assert tokens[3].get_alias() == 'd'
    assert tokens[4].match(T.Keyword, operator)
    assert isinstance(tokens[5], sql.Identifier)
    assert tokens[5].value == right
    assert tokens[5].get_alias() == 'r'
    assert str(statement) == query


@pytest.mark.parametrize('operator', APPLY_OPERATORS)
@pytest.mark.parametrize('case', ['upper', 'lower'])
def test_apply_keyword_case(operator, case):
    query = (f'select * from Departments d {operator} '
             'dbo.GetReports(d.DeptMgrID) r')
    convert = str.upper if case == 'upper' else str.lower
    expected = (f'{convert("select")} * {convert("from")} Departments d '
                f'{convert(operator)} dbo.GetReports(d.DeptMgrID) r')
    assert sqlparse.format(query, keyword_case=case) == expected.replace('\r\n', '\n')


@pytest.mark.parametrize('name', ['apply_column', 'apply2', 'apply$column',
                                  'apply#column'])
@pytest.mark.parametrize('prefix', ['cross', 'outer'])
def test_apply_name_boundary(prefix, name):
    assert list(lexer.tokenize(f'{prefix} {name}')) == [
        (T.Keyword, prefix), (T.Whitespace, ' '), (T.Name, name),
    ]


@pytest.mark.parametrize('expression', [
    'apply', 'cross_apply', 'outer_apply', 'apply(1)',
    '"cross apply"', '[outer apply]', '`cross apply`',
    "'outer apply'", '$$cross apply$$',
])
def test_apply_identifiers_and_quoted_text(expression):
    query = f'select {expression} from t'
    assert sqlparse.format(query, keyword_case='upper') == (
        f'SELECT {expression} FROM t')
