'''
Created on 17/05/2012

@author: piranna

Several utility functions to extract info from the SQL sentences
'''

from sqlparse.filters import ColumnsSelect, InfoCreateTable, Limit
from sqlparse.pipeline import Pipeline
from sqlparse.tokens import Keyword, Whitespace


def getlimit(stream):
    pipe = Pipeline()

    pipe.append(Limit())

    result = pipe(stream)
    try:
        return int(result)
    except ValueError:
        return result


def getcolumns(stream):
    """Function that return the colums of a SELECT query"""
    pipe = Pipeline()

    pipe.append(ColumnsSelect())

    return pipe(stream)



def get_create_table_info(stream):
    """
    Function that returns the columns of a CREATE TABLE statement including their type and NULL
    declaration.

    The nullable declaration is None if not specified, else 'NOT NULL' or 'NULL'.
    """
    pipe = Pipeline()

    pipe.append(InfoCreateTable())

    return pipe(stream)



class IsType(object):
    """Functor that return is the statement is of a specific type"""
    def __init__(self, type):
        self.type = type

    def __call__(self, stream):
        for token_type, value in stream:
            if token_type not in Whitespace:
                return token_type in Keyword and value == self.type
