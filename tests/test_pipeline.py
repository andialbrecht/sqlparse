import unittest

from sqlparse.filters import ColumnsSelect
from sqlparse.lexer import tokenize
from sqlparse.pipeline import Pipeline


class Test(unittest.TestCase):

    def setUp(self):
        self.pipe = Pipeline()
        self.pipe.append(tokenize)
        self.pipe.append(ColumnsSelect())

    def test_1(self):
        sql = """
        -- type: script
        -- return: integer

        INCLUDE "Direntry.make.sql";

        INSERT INTO directories(inode)
        VALUES(:inode)
        LIMIT 1"""
        self.assertEqual([], self.pipe(sql))

    def test_2(self):
        sql = """
        SELECT child_entry,asdf AS inode, creation
        FROM links
        WHERE parent_dir == :parent_dir AND name == :name
        LIMIT 1"""
        self.assertEqual([u'child_entry', u'inode', u'creation'],
                         self.pipe(sql))

    def test_3(self):
        sql = """
SELECT
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
        self.assertEqual([u'st_dev', u'st_uid', u'st_gid', u'st_mode',
                          u'st_ino', u'st_nlink', u'st_ctime',
                          u'st_atime', u'st_mtime', u'st_size', u'size'],
                         self.pipe(sql))
