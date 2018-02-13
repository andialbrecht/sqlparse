# -*- coding: utf-8 -*-

import types

import pytest

import sqlparse
from sqlparse import lexer
from sqlparse import sql, tokens as T
from sqlparse.compat import StringIO


@pytest.mark.parametrize('options', [{'sql_dialect': 'Default'},
                                     {'sql_dialect': 'TransactSQL'}])
def test_tokenize_simple(options):
    s = 'select * from foo;'
    stream = lexer.tokenize(s, **options)
    assert isinstance(stream, types.GeneratorType)
    tokens = list(stream)
    assert len(tokens) == 8
    assert len(tokens[0]) == 2
    assert tokens[0] == (T.Keyword.DML, 'select')
    assert tokens[-1] == (T.Punctuation, ';')


@pytest.mark.parametrize('options', [{'sql_dialect': 'Default'}])
def test_tokenize_backticks(options):
    s = '`foo`.`bar`'
    tokens = list(lexer.tokenize(s, **options))
    assert len(tokens) == 3
    assert tokens[0] == (T.Name, '`foo`')


@pytest.mark.parametrize(['s', 'options'],
                         [('foo\nbar\n', {'sql_dialect': 'Default'}),
                          ('foo\rbar\r', {'sql_dialect': 'Default'}),
                          ('foo\r\nbar\r\n', {'sql_dialect': 'Default'}),
                          ('foo\r\nbar\n', {'sql_dialect': 'Default'}),
                          ('foo\nbar\n', {'sql_dialect': 'TransactSQL'}),
                          ('foo\rbar\r', {'sql_dialect': 'TransactSQL'}),
                          ('foo\r\nbar\r\n', {'sql_dialect': 'TransactSQL'}),
                          ('foo\r\nbar\n', {'sql_dialect': 'TransactSQL'})
                          ])
def test_tokenize_linebreaks(s, options):
    # issue1
    tokens = lexer.tokenize(s, **options)
    assert ''.join(str(x[1]) for x in tokens) == s


@pytest.mark.parametrize('options', [{'sql_dialect': 'Default'},
                                     {'sql_dialect': 'TransactSQL'}])
def test_tokenize_inline_keywords(options):
    # issue 7
    s = "create created_foo"
    tokens = list(lexer.tokenize(s, **options))
    assert len(tokens) == 3
    assert tokens[0][0] == T.Keyword.DDL
    assert tokens[2][0] == T.Name
    assert tokens[2][1] == 'created_foo'
    s = "enddate"
    tokens = list(lexer.tokenize(s, **options))
    assert len(tokens) == 1
    assert tokens[0][0] == T.Name
    s = "join_col"
    tokens = list(lexer.tokenize(s, **options))
    assert len(tokens) == 1
    assert tokens[0][0] == T.Name
    s = "left join_col"
    tokens = list(lexer.tokenize(s, **options))
    assert len(tokens) == 3
    assert tokens[2][0] == T.Name
    assert tokens[2][1] == 'join_col'


@pytest.mark.parametrize('options', [{'sql_dialect': 'Default'},
                                     {'sql_dialect': 'TransactSQL'}])
def test_tokenize_negative_numbers(options):
    s = "values(-1)"
    tokens = list(lexer.tokenize(s, **options))
    assert len(tokens) == 4
    assert tokens[2][0] == T.Number.Integer
    assert tokens[2][1] == '-1'


def test_token_str():
    token = sql.Token(None, 'FoO')
    assert str(token) == 'FoO'


def test_token_repr():
    token = sql.Token(T.Keyword, 'foo')
    tst = "<Keyword 'foo' at 0x"
    assert repr(token)[:len(tst)] == tst
    token = sql.Token(T.Keyword, '1234567890')
    tst = "<Keyword '123456...' at 0x"
    assert repr(token)[:len(tst)] == tst


def test_token_flatten():
    token = sql.Token(T.Keyword, 'foo')
    gen = token.flatten()
    assert isinstance(gen, types.GeneratorType)
    lgen = list(gen)
    assert lgen == [token]


@pytest.mark.parametrize('options', [{'sql_dialect': 'Default'},
                                     {'sql_dialect': 'TransactSQL'}])
def test_tokenlist_repr(options):
    p = sqlparse.parse('foo, bar, baz', **options)[0]
    tst = "<IdentifierList 'foo, b...' at 0x"
    assert repr(p.tokens[0])[:len(tst)] == tst


@pytest.mark.parametrize('options', [{'sql_dialect': 'Default'},
                                     {'sql_dialect': 'TransactSQL'}])
def test_single_quotes(options):
    p = sqlparse.parse("'test'", **options)[0]
    tst = "<Single \"'test'\" at 0x"
    assert repr(p.tokens[0])[:len(tst)] == tst


@pytest.mark.parametrize('options', [{'sql_dialect': 'Default'},
                                     {'sql_dialect': 'TransactSQL'}])
