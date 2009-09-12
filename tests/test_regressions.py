# -*- coding: utf-8 -*-

import sqlparse
from sqlparse import tokens as T
from sqlparse.engine.grouping import *

from tests.utils import TestCaseBase


class TestRegression(TestCaseBase):

    def test_where_doesnt_consume_parenthesis(self):  # issue9
        p = sqlparse.parse('(where 1)')[0]
        self.assert_(isinstance(p, Statement))
        self.assertEqual(len(p.tokens), 1)
        self.assert_(isinstance(p.tokens[0], Parenthesis))
        prt = p.tokens[0]
        self.assertEqual(len(prt.tokens), 3)
        self.assertEqual(prt.tokens[0].ttype, T.Punctuation)
        self.assertEqual(prt.tokens[-1].ttype, T.Punctuation)
