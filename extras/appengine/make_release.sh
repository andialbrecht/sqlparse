#!/bin/sh

# Script to create a "release" subdirectory.  This is a subdirectory
# containing a bunch of symlinks, from which the app can be updated.
# The main reason for this is to import Django from a zipfile, which
# saves dramatically in upload time: statting and computing the SHA1
# for 1000s of files is slow.  Even if most of those files don't
# actually need to be uploaded, they still add to the work done for
# each update.

ZIPFILE=django.zip
RELEASE=release
FILES="app.yaml index.yaml __init__.py main.py settings.py"
DIRS="static templates sqlparse pygments sqlformat examples"

# Remove old $ZIPFILE file.
rm -rf $ZIPFILE

# Create new $ZIPFILE file.
# We prune:
# - .svn subdirectories for obvious reasons.
# - contrib/gis/ and related files because it's huge and unneeded.
# - *.po and *.mo files because they are bulky and unneeded.
# - *.pyc and *.pyo because they aren't used by App Engine anyway.
zip -q $ZIPFILE `find django/ \
    -name .svn -prune -o \
    -name gis -prune -o \
    -name admin -prune -o \
    -name localflavor -prune -o \
    -name mysql -prune -o \
    -name mysql_old -prune -o \
    -name oracle -prune -o \
    -name postgresql-prune -o \
    -name postgresql_psycopg2 -prune -o \
    -name sqlite3 -prune -o \
    -name test -prune -o \
    -type f ! -name \*.py[co] ! -name \*.[pm]o -print`

# Remove old $RELEASE directory.
rm -rf $RELEASE

# Create new $RELEASE directory.
mkdir $RELEASE

# Create symbolic links.
for x in $FILES $DIRS $ZIPFILE
do
    ln -s ../$x $RELEASE/$x
done
