'''
Created on 24/03/2012

@author: piranna
'''
import unittest

from sqlparse.filters import StripWhitespace, Tokens2Unicode
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
            ':inode GROUP BY dir_entries.inode LIMIT 1')


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
