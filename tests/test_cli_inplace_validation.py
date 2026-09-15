import sqlparse


def test_invalid_options_do_not_truncate_inplace_file(tmpdir, capsys):
    path = tmpdir.join("query.sql")
    original = "select * from example\n"
    path.write(original)

    result = sqlparse.cli.main(
        [str(path), "--in-place", "--reindent", "--indent_width", "0"]
    )

    assert result == 1
    assert path.read() == original
    _, err = capsys.readouterr()
    assert "Invalid options" in err
