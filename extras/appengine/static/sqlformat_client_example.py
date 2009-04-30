#!/usr/bin/env python

import urllib
import urllib2

REMOTE_API = 'http://sqlformat.appspot.com/format/'
REMOTE_API = 'http://127.0.0.1:8080/format/'

payload = (
    ('data', 'select * from foo join bar on val1 = val2 where id = 123;'),
    ('format', 'text'),
    ('keyword_case', 'upper'),
    ('reindent', True),
    ('n_indents', 2),
    )

response = urllib2.urlopen(REMOTE_API,
                           urllib.urlencode(payload))
print response.read()

