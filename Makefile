# Makefile to simplify some common development tasks.
# Run 'make help' for a list of commands.

PYTHON=`which python`

default: help

help:
	@echo "Available commands:"
	@sed -n '/^[a-zA-Z0-9_.]*:/s/:.*//p' <Makefile | sort

test:
	tox

coverage:
	pytest --cov=sqlparse --cov-report=html --cov-report=term

clean:
	$(PYTHON) setup.py clean
	find . -name '*.pyc' -delete
	find . -name '*~' -delete

release:
	@rm -rf dist/
	python -m build
	twine upload --sign --identity E0B84F81 dist/*
	@echo "Reminder: Add release on github https://github.com/andialbrecht/sqlparse/releases"
