'''
Created on 18/05/2012

@author: piranna
'''

from unittest import main, TestCase

from sqlparse import format


class Issue_50(TestCase):
    def test_issue(self):
        result = format("SELECT foo, null bar, car FROM dual", reindent=True)
        self.assertEqual(result, "SELECT      foo,\n"
                                 "       null bar,\n"
                                 "            car\n"
                                 "FROM dual")


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    main()