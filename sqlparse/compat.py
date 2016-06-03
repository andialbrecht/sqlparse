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


    text_type = unicode
    string_types = (basestring,)
    from StringIO import StringIO
