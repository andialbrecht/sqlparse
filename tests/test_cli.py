import subprocess
import sys

import pytest

import sqlparse


def test_cli_main_empty():
    with pytest.raises(SystemExit):
        sqlparse.cli.main([])


@pytest.mark.parametrize('option', ['comma_first', 'compact'])
@pytest.mark.parametrize('value, expected', [
    ('True', True), ('true', True), ('TRUE', True), ('1', True),
    ('False', False), ('false', False), ('FALSE', False), ('0', False),
])
def test_parser_boolean_values(option, value, expected):
    parser = sqlparse.cli.create_parser()
    args = parser.parse_args(['-', '--' + option, value])
    assert getattr(args, option) is expected


@pytest.mark.parametrize('option', ['comma_first', 'compact'])
def test_parser_boolean_default(option):
    args = sqlparse.cli.create_parser().parse_args(['-'])
    assert getattr(args, option) is False


@pytest.mark.parametrize('option', ['comma_first', 'compact'])
@pytest.mark.parametrize('value', ['xxx', '2', ''])
def test_parser_boolean_invalid(option, value, capsys):
    with pytest.raises(SystemExit) as exc:
        sqlparse.cli.create_parser().parse_args(['-', '--' + option, value])
    assert exc.value.code == 2
    out, err = capsys.readouterr()
    assert out == ''
    assert '--' + option in err
    assert 'expected true, false, 1 or 0' in err


@pytest.mark.parametrize('option, sql, normal, enabled', [
    ('comma_first', 'select a, b from foo',
     'select a,\n       b\nfrom foo', 'select a\n     , b\nfrom foo'),
    ('compact', 'case when foo then 1 else bar end',
     'case\n    when foo then 1\n    else bar\nend',
     'case when foo then 1 else bar end'),
])
@pytest.mark.parametrize('value', [None, 'False', '0', 'True', '1'])
def test_cli_boolean_formatting(option, sql, normal, enabled, value):
    cmd = [sys.executable, '-m', 'sqlparse', '-', '--reindent']
    if value is not None:
        cmd.extend(['--' + option, value])
    result = subprocess.run(cmd, input=sql, capture_output=True, text=True)
    assert result.returncode == 0
    assert result.stderr == ''
    assert result.stdout == (enabled if value in ('True', '1') else normal)


def test_parser_empty():
    with pytest.raises(SystemExit):
        parser = sqlparse.cli.create_parser()
        parser.parse_args([])


def test_main_help():
    # Call with the --help option as a basic sanity check.
    with pytest.raises(SystemExit) as exinfo:
        sqlparse.cli.main(["--help", ])
    assert exinfo.value.code == 0


def test_valid_args(filepath):
    # test doesn't abort
    path = filepath('function.sql')
    assert sqlparse.cli.main([path, '-r']) is not None


def test_invalid_choice(filepath):
    path = filepath('function.sql')
    with pytest.raises(SystemExit):
        sqlparse.cli.main([path, '-l', 'Spanish'])


def test_invalid_args(filepath, capsys):
    path = filepath('function.sql')
    sqlparse.cli.main([path, '-r', '--indent_width', '0'])
    _, err = capsys.readouterr()
    assert err == ("[ERROR] Invalid options: indent_width requires "
                   "a positive integer\n")


def test_invalid_infile(filepath, capsys):
    path = filepath('missing.sql')
    sqlparse.cli.main([path, '-r'])
    _, err = capsys.readouterr()
    assert err[:22] == "[ERROR] Failed to read"


def test_invalid_outfile(filepath, capsys):
    path = filepath('function.sql')
    outpath = filepath('/missing/function.sql')
    sqlparse.cli.main([path, '-r', '-o', outpath])
    _, err = capsys.readouterr()
    assert err[:22] == "[ERROR] Failed to open"


def test_stdout(filepath, load_file, capsys):
    path = filepath('begintag.sql')
    expected = load_file('begintag.sql')
    sqlparse.cli.main([path])
    out, _ = capsys.readouterr()
    assert out == expected


def test_script():
    # Call with the --help option as a basic sanity check.
    cmd = [sys.executable, '-m', 'sqlparse.cli', '--help']
    assert subprocess.call(cmd) == 0


@pytest.mark.parametrize('fpath, encoding', (
    ('encoding_utf8.sql', 'utf-8'),
    ('encoding_gbk.sql', 'gbk'),
))
def test_encoding_stdout(fpath, encoding, filepath, load_file, capfd):
    path = filepath(fpath)
    expected = load_file(fpath, encoding)
    sqlparse.cli.main([path, '--encoding', encoding])
    out, _ = capfd.readouterr()
    assert out == expected


