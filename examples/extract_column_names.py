#!/usr/bin/env python
#
# Copyright (C) 2009-2020 the sqlparse authors and contributors
# <see AUTHORS file>
#
# This example is part of python-sqlparse and is released under
# the BSD License: https://opensource.org/licenses/BSD-3-Clause
#
# This example illustrates how to extract table names from nested
# SELECT statements.
#
# See:
# https://groups.google.com/forum/#!forum/sqlparse/browse_thread/thread/b0bd9a022e9d4895

import sqlparse
from sqlparse.sql import IdentifierList, Identifier
from sqlparse.tokens import Keyword, DML


def extract_select_part(parsed):
    select_seen = False
    for item in parsed.tokens:
        if item.ttype is Keyword and item.value.upper() == 'FROM':
            return
        if select_seen:
            yield item
        if item.ttype is DML and item.value.upper() == 'SELECT':
            select_seen = True


def extract_column_identifiers(token_stream):
    for item in token_stream:
        if isinstance(item, IdentifierList):
            for identifier in item.get_identifiers():
                yield identifier.get_name()
        elif isinstance(item, Identifier):
            yield item.get_name()


def extract_columns(sql):
    stream = extract_select_part(sqlparse.parse(sql)[0])
    return list(extract_column_identifiers(stream))


if __name__ == '__main__':
    sql = """
    WITH schema AS (
        SELECT a, b, c, d
        FROM schema
    )
    SELECT ALL t0_as_b, `t1_as_c` AS "t1 as c", COUNT(*) AS "count"
    FROM (
        SELECT ALL `t0_as_b`, max(`t1_as_c`) AS `t1_as_c`, max(`t2 d as d`) AS `t2 d as d`
        FROM (
            SELECT a, b AS `t0_as_b`
            FROM schema
        ) t0
            INNER JOIN (
                SELECT a, c AS "t1_as_c"
                FROM schema
            ) t1
            ON t0.a = t1.a
            INNER JOIN (
                SELECT a, d AS 't2 d as d'
                FROM schema
            ) t2
            ON t0.a = t2.a
        WHERE 1 = 1
        GROUP BY a, `t0_as_b`
    ) "virtual_table"
    GROUP BY `t0_as_b`, `t1_as_c`
    ORDER BY `t1_as_c` DESC
    LIMIT 1000;
    """

    columns = ', '.join(extract_columns(sql))
    print('Columns: {}'.format(columns))
    # >>> [Output]:
    # >>> Columns: t0_as_b, t1 as c, count
