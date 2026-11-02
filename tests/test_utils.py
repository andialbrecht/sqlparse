import pytest

from sqlparse import utils


@pytest.mark.parametrize('value, expected', (
    [None, None],
    ['\'foo\'', 'foo'],
    ['"foo"', 'foo'],
    ['`foo`', 'foo']))
def test_remove_quotes(value, expected):
    assert utils.remove_quotes(value) == expected


@pytest.mark.parametrize('text, expected', [
    ('', ['']),
    ('select 1', ['select 1']),
    ('a\nb\r\nc\rd', ['a', 'b', 'c', 'd']),
    ('a\n', ['a', '']),
    # newlines inside quoted strings are kept
    ("select 'a\nb'\nfrom t", ["select 'a\nb'", 'from t']),
    ('select "a\r\nb"\nfrom t', ['select "a\r\nb"', 'from t']),
    # escaped quotes don't end a string
    ("'a\\'\nb'\nc", ["'a\\'\nb'", 'c']),
    ('"a\\"\nb"\nc', ['"a\\"\nb"', 'c']),
    # the other quote character doesn't end a string
    ("'a\"\nb'\nc", ["'a\"\nb'", 'c']),
    # an unterminated quote is plain text
    ("a'b\nc", ["a'b", 'c']),
    ('a"b\nc', ['a"b', 'c']),
    # a backslash before a newline doesn't escape it
    ("'a\\\nb'\nc", ["'a\\", "b'", 'c']),
])
def test_split_unquoted_newlines(text, expected):
    assert utils.split_unquoted_newlines(text) == expected
