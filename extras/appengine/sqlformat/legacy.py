"""Legacy URLs."""

# This module reflects the URLs and behavior of the former Django
# application.

import logging
import os
import time

from google.appengine.api import memcache

from flask import Blueprint, make_response, render_template, Response, request

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import SqlLexer, PythonLexer, PhpLexer

import simplejson as json

import sqlparse


legacy = Blueprint('', 'legacy')


EXAMPLES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../examples'))


@legacy.route('/', methods=['POST', 'GET'])
def index():
    data = {'examples': _get_examples()}
    extra = {'highlight': True, 'comments': False,
             'keywords': 'upper', 'idcase': '',
             'n_indents': '2',
             'lang': 'sql'}
    sql_orig = 'select * from foo join bar on val1 = val2 where id = 123;'
    if request.method == 'POST':
        oformat = request.form.get('format', 'html')
        extra['highlight'] = 'highlight' in request.form
        extra['comments'] = 'remove_comments' in request.form
        extra['keywords'] = request.form.get('keyword_case', '')
        extra['idcase'] = request.form.get('identifier_case', '')
        extra['n_indents'] = request.form.get('n_indents', '2')
        extra['lang'] = request.form.get('output_format', 'sql')
        sql = _get_sql(request.form, request.files)
        sql_orig = sql
        start = time.time()
        data['output'] = _format_sql(sql, request.form, format=oformat)
        data['proc_time'] = '%.3f' % (time.time()-start)
        if oformat == 'json':
            data['errors'] = ''
            return make_response(Response(json.dumps(data),
                                          content_type='text/x-json'))
        elif oformat == 'text':
            return make_response(Response(data['output'], content_type='text/plain'))
    data['sql_orig'] = sql_orig
    data['extra'] = extra
    return render_template('index.html', **data)


@legacy.route('/source/')
def source():
    return render_template('source.html')


@legacy.route('/about/')
def about():
    return render_template('about.html')

@legacy.route('/api/')
def api():
    return render_template('api.html')


@legacy.route('/format/', methods=['GET', 'POST'])
@legacy.route('/format', methods=['GET', 'POST'])
def format_():
    if request.method == 'POST':
        sql = _get_sql(request.form, request.files)
        data = request.form
    else:
        sql = _get_sql(request.args)
        data = request.args
    formatted = _format_sql(sql, data, format='text')
    return make_response(Response(formatted, content_type='text/plain'))


@legacy.route('/load_example', methods=['GET', 'POST'])
def load_example():
    fname = request.form.get('fname')
    if fname is None:
        answer = 'Uups, I\'ve got no filename...'
    elif fname not in _get_examples():
        answer = 'Hmm, I think you don\'t want to do that.'
    else:
        answer = open(os.path.join(EXAMPLES_DIR, fname)).read()
    data = json.dumps({'answer': answer})
    return make_response(Response(data, content_type='text/x-json'))


def _get_examples():
    examples = memcache.get('legacy_examples')
    if examples is None:
        examples = os.listdir(EXAMPLES_DIR)
        memcache.set('legacy_examples', examples)
    return examples


def _get_sql(data, files=None):
    sql = None
    if files is not None and 'datafile' in files:
        raw = files['datafile'].read()
        try:
            sql = raw.decode('utf-8')
        except UnicodeDecodeError, err:
            logging.error(err)
            logging.debug(repr(raw))
            sql = (u'-- UnicodeDecodeError: %s\n'
                   u'-- Please make sure to upload UTF-8 encoded data for now.\n'
                   u'-- If you want to help improving this part of the application\n'
                   u'-- please file a bug with some demo data at:\n'
                   u'-- http://code.google.com/p/python-sqlparse/issues/entry\n'
                   u'-- Thanks!\n' % err)
    if not sql:
        sql = data.get('data')
    return sql or ''


def _format_sql(sql, data, format='html'):
    popts = {}
    if data.get('remove_comments'):
        popts['strip_comments'] = True
    if data.get('keyword_case', 'undefined') not in ('undefined', ''):
        popts['keyword_case'] = data.get('keyword_case')
    if data.get('identifier_case', 'undefined') not in ('undefined', ''):
        popts['identifier_case'] = data.get('identifier_case')
    if data.get('n_indents', None) is not None:
        val = data.get('n_indents')
        try:
            popts['indent_width'] = max(1, min(1000, int(val)))
            popts['reindent'] = True
        except (ValueError, TypeError):
            pass
    if (not 'indent_width' in popts and
        data.get('reindent', '').lower() in ('1', 'true', 't')):
        popts['indent_width'] = 2
        popts['reindent'] = True
    if data.get('output_format', None) is not None:
        popts['output_format'] = data.get('output_format')
    logging.debug('Format: %s, POPTS: %r', format, popts)
    logging.debug(sql)
    sql = sqlparse.format(sql, **popts)
    if format in ('html', 'json'):
        if data.get('highlight', False):
            if popts['output_format'] == 'python':
                lexer = PythonLexer()
            elif popts['output_format'] == 'php':
                lexer = PhpLexer()
            else:
                lexer = SqlLexer()
            sql = highlight(sql, lexer, HtmlFormatter())
        else:
            sql = ('<textarea class="resizable" '
                   'style="height: 350px; margin-top: 1em;">%s</textarea>'
                   % sql)
    return sql
