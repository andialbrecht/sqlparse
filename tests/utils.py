# -*- coding: utf-8 -*-

"""Helpers for testing."""

import difflib
import io
import os
import unittest

from sqlparse.utils import split_unquoted_newlines
from sqlparse.compat import StringIO

DIR_PATH = os.path.dirname(__file__)
FILES_DIR = os.path.join(DIR_PATH, 'files')


def load_file(filename, encoding='utf-8'):
    """Opens filename with encoding and return its contents."""
    with io.open(os.path.join(FILES_DIR, filename), encoding=encoding) as f:
        return f.read()


class TestCaseBase(unittest.TestCase):
    """Base class for test cases with some additional checks."""

    # Adopted from Python's tests.
    def ndiffAssertEqual(self, first, second):
        """Like failUnlessEqual except use ndiff for readable output."""
        if first != second:
            # Using the built-in .splitlines() method here will cause incorrect
            # results when splitting statements that have quoted CR/CR+LF
            # characters.
            sfirst = split_unquoted_newlines(first)
            ssecond = split_unquoted_newlines(second)
            diff = difflib.ndiff(sfirst, ssecond)

            fp = StringIO()
            fp.write('\n')
            fp.write('\n'.join(diff))

            raise self.failureException(fp.getvalue())
