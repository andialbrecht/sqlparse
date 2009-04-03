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

