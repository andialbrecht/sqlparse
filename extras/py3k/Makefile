2TO3=2to3
2TO3OPTS=--no-diffs -w -n

all: sqlparse tests

sqlparse:
	cp -r ../../sqlparse .
	$(2TO3) $(2TO3OPTS) sqlparse
	patch -p0 < fixes.diff

tests:
	cp -r ../../tests .
	$(2TO3) $(2TO3OPTS) tests

clean:
	rm -rf sqlparse
	rm -rf tests
	rm -f sqlparse.diff
	rm -f tests.diff