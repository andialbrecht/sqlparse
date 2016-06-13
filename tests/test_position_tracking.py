import unittest

import sqlparse
from sqlparse import lexer
from sqlparse import tokens as T


class TestPositionTracking(unittest.TestCase):

    def setUp(self):
        #           012345678901234567
        self.sql = 'select * from foo;'
        self.results = [  # List of (type, value, row, col) tuples
            (T.Keyword.DML, u'select', 1, 0),
            (T.Text.Whitespace, u' ', 1, 6),
            (T.Wildcard, u'*', 1, 7),
            (T.Text.Whitespace, u' ', 1, 8),
            (T.Keyword, u'from', 1, 9),
            (T.Text.Whitespace, u' ', 1, 13),
            (T.Name, u'foo', 1, 14),
            (T.Punctuation, u';', 1, 17),
        ]

    def test_tokenizer_yields_positions(self):
        tokens = list(lexer.tokenize(self.sql))
        self.assertEqual(len(tokens), 8)
        self.assertEqual(tokens, self.results)

    def test_parser_augments_tokens_with_positions(self):
        t = sqlparse.parse(self.sql)[0].tokens
        self.assertEqual(len(t), 8)
        for idx in range(8):
            # Only test positions, the rest is already tested elsewhere.
            self.assertEqual(t[idx].row, self.results[idx][2])
            self.assertEqual(t[idx].col, self.results[idx][3])

    def test_parser_multiline_statement(self):
        #      01234567| 01234567| 01234567890123
        sql = 'select *\nfrom foo\nwhere bar > 0;'
        t = sqlparse.parse(sql)[0].tokens

        self.assertEqual(len(t), 9, t)
        self.assertEqual(t[8].value, u'where bar > 0;')
        self.assertEqual(t[8].row, 3)
        self.assertEqual(t[8].col, 0)

        self.assertEqual(len(t[8].tokens), 4)
        self.assertEqual(t[8].tokens[3].ttype, T.Punctuation)
        self.assertEqual(t[8].tokens[3].row, 3)
        self.assertEqual(t[8].tokens[3].col, 13)
