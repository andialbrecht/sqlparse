"""Tests for DoS prevention mechanisms in sqlparse."""

import pytest
import sqlparse
from sqlparse.exceptions import RecursionLimitError
import time


class TestDoSPrevention:
    """Test cases to ensure sqlparse is protected against DoS attacks."""

    def test_large_tuple_list_performance(self):
        """Test that parsing a large list of tuples doesn't cause DoS."""
        # Generate SQL with many tuples (like Django composite primary key queries)
        sql = '''
        SELECT "composite_pk_comment"."tenant_id", "composite_pk_comment"."comment_id"
        FROM "composite_pk_comment"
        WHERE ("composite_pk_comment"."tenant_id", "composite_pk_comment"."comment_id") IN ('''

        # Generate 5000 tuples - this would previously cause a hang
        tuples = []
        for i in range(1, 5001):
            tuples.append(f"(1, {i})")

        sql += ", ".join(tuples) + ")"

        # Test should complete quickly (under 5 seconds)
        start_time = time.time()
        result = sqlparse.format(sql, reindent=True, keyword_case="upper")
        execution_time = time.time() - start_time

        assert execution_time < 5.0, f"Parsing took too long: {execution_time:.2f}s"
        assert len(result) > 0, "Result should not be empty"
        assert "SELECT" in result.upper(), "SQL should be properly formatted"

    def test_deeply_nested_groups_limited(self):
        """Test that deeply nested groups raise RecursionLimitError."""
        # Create deeply nested parentheses (exceeds MAX_GROUPING_DEPTH of 100)
        sql = "SELECT " + "(" * 200 + "1" + ")" * 200

        # Should raise RecursionLimitError, not RecursionError
        with pytest.raises(RecursionLimitError) as exc_info:
            sqlparse.format(sql, reindent=True)

        assert "Maximum grouping depth exceeded" in str(exc_info.value)

    def test_very_large_token_list_limited(self):
        """Test that very large token lists raise RecursionLimitError."""
        # Create a SQL with many identifiers (exceeds MAX_GROUPING_TOKENS of 10000)
        identifiers = []
        for i in range(15000):  # More than MAX_GROUPING_TOKENS
            identifiers.append(f"col{i}")

        sql = f"SELECT {', '.join(identifiers)} FROM table1"

        # Should raise RecursionLimitError
        with pytest.raises(RecursionLimitError) as exc_info:
            sqlparse.format(sql, reindent=True)

        assert "Maximum token count exceeded" in str(exc_info.value)

    def test_normal_sql_still_works(self):
        """Test that normal SQL still works correctly after DoS protections."""
        sql = """
        SELECT u.id, u.name, p.title
        FROM users u
        JOIN posts p ON u.id = p.user_id
        WHERE u.active = 1
        AND p.published_at > '2023-01-01'
        ORDER BY p.published_at DESC
        """

        result = sqlparse.format(sql, reindent=True, keyword_case="upper")

        assert "SELECT" in result
        assert "FROM" in result
        assert "JOIN" in result
        assert "WHERE" in result
        assert "ORDER BY" in result

    def test_reasonable_tuple_list_works(self):
        """Test that reasonable-sized tuple lists still work correctly."""
        sql = '''
        SELECT id FROM table1
        WHERE (col1, col2) IN ('''

        # 100 tuples should work fine
        tuples = []
        for i in range(1, 101):
            tuples.append(f"({i}, {i * 2})")

        sql += ", ".join(tuples) + ")"

        result = sqlparse.format(sql, reindent=True, keyword_case="upper")

        assert "SELECT" in result
        assert "WHERE" in result
        assert "IN" in result
        assert "1," in result  # First tuple should be there
        assert "200" in result  # Last tuple should be there

    def test_reasonable_nesting_works(self):
        """Test that reasonable nesting depth still works."""
        # Create 50 nested parentheses (well under MAX_GROUPING_DEPTH of 100)
        sql = "SELECT " + "(" * 50 + "1" + ")" * 50

        result = sqlparse.format(sql, reindent=True)
        assert "SELECT" in result
        assert "1" in result

    def test_exception_can_be_caught(self):
        """Test that RecursionLimitError can be caught and handled."""
        sql = "SELECT " + "(" * 200 + "1" + ")" * 200

        try:
            sqlparse.format(sql, reindent=True)
            assert False, "Should have raised RecursionLimitError"
        except RecursionLimitError as e:
            # Verify exception has useful information
            assert "Maximum grouping depth exceeded" in str(e)
            assert "100" in str(e)  # The limit value
            assert "complex or deeply nested" in str(e)
