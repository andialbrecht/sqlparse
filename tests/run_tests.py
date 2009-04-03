#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Test runner for sqlparse."""

import os
import sys
import unittest

sys.path.insert(1, os.path.join(os.path.dirname(__file__), '../'))


def main():
    """Create a TestSuite and run it."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    fnames = [os.path.split(f)[-1] for f in sys.argv[1:]]
    for fname in os.listdir(os.path.dirname(__file__)):
        if (not fname.startswith('test_') or not fname.endswith('.py')
            or (fnames and fname not in fnames)):
            continue
        modname = os.path.splitext(fname)[0]
        mod = __import__(os.path.splitext(fname)[0])
        suite.addTests(loader.loadTestsFromModule(mod))
    unittest.TextTestRunner(verbosity=2).run(suite)




if __name__ == '__main__':
    main()
