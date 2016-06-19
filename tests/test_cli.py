# -*- coding: utf-8 -*-

import subprocess
import sys

import pytest

import sqlparse


def test_cli_main_empty():
    with pytest.raises(SystemExit):
        sqlparse.cli.main([])


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


def test_script():
    # Call with the --help option as a basic sanity check.
    cmd = "{0:s} -m sqlparse.cli --help".format(sys.executable)
    assert subprocess.call(cmd.split()) == 0
