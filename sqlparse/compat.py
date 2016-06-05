# -*- coding: utf-8 -*-
#
# Copyright (C) 2016 Andi Albrecht, albrecht.andi@gmail.com
#
# This module is part of python-sqlparse and is released under
# the BSD License: http://www.opensource.org/licenses/bsd-license.php

"""Python 2/3 compatibility.

This module only exists to avoid a dependency on six
for very trivial stuff. We only need to take care of
string types, buffers and metaclasses.

Parts of the code is copied directly from six:
https://bitbucket.org/gutworth/six
"""

import sys

PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3

if PY3:
    def u(s, encoding=None):
        return str(s)


    def unicode_compatible(cls):
        return cls


    text_type = str
    string_types = (str,)
    from io import StringIO


elif PY2:
    def u(s, encoding=None):
        encoding = encoding or 'unicode-escape'
        try:
            return unicode(s)
        except UnicodeDecodeError:
            return unicode(s, encoding)


    def unicode_compatible(cls):
        cls.__unicode__ = cls.__str__
        cls.__str__ = lambda x: x.__unicode__().encode('utf-8')
        return cls


    text_type = unicode
    string_types = (str, unicode,)
    from StringIO import StringIO
