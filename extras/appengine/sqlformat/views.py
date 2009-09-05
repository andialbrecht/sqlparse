# -*- coding: utf-8 -*-

import logging
import md5
import os
import sys
import time

from django import forms
from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.utils import simplejson as json

from google.appengine.api import users

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import SqlLexer, PythonLexer, PhpLexer

import sqlparse


INITIAL_SQL = "select * from foo join bar on val1 = val2 where id = 123;"
EXAMPLES_DIR = os.path.join(os.path.dirname(__file__), '../examples')

def _get_user_image(user):
    if user is None:
        return None
    digest = md5.new(user.email().lower()).hexdigest()
    if os.environ['SERVER_SOFTWARE'].startswith('Dev'):
        host = 'localhost%3A8080'
    else:
        host = 'sqlformat.appspot.com'
    default = 'http%3A%2F%2F'+host+'%2Fstatic%2Fblank.gif'
    return 'http://gravatar.com/avatar/%s?s=32&d=%s' % (digest, default)

def _get_examples():
    fnames = os.listdir(EXAMPLES_DIR)
    fnames.sort()
    return fnames


class FormOptions(forms.Form):
    data = forms.CharField(widget=forms.Textarea({'class': 'resizable'}),
                           initial=INITIAL_SQL, required=False)
    datafile = forms.FileField(required=False)
    highlight = forms.BooleanField(initial=True, required=False,
                                   widget=forms.CheckboxInput(),
                                   label='Enable syntax highlighting')
    remove_comments = forms.BooleanField(initial=False, required=False,
                                         widget=forms.CheckboxInput(),
                                         label='Remove comments')
    keyword_case = forms.CharField(
        widget=forms.Select(choices=(('', 'Unchanged'),
                                     ('lower', 'Lower case'),
                                     ('upper', 'Upper case'),
                                     ('capitalize', 'Capitalize'))),
        required=False, initial='upper', label='Keywords')
    identifier_case = forms.CharField(
        widget=forms.Select(choices=(('', 'Unchanged'),
                                     ('lower', 'Lower case'),
                                     ('upper', 'Upper case'),
                                     ('capitalize', 'Capitalize'))),
        required=False, initial='', label='Identifiers')
    n_indents = forms.IntegerField(min_value=1, max_value=30,
                                   initial=2, required=False,
                                   label='spaces',
                                   widget=forms.TextInput({'size': 2,
                                                           'maxlength': 2}))
#    right_margin = forms.IntegerField(min_value=10, max_value=500,
#                                      initial=60, required=False,
#                                      label='characters',
#                                      widget=forms.TextInput({'size': 3,
#                                                              'maxlength': 3}))
    output_format = forms.CharField(
        widget=forms.Select(choices=(('sql', 'SQL'),
                                     ('python', 'Python'),
                                     ('php', 'PHP'),
                                     )),
        required=False, initial='sql', label='Language')

    def clean(self):
        super(FormOptions, self).clean()
        data = self.cleaned_data.get('data')
        logging.info(self.files)
        if 'datafile' in self.files:
            self._datafile = self.files['datafile'].read()
        else:
            self._datafile =  None
        if not data and not self._datafile:
            raise forms.ValidationError('Whoops, I need a file or text!')
        elif data and self._datafile:
            raise forms.ValidationError('Whoops, I need a file OR text!')
        return self.cleaned_data

    def clean_output_format(self):
        frmt = self.cleaned_data.get('output_format')
        if not frmt:
            frmt = 'sql'
        return frmt.lower()

    def get_data(self):
        data = self.cleaned_data.get('data')
        if self._datafile:
            return self._datafile
        else:
            return data


def format_sql(form, format='html'):
    data = form.cleaned_data
    popts = {}
    sql = form.get_data()
    if data.get('remove_comments'):
        popts['strip_comments'] = True
    if data.get('keyword_case'):
        popts['keyword_case'] = data.get('keyword_case')
    if data.get('identifier_case'):
        popts['identifier_case'] = data.get('identifier_case')
    if data.get('n_indents', None) is not None:
        popts['reindent'] = True
        popts['indent_width'] = data.get('n_indents')
    if data.get('right_margin', None) is not None:
        popts['right_margin'] = data.get('right_margin')
    if data.get('output_format', None) is not None:
        popts['output_format'] = data.get('output_format')
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


def index(request):
    output = None
    data = {}
    proc_time = None
    if request.method == 'POST':
        logging.debug(request.POST)
        form = FormOptions(request.POST, request.FILES)
        if form.is_valid():
            start = time.time()
            output = format_sql(form,
                                format=request.POST.get('format', 'html'))
            proc_time = time.time()-start
    else:
        form = FormOptions()
    if request.POST.get('format', None) == 'json':
        logging.warning(form.errors)
        data['errors'] = str(form.errors)
        data['output'] = output
        logging.info('%r', proc_time)
        data['proc_time'] = '%.3f' % proc_time or 0.0
        data = json.dumps(data)
        return HttpResponse(data, content_type='text/x-json')
    elif request.POST.get('format', None) == 'text':
        if not form.is_valid():
            data = str(form.errors)  # XXX convert to plain text
        else:
            data = output
        return HttpResponse(data, content_type='text/plain')
    return render_to_response('index.html',
                              {'form': form, 'output': output,
                               'proc_time': proc_time and '%.3f' % proc_time or None,
                               'user': users.get_current_user(),
                               'login_url': users.create_login_url('/'),
                               'logout_url': users.create_logout_url('/'),
                               'userimg': _get_user_image(users.get_current_user()),
                               'examples': _get_examples()})


def format(request):
    if request.method == 'POST':
        form = FormOptions(request.POST)
        if form.is_valid():
            try:
                response = format_sql(form, format='text')
            except:
                err = sys.exc_info()[1]
                response = 'ERROR: Parsing failed. %s' % str(err)
        else:
            response = 'ERROR: %s' % str(form.errors)
    else:
        response = 'POST request required'
    return HttpResponse(response, content_type='text/plain')

def source(request):
    return render_to_response('source.html')

def about(request):
    return render_to_response('about.html')

def api(request):
    return render_to_response('api.html')

def load_example(request):
    fname = request.POST.get('fname')
    if fname is None:
        answer = 'Uups, I\'ve got no filename...'
    elif fname not in _get_examples():
        answer = 'Hmm, I think you don\'t want to do that.'
    else:
        answer = open(os.path.join(EXAMPLES_DIR, fname)).read()
    data = json.dumps({'answer': answer})
    return HttpResponse(data, content_type='text/x-json')
