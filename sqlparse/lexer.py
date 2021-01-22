#
# Copyright (C) 2009-2020 the sqlparse authors and contributors
# <see AUTHORS file>
#
# This module is part of python-sqlparse and is released under
# the BSD License: https://opensource.org/licenses/BSD-3-Clause

"""SQL Lexer"""

# This code is based on the SqlLexer in pygments.
# http://pygments.org/
# It's separated from the rest of pygments to increase performance
# and to allow some customizations.

from io import TextIOBase, StringIO

from collections import deque

from sqlparse import tokens
from sqlparse.keywords import SQL_REGEX
from sqlparse.utils import consume
from sqlparse.engine.statement_splitter import StatementSplitter


class Lexer:
    """Lexer
    Empty class. Leaving for backwards-compatibility
    """

    @staticmethod
    def get_tokens(text, encoding=None):
        """
        Return an iterable of (tokentype, value) pairs generated from
        `text`. If `unfiltered` is set to `True`, the filtering mechanism
        is bypassed even if filters are defined.

        Also preprocess the text, i.e. expand tabs and strip it if
        wanted and applies registered filters.

        Split ``text`` into (tokentype, text) pairs.

        ``stack`` is the initial stack (default: ``['root']``)
        """
        text = encode(text, encoding)
        iterable = enumerate(text)
        for pos, char in iterable:
            for rexmatch, action in SQL_REGEX:
                m = rexmatch(text, pos)

                if not m:
                    continue
                elif isinstance(action, tokens._TokenType):
                    yield action, m.group()
                elif callable(action):
                    yield action(m.group())

                consume(iterable, m.end() - pos - 1)
                break
            else:
                yield tokens.Error, char


def encode(text, encoding=None):
    """
    Encode a string
    """
    if isinstance(text, str):
        pass
    elif isinstance(text, bytes):
        if encoding:
            text = text.decode(encoding)
        else:
            try:
                text = text.decode('utf-8')
            except UnicodeDecodeError:
                text = text.decode('unicode-escape')
    else:
        raise TypeError("Expected text or file-like object, got {!r}".
                        format(type(text)))
    return text


class StreamLexer:
    """
    Support streaming of tokens from a filelike object without loading the
    whole content in memory.

    It use a buffer of statements to defer token generation when the buffer
    exceed the configured ``statement_buffer_size``. This allow to defer yield
    of tokens and join some statements that have been wrongly detected as
    separated statements because filelike object is read line by line.
    """

    def __init__(self, statement_buffer_size=3, encoding=None,
                 get_tokens=Lexer.get_tokens):
        self.statement_buffer_size = statement_buffer_size
        self.encoding = encoding
        self.get_tokens = get_tokens
        self.buferred_text = ""
        self.buferred_statements = deque()
        self.statement_splitter = StatementSplitter()

    def _handle_buffer_and_get_tokens(self, flush=False):
        """
        Yield tokens from buffered statements until buffer doesn't exceed
        buffer size if flush is False, or until buffer is empty if flush is
        True.


        """
        target_buffer_size = 0 if flush else self.statement_buffer_size
        while len(self.buferred_statements) > target_buffer_size:
            statement, statement_text = self.buferred_statements.popleft()
            text = statement_text
            for _, next_text in list(self.buferred_statements):
                text = text + next_text
                total_statement = next(StatementSplitter().process(
                    self.get_tokens(text, self.encoding)))
                if total_statement.tokens != statement.tokens:
                    statement_text = text
                    self.buferred_statements.popleft()

            yield from self.get_tokens(statement_text, self.encoding)

    def _handle_statement_and_get_tokens(self, statement, flush=False):
        """
        Add a statement that should be processed.

        This generates tokens from older statements, when they are dequeued.
        """
        if statement:
            self.buferred_statements.append((statement, self.buferred_text))

        yield from self._handle_buffer_and_get_tokens(flush)
        self.buferred_text = ""
        self.statement_splitter = StatementSplitter()

    def stream_tokens(self, filelike):
        """
        Split ``filelike`` content into (tokentype, text) pairs while keeping
        the memory usage low.
        """
        pending_statement = None

        while True:
            line = filelike.readline()
            if not line:
                yield from self._handle_statement_and_get_tokens(
                    pending_statement, flush=True)
                break

            self.buferred_text = self.buferred_text + line

            for statement in self.statement_splitter.process(
                self.get_tokens(line, self.encoding)
            ):
                if statement.pending:
                    pending_statement = statement
                else:
                    pending_statement = None
                    yield from self._handle_statement_and_get_tokens(statement)


def tokenize(sql, encoding=None, stream=None):
    """Tokenize sql.

    Tokenize *sql* using the :class:`Lexer` and return a 2-tuple stream
    of ``(token type, value)`` items.
    """
    if isinstance(sql, TextIOBase):
        if stream is not False:
            return StreamLexer().stream_tokens(sql)
        sql = sql.read()
    if stream:
        sql = StringIO(encode(sql, encoding))
        return StreamLexer().stream_tokens(sql)
    return Lexer.get_tokens(sql, encoding)
