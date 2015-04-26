'''
Created on 13/02/2012

@author: piranna
'''
from unittest import main, TestCase

from sqlparse.filters import IncludeStatement, Tokens2Unicode
from sqlparse.lexer import tokenize

import re
import sys
sys.path.insert(0, '..')

from sqlparse.filters import compact
from sqlparse.functions import getcolumns, get_create_table_info, getlimit, IsType


class TestCasePy27Features(object):
    class __AssertRaisesContext(object):
        def __init__(self, expected_exception, expected_regexp):
            self.expected = expected_exception
            self.expected_regexp = expected_regexp

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, tb):
            if exc_type is None:
                raise self.failureException('%s not raised' % exc_type.__name__)
            if not issubclass(exc_type, self.expected):
                return False
            self.exception = exc_value
            expected_regexp = self.expected_regexp
            if isinstance(expected_regexp, basestring):
                expected_regexp = re.compile(expected_regexp)
            if not expected_regexp.search(str(exc_value)):
                raise self.failureException('"%s" does not match "%s"' %
                                            (expected_regexp.pattern, str(exc_value)))
            return True

    """Adds simple replacements for unittest features not available before Python 2.7"""
    def assertRaisesRegexp(self, expected_exception, expected_regexp):
        return self.__AssertRaisesContext(expected_exception, expected_regexp)


class Test_IncludeStatement(TestCase):
    sql = """-- type: script
            -- return: integer

            INCLUDE "_Make_DirEntry.sql";

            INSERT INTO directories(inode)
                            VALUES(:inode)
            LIMIT 1"""

    def test_includeStatement(self):
        stream = tokenize(self.sql)
        includeStatement = IncludeStatement('tests/files',
                                            raiseexceptions=True)
        stream = includeStatement.process(None, stream)
        stream = compact(stream)

        result = Tokens2Unicode(stream)

        self.assertEqual(
            result, (
                'INSERT INTO dir_entries(type)VALUES(:type);INSERT INTO '
                'directories(inode)VALUES(:inode)LIMIT 1'))


class Test_SQL(TestCase):
    sql = """-- type: script
            -- return: integer

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
--    :creation                                                AS st_ctime,
--    CAST(STRFTIME('%s',dir_entries.access)       AS INTEGER) AS st_atime,
--    CAST(STRFTIME('%s',dir_entries.modification) AS INTEGER) AS st_mtime,

    COALESCE(files.size,0) AS st_size, -- Python-FUSE
    COALESCE(files.size,0) AS size     -- PyFilesystem

FROM dir_entries
    LEFT JOIN files
        ON dir_entries.inode == files.inode
    LEFT JOIN links
        ON dir_entries.inode == links.child_entry

WHERE dir_entries.inode == :inode

GROUP BY dir_entries.inode
LIMIT 1"""


class Test_Compact(Test_SQL):
    def test_compact1(self):
        stream = compact(tokenize(self.sql))

        result = Tokens2Unicode(stream)

        self.assertEqual(result,
                         'INSERT INTO directories(inode)VALUES(:inode)LIMIT 1')

    def test_compact2(self):
        stream = tokenize(self.sql2)

        result = compact(stream)

        self.assertEqual(
            Tokens2Unicode(result),
            'SELECT child_entry,asdf AS inode,creation FROM links WHERE '
            'parent_dir==:parent_dir AND name==:name LIMIT 1')

    def test_compact3(self):
        stream = tokenize(self.sql3)

        result = compact(stream)

        self.assertEqual(
            Tokens2Unicode(result),
            'SELECT 0 AS st_dev,0 AS st_uid,0 AS st_gid,dir_entries.type AS '
            'st_mode,dir_entries.inode AS st_ino,COUNT(links.child_entry)AS '
            'st_nlink,:creation AS st_ctime,dir_entries.access AS st_atime,'
            'dir_entries.modification AS st_mtime,COALESCE(files.size,0)AS '
            'st_size,COALESCE(files.size,0)AS size FROM dir_entries LEFT JOIN'
            ' files ON dir_entries.inode==files.inode LEFT JOIN links ON '
            'dir_entries.inode==links.child_entry WHERE dir_entries.inode=='
            ':inode GROUP BY dir_entries.inode LIMIT 1')


class Test_GetColumns(Test_SQL):
    def test_getcolumns1(self):
        columns = getcolumns(tokenize(self.sql))
        self.assertEqual(columns, [])

    def test_getcolumns2(self):
        columns = getcolumns(tokenize(self.sql2))
        self.assertEqual(columns, ['child_entry', 'inode', 'creation'])

    def test_getcolumns3(self):
        columns = getcolumns(tokenize(self.sql3))
        self.assertEqual(columns, ['st_dev', 'st_uid', 'st_gid', 'st_mode',
                                   'st_ino', 'st_nlink', 'st_ctime',
                                   'st_atime', 'st_mtime', 'st_size', 'size'])


