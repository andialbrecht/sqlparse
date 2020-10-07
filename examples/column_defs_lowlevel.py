#!/usr/bin/env python
#
# Copyright (C) 2009-2020 the sqlparse authors and contributors
# <see AUTHORS file>
#
# This example is part of python-sqlparse and is released under
# the BSD License: https://opensource.org/licenses/BSD-3-Clause
#
# Example for retrieving column definitions from a CREATE statement
# using low-level functions.

import sqlparse


def extract_definitions(token_list):
    # assumes that token_list is a parenthesis
    definitions = []
    tmp = []
    par_level = 0
    for token in token_list.flatten():
        if token.is_whitespace:
            continue
        elif token.match(sqlparse.tokens.Punctuation, '('):
            par_level += 1
            continue
        if token.match(sqlparse.tokens.Punctuation, ')'):
            if par_level == 0:
                break
            else:
                par_level += 1
        elif token.match(sqlparse.tokens.Punctuation, ','):
            if tmp:
                definitions.append(tmp)
            tmp = []
        else:
            tmp.append(token)
    if tmp:
        definitions.append(tmp)
    return definitions


if __name__ == '__main__':
    SQL = """CREATE TABLE foo (
             id integer primary key,
             title varchar(200) not null,
             description text);"""

    parsed = sqlparse.parse(SQL)[0]

    # extract the parenthesis which holds column definitions
    _, par = parsed.token_next_by(i=sqlparse.sql.Parenthesis)
    columns = extract_definitions(par)

    for column in columns:
        print('NAME: {name!s:12} DEFINITION: {definition}'.format(
            name=column[0], definition=' '.join(str(t) for t in column[1:])))
