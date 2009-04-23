#!/usr/bin/env python

# Example for retrieving column definitions from a CREATE statement
# using low-level functions.

import sqlparse

SQL = """CREATE TABLE foo (
  id integer primary key,
  title varchar(200) not null,
  description text
);"""


parsed = sqlparse.parse(SQL)[0]

# extract the parenthesis which holds column definitions
par = parsed.token_next_by_instance(0, sqlparse.sql.Parenthesis)


def extract_definitions(token_list):
    # assumes that token_list is a parenthesis
    definitions = []
    # grab the first token, ignoring whitespace
    token = token_list.token_next(0)
    tmp = []
    while token and not token.match(sqlparse.tokens.Punctuation, ')'):
        tmp.append(token)
        idx = token_list.token_index(token)
        # grab the next token, this times including whitespace
        token = token_list.token_next(idx, skip_ws=False)
        # split on ","
        if (token is not None  # = end of statement
            and token.match(sqlparse.tokens.Punctuation, ',')):
            definitions.append(tmp)
            tmp = []
            idx = token_list.token_index(token)
            token = token_list.token_next(idx)
    if tmp and isinstance(tmp[0], sqlparse.sql.Identifier):
        definitions.append(tmp)
    return definitions


columns = extract_definitions(par)

for column in columns:
    print 'NAME: %-12s DEFINITION: %s' % (column[0],
                                         ''.join(str(t) for t in column[1:]))
