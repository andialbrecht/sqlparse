import sqlparse

from sqlparse import sql
from sqlparse import tokens as T


def test_select_followed_by_parenthesis_without_space():
    statement = sqlparse.parse('select(select 1)')[0]

    assert statement.get_type() == 'SELECT'
    assert statement.tokens[0].ttype is T.Keyword.DML
    assert statement.tokens[0].value == 'select'
    assert isinstance(statement.tokens[1], sql.Parenthesis)
