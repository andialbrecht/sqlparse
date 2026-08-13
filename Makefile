# Makefile to simplify some common development tasks.
# Run 'make help' for a list of commands.

PYTHON=`which python`

default: help

help:
	@echo "Available commands:"
	@sed -n '/^[a-zA-Z0-9_.]*:/s/:.*//p' <Makefile | sort

test:
	uv run --group dev --python 3.10 pytest tests/
	uv run --group dev --python 3.11 pytest tests/
	uv run --group dev --python 3.12 pytest tests/
	uv run --group dev --python 3.13 pytest tests/
	uv run --group dev --python 3.14 pytest tests/

lint:
	uv run --group dev ruff check sqlparse/

benchmark:
	@for bench in benchmarks/bench_*.py; do \
		uv run --group dev python $$bench || exit 1; \
		echo; \
	done

coverage:
	uv run --group dev coverage run -m pytest tests/
	uv run --group dev coverage combine
	uv run --group dev coverage report

coverage-xml:
	uv run --group dev coverage run -m pytest tests/
	uv run --group dev coverage combine
	uv run --group dev coverage xml

clean:
	$(PYTHON) setup.py clean
	find . -name '*.pyc' -delete
	find . -name '*~' -delete

release:
	@rm -rf dist/
	uv run python -m build
	uv run hatch publish
