from typing import List, Optional, Tuple, Type, Union

from sqlparse import parse
from sqlparse.sql import Identifier, IdentifierList, Statement, Token
from sqlparse.tokens import (
    CTE,
    DML,
    Comparison,
    Keyword,
    Number,
    _TokenType as TokenType,
)


def itertokens(token: Token):
    yield token
    if token.is_group:
        for child in token.tokens:
            yield from itertokens(child)


# allow matching by Token subclass or ttype
TokenClassOrType = Union[TokenType, Type[Token]]


def parsed_tokens_with_sources(
    sql: str, types: Tuple[TokenClassOrType, ...]
) -> List[Tuple[TokenClassOrType, str, str]]:
    # given a query, parses it, iterates over all the tokens it contains, and
    # for each token that matches `types`, returns a tuple of the matched token
    # type, the token's value, and the source of the token retrieved by slicing
    # into the original query using the token's `pos` and `length` attributes

    def matches(token: Token) -> Optional[TokenClassOrType]:
        for class_or_type in types:
            if isinstance(class_or_type, TokenType):
                if token.ttype is class_or_type:
                    return class_or_type
            elif isinstance(token, class_or_type):
                return class_or_type

    def get_source(token: Token) -> str:
        return sql[token.pos : token.pos + token.length]

    statements = parse(sql)
    return [
        (match, token.value, get_source(token))
        for statement in statements
        for token in itertokens(statement)
        if (match := matches(token))
    ]


def test_simple_query():
    assert parsed_tokens_with_sources(
        "select * from foo;", (DML, Identifier, Keyword, Statement)
    ) == [
        (Statement, "select * from foo;", "select * from foo;"),
        (DML, "select", "select"),
        (Keyword, "from", "from"),
        (Identifier, "foo", "foo"),
    ]


def test_multiple_statements():
    stmt1 = "select * from foo;"
    stmt2 = "\nselect *\nfrom bar;"
    assert parsed_tokens_with_sources(
        stmt1 + stmt2, (DML, Identifier, Keyword, Statement)
    ) == [
        (Statement, stmt1, stmt1),
        (DML, "select", "select"),
        (Keyword, "from", "from"),
        (Identifier, "foo", "foo"),
        (Statement, stmt2, stmt2),
        (DML, "select", "select"),
        (Keyword, "from", "from"),
        (Identifier, "bar", "bar"),
    ]


def test_subselect():
    stmt = """select a0, b0, c0, d0, e0 from
           (select * from dual) q0 where 1=1 and 2=2"""
    assert parsed_tokens_with_sources(
        stmt,
        (
            DML,
            Comparison,
            Identifier,
            IdentifierList,
            Keyword,
            Number.Integer,
            Statement,
        ),
    ) == [
        (Statement, stmt, stmt),
        (DML, "select", "select"),
        (IdentifierList, "a0, b0, c0, d0, e0", "a0, b0, c0, d0, e0"),
        (Identifier, "a0", "a0"),
        (Identifier, "b0", "b0"),
        (Identifier, "c0", "c0"),
        (Identifier, "d0", "d0"),
        (Identifier, "e0", "e0"),
        (Keyword, "from", "from"),
        (Identifier, "(select * from dual) q0", "(select * from dual) q0"),
        (DML, "select", "select"),
        (Keyword, "from", "from"),
        (Identifier, "dual", "dual"),
        (Identifier, "q0", "q0"),
        (Keyword, "where", "where"),
        (Number.Integer, "1", "1"),
        (Comparison, "=", "="),
        (Number.Integer, "1", "1"),
        (Keyword, "and", "and"),
        (Number.Integer, "2", "2"),
        (Comparison, "=", "="),
        (Number.Integer, "2", "2"),
    ]


def test_cte():
    stmt = """WITH foo AS (SELECT 1, 2, 3)
              SELECT * FROM foo;"""
    assert parsed_tokens_with_sources(
        stmt, (CTE, DML, Identifier, Keyword, Statement)
    ) == [
        (Statement, stmt, stmt),
        (CTE, "WITH", "WITH"),
        (Identifier, "foo AS (SELECT 1, 2, 3)", "foo AS (SELECT 1, 2, 3)"),
        (Keyword, "AS", "AS"),
        (DML, "SELECT", "SELECT"),
        (DML, "SELECT", "SELECT"),
        (Keyword, "FROM", "FROM"),
        (Identifier, "foo", "foo"),
    ]
