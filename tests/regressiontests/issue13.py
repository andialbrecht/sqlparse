import unittest

import sqlparse


TEST_SQL = """select 'one';
select 'two\\'';
select 'three';"""


class TestIssue13(unittest.TestCase):

    def test_quoted(self):
        parsed = sqlparse.parse(TEST_SQL)
        self.assertEqual(len(parsed), 3)
        self.assertEqual(str(parsed[1]).strip(), "select 'two\\'';")
