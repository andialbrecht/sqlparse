import unittest

import sqlparse
from sqlparse.sql import Statement, Parenthesis
from sqlparse import tokens as T


class TestIssue9(unittest.TestCase):

    def test_where_doesnt_consume_parenthesis(self):
        p = sqlparse.parse('(where 1)')[0]
        self.assert_(isinstance(p, Statement))
        self.assertEqual(len(p.tokens), 1)
        self.assert_(isinstance(p.tokens[0], Parenthesis))
        prt = p.tokens[0]
        self.assertEqual(len(prt.tokens), 3)
        self.assertEqual(prt.tokens[0].ttype, T.Punctuation)
        self.assertEqual(prt.tokens[-1].ttype, T.Punctuation)
