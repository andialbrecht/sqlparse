from sqlparse import lexer
from sqlparse import tokens as T


def test_escaped_backslashes_single_quoted_token_stream():
    tokens = list(lexer.tokenize(r"SELECT '\\', '\\'"))

    assert tokens == [
        (T.Keyword.DML, "SELECT"),
        (T.Whitespace, " "),
        (T.String.Single, r"'\\'"),
        (T.Punctuation, ","),
        (T.Whitespace, " "),
        (T.String.Single, r"'\\'"),
    ]


def test_escaped_backslashes_double_quoted_token_stream():
    tokens = list(lexer.tokenize(r'SELECT "\\", "\\"'))

    assert tokens == [
        (T.Keyword.DML, "SELECT"),
        (T.Whitespace, " "),
        (T.String.Symbol, r'"\\"'),
        (T.Punctuation, ","),
        (T.Whitespace, " "),
        (T.String.Symbol, r'"\\"'),
    ]