@pytest.mark.parametrize('fpath, encoding', (
    ('encoding_utf8.sql', 'utf-8'),
    ('encoding_gbk.sql', 'gbk'),
))
def test_encoding_output_file(fpath, encoding, filepath, load_file, tmpdir):
    in_path = filepath(fpath)
    expected = load_file(fpath, encoding)
    out_path = tmpdir.dirname + '/encoding_out.sql'
    sqlparse.cli.main([in_path, '--encoding', encoding, '-o', out_path])
    out = load_file(out_path, encoding)
    assert out == expected


@pytest.mark.parametrize('fpath, encoding', (
    ('encoding_utf8.sql', 'utf-8'),
    ('encoding_gbk.sql', 'gbk'),
))
def test_encoding_stdin(fpath, encoding, filepath, load_file, capfd):
    path = filepath(fpath)
    expected = load_file(fpath, encoding)
    old_stdin = sys.stdin
    with open(path) as f:
        sys.stdin = f
        sqlparse.cli.main(['-', '--encoding', encoding])
    sys.stdin = old_stdin
    out, _ = capfd.readouterr()
    assert out == expected


def test_encoding(filepath, capsys):
    path = filepath('test_cp1251.sql')
    expected = 'insert into foo values (1); -- Песня про надежду\n'
    sqlparse.cli.main([path, '--encoding=cp1251'])
    out, _ = capsys.readouterr()
    assert out == expected


def test_cli_multiple_files_with_inplace(tmpdir):
    """Test CLI with multiple files and --in-place flag."""
    # Create test files
    file1 = tmpdir.join("test1.sql")
    file1.write("select   *   from   foo")
    file2 = tmpdir.join("test2.sql")
    file2.write("select   *   from   bar")

    # Run sqlformat with --in-place
    result = sqlparse.cli.main([str(file1), str(file2), '--in-place', '--reindent'])

    assert result == 0
    # Files should be modified in-place
    assert "select" in file1.read()
    assert "select" in file2.read()


def test_cli_multiple_files_without_inplace_fails(tmpdir, capsys):
    """Test that multiple files require --in-place flag."""
    file1 = tmpdir.join("test1.sql")
    file1.write("select * from foo")
    file2 = tmpdir.join("test2.sql")
    file2.write("select * from bar")

    result = sqlparse.cli.main([str(file1), str(file2)])

    assert result != 0  # Should fail
    _, err = capsys.readouterr()
    assert "Multiple files require --in-place flag" in err


def test_cli_inplace_with_stdin_fails(capsys):
    """Test that --in-place flag cannot be used with stdin."""
    result = sqlparse.cli.main(['-', '--in-place'])
    assert result != 0  # Should fail
    _, err = capsys.readouterr()
    assert "Cannot use --in-place with stdin" in err


def test_cli_outfile_with_multiple_files_fails(tmpdir, capsys):
    """Test that -o cannot be used with multiple files."""
    file1 = tmpdir.join("test1.sql")
    file1.write("select * from foo")
    file2 = tmpdir.join("test2.sql")
    file2.write("select * from bar")
    out = tmpdir.join("out.sql")

    result = sqlparse.cli.main([str(file1), str(file2), '-o', str(out)])
    assert result != 0  # Should fail
    _, err = capsys.readouterr()
    assert "Cannot use -o/--outfile with multiple files" in err


def test_cli_single_file_inplace(tmpdir):
    """Test --in-place flag with a single file."""
    test_file = tmpdir.join("test.sql")
    test_file.write("select   *   from   foo")

    result = sqlparse.cli.main([str(test_file), '--in-place', '--keywords', 'upper'])

    assert result == 0
    content = test_file.read()
    assert "SELECT" in content


def test_cli_error_handling_continues(tmpdir, capsys):
    """Test that errors in one file don't stop processing of others."""
    file1 = tmpdir.join("test1.sql")
    file1.write("select * from foo")
    # file2 doesn't exist - it will cause an error
    file3 = tmpdir.join("test3.sql")
    file3.write("select * from baz")

    result = sqlparse.cli.main([str(file1), str(tmpdir.join("nonexistent.sql")),
                               str(file3), '--in-place'])

    # Should return error code but still process valid files
    assert result != 0
    assert "select * from foo" in file1.read()
    assert "select * from baz" in file3.read()
    _, err = capsys.readouterr()
    assert "Failed to read" in err
