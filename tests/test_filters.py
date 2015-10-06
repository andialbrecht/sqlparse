'''
Created on 24/03/2012

@author: piranna
'''
import unittest

import sqlparse
from sqlparse import sql
from sqlparse import tokens as T
from sqlparse.filters import StripWhitespace
from sqlparse.filters import Tokens2Unicode
from sqlparse.lexer import tokenize


class Test__StripWhitespace(unittest.TestCase):
    sql = """INSERT INTO dir_entries(type)VALUES(:type);

            INSERT INTO directories(inode)
                            VALUES(:inode)
            LIMIT 1"""

    sql2 = """SELECT child_entry,asdf AS inode, creation
              FROM links
              WHERE parent_dir == :parent_dir AND name == :name
              LIMIT 1"""

    sql3 = """SELECT
    0 AS st_dev,
    0 AS st_uid,
    0 AS st_gid,

    dir_entries.type         AS st_mode,
    dir_entries.inode        AS st_ino,
    COUNT(links.child_entry) AS st_nlink,

    :creation                AS st_ctime,
    dir_entries.access       AS st_atime,
    dir_entries.modification AS st_mtime,

    COALESCE(files.size,0) AS st_size,
    COALESCE(files.size,0) AS size

FROM dir_entries
    LEFT JOIN files
        ON dir_entries.inode == files.inode
    LEFT JOIN links
        ON dir_entries.inode == links.child_entry

WHERE dir_entries.inode == :inode

GROUP BY dir_entries.inode
LIMIT 1"""

    def test_StripWhitespace1(self):
        self.assertEqual(
            Tokens2Unicode(StripWhitespace(tokenize(self.sql))),
            'INSERT INTO dir_entries(type)VALUES(:type);INSERT INTO '
            'directories(inode)VALUES(:inode)LIMIT 1')

    def test_StripWhitespace2(self):
        self.assertEqual(
            Tokens2Unicode(StripWhitespace(tokenize(self.sql2))),
            'SELECT child_entry,asdf AS inode,creation FROM links WHERE '
            'parent_dir==:parent_dir AND name==:name LIMIT 1')

    def test_StripWhitespace3(self):
        self.assertEqual(
            Tokens2Unicode(StripWhitespace(tokenize(self.sql3))),
            'SELECT 0 AS st_dev,0 AS st_uid,0 AS st_gid,dir_entries.type AS '
            'st_mode,dir_entries.inode AS st_ino,COUNT(links.child_entry)AS '
            'st_nlink,:creation AS st_ctime,dir_entries.access AS st_atime,'
            'dir_entries.modification AS st_mtime,COALESCE(files.size,0)AS '
            'st_size,COALESCE(files.size,0)AS size FROM dir_entries LEFT JOIN'
            ' files ON dir_entries.inode==files.inode LEFT JOIN links ON '
            'dir_entries.inode==links.child_entry WHERE dir_entries.inode=='
            ':inode GROUP BY dir_entries.inode LIMIT 1'
        )


