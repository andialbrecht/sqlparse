#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Test runner for sqlparse."""

import fnmatch
import optparse
import os
import sys
import unittest

test_mod = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
if test_mod not in sys.path:
    sys.path.insert(1, test_mod)


parser = optparse.OptionParser()
parser.add_option('-P', '--profile',
                  help='Create hotshot profile.',
                  action='store_true', default=False)


def _path_matches(path, *patterns):
    if not patterns:
        return True
    for pattern in patterns:
        if fnmatch.fnmatch(path, pattern):
            return True
    return False


def _collect_test_modules(base=None, *patterns):
    for root, dirnames, filenames in os.walk(os.path.dirname(__file__)):
        print root, filenames
        for fname in filenames:
            if not fname.endswith('.py'):
                continue
            elif not _path_matches(os.path.join(root, fname), *patterns):
                continue
            if not root in sys.path:
                sys.path.append(root)
            modname = os.path.splitext(fname)[0]
            yield __import__(modname)


def main(args):
    """Create a TestSuite and run it."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for mod in _collect_test_modules(*args):
        suite.addTests(loader.loadTestsFromModule(mod))
    return unittest.TextTestRunner(verbosity=2).run(suite)




if __name__ == '__main__':
    opts, args = parser.parse_args()
    if opts.profile:
        import hotshot
        prof = hotshot.Profile("sqlparse.prof")
        prof.runcall(main, args)
        prof.close()
    else:
        result = main(args)
    if not result.wasSuccessful():
        return_code = 1
    else:
        return_code = 0
    sys.exit(return_code)
