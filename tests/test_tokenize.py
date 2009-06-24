# -*- coding: utf-8 -*-

import unittest
import types

import sqlparse
from sqlparse import lexer
from sqlparse import sql
from sqlparse.tokens import *


class TestTokenize(unittest.TestCase):

    def test_simple(self):
        sql = 'select * from foo;'
        stream = lexer.tokenize(sql)
        self.assert_(type(stream) is types.GeneratorType)
        tokens = list(stream)
        self.assertEqual(len(tokens), 8)
        self.assertEqual(len(tokens[0]), 2)
        self.assertEqual(tokens[0], (Keyword.DML, u'select'))
        self.assertEqual(tokens[-1], (Punctuation, u';'))

    def test_backticks(self):
        sql = '`foo`.`bar`'
        tokens = list(lexer.tokenize(sql))
        self.assertEqual(len(tokens), 3)
        self.assertEqual(tokens[0], (Name, u'`foo`'))

    def test_linebreaks(self):  # issue1
        sql = 'foo\nbar\n'
        tokens = lexer.tokenize(sql)
        self.assertEqual(''.join(str(x[1]) for x in tokens), sql)
        sql = 'foo\rbar\r'
        tokens = lexer.tokenize(sql)
        self.assertEqual(''.join(str(x[1]) for x in tokens), sql)
        sql = 'foo\r\nbar\r\n'
        tokens = lexer.tokenize(sql)
        self.assertEqual(''.join(str(x[1]) for x in tokens), sql)
        sql = 'foo\r\nbar\n'
        tokens = lexer.tokenize(sql)
        self.assertEqual(''.join(str(x[1]) for x in tokens), sql)

    def test_inline_keywords(self):  # issue 7
        sql = "create created_foo"
        tokens = list(lexer.tokenize(sql))
        self.assertEqual(len(tokens), 3)
        self.assertEqual(tokens[0][0], Keyword.DDL)
        self.assertEqual(tokens[2][0], Name)
        self.assertEqual(tokens[2][1], u'created_foo')
        sql = "enddate"
        tokens = list(lexer.tokenize(sql))
        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens[0][0], Name)
        sql = "join_col"
        tokens = list(lexer.tokenize(sql))
        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens[0][0], Name)
        sql = "left join_col"
        tokens = list(lexer.tokenize(sql))
        self.assertEqual(len(tokens), 3)
        self.assertEqual(tokens[2][0], Name)
        self.assertEqual(tokens[2][1], 'join_col')


class TestToken(unittest.TestCase):

    def test_str(self):
        token = sql.Token(None, 'FoO')
        self.assertEqual(str(token), 'FoO')

    def test_repr(self):
        token = sql.Token(Keyword, 'foo')
        tst = "<Keyword 'foo' at 0x"
        self.assertEqual(repr(token)[:len(tst)], tst)
        token = sql.Token(Keyword, '1234567890')
        tst = "<Keyword '123456...' at 0x"
        self.assertEqual(repr(token)[:len(tst)], tst)

    def test_flatten(self):
        token = sql.Token(Keyword, 'foo')
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
        self.assertEqual(p.token_first(ignore_whitespace=False).value, ' ')
        self.assertEqual(sql.TokenList([]).token_first(), None)

    def test_token_matching(self):
        t1 = sql.Token(Keyword, 'foo')
        t2 = sql.Token(Punctuation, ',')
        x = sql.TokenList([t1, t2])
        self.assertEqual(x.token_matching(0, [lambda t: t.ttype is Keyword]),
                         t1)
        self.assertEqual(x.token_matching(0,
                                          [lambda t: t.ttype is Punctuation]),
                         t2)
        self.assertEqual(x.token_matching(1, [lambda t: t.ttype is Keyword]),
                         None)