class TestMysqlCreateStatementFilter(unittest.TestCase):

    @property
    def create_stmt(self):
        return """
            CREATE TABLE `abc` (
                `id` int(11) NOT NULL auto_increment,
                `name` varchar(64) collate utf8_unicode_ci default NULL,
                `address` varchar(128) collate utf8_unicode_ci default NULL,
                `related_id` int(11) NOT NULL default '0',
                `currency` double(8,2) default NULL,
                `time_created` int(11) NOT NULL default '0',
                `age` int(10) unsigned default NULL,
                `type` tinyint(3) unsigned default NULL,
                PRIMARY KEY  (`id`),
                KEY `name_address` (`name`,`address`),
                KEY `related_id` (`related_id`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci
        """

    @property
    def create_stmt_without_col_type_length(self):
        return """
            CREATE TABLE `abc` (
                `id` int NOT NULL auto_increment,
                `age` int default NULL,
                `name` varchar collate utf8_unicode_ci default NULL,
                PRIMARY KEY  (`id`),
                KEY `age_name` (`age`,`name`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci
        """

    @property
    def create_stmt_without_col_attributes(self):
        return """
            CREATE TABLE `abc` (
                `id` int(11),
                `age` int(11),
                `name` varchar(64),
                PRIMARY KEY  (`id`),
                KEY `age_name` (`age`,`name`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci
        """

    def _pre_process_sql(self, sql):
        stream = sqlparse.parse(sql, dialect='mysql')
        return stream[0]

    def test_complex_create_statement(self):
        statement = self._pre_process_sql(self.create_stmt)
        assert isinstance(statement, sql.Statement)
        assert statement.get_type() == 'CREATE'
        table_name = statement.token_next_by_instance(0, sql.TableName)
        self.assertEqual(table_name.value, u'abc')
        column_definitions = statement.token_next_by_instance(0, sql.ColumnsDefinition).tokens
        self.assertEqual(len(column_definitions), 8)
        self._assert_column_definition(
            column_definition_token=column_definitions[0],
            column_name=u'id',
            column_type=u'int',
            column_type_length=(u'11',),
            column_attributes=[(u'not null',), (u'auto_increment',)]
        )
        self._assert_column_definition(
            column_definition_token=column_definitions[1],
            column_name=u'name',
            column_type=u'varchar',
            column_type_length=(u'64',),
            column_attributes=[(u'collate', u'utf8_unicode_ci'), (u'default', u'null')]
        )
        self._assert_column_definition(
            column_definition_token=column_definitions[2],
            column_name=u'address',
            column_type=u'varchar',
            column_type_length=(u'128',),
            column_attributes=[(u'collate', u'utf8_unicode_ci'), (u'default', u'null')]
        )
        self._assert_column_definition(
            column_definition_token=column_definitions[3],
            column_name=u'related_id',
            column_type=u'int',
            column_type_length=(u'11',),
            column_attributes=[(u'not null',), (u'default', u'0',)]
        )
        self._assert_column_definition(
            column_definition_token=column_definitions[4],
            column_name=u'currency',
            column_type=u'double',
            column_type_length=(u'8', u'2'),
            column_attributes=[(u'default', u'null')]
        )
        self._assert_column_definition(
            column_definition_token=column_definitions[5],
            column_name=u'time_created',
            column_type=u'int',
            column_type_length=(u'11',),
            column_attributes=[(u'not null',), (u'default', u'0')]
        )
        self._assert_column_definition(
            column_definition_token=column_definitions[6],
            column_name=u'age',
            column_type=u'int',
            column_type_length=(u'10',),
            column_attributes=[(u'unsigned',), (u'default', u'null')]
        )
        self._assert_column_definition(
            column_definition_token=column_definitions[7],
            column_name=u'type',
            column_type=u'tinyint',
            column_type_length=(u'3',),
            column_attributes=[(u'unsigned',), (u'default', u'null')]
        )

    def test_create_statement_without_column_type_length(self):
        statement = self._pre_process_sql(
            self.create_stmt_without_col_type_length
        )
        assert isinstance(statement, sql.Statement)
        assert statement.get_type() == 'CREATE'
        table_name = statement.token_next_by_instance(0, sql.TableName)
        self.assertEqual(table_name.value, u'abc')
        column_definitions = statement.token_next_by_instance(0, sql.ColumnsDefinition).tokens
        self.assertEqual(len(column_definitions), 3)
        self._assert_column_definition(
            column_definition_token=column_definitions[0],
            column_name=u'id',
            column_type=u'int',
            column_type_length=None,
            column_attributes=[(u'not null',), (u'auto_increment',)]
        )
        self._assert_column_definition(
            column_definition_token=column_definitions[1],
            column_name=u'age',
            column_type=u'int',
            column_type_length=None,
            column_attributes=[(u'default', u'null')]
        )
        self._assert_column_definition(
            column_definition_token=column_definitions[2],
            column_name=u'name',
            column_type=u'varchar',
            column_type_length=None,
            column_attributes=[(u'collate', u'utf8_unicode_ci'), (u'default', u'null')]
        )

    def test_create_statement_without_column_attributes(self):
        statement = self._pre_process_sql(
            self.create_stmt_without_col_attributes
        )
        assert isinstance(statement, sql.Statement)
        assert statement.get_type() == 'CREATE'
        table_name = statement.token_next_by_instance(0, sql.TableName)
        self.assertEqual(table_name.value, u'abc')
        column_definitions = statement.token_next_by_instance(0, sql.ColumnsDefinition).tokens
        self.assertEqual(len(column_definitions), 3)
        self._assert_column_definition(
            column_definition_token=column_definitions[0],
            column_name=u'id',
            column_type=u'int',
            column_type_length=(u'11',),
            column_attributes=[]
        )
        self._assert_column_definition(
            column_definition_token=column_definitions[1],
            column_name=u'age',
            column_type=u'int',
            column_type_length=(u'11',),
            column_attributes=[]
        )
        self._assert_column_definition(
            column_definition_token=column_definitions[2],
            column_name=u'name',
            column_type=u'varchar',
            column_type_length=(u'64',),
            column_attributes=[]
        )

    @property
    def create_stmt_without_keys(self):
        return """
            CREATE TABLE `abc` (
                `name` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
                `count` int(11) unsigned DEFAULT '0'
            ) ENGINE=BLACKHOLE DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci
        """

    def test_create_stmt_without_keys(self):
        statement = self._pre_process_sql(self.create_stmt_without_keys)

        assert isinstance(statement, sql.Statement)
        assert statement.get_type() == 'CREATE'
        table_name = statement.token_next_by_instance(0, sql.TableName)
        self.assertEqual(table_name.value, u'abc')
        column_definitions = statement.token_next_by_instance(0, sql.ColumnsDefinition).tokens
        self.assertEqual(len(column_definitions), 2)
        self._assert_column_definition(
            column_definition_token=column_definitions[0],
            column_name=u'name',
            column_type=u'varchar',
            column_type_length=(u'255',),
            column_attributes=[(u'collate', u'utf8_unicode_ci'), (u'not null',)]
        )
        self._assert_column_definition(
            column_definition_token=column_definitions[1],
            column_name=u'count',
            column_type=u'int',
            column_type_length=(u'11',),
            column_attributes=[(u'unsigned',), (u'default', u'0')]
        )

    @property
    def create_stmt_with_simple_column(self):
        return """
            CREATE TABLE `abc` (
                `amount` double
            ) ENGINE=BLACKHOLE DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci
        """

    def test_create_stmt_with_simple_column(self):
        statement = self._pre_process_sql(self.create_stmt_with_simple_column)

        assert isinstance(statement, sql.Statement)
        assert statement.get_type() == 'CREATE'
        table_name = statement.token_next_by_instance(0, sql.TableName)
        self.assertEqual(table_name.value, u'abc')
        column_definitions = statement.token_next_by_instance(0, sql.ColumnsDefinition).tokens
        self.assertEqual(len(column_definitions), 1)
        self._assert_column_definition(
            column_definition_token=column_definitions[0],
            column_name=u'amount',
            column_type=u'double',
            column_type_length=None,
            column_attributes=[]
        )

    def test_clean_quotes(self):
        filter = sqlparse.filters.MysqlCreateStatementFilter()
        assert filter._clean_quote('abc') == 'abc'
        assert filter._clean_quote('"abc"') == 'abc'
        assert filter._clean_quote('ab`c') == 'ab`c'
        assert filter._clean_quote('ab"c') == 'ab"c'
        assert filter._clean_quote('`abc') == '`abc'
        assert filter._clean_quote('abc"') == 'abc"'
        assert filter._clean_quote('`ab``c`') == 'ab`c'
        assert filter._clean_quote('"ab""c"') == 'ab"c'
        assert filter._clean_quote('`ab""c`') == 'ab""c'
        assert filter._clean_quote('"ab``c"') == 'ab``c'
        assert filter._clean_quote('"ab""c"') == 'ab"c'
        assert filter._clean_quote('`"abc"`') == '"abc"'
        assert filter._clean_quote('"`abc`"') == '`abc`'
        assert filter._clean_quote('`"a""b``c"`') == '"a""b`c"'
        assert filter._clean_quote('"`a``b""c`"') == '`a``b"c`'

    def _assert_column_definition(
        self,
        column_definition_token,
        column_name,
        column_type,
        column_type_length,
        column_attributes
    ):
        assert isinstance(
            column_definition_token,
            sql.ColumnDefinition
        )
        self.assertEqual(
            self._get_column_name(column_definition_token),
            column_name
        )
        self.assertEqual(
            self._get_column_type(column_definition_token),
            column_type
        )
        self.assertEqual(
            self._get_column_type_length(column_definition_token),
            column_type_length
        )
        self.assertEqual(
            self._get_column_attributes(column_definition_token),
            column_attributes
        )

    def _get_column_name(self, column_definition_token):
        column_name_token = column_definition_token.token_next_by_instance(0, sql.ColumnName)
        return column_name_token.value

    def _get_column_type(self, column_definition_token):
        column_type_token = column_definition_token.token_next_by_instance(0, sql.ColumnType)
        return column_type_token.value

    def _get_column_type_length(self, column_definition_token):
        column_type_length_token = column_definition_token.token_next_by_instance(
            0, sql.ColumnTypeLength
        )
        if column_type_length_token is not None:
            return tuple(
                token.value
                for token in column_type_length_token.tokens
                if token.ttype is T.Literal.Number.Integer
            )
        return None

    def _get_column_attributes(self, column_definition_token):
        for token in column_definition_token.tokens:
            if isinstance(token, sql.ColumnAttributes):
                return [
                    self._get_attribute(attribute_token)
                    for attribute_token in token.tokens
                    if isinstance(attribute_token, sql.Attribute)
                ]
        return None

    def _get_attribute(self, attribute):
        return tuple(token.value.lower() for token in attribute.tokens)


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
