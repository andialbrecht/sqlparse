"""Tests for DoS prevention mechanisms in sqlparse."""

import pytest
import sqlparse
from sqlparse.exceptions import SQLParseError
import time


class TestDoSPrevention:
    """Test cases to ensure sqlparse is protected against DoS attacks."""

    def test_large_tuple_list_performance(self):
        """Test that parsing a large list of tuples raises SQLParseError."""
        # Generate SQL with many tuples (like Django composite primary key queries)
        sql = '''
        SELECT "composite_pk_comment"."tenant_id", "composite_pk_comment"."comment_id"
        FROM "composite_pk_comment"
        WHERE ("composite_pk_comment"."tenant_id", "composite_pk_comment"."comment_id") IN ('''

        # Generate 5000 tuples - this should trigger MAX_GROUPING_TOKENS
        tuples = []
        for i in range(1, 5001):
            tuples.append(f"(1, {i})")

        sql += ", ".join(tuples) + ")"

        # Should raise SQLParseError due to token limit
        with pytest.raises(SQLParseError, match="Maximum number of tokens exceeded"):
            sqlparse.format(sql, reindent=True, keyword_case="upper")

    def test_deeply_nested_groups_limited(self):
        """Test that deeply nested groups raise SQLParseError."""
        # Create deeply nested parentheses
        sql = "SELECT " + "(" * 200 + "1" + ")" * 200

        # Should raise SQLParseError due to depth limit
        with pytest.raises(SQLParseError, match="Maximum grouping depth exceeded"):
            sqlparse.format(sql, reindent=True)

    def test_very_large_token_list_limited(self):
        """Test that very large token lists raise SQLParseError."""
        # Create a SQL with many identifiers
        identifiers = []
        for i in range(15000):  # More than MAX_GROUPING_TOKENS
            identifiers.append(f"col{i}")

        sql = f"SELECT {', '.join(identifiers)} FROM table1"

        # Should raise SQLParseError due to token limit
        with pytest.raises(SQLParseError, match="Maximum number of tokens exceeded"):
            sqlparse.format(sql, reindent=True)

    def test_nested_paren_within_cap_under_1s(self):
        """Reaching MAX_GROUPING_DEPTH must not require multi-second CPU.

        Before the TokenList.__init__ fix, a 1 KB payload of 500 nested
        parens took ~1.3 s and a 2 KB payload of 1000 nested parens took
        ~11 s before the depth cap raised SQLParseError, because each
        TokenList materialised its ``value`` via ``str(self)`` which
        recursed over the full subtree (O(n * depth)).
        """
        sql = 'SELECT ' + '(' * 1000 + '1' + ')' * 1000
        t0 = time.perf_counter()
        with pytest.raises(SQLParseError, match='Maximum grouping depth'):
            sqlparse.parse(sql)
        dt = time.perf_counter() - t0
        assert dt < 1.0, f'parse took {dt:.2f}s, expected sub-second'

    def test_nested_case_within_cap_under_1s(self):
        """Same invariant as nested parentheses, exercised via CASE WHEN."""
        case = '1'
        for i in range(400):
            case = f'CASE WHEN x={i} THEN {case} ELSE NULL END'
        sql = f'SELECT {case} FROM t'
        t0 = time.perf_counter()
        with pytest.raises(SQLParseError, match='Maximum grouping depth'):
            sqlparse.parse(sql)
        dt = time.perf_counter() - t0
        assert dt < 1.0, f'parse took {dt:.2f}s, expected sub-second'

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
