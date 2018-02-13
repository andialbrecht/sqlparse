# -*- coding: utf-8 -*-
import pytest

from sqlparse import tokens
from sqlparse.keywords import get_sql_regex


class TestSQLREGEX:
    @pytest.mark.parametrize('number', ['1.0', '-1.0',
                                        '1.', '-1.',
                                        '.1', '-.1'])
    def test_float_numbers(self, number):
        SQL_REGEX = get_sql_regex()

        ttype = next(tt for action, tt in SQL_REGEX if action(number))
        assert tokens.Number.Float == ttype

    @pytest.mark.parametrize(['number', 'options'],
                             [('1.0', {'sql_dialect': 'TransactSQL'}),
                              ('-1.0', {'sql_dialect': 'TransactSQL'}),
                              ('1.', {'sql_dialect': 'TransactSQL'}),
                              ('-1.', {'sql_dialect': 'TransactSQL'}),
                              ('.1', {'sql_dialect': 'TransactSQL'}),
                              ('-.1', {'sql_dialect': 'TransactSQL'})
                              ])
    def test_float_numbers_for_TSQL(self, number, options):
        SQL_REGEX = get_sql_regex(**options)

        ttype = next(tt for action, tt in SQL_REGEX if action(number))
        assert tokens.Number.Float == ttype