def test_tokenlist_first(options):
    p = sqlparse.parse(' select foo', **options)[0]
    first = p.token_first()
    assert first.value == 'select'
    assert p.token_first(skip_ws=False).value == ' '
    assert sql.TokenList([]).token_first() is None


def test_tokenlist_token_matching():
    t1 = sql.Token(T.Keyword, 'foo')
    t2 = sql.Token(T.Punctuation, ',')
    x = sql.TokenList([t1, t2])
    assert x.token_matching([lambda t: t.ttype is T.Keyword], 0) == t1
    assert x.token_matching([lambda t: t.ttype is T.Punctuation], 0) == t2
    assert x.token_matching([lambda t: t.ttype is T.Keyword], 1) is None


@pytest.mark.parametrize('options', [{'sql_dialect': 'Default'},
                                     {'sql_dialect': 'TransactSQL'}])
def test_stream_simple(options):
    stream = StringIO("SELECT 1; SELECT 2;")

    tokens = lexer.tokenize(stream, **options)
    assert len(list(tokens)) == 9

    stream.seek(0)
    tokens = list(lexer.tokenize(stream, **options))
    assert len(tokens) == 9

    stream.seek(0)
    tokens = list(lexer.tokenize(stream, **options))
    assert len(tokens) == 9


@pytest.mark.parametrize('options', [{'sql_dialect': 'Default'},
                                     {'sql_dialect': 'TransactSQL'}])
def test_stream_error(options):
    stream = StringIO("FOOBAR{")

    tokens = list(lexer.tokenize(stream, **options))
    assert len(tokens) == 2
    assert tokens[1][0] == T.Error


@pytest.mark.parametrize(['expr', 'options'], [
    ('JOIN', {'sql_dialect': 'Default'}),
    ('LEFT JOIN', {'sql_dialect': 'Default'}),
    ('LEFT OUTER JOIN', {'sql_dialect': 'Default'}),
    ('FULL OUTER JOIN', {'sql_dialect': 'Default'}),
    ('NATURAL JOIN', {'sql_dialect': 'Default'}),
    ('CROSS JOIN', {'sql_dialect': 'Default'}),
    ('STRAIGHT JOIN', {'sql_dialect': 'Default'}),
    ('INNER JOIN', {'sql_dialect': 'Default'}),
    ('LEFT INNER JOIN', {'sql_dialect': 'Default'}),
    ('JOIN', {'sql_dialect': 'TransactSQL'}),
    ('LEFT JOIN', {'sql_dialect': 'TransactSQL'}),
    ('LEFT OUTER JOIN', {'sql_dialect': 'TransactSQL'}),
    ('FULL OUTER JOIN', {'sql_dialect': 'TransactSQL'}),
    ('CROSS JOIN', {'sql_dialect': 'TransactSQL'}),
    ('INNER JOIN', {'sql_dialect': 'TransactSQL'}),
    ('LEFT INNER JOIN', {'sql_dialect': 'TransactSQL'})
])
def test_parse_join(expr, options):
    p = sqlparse.parse('{0} foo'.format(expr),
                       **options)[0]
    assert len(p.tokens) == 3
    assert p.tokens[0].ttype is T.Keyword


@pytest.mark.parametrize('options', [{'sql_dialect': 'Default'},
                                     {'sql_dialect': 'TransactSQL'}])
def test_parse_union(options):  # issue294
    p = sqlparse.parse('UNION ALL',
                       **options)[0]
    assert len(p.tokens) == 1
    assert p.tokens[0].ttype is T.Keyword


@pytest.mark.parametrize(['s', 'options'],
                         [('END IF', {'sql_dialect': 'Default'}),
                          ('END   IF', {'sql_dialect': 'Default'}),
                          ('END\t\nIF', {'sql_dialect': 'Default'}),
                          ('END LOOP', {'sql_dialect': 'Default'}),
                          ('END   LOOP', {'sql_dialect': 'Default'})
                          ])
def test_parse_endifloop(s, options):
    p = sqlparse.parse(s, **options)[0]
    assert len(p.tokens) == 1
    assert p.tokens[0].ttype is T.Keyword


@pytest.mark.parametrize(['s', 'options'],
                         [('foo', {'sql_dialect': 'Default'}),
                          ('Foo', {'sql_dialect': 'Default'}),
                          ('FOO', {'sql_dialect': 'Default'}),
                          ('v$name', {'sql_dialect': 'Default'}),  # issue291
                          ('foo', {'sql_dialect': 'TransactSQL'}),
                          ('Foo', {'sql_dialect': 'TransactSQL'}),
                          ('FOO', {'sql_dialect': 'TransactSQL'}),
                          ])
def test_parse_identifiers(s, options):
    p = sqlparse.parse(s, **options)[0]
    assert len(p.tokens) == 1
    token = p.tokens[0]
    assert str(token) == s
    assert isinstance(token, sql.Identifier)
