import sqlparse


def test_reindent_aligned_malformed_case_does_not_crash():
    sql = "CASE 'a' := WHERE END SELECT GO # ->>"

    formatted = sqlparse.format(sql, reindent_aligned=True)

    assert isinstance(formatted, str)
    assert "CASE" in formatted
    assert "END" in formatted
    assert "SELECT" in formatted
