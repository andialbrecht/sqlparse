#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Test runner for sqlparse."""

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


def main(args):
    """Create a TestSuite and run it."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    fnames = [os.path.split(f)[-1] for f in args]
    for fname in os.listdir(os.path.dirname(__file__)):
        if (not fname.startswith('test_') or not fname.endswith('.py')
            or (fnames and fname not in fnames)):
            continue
        modname = os.path.splitext(fname)[0]
        mod = __import__(os.path.splitext(fname)[0])
        suite.addTests(loader.loadTestsFromModule(mod))
    unittest.TextTestRunner(verbosity=2).run(suite)




if __name__ == '__main__':
    opts, args = parser.parse_args()
    if opts.profile:
        import hotshot
        prof = hotshot.Profile("sqlparse.prof")
        prof.runcall(main, args)
        prof.close()
    else:
        main(args)
