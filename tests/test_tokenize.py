# -*- coding: utf-8 -*-

import unittest
import types

from sqlparse import lexer
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
