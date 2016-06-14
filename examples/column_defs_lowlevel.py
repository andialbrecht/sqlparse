#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2016 Andi Albrecht, albrecht.andi@gmail.com
#
# This example is part of python-sqlparse and is released under
# the BSD License: http://www.opensource.org/licenses/bsd-license.php
#
# Example for retrieving column definitions from a CREATE statement
# using low-level functions.

import sqlparse


def extract_definitions(token_list):
    # assumes that token_list is a parenthesis
    definitions = []
    tmp = []
    # grab the first token, ignoring whitespace. idx=1 to skip open (
    tidx, token = token_list.token_next(1)
    while token and not token.match(sqlparse.tokens.Punctuation, ')'):
        tmp.append(token)
        # grab the next token, this times including whitespace
        tidx, token = token_list.token_next(tidx, skip_ws=False)
        # split on ",", except when on end of statement
        if token and token.match(sqlparse.tokens.Punctuation, ','):
            definitions.append(tmp)
            tmp = []
            tidx, token = token_list.token_next(tidx)
    if tmp and isinstance(tmp[0], sqlparse.sql.Identifier):
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
        print('NAME: {name:10} DEFINITION: {definition}'.format(
            name=column[0], definition=''.join(str(t) for t in column[1:])))
