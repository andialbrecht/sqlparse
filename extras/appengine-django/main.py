# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Main program for Rietveld.

This is also a template for running a Django app under Google App
Engine, especially when using a newer version of Django than provided
in the App Engine standard library.

The site-specific code is all in other files: urls.py, models.py,
views.py, settings.py.
"""

# Standard Python imports.
import os
import sys
import logging
import traceback


# Log a message each time this module get loaded.
logging.info('Loading %s, app version = %s',
             __name__, os.getenv('CURRENT_VERSION_ID'))

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

from google.appengine.dist import use_library
use_library('django', '1.2')

# Fail early if we can't import Django.  Log identifying information.
import django
logging.info('django.__file__ = %r, django.VERSION = %r',
             django.__file__, django.VERSION)
assert django.VERSION[0] >= 1, "This Django version is too old"

# AppEngine imports.
from google.appengine.ext.webapp import util
from google.appengine.api import mail


# Helper to enter the debugger.  This passes in __stdin__ and
# __stdout__, because stdin and stdout are connected to the request
# and response streams.  You must import this from __main__ to use it.
# (I tried to make it universally available via __builtin__, but that
# doesn't seem to work for some reason.)
def BREAKPOINT():
  import pdb
  p = pdb.Pdb(None, sys.__stdin__, sys.__stdout__)
  p.set_trace()


# Custom Django configuration.
from django.conf import settings
settings._target = None

# Import various parts of Django.
import django.core.handlers.wsgi
import django.core.signals
import django.db
import django.dispatch.dispatcher
import django.forms

# Work-around to avoid warning about django.newforms in djangoforms.
django.newforms = django.forms


def log_exception(*args, **kwds):
  """Django signal handler to log an exception."""
  excinfo = sys.exc_info()
  cls, err = excinfo[:2]
  subject = 'Exception in request: %s: %s' % (cls.__name__, err)
  logging.exception(subject)
  try:
    repr_request = repr(kwds.get('request', 'Request not available.'))
  except:
    repr_request = 'Request repr() not available.'
  msg = ('Application: %s\nVersion: %s\n\n%s\n\n%s'
         % (os.getenv('APPLICATION_ID'), os.getenv('CURRENT_VERSION_ID'),
            '\n'.join(traceback.format_exception(*excinfo)),
            repr_request))
  mail.send_mail_to_admins('albrecht.andi@googlemail.com',
                           '[%s] %s' % (os.getenv('APPLICATION_ID'), subject),
                           msg)


# Log all exceptions detected by Django.
django.core.signals.got_request_exception.connect(log_exception)

# Unregister Django's default rollback event handler.
#django.core.signals.got_request_exception.disconnect(
#    django.db._rollback_on_exception)


def real_main():
  """Main program."""
  # Create a Django application for WSGI.
  application = django.core.handlers.wsgi.WSGIHandler()
  # Run the WSGI CGI handler with that application.
  util.run_wsgi_app(application)


def profile_main():
  """Main program for profiling."""
  import cProfile
  import pstats
  import StringIO

  prof = cProfile.Profile()
  prof = prof.runctx('real_main()', globals(), locals())
  stream = StringIO.StringIO()
  stats = pstats.Stats(prof, stream=stream)
  # stats.strip_dirs()  # Don't; too many modules are named __init__.py.
  stats.sort_stats('time')  # 'time', 'cumulative' or 'calls'
  stats.print_stats()  # Optional arg: how many to print
  # The rest is optional.
  # stats.print_callees()
  # stats.print_callers()
  print '\n<hr>'
  print '<h1>Profile</h1>'
  print '<pre>'
  print stream.getvalue()[:1000000]
  print '</pre>'

# Set this to profile_main to enable profiling.
main = real_main


if __name__ == '__main__':
  main()
