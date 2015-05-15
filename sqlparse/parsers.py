# -*- coding: utf-8 -*-
import abc

from sqlparse import engine
from sqlparse import filters
from sqlparse import lexer
from sqlparse import tokens as T
from sqlparse.engine import grouping
from sqlparse.engine.filter import StatementFilter


class SQLParser(object):

    dialect = 'unknown'

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def parse(self, sql, encoding):
        raise NotImplementedError()


def _split_statements(stream):
    splitter = StatementFilter()
    return list(splitter.process(None, stream))


def _is_create_table_statement(statement):
    if statement.get_type() == 'CREATE':
        first_keyword_token = statement.token_first()
        first_keyword_token_index = statement.token_index(first_keyword_token)
        second_keyword_token = statement.token_next_by_type(
            first_keyword_token_index+1,
            T.Keyword
        )
        if second_keyword_token and second_keyword_token.normalized == 'TABLE':
            return True
    return False


class GeneralSQLParser(SQLParser):

    dialect = None

    def parse(self, sql, encoding):
        stream = lexer.tokenize(sql, encoding)
        statements = _split_statements(stream)
        stack = engine.FilterStack()
        for statement in statements:
            stack.enable_grouping()
            yield stack.run(statement)


class MysqlSQLParser(SQLParser):

    dialect = 'mysql'

    def parse(self, sql, encoding):
        stream = lexer.tokenize(sql, encoding)
        statements = _split_statements(stream)

        default_stack = engine.FilterStack()
        for statement in statements:
            if _is_create_table_statement(statement):
                stack = engine.FilterStack(
                    stmtprocess=[filters.MysqlCreateStatementFilter()],
                    grouping_funcs=[grouping.group_brackets]
                )
            else:
                stack = default_stack
            stack.enable_grouping()
            yield stack.run(statement)
