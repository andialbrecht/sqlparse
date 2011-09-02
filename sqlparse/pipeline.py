# Copyright (C) 2011 Jesus Leganes "piranna", piranna@gmail.com
#
# This module is part of python-sqlparse and is released under
# the BSD License: http://www.opensource.org/licenses/bsd-license.php.

from types import GeneratorType


class Pipeline(list):
    """Pipeline to process filters sequentially"""

    def __call__(self, stream):
        """Run the pipeline

        Return a static (non generator) version of the result
        """

        # Run the stream over all the filters on the pipeline
        for filter in self:
            # Functions and callable objects (objects with '__call__' method)
            if callable(filter):
                stream = filter(stream)

            # Normal filters (objects with 'process' method)
            else:
                stream = filter.process(None, stream)

        # If last filter return a generator, staticalize it inside a list
        if isinstance(stream, GeneratorType):
            return list(stream)
        return stream


if __name__ == '__main__':
    import unittest

    from filters import ColumnsSelect
    from lexer import tokenize

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
            self.assertListEqual([], self.pipe(sql))

        def test_2(self):
            sql = """
                SELECT child_entry,asdf AS inode, creation
                FROM links
                WHERE parent_dir == :parent_dir AND name == :name
                LIMIT 1"""
            self.assertListEqual([u'child_entry', u'inode', u'creation'],
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
            self.assertListEqual([u'st_dev', u'st_uid', u'st_gid', u'st_mode',
                                  u'st_ino', u'st_nlink', u'st_ctime',
                                  u'st_atime', u'st_mtime', u'st_size', u'size'],
                                 self.pipe(sql))

    unittest.main()