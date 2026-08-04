# sqlparse

[![Build Status](https://github.com/andialbrecht/sqlparse/actions/workflows/python-app.yml/badge.svg)](https://github.com/andialbrecht/sqlparse/actions/workflows/python-app.yml)
[![Coverage](https://codecov.io/gh/andialbrecht/sqlparse/branch/master/graph/badge.svg)](https://codecov.io/gh/andialbrecht/sqlparse)
[![Documentation](https://readthedocs.org/projects/sqlparse/badge/?version=latest)](https://sqlparse.readthedocs.io/en/latest/)
[![PyPI](https://img.shields.io/pypi/v/sqlparse?color=%2334D058&label=pypi%20package)](https://pypi.org/project/sqlparse)
[![Python versions](https://img.shields.io/pypi/pyversions/sqlparse)](https://pypi.org/project/sqlparse)
[![License](https://img.shields.io/badge/license-BSD--3--Clause-blue)](https://opensource.org/licenses/BSD-3-Clause)

A non-validating SQL parser for Python. Split scripts into statements, format
them, and walk their token tree.

sqlparse tokenizes SQL text and groups the parts it recognizes into a tree of
statements, clauses, identifiers and expressions. It accepts any input without
validating it, and makes no assumptions about a particular SQL dialect, so
vendor extensions and templated SQL parse too. It is a building block for
formatters, linters, editors and query analysis tools.

Licensed under the
[New BSD license](https://opensource.org/licenses/BSD-3-Clause).

## Install

```bash
pip install sqlparse
```

## Usage

Three module-level functions cover most needs: `split()`, `format()` and
`parse()`.

### Split a script into statements

```python
import sqlparse

sqlparse.split("select * from foo; select * from bar;")
# ['select * from foo;', 'select * from bar;']
```

### Format a statement

```python
print(sqlparse.format("select id,name from users where active=1",
                      reindent=True, keyword_case="upper"))
```

```sql
SELECT id,
       name
FROM users
WHERE active=1
```

`format()` accepts the same options as the command line, among them
`reindent`, `keyword_case`, `strip_comments` and `indent_width`.

### Parse and inspect a statement

```python
statement = sqlparse.parse("select id, name from users where active = 1")[0]

print(statement.get_type())
for token in statement.tokens:
    if not token.is_whitespace:
        print(f"{token.ttype or type(token).__name__!s:20} {token!s}")
```

```
SELECT
Token.Keyword.DML    select
IdentifierList       id, name
Token.Keyword        from
Identifier           users
Where                where active = 1
```

Tokens with a `ttype` are leaves. The others are groups you can descend into,
which is how nested constructs like subqueries and `CASE` expressions are
represented. See
[Analyzing SQL statements](https://sqlparse.readthedocs.io/en/latest/analyzing.html)
for the traversal API.

## Command line

Installing sqlparse also provides the `sqlformat` command. It reads from stdin
when the filename is `-`, writes to stdout by default, and rewrites files in
place with `--in-place`:

```bash
sqlformat --reindent --keywords upper query.sql
```

Run `sqlformat --help` for all formatting options.

## Pre-commit hook

Format SQL files on commit with [pre-commit](https://pre-commit.com/):

```yaml
repos:
  - repo: https://github.com/andialbrecht/sqlparse
    rev: 0.5.5  # use the latest release
    hooks:
      - id: sqlformat
        args: [--in-place, --reindent, --keywords, upper]
```

The hook defaults to `--in-place --reindent`. When overriding `args`, keep
`--in-place`, or the hook writes to stdout and leaves your files unchanged.

## Links

| | |
|---|---|
| Documentation | <https://sqlparse.readthedocs.io/> |
| Release notes | <https://sqlparse.readthedocs.io/en/latest/changes.html> |
| Issues | <https://github.com/andialbrecht/sqlparse/issues> |
| Discussions | <https://github.com/andialbrecht/sqlparse/discussions> |
| Online demo | <https://sqlformat.org/> |

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) to get
started.

sqlparse is maintained in spare time, so it can take a while before an issue or
pull request gets a reply. Thanks for your patience. A pull request that comes
with tests for the behavior it changes is usually the quickest to review.

For security issues, please follow [SECURITY.md](SECURITY.md) rather than
opening a public issue.

## License

sqlparse is licensed under the New BSD license; see [LICENSE](LICENSE) for the
full text. Parts of the code are based on [Pygments](https://pygments.org/),
written by Georg Brandl and others.
