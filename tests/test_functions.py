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
            score DOUBLE,
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
        CREATE TABLE b ( bfield VARCHAR(10) NULL ) ;
        CREATE TABLE c ( cfield TEXT PRIMARY KEY NOT NULL ) this gets ignored;
        CREATE TABLE d ( dfield NVARCHAR PRIMARY KEY )
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
            `i` DECIMAL(4,0)unsigned ,
            `j` VARCHAR(30)unsigned not null,
            `k` DECIMAL(13,2) unsigned not null,
            `l` VARCHAR(1)not null ,
            `m` DECIMAL(13,2) unsigned not null,
            `n` VARCHAR(1) unsigned not null,
            PRIMARY KEY (`a`)
        )ENGINE=InnoDB;
    """

    sql6 = 'SELECT * FROM a'
    sql7 = 'CREATE TABLE ('
    sql8 = 'CREATE TABLE'
    sql9 = 'CREATE TABLE t (,)'
    sql10 = 'CREATE TABLE t ( a NULL )'

    sql11 = """
        CREATE TABLE t (
            a INT,
            PRIMARY KEY (a),
            FOREIGN KEY (a) REFERENCES other(id)
        )
    """

    sql12 = 'CREATE TABLE a,'
    sql13 = 'CREATE TABLE t (a INT, a INT)'
    sql14 = 'CREATE TABLE pair ( id VARCHAR(10) PRIMARY KEY NOT NULL, source VARCHAR(3) NOT NULL, target VARCHAR(3) NOT NULL );'

    def test_get_create_table_info1(self):
        info = get_create_table_info(tokenize(self.sql1))

        self.assertEqual(info, [('item', {
            0: ('id',         'INT',     'NOT NULL'),
            1: ('type',       'VARCHAR', 'NOT NULL'),
            2: ('score',      'DOUBLE',  None),
            3: ('url',        'TEXT',    'NULL'),
            4: ('text',       'TEXT',    'NOT NULL'),
            5: ('item2other', 'INT',     'NULL'),
        })])

    def test_get_create_table_info3(self):
        info = get_create_table_info(tokenize(self.sql3))

        self.assertEqual(info, [
            ('a', {
                0: ('afield', 'INT', 'NOT NULL'),
            }),
            ('b', {
                0: ('bfield', 'VARCHAR', 'NULL'),
            }),
            ('c', {
                0: ('cfield', 'TEXT', 'NOT NULL'),
            }),
            ('d', {
                0: ('dfield', 'NVARCHAR', None),
            }),
        ])

    def test_get_create_table_info4(self):
        info = get_create_table_info(tokenize(self.sql4))

        self.assertEqual(info, [('example', {
            0: ('id', 'INT', None),
            1: ('data', 'VARCHAR', None),
        })])

    def test_get_create_table_info5(self):
        info = get_create_table_info(tokenize(self.sql5))

        self.assertEqual(info, [('mydb.mytable', {
             0: ('a', 'INT',     'NOT NULL'),
             1: ('b', 'DECIMAL', 'NOT NULL'),
             2: ('c', 'DATE',    None),
             3: ('d', 'DECIMAL', 'NOT NULL'),
             4: ('e', 'VARCHAR', 'NOT NULL'),
             5: ('f', 'VARCHAR', 'NOT NULL'),
             6: ('g', 'VARCHAR', 'NOT NULL'),
             7: ('h', 'DECIMAL', 'NOT NULL'),
             8: ('i', 'DECIMAL', None),
             9: ('j', 'VARCHAR', 'NOT NULL'),
            10: ('k', 'DECIMAL', 'NOT NULL'),
            11: ('l', 'VARCHAR', 'NOT NULL'),
            12: ('m', 'DECIMAL', 'NOT NULL'),
            13: ('n', 'VARCHAR', 'NOT NULL'),
        })])

    def test_get_create_table_info11(self):
        info = get_create_table_info(tokenize(self.sql11))

        self.assertEqual(info, [('t', {
            0: ('a', 'INT', None),
        })])

    def test_get_create_table_info14(self):
        info = get_create_table_info(tokenize(self.sql14))

        self.assertEqual(info, [('pair', {
            0: ('id', 'VARCHAR', 'NOT NULL'),
            1: ('source', 'VARCHAR', 'NOT NULL'),
            2: ('target', 'VARCHAR', 'NOT NULL'),
        })])

    def test_get_create_table_info_errors(self):
        for test, expected_regexp in (
            ('sql6', 'Not a CREATE statement'),
            ('sql2', 'Not a CREATE TABLE statement'),
            ('sql7', 'No table name given'),
            ('sql8', 'Unexpected end state'),
            ('sql9', 'No column name given'),
            ('sql10', 'No column type given'),
            ('sql12', 'No opening paren for CREATE TABLE'),
            ('sql13', 'Duplicate column name'),
        ):
            try:
                with self.assertRaisesRegexp(ValueError, expected_regexp):
                    get_create_table_info(tokenize(getattr(self, test)))
            except self.failureException, e:
                raise self.failureException('%s (in test %r)' % (e, test))


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
