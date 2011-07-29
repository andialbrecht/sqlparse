#!/usr/bin/env python

"""Downloads required third-party modules."""

import os
import urllib2
import gzip
import tarfile
import tempfile
import shutil
import sys
from StringIO import StringIO

HERE = os.path.abspath(os.path.dirname(__file__))
LIB_DIR = os.path.join(HERE, 'lib')

PACKAGES = {
    'http://pypi.python.org/packages/source/F/Flask/Flask-0.7.2.tar.gz':
    [('Flask-0.7.2/flask', 'flask')],
    'http://pypi.python.org/packages/source/W/Werkzeug/Werkzeug-0.6.2.tar.gz':
    [('Werkzeug-0.6.2/werkzeug', 'werkzeug')],
    'http://pypi.python.org/packages/source/J/Jinja2/Jinja2-2.5.5.tar.gz':
    [('Jinja2-2.5.5/jinja2/', 'jinja2')],
    'http://pypi.python.org/packages/source/s/simplejson/simplejson-2.1.6.tar.gz':
    [('simplejson-2.1.6/simplejson', 'simplejson')],
    'http://pypi.python.org/packages/source/P/Pygments/Pygments-1.4.tar.gz':
    [('Pygments-1.4/pygments', 'pygments')],
}


def fetch_all():
    if not os.path.isdir(LIB_DIR):
        os.makedirs(LIB_DIR)
    for url, targets in PACKAGES.iteritems():
        if not _missing_targets(targets):
            continue
        sys.stdout.write(url)
        sys.stdout.flush()
        fetch(url, targets)
        sys.stdout.write(' done\n')
        sys.stdout.flush()


def fetch(url, targets):
    blob = urllib2.urlopen(url).read()
    gz = gzip.GzipFile(fileobj=StringIO(blob))
    tar = tarfile.TarFile(fileobj=gz)
    tmpdir = tempfile.mkdtemp()
    try:
        tar.extractall(tmpdir)
        for src, dest in targets:
            dest = os.path.join(LIB_DIR, dest)
            if os.path.isdir(dest):
                shutil.rmtree(dest)
            shutil.copytree(os.path.join(tmpdir, src), dest)
    finally:
        shutil.rmtree(tmpdir)


def _missing_targets(targets):
    for _, dest in targets:
        dest = os.path.join(LIB_DIR, dest)
        if not os.path.isdir(dest):
            return True
    return False


def link_sqlparse():
    if os.path.islink('sqlparse'):
        return
    elif os.path.exists('sqlparse'):
        shutil.rmtree('sqlparse')
    if hasattr(os, 'symlink'):
        os.symlink('../../sqlparse', 'sqlparse')
    else:
        shutil.copytree(os.path.join(HERE, '../../sqlparse'),
                        'sqlparse')


if __name__ == '__main__':
    fetch_all()
    link_sqlparse()
