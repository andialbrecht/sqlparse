import pytest

import sqlparse
from sqlparse import tokens
from sqlparse.keywords import SQL_REGEX


class TestSQLREGEX:
    @pytest.mark.parametrize('number', ['1.0', '-1.0',
                                        '1.', '-1.',
                                        '.1', '-.1'])
    def test_float_numbers(self, number):
        ttype = next(tt for action, tt in SQL_REGEX if action(number))
        assert tokens.Number.Float == ttype

    def test_spark_keywords(self):
        statements = sqlparse.parse(
            """
            CREATE DATABASE IF NOT EXISTS database_name
            COMMENT "my database comment"
            LOCATION "/mnt/path/to/db"
            WITH DBPROPERTIES (property_name=property_value) ;

            CREATE TABLE IF NOT EXISTS database_name.table_identifier
            (
                col_name1 int COMMENT "woah, cool column",
                b string
            )
            USING DELTA
            OPTIONS ( key1=val1, key2=val2 )
            PARTITIONED BY ( col_name1  )
            CLUSTERED BY ( b )
            SORTED BY ( col_name1  DESC )
            INTO 4 BUCKETS
            LOCATION "/mnt/path/to/db/tbl"
            COMMENT "nice table"
            TBLPROPERTIES ( key1=val1, key2=val2  )
        """
        )

        db_tokens = list(
            filter(lambda t: str(t.ttype).find("Whitespace") < 0, statements[0].tokens)
        )

        # DBPROPERTIES
        assert db_tokens[11].ttype == tokens.Keyword

        tbl_tokens = list(
            filter(lambda t: str(t.ttype).find("Whitespace") < 0, statements[1].tokens)
        )
        position = {
            7: "USING",
            8: "DELTA",
            11: "PARTITIONED",
            14: "CLUSTERED",
            17: "SORTED",
            22: "BUCKETS",
        }
        for pos, val in position.items():
            assert tbl_tokens[pos].ttype == tokens.Keyword
            assert tbl_tokens[pos].value == val
