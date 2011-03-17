# -*- coding: utf-8 -*-

import unittest

import sqlparse
from sqlparse import tokens


class RegressionTests(unittest.TestCase):

    def test_issue34(self):
        t = sqlparse.parse("create")[0].token_first()
        self.assertEqual(t.match(tokens.Keyword.DDL, "create"), True)
        self.assertEqual(t.match(tokens.Keyword.DDL, "CREATE"), True)
