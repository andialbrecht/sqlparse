"""Ordered-set aggregate grouping (issue700)."""
import pytest

import sqlparse
from sqlparse import sql


@pytest.mark.parametrize('aggregate', [
    "LISTAGG(attr, ', ')",
    'PERCENTILE_CONT(0.5)',
    'percentile_disc(0.5)',
])
@pytest.mark.parametrize('clause', [
    'WITHIN GROUP(ORDER BY attr)',
    'within group (order by attr desc)',
    'WITHIN\nGROUP (ORDER BY attr)',
    'WITHIN\tGROUP (ORDER BY attr)',
])
def test_ordered_set_aggregate_has_one_alias(aggregate, clause):
    expression = f'{aggregate} {clause}'
    query = f'SELECT {expression} AS result FROM source'
    stmt, = sqlparse.parse(query)
    column = stmt.tokens[2]
    assert isinstance(column, sql.Identifier)
    assert str(column) == expression + ' AS result'
    assert column.get_alias() == 'result'
    function = column.tokens[0]
    assert isinstance(function, sql.Function)
    assert str(function) == expression
    assert function.get_name().lower() == aggregate.split('(')[0].lower()
    assert str(stmt) == query


def test_ordered_set_argument_list_excludes_ordering():
    query = "SELECT LISTAGG(attr, ', ') WITHIN GROUP(ORDER BY attr)"
    function = sqlparse.parse(query)[0].tokens[2]
    assert isinstance(function, sql.Function)
    assert [str(p) for p in function.get_parameters()] == ['attr', "', '"]


def test_ordered_set_aggregate_followed_by_window_and_alias():
    expression = ('LISTAGG(attr) WITHIN GROUP (ORDER BY attr) '
                  'OVER (PARTITION BY category)')
    stmt = sqlparse.parse(f'SELECT {expression} ordered_value FROM source')[0]
    column = stmt.tokens[2]
    assert isinstance(column, sql.Identifier)
    assert column.get_alias() == 'ordered_value'
    assert str(column.tokens[0]) == expression
    assert isinstance(column.tokens[0].tokens[-1], sql.Over)


def test_ordered_set_aggregate_in_expression_and_column_list():
    query = ('SELECT COALESCE(PERCENTILE_CONT(0.5) '
             'WITHIN GROUP (ORDER BY attr), 0) AS p, other FROM source')
    stmt = sqlparse.parse(query)[0]
    columns = list(stmt.tokens[2].get_identifiers())
    assert len(columns) == 2
    assert columns[0].get_alias() == 'p'
    coalesce = columns[0].tokens[0]
    args = list(coalesce.get_parameters())
    assert len(args) == 2
    assert isinstance(args[0], sql.Function)
    assert str(args[0]).endswith('WITHIN GROUP (ORDER BY attr)')
    assert str(columns[1]) == 'other'


def test_within_group_keyword_case():
    query = 'select percentile_cont(0.5) within group (order by attr)'
    assert sqlparse.format(query, keyword_case='upper') == (
        'SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY attr)')


@pytest.mark.parametrize('gap1,gap2,gap3', [
    (' /* a */ ', ' ', ' '),
    (' ', ' /* b */ ', ' '),
    (' ', ' ', ' /* c */ '),
    (' -- a\n', ' -- b\n', ' -- c\n'),
])
def test_comments_between_aggregate_clauses(gap1, gap2, gap3):
    expression = (f'LISTAGG(attr){gap1}WITHIN GROUP{gap2}(ORDER BY attr)'
                  f'{gap3}OVER (PARTITION BY category)')
    stmt = sqlparse.parse(f'SELECT {expression} AS result FROM source')[0]
    column = stmt.tokens[2]
    assert column.get_alias() == 'result'
    assert str(column.tokens[0]) == expression


@pytest.mark.parametrize('query,identifier,group_by', [
    ('SELECT f(x) within GROUP BY x', 'f(x) within', 'GROUP BY'),
    ('SELECT x AS within GROUP BY x', 'x AS within', 'GROUP BY'),
    ('SELECT x FROM src within GROUP BY x', 'src within', 'GROUP BY'),
    ('SELECT f(x) within\nGROUP\tBY x', 'f(x) within', 'GROUP\tBY'),
])
@pytest.mark.parametrize('case', [None, 'lower', 'swapcase'])
def test_within_alias_before_group_by(query, identifier, group_by, case):
    if case:
        query = getattr(query, case)()
        identifier = getattr(identifier, case)()
        group_by = getattr(group_by, case)()
    alias = identifier.split()[-1]
    lexical = list(sqlparse.lexer.tokenize(query))
    assert (sqlparse.tokens.Name, alias) in lexical
    assert (sqlparse.tokens.Keyword, group_by) in lexical
    assert not any(' '.join(value.upper().split()) == 'WITHIN GROUP'
                   for _, value in lexical)

    stmt, = sqlparse.parse(query)
    columns = [token for token in stmt.tokens
               if isinstance(token, sql.Identifier)
               and token.get_alias() == alias]
    assert len(columns) == 1
    assert str(columns[0]) == identifier
    group_tokens = [token for token in stmt.tokens
                    if token.ttype is sqlparse.tokens.Keyword
                    and token.value == group_by]
    assert len(group_tokens) == 1
    assert stmt.token_next(stmt.token_index(columns[0]))[1] is group_tokens[0]
    assert str(stmt) == query


def test_bare_within_remains_an_alias():
    column = sqlparse.parse('SELECT f(x) within FROM source')[0].tokens[2]
    assert column.get_alias() == 'within'


@pytest.mark.parametrize('query', [
    'SELECT f(x) within FROM source',
    'SELECT within_group(x) FROM source',
    'SELECT f(x), g(y) FROM source',
    'SELECT f(x) OVER (PARTITION BY y) FROM source',
])
def test_unrelated_function_syntax_roundtrips(query):
    assert str(sqlparse.parse(query)[0]) == query
