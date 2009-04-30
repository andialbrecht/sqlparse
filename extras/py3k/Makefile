2TO3=2to3-3.0

all: sqlparse tests

sqlparse:
	cp -r ../../sqlparse .
	$(2TO3) sqlparse > sqlparse.diff
	patch -p0 < sqlparse.diff
	patch -p0 < fixes.diff

tests:
	cp -r ../../tests .
	$(2TO3) tests > tests.diff
	patch -p0 < tests.diff

clean:
	rm -rf sqlparse
	rm -rf tests
	rm -f sqlparse.diff
	rm -f tests.diff