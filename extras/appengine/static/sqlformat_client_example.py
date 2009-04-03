#!/usr/bin/env python

import urllib
import urllib2

payload = (
    ('data', 'select * from foo join bar on val1 = val2 where id = 123;'),
    ('format', 'text'),
    ('keyword_case', 'upper'),
    ('reindent', True),
    ('n_indents', 2),
    )

response = urllib2.urlopen('http://sqlformat.appspot.com/format/',
                           urllib.urlencode(payload))
print response.read()

