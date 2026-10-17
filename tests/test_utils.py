import pytest

from sqlparse import utils


@pytest.mark.parametrize('value, expected', (
    [None, None],
    ['\'foo\'', 'foo'],
    ['"foo"', 'foo'],
    ['`foo`', 'foo']))
def test_remove_quotes(value, expected):
    assert utils.remove_quotes(value) == expected


@pytest.mark.parametrize('quote', ["'", '"'])
@pytest.mark.parametrize('newline', ['\n', '\r', '\r\n'])
@pytest.mark.parametrize('backslashes', [1, 2])
def test_split_unquoted_newlines_after_backslash(quote, newline, backslashes):
    quoted = (quote + 'a' + '\\' * backslashes + newline
              + 'b  \r\nc' + quote)
    text = 'SELECT\r\n' + quoted + '\rFROM t'

    assert utils.split_unquoted_newlines(text) == ['SELECT', quoted, 'FROM t']
