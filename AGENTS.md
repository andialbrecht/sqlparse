# AGENTS.md

This file provides guidance to Agents when working with code in this repository.

## Project Overview

sqlparse is a non-validating SQL parser for Python that provides support for parsing, splitting, and formatting SQL statements. It's compatible with Python 3.10+ and supports multiple SQL dialects (Oracle, MySQL, PostgreSQL/PL/pgSQL, HQL, MS Access, Snowflake, BigQuery).

## Development Commands

This project uses `uv` for dependency and environment management. Common commands:

### Testing
- Run all tests across Python versions: `make test`
- Run tests for specific Python version: `uv run --group dev --python 3.11 pytest tests/`
- Run single test file: `uv run --group dev --python 3.11 pytest tests/test_format.py`
- Run specific test: `uv run --group dev --python 3.11 pytest tests/test_format.py::test_name`
- Using Makefile: `make test`

### Linting
- `uv run --group dev ruff check sqlparse/` or `make lint`

### Coverage
- `make coverage` (runs tests with coverage and shows report)
- `make coverage-xml` (generates XML coverage report)

### Building
- `python -m build` (builds distribution packages)

## Architecture

### Core Processing Pipeline

The parsing and formatting workflow follows this sequence:

1. **Lexing** (`sqlparse/lexer.py`): Tokenizes SQL text into `(token_type, value)` pairs using regex-based pattern matching
2. **Filtering** (`sqlparse/engine/filter_stack.py`): Processes token stream through a `FilterStack` with three stages:
   - `preprocess`: Token-level filters
   - `stmtprocess`: Statement-level filters
   - `postprocess`: Final output filters
3. **Statement Splitting** (`sqlparse/engine/statement_splitter.py`): Splits token stream into individual SQL statements
4. **Grouping** (`sqlparse/engine/grouping.py`): Groups tokens into higher-level syntactic structures (parentheses, functions, identifiers, etc.)
5. **Formatting** (`sqlparse/formatter.py` + `sqlparse/filters/`): Applies formatting filters based on options

### Token Hierarchy

The token system is defined in `sqlparse/sql.py`:

- `Token`: Base class with `value`, `ttype` (token type), and `parent` attributes
- `TokenList`: Group of tokens, base for all syntactic structures
  - `Statement`: Top-level SQL statement
  - `Identifier`: Table/column names, possibly with aliases
  - `IdentifierList`: Comma-separated identifiers
  - `Function`: Function calls with parameters
  - `Parenthesis`, `SquareBrackets`: Bracketed expressions
  - `Case`, `If`, `For`, `Begin`: Control structures
  - `Where`, `Having`, `Over`: SQL clauses
  - `Comparison`, `Operation`: Expressions

All tokens maintain parent-child relationships for tree traversal.

### Token Types

Token types are defined in `sqlparse/tokens.py` and used for classification during lexing (e.g., `T.Keyword.DML`, `T.Name`, `T.Punctuation`).

### Keywords and Lexer Configuration

`sqlparse/keywords.py` contains:
- `SQL_REGEX`: List of regex patterns for tokenization
- Multiple `KEYWORDS_*` dictionaries for different SQL dialects
- The `Lexer` class uses a singleton pattern (`Lexer.get_default_instance()`) that can be configured with different keyword sets

### Grouping Algorithm

`sqlparse/engine/grouping.py` contains the grouping logic that transforms flat token lists into nested tree structures. Key functions:

- `_group_matching()`: Groups tokens with matching open/close markers (parentheses, CASE/END, etc.)
- Various `group_*()` functions for specific constructs (identifiers, functions, comparisons, etc.)
- Includes DoS protection via `MAX_GROUPING_DEPTH` and `MAX_GROUPING_TOKENS` limits

### Formatting Filters

`sqlparse/filters/` contains various formatting filters:
- `reindent.py`: Indentation logic
- `aligned_indent.py`: Aligned indentation style
- `right_margin.py`: Line wrapping
- `tokens.py`: Token-level transformations (keyword case, etc.)
- `output.py`: Output format serialization (SQL, Python, PHP)
- `others.py`: Miscellaneous filters (strip comments, whitespace, etc.)

## Public API

The main entry points in `sqlparse/__init__.py`:

- `parse(sql, encoding=None)`: Parse SQL into tuple of `Statement` objects
- `format(sql, encoding=None, **options)`: Format SQL with options (reindent, keyword_case, etc.)
- `split(sql, encoding=None, strip_semicolon=False)`: Split SQL into individual statement strings
- `parsestream(stream, encoding=None)`: Generator version of parse for file-like objects

## Important Patterns

### Token Traversal
- `token.flatten()`: Recursively yields all leaf tokens (ungrouped)
- `token_first()`, `token_next()`, `token_prev()`: Navigate token lists
- `token_next_by(i=, m=, t=)`: Find next token by instance type, match criteria, or token type
- `token.match(ttype, values, regex=False)`: Check if token matches criteria

### Adding Keyword Support
Use `Lexer.add_keywords()` to extend the parser with new keywords for different SQL dialects.

### DoS Prevention
Be aware of recursion limits and token count limits in grouping operations when handling untrusted SQL input.

## Testing Conventions

- Tests are in `tests/` directory
- Test files follow pattern `test_*.py`
- Uses pytest framework
- Test data often includes SQL strings with expected parsing/formatting results