class Test_GetCreateTableInfo(TestCase, TestCasePy27Features):
    sql1 = """
        CREATE TABLE item (
            id INT PRIMARY KEY NOT NULL,
            type VARCHAR(3) NOT NULL,
            score DOUBLE NULL,
            url TEXT NULL,
            text TEXT NOT NULL,
            item2other INT NULL,

            FOREIGN KEY(item2other) REFERENCES othertable(id)
        );
    """

    sql2 = """
        CREATE UNIQUE INDEX t1b ON t1(b);
    """

    sql3 = """
        CREATE TABLE a ( afield INT PRIMARY KEY NOT NULL );
        CREATE TABLE b ( bfield VARCHAR(10) PRIMARY KEY NOT NULL ) ;
        CREATE TABLE c ( cfield TEXT PRIMARY KEY NOT NULL ) this gets ignored;
        CREATE TABLE d ( dfield NVARCHAR PRIMARY KEY NOT NULL )
    """

    sql4 = """
        CREATE TABLE example (
            id INT,
            data VARCHAR(10)
        ) TYPE=innodb;
    """

    sql5 = """
        CREATE TABLE mydb.mytable (
            `a` INT(10) unsigned not null default '0',
            `b` DECIMAL(6,0) unsigned NOT null ,
            `c` DATE,
            `d` DECIMAL(4,0) unsigned not null ,
            `e` VARCHAR(6) not null ,
            `f` VARCHAR(1) not null ,
            `g` VARCHAR(1) not null,
            `h` DECIMAL(13,2)unsigned not null ,
            `i` DECIMAL(4,0)unsigned not null ,
            `j` VARCHAR(30)unsigned not null,
            `k` DECIMAL(13,2) unsigned not null,
            `l` VARCHAR(1)not null ,
            `m` DECIMAL(13,2) unsigned not null,
            `n` VARCHAR(1) unsigned not null,
            PRIMARY KEY (`a`)
        )ENGINE=InnoDB;
    """

    def test_get_create_table_info1(self):
        info = get_create_table_info(tokenize(self.sql1))

        self.assertEqual(info, [('item', {
            0: ('id',         'INT'),
            1: ('type',       'VARCHAR'),
            2: ('score',      'DOUBLE'),
            3: ('url',        'TEXT'),
            4: ('text',       'TEXT'),
            5: ('item2other', 'INT'),
        })])

    def test_get_create_table_info2(self):
        with self.assertRaisesRegexp(ValueError, 'Not a CREATE TABLE statement'):
            info = get_create_table_info(tokenize(self.sql2))

    def test_get_create_table_info3(self):
        info = get_create_table_info(tokenize(self.sql3))

        self.assertEqual(info, [
            ('a', {
                0: ('afield', 'INT'),
            }),
            ('b', {
                0: ('bfield', 'VARCHAR'),
            }),
            ('c', {
                0: ('cfield', 'TEXT'),
            }),
            ('d', {
                0: ('dfield', 'NVARCHAR'),
            }),
        ])

    def test_get_create_table_info4(self):
        info = get_create_table_info(tokenize(self.sql4))

        self.assertEqual(info, [('example', {
            0: ('id', 'INT'),
            1: ('data', 'VARCHAR'),
        })])

    def test_get_create_table_info5(self):
        info = get_create_table_info(tokenize(self.sql5))

        self.assertEqual(info, [('mydb.mytable', {
             0: ('a', 'INT'),
             1: ('b', 'DECIMAL'),
             2: ('c', 'DATE'),
             3: ('d', 'DECIMAL'),
             4: ('e', 'VARCHAR'),
             5: ('f', 'VARCHAR'),
             6: ('g', 'VARCHAR'),
             7: ('h', 'DECIMAL'),
             8: ('i', 'DECIMAL'),
             9: ('j', 'VARCHAR'),
            10: ('k', 'DECIMAL'),
            11: ('l', 'VARCHAR'),
            12: ('m', 'DECIMAL'),
            13: ('n', 'VARCHAR'),
        })])


class Test_GetLimit(Test_SQL):
    def test_getlimit1(self):
        limit = getlimit(tokenize(self.sql))
        self.assertEqual(limit, 1)

    def test_getlimit2(self):
        limit = getlimit(tokenize(self.sql2))
        self.assertEqual(limit, 1)

    def test_getlimit3(self):
        limit = getlimit(tokenize(self.sql3))
        self.assertEqual(limit, 1)


class Test_IsType(Test_SQL):
    def test_istype2(self):
        stream = tokenize(self.sql2)
        self.assertTrue(IsType('SELECT')(stream))

        stream = tokenize(self.sql2)
        self.assertFalse(IsType('INSERT')(stream))


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    main()
