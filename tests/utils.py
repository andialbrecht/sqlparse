# -*- coding: utf-8 -*-

"""Helpers for testing."""

import codecs
import difflib
import os
import unittest
from StringIO import StringIO

NL = '\n'
DIR_PATH = os.path.abspath(os.path.dirname(__file__))
PARENT_DIR = os.path.dirname(DIR_PATH)
FILES_DIR = os.path.join(DIR_PATH, 'files')


def load_file(filename, encoding='utf-8'):
    """Opens filename with encoding and return it's contents."""
    f = codecs.open(os.path.join(FILES_DIR, filename), 'r', encoding)
    data = f.read()
    f.close()
    return data


class TestCaseBase(unittest.TestCase):
    """Base class for test cases with some additional checks."""

    # Adopted from Python's tests.
    def ndiffAssertEqual(self, first, second):
        """Like failUnlessEqual except use ndiff for readable output."""
        if first <> second:
            sfirst = unicode(first)
            ssecond = unicode(second)
            diff = difflib.ndiff(sfirst.splitlines(), ssecond.splitlines())
            fp = StringIO()
            print >> fp, NL, NL.join(diff)
            print fp.getvalue()
            raise self.failureException, fp.getvalue()
