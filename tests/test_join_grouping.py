import sqlparse
from sqlparse import sql, tokens as T


def _significant_tokens(statement):
    return [token for token in statement.tokens if not token.is_whitespace]


def test_join_condition_not_grouped_with_comma_join():
    statement = sqlparse.parse(
        "select c1, c2, c3 "
        "from t1 left join t2 on t1.c1 = t2.c2, t3 "
        "where t1.c1 = t3.c3"
    )[0]
    tokens = _significant_tokens(statement)

    assert tokens[6].match(T.Keyword, "ON")
    assert isinstance(tokens[7], sql.Comparison)
    assert tokens[8].match(T.Punctuation, ",")
    assert isinstance(tokens[9], sql.Identifier)
    assert tokens[9].value == "t3"


def test_join_condition_with_and_not_grouped_with_comma_join():
    statement = sqlparse.parse(
        "select * from t1 left join t2 "
        "on t1.c1 = t2.c2 and t1.c2 = t2.c3, t3"
    )[0]
    tokens = _significant_tokens(statement)

    comma_idx = next(
        idx for idx, token in enumerate(tokens)
        if token.match(T.Punctuation, ",")
    )
    assert isinstance(tokens[comma_idx - 1], sql.Comparison)
    assert isinstance(tokens[comma_idx + 1], sql.Identifier)
    assert tokens[comma_idx + 1].value == "t3"


def test_comparison_expression_list_still_groups():
    statement = sqlparse.parse("select a = 1, b from t")[0]
    tokens = _significant_tokens(statement)

    assert isinstance(tokens[1], sql.IdentifierList)
