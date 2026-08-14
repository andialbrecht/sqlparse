import pytest
import sqlparse
from sqlparse.engine import grouping, set_max_grouping_tokens
from sqlparse.exceptions import SQLParseError


@pytest.fixture
def restore_grouping_token_limit():
    original = grouping.MAX_GROUPING_TOKENS
    try:
        yield
    finally:
        set_max_grouping_tokens(original)


def test_set_max_grouping_tokens_changes_grouping_limit(
    restore_grouping_token_limit,
):
    set_max_grouping_tokens(1)

    with pytest.raises(SQLParseError, match="Maximum number of tokens exceeded"):
        sqlparse.parse("SELECT 1")


def test_set_max_grouping_tokens_can_disable_limit(restore_grouping_token_limit):
    set_max_grouping_tokens(None)

    statements = sqlparse.parse("SELECT 1")

    assert len(statements) == 1


@pytest.mark.parametrize("limit", [0, -1, 1.5, "10", True])
def test_set_max_grouping_tokens_rejects_invalid_values(
    restore_grouping_token_limit, limit
):
    with pytest.raises(ValueError, match="positive integer or None"):
        set_max_grouping_tokens(limit)
