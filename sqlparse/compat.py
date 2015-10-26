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
    text_type = str
    string_types = (str,)
    from io import StringIO

    def u(s):
        return str(s)

elif PY2:
    text_type = unicode
    string_types = (basestring,)
    from StringIO import StringIO  # flake8: noqa

    def u(s):
        return unicode(s)


# Directly copied from six:
def with_metaclass(meta, *bases):
    """Create a base class with a metaclass."""
    # This requires a bit of explanation: the basic idea is to make a dummy
    # metaclass for one level of class instantiation that replaces itself with
    # the actual metaclass.
    class metaclass(meta):
        def __new__(cls, name, this_bases, d):
            return meta(name, bases, d)
    return type.__new__(metaclass, 'temporary_class', (), {})
