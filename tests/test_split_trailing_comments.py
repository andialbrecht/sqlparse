import sqlparse


def test_split_keeps_trailing_block_comment_with_statement():
    sql = "SELECT 1; /* trailing */\nSELECT 2;"

    assert sqlparse.split(sql) == [
        "SELECT 1; /* trailing */",
        "SELECT 2;",
    ]


def test_split_trailing_comments_are_consistent():
    block = "SELECT 1; /* trailing */\nSELECT 2;"
    line = "SELECT 1; -- trailing\nSELECT 2;"

    assert sqlparse.split(block)[0] == "SELECT 1; /* trailing */"
    assert sqlparse.split(line)[0] == "SELECT 1; -- trailing"
