# Makefile to simplify some common AppEngine actions.
# Use 'make help' for a list of commands.

PYTHON=`which python2.5`
DEV_APPSERVER=$(PYTHON) `which dev_appserver.py`
APPCFG=$(PYTHON) `which appcfg.py`
PORT=8080


default: help

help:
	@echo "Available commands:"
	@sed -n '/^[a-zA-Z0-9_.]*:/s/:.*//p' <Makefile | sort

serve:
	$(DEV_APPSERVER) --port=$(PORT) .

serve_remote:
	$(DEV_APPSERVER) --port=$(PORT) --address 0.0.0.0 .

serve_email:
	$(DEV_APPSERVER) --port=$(PORT) --enable_sendmail .

serve_remote_email:
	$(DEV_APPSERVER) --port=$(PORT) --enable_sendmail --address 0.0.0.0 .

release: make_release.sh django/.svn
	sh make_release.sh

update: release
	$(APPCFG) update release

upload: update

update_indexes:
	$(APPCFG) update_indexes .

vacuum_indexes:
	$(APPCFG) vacuum_indexes .

all: django pygments sqlparse

django:
	svn co http://code.djangoproject.com/svn/django/trunk/django

pygments:
	ln -s `python -c "import pygments,os; print os.path.dirname(pygments.__file__)"` .

sqlparse:
	ln -s ../../sqlparse .
