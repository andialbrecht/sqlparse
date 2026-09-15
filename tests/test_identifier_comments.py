import pytest

import sqlparse
from sqlparse import sql


@pytest.mark.parametrize('gap', [' ', ' /* comment */ ', ' -- comment\n ', '/*a*//*b*/'])
@pytest.mark.parametrize('template', ['a{gap}.b', 'a.{gap}b', 'a{gap}.{gap}b',
                                     'a{gap}.{gap}b AS{gap}c',
                                     'a{gap}.{gap}b{gap}AS c',
                                     'a{gap}.{gap}b{gap}c'])
def test_identifier_comment_separators(gap, template):
    text = template.format(gap=gap)
    statement = sqlparse.parse('SELECT ' + text + ' FROM t')[0]
    meaningful = [t for t in statement.tokens if not t.is_whitespace]
    assert len(meaningful) == 4
    identifier = meaningful[1]
    assert isinstance(identifier, sql.Identifier)
    assert str(identifier) == text
    assert identifier.get_parent_name() == 'a'
    assert identifier.get_real_name() == 'b'
    if template.endswith('c'):
        assert identifier.get_alias() == 'c'
    else:
        assert identifier.get_alias() is None
    assert str(statement) == 'SELECT ' + text + ' FROM t'
    def check_parents(node):
        if isinstance(node, sql.TokenList):
            for child in node.tokens:
                assert child.parent is node
                check_parents(child)
    check_parents(statement)


def test_issue_712_query():
    text = '''select count(*)
from
  -- In SQL, Identifiers
  my_namespace
  -- can have whitespace
  .
  -- and comments
  "my_table"
  -- in between the tokens
  as
  -- comments can go anywhere really
  my_alias
where
   my_alias
   -- also true here
   .
   -- Yes, a little silly, but important
   my_value is not Null
'''
    statement = sqlparse.parse(text)[0]
    identifiers = [t for t in statement.tokens if isinstance(t, sql.Identifier)]
    assert len(identifiers) == 1
    assert identifiers[0].get_parent_name() == 'my_namespace'
    assert identifiers[0].get_real_name() == 'my_table'
    assert identifiers[0].get_alias() == 'my_alias'
    where = next(t for t in statement.tokens if isinstance(t, sql.Where))
    identifier = next(t for t in where.tokens if isinstance(t, sql.Identifier))
    assert identifier.get_parent_name() == 'my_alias'
    assert identifier.get_real_name() == 'my_value'
    assert str(statement) == text


@pytest.mark.parametrize('text, parent, name, alias', [
    ('"a"/*c*/./*d*/"b"./*e*/"c" AS/*f*/"d"', 'a', 'c', 'd'),
    ('a/*c*/./*d*/*', 'a', '*', None),
    ('a/*c*/./*d*/func(1) AS/*e*/b', 'a', 'func', 'b'),
    ('a/*c*/b', None, 'a', 'b'),
    ('a/*c*/', None, 'a', None),
    ('a./*c*/', 'a', None, None),
])
def test_identifier_comment_boundaries(text, parent, name, alias):
    statement = sqlparse.parse('SELECT ' + text)[0]
    identifier = statement.tokens[2]
    assert isinstance(identifier, sql.Identifier)
    assert identifier.get_parent_name() == parent
    assert identifier.get_real_name() == name
    assert identifier.get_alias() == alias
    assert str(statement) == 'SELECT ' + text


@pytest.mark.parametrize('text', [
    'SELECT (SELECT a/*c*/./*d*/b AS/*e*/c FROM t)',
    'SELECT a/*c*/./*d*/b, d/*e*/./*f*/g FROM t',
    'SELECT a/*c*/. FROM t',
    'SELECT a./*c*/ WHERE b = 1',
])
def test_identifier_comments_preserve_nested_and_incomplete_sql(text):
    statement = sqlparse.parse(text)[0]
    assert str(statement) == text
    assert ''.join(t.value for t in statement.flatten()) == text


@pytest.mark.parametrize('text, expected', [
    ('SELECT a/*c*/ AS b', 'SELECT a AS b'),
    ('SELECT a/*c*/AS b', 'SELECT a AS b'),
    ('SELECT a--c\n AS b', 'SELECT a\n AS b'),
    ('SELECT a/*+hint*/ AS b', 'SELECT a/*+hint*/ AS b'),
])
def test_strip_identifier_comments(text, expected):
    assert sqlparse.format(text, strip_comments=True) == expected
