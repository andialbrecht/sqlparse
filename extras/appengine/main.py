# SQLFormat's main script, dead simple :)

import os
import sys

LIB_DIR = os.path.join(os.path.dirname(__file__), 'lib')

if LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)

from sqlformat import app

import config

import logging
from google.appengine.ext import ereporter

ereporter.register_logger()


class EreporterMiddleware(object):

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        try:
            return self.app(environ, start_response)
        except:
            logging.exception('Exception in request:')
            logging.debug(environ)
            raise


app.config.from_object(config)

app = EreporterMiddleware(app)
