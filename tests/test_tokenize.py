# -*- coding: utf-8 -*-

import types
import unittest

import pytest

import sqlparse
from sqlparse import lexer
from sqlparse import sql
from sqlparse import tokens as T
from sqlparse.compat import StringIO


class TestTokenize(unittest.TestCase):

    def test_simple(self):
        s = 'select * from foo;'
        stream = lexer.tokenize(s)
        self.assert_(isinstance(stream, types.GeneratorType))
        tokens = list(stream)
        self.assertEqual(len(tokens), 8)
        self.assertEqual(len(tokens[0]), 2)
        self.assertEqual(tokens[0], (T.Keyword.DML, u'select'))
        self.assertEqual(tokens[-1], (T.Punctuation, u';'))

    def test_backticks(self):
        s = '`foo`.`bar`'
        tokens = list(lexer.tokenize(s))
        self.assertEqual(len(tokens), 3)
        self.assertEqual(tokens[0], (T.Name, u'`foo`'))

    def test_linebreaks(self):  # issue1
        s = 'foo\nbar\n'
        tokens = lexer.tokenize(s)
        self.assertEqual(''.join(str(x[1]) for x in tokens), s)
        s = 'foo\rbar\r'
        tokens = lexer.tokenize(s)
        self.assertEqual(''.join(str(x[1]) for x in tokens), s)
        s = 'foo\r\nbar\r\n'
        tokens = lexer.tokenize(s)
        self.assertEqual(''.join(str(x[1]) for x in tokens), s)
        s = 'foo\r\nbar\n'
        tokens = lexer.tokenize(s)
        self.assertEqual(''.join(str(x[1]) for x in tokens), s)

    def test_inline_keywords(self):  # issue 7
        s = "create created_foo"
        tokens = list(lexer.tokenize(s))
        self.assertEqual(len(tokens), 3)
        self.assertEqual(tokens[0][0], T.Keyword.DDL)
        self.assertEqual(tokens[2][0], T.Name)
        self.assertEqual(tokens[2][1], u'created_foo')
        s = "enddate"
        tokens = list(lexer.tokenize(s))
        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens[0][0], T.Name)
        s = "join_col"
        tokens = list(lexer.tokenize(s))
        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens[0][0], T.Name)
        s = "left join_col"
        tokens = list(lexer.tokenize(s))
        self.assertEqual(len(tokens), 3)
        self.assertEqual(tokens[2][0], T.Name)
        self.assertEqual(tokens[2][1], 'join_col')

    def test_negative_numbers(self):
        s = "values(-1)"
        tokens = list(lexer.tokenize(s))
        self.assertEqual(len(tokens), 4)
        self.assertEqual(tokens[2][0], T.Number.Integer)
        self.assertEqual(tokens[2][1], '-1')


class TestToken(unittest.TestCase):

    def test_str(self):
        token = sql.Token(None, 'FoO')
        self.assertEqual(str(token), 'FoO')

    def test_repr(self):
        token = sql.Token(T.Keyword, 'foo')
        tst = "<Keyword 'foo' at 0x"
        self.assertEqual(repr(token)[:len(tst)], tst)
        token = sql.Token(T.Keyword, '1234567890')
        tst = "<Keyword '123456...' at 0x"
        self.assertEqual(repr(token)[:len(tst)], tst)

    def test_flatten(self):
        token = sql.Token(T.Keyword, 'foo')
        gen = token.flatten()
        self.assertEqual(type(gen), types.GeneratorType)
        lgen = list(gen)
        self.assertEqual(lgen, [token])


class TestTokenList(unittest.TestCase):

    def test_repr(self):
        p = sqlparse.parse('foo, bar, baz')[0]
        tst = "<IdentifierList 'foo, b...' at 0x"
        self.assertEqual(repr(p.tokens[0])[:len(tst)], tst)

    def test_token_first(self):
        p = sqlparse.parse(' select foo')[0]
        first = p.token_first()
        self.assertEqual(first.value, 'select')
        self.assertEqual(p.token_first(skip_ws=False).value, ' ')
        self.assertEqual(sql.TokenList([]).token_first(), None)

    def test_token_matching(self):
        t1 = sql.Token(T.Keyword, 'foo')
        t2 = sql.Token(T.Punctuation, ',')
        x = sql.TokenList([t1, t2])
        self.assertEqual(x.token_matching(0, [lambda t: t.ttype is T.Keyword]),
                         t1)
        self.assertEqual(x.token_matching(
            0,
            [lambda t: t.ttype is T.Punctuation]),
            t2)
        self.assertEqual(x.token_matching(1, [lambda t: t.ttype is T.Keyword]),
                         None)


class TestStream(unittest.TestCase):
    def test_simple(self):
        stream = StringIO("SELECT 1; SELECT 2;")

        tokens = lexer.tokenize(stream)
        self.assertEqual(len(list(tokens)), 9)

        stream.seek(0)
        tokens = list(lexer.tokenize(stream))
        self.assertEqual(len(tokens), 9)

        stream.seek(0)
        tokens = list(lexer.tokenize(stream))
        self.assertEqual(len(tokens), 9)

    def test_error(self):
        stream = StringIO("FOOBAR{")

        tokens = list(lexer.tokenize(stream))
        self.assertEqual(len(tokens), 2)
        self.assertEqual(tokens[1][0], T.Error)


@pytest.mark.parametrize('expr', ['JOIN', 'LEFT JOIN', 'LEFT OUTER JOIN',
                                  'FULL OUTER JOIN', 'NATURAL JOIN',
                                  'CROSS JOIN', 'STRAIGHT JOIN',
                                  'INNER JOIN', 'LEFT INNER JOIN'])
def test_parse_join(expr):
    p = sqlparse.parse('%s foo' % expr)[0]
    assert len(p.tokens) == 3
    assert p.tokens[0].ttype is T.Keyword


def test_parse_endifloop():
    p = sqlparse.parse('END IF')[0]
    assert len(p.tokens) == 1
    assert p.tokens[0].ttype is T.Keyword
    p = sqlparse.parse('END   IF')[0]
    assert len(p.tokens) == 1
    p = sqlparse.parse('END\t\nIF')[0]
    assert len(p.tokens) == 1
    assert p.tokens[0].ttype is T.Keyword
    p = sqlparse.parse('END LOOP')[0]
    assert len(p.tokens) == 1
    assert p.tokens[0].ttype is T.Keyword
    p = sqlparse.parse('END  LOOP')[0]
    assert len(p.tokens) == 1
    assert p.tokens[0].ttype is T.Keyword
