# -*- coding: utf-8 -*-

import pytest

import sqlparse
from sqlparse import sql, tokens as T


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_grouping_parenthesis(sql_dialect):
    s = 'select (select (x3) x2) and (y2) bar'
    parsed = sqlparse.parse(s, sql_dialect=sql_dialect)[0]
    assert str(parsed) == s
    assert len(parsed.tokens) == 7
    assert isinstance(parsed.tokens[2], sql.Parenthesis)
    assert isinstance(parsed.tokens[-1], sql.Identifier)
    assert len(parsed.tokens[2].tokens) == 5
    assert isinstance(parsed.tokens[2].tokens[3], sql.Identifier)
    assert isinstance(parsed.tokens[2].tokens[3].tokens[0], sql.Parenthesis)
    assert len(parsed.tokens[2].tokens[3].tokens) == 3


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_grouping_comments(sql_dialect):
    s = '/*\n * foo\n */   \n  bar'
    parsed = sqlparse.parse(s, sql_dialect=sql_dialect)[0]
    assert str(parsed) == s
    assert len(parsed.tokens) == 2


@pytest.mark.parametrize('s', ['foo := 1;', 'foo := 1'])
def test_grouping_assignment(s):
    parsed = sqlparse.parse(s)[0]
    assert len(parsed.tokens) == 1
    assert isinstance(parsed.tokens[0], sql.Assignment)


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_grouping_identifiers(sql_dialect):
    s = 'select foo.bar from "myscheme"."table" where fail. order'
    parsed = sqlparse.parse(s, sql_dialect=sql_dialect)[0]
    assert str(parsed) == s
    assert isinstance(parsed.tokens[2], sql.Identifier)
    assert isinstance(parsed.tokens[6], sql.Identifier)
    assert isinstance(parsed.tokens[8], sql.Where)
    s = 'select * from foo where foo.id = 1'
    parsed = sqlparse.parse(s, sql_dialect=sql_dialect)[0]
    assert str(parsed) == s
    assert isinstance(parsed.tokens[-1].tokens[-1].tokens[0], sql.Identifier)
    s = 'select * from (select "foo"."id" from foo)'
    parsed = sqlparse.parse(s, sql_dialect=sql_dialect)[0]
    assert str(parsed) == s
    assert isinstance(parsed.tokens[-1].tokens[3], sql.Identifier)

    s = "INSERT INTO `test` VALUES('foo', 'bar');"
    parsed = sqlparse.parse(s)[0]
    types = [l.ttype for l in parsed.tokens if not l.is_whitespace]
    assert types == [T.DML, T.Keyword, None, T.Keyword, None, T.Punctuation]

    s = "select 1.0*(a+b) as col, sum(c)/sum(d) from myschema.mytable"
    parsed = sqlparse.parse(s, sql_dialect=sql_dialect)[0]
    assert len(parsed.tokens) == 7
    assert isinstance(parsed.tokens[2], sql.IdentifierList)
    assert len(parsed.tokens[2].tokens) == 4
    identifiers = list(parsed.tokens[2].get_identifiers())
    assert len(identifiers) == 2
    assert identifiers[0].get_alias() == "col"


@pytest.mark.parametrize(['s', 'sql_dialect'], [
    ('1 as f', None),
    ('foo as f', None),
    ('foo f', None),
    ('1/2 as f', None),
    ('1/2 f', None),
    ('1<2 as f', None),  # issue327
    ('1<2 f', None),
    ('1 as f', 'TransactSQL'),
    ('foo as f', 'TransactSQL'),
    ('foo f', 'TransactSQL'),
    ('1/2 as f', 'TransactSQL'),
    ('1/2 f', 'TransactSQL'),
    ('1<2 as f', 'TransactSQL'),  # issue327
    ('1<2 f', 'TransactSQL')
])
def test_simple_identifiers(s, sql_dialect):
    parsed = sqlparse.parse(s, sql_dialect=sql_dialect)[0]
    assert isinstance(parsed.tokens[0], sql.Identifier)


@pytest.mark.parametrize('s', [
    'foo, bar',
    'sum(a), sum(b)',
    'sum(a) as x, b as y',
    'sum(a)::integer, b',
    'sum(a)/count(b) as x, y',
    'sum(a)::integer as x, y',
    'sum(a)::integer/count(b) as x, y',  # issue297
])
def test_group_identifier_list(s):
    parsed = sqlparse.parse(s)[0]
    assert isinstance(parsed.tokens[0], sql.IdentifierList)


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_grouping_identifier_wildcard(sql_dialect):
    p = sqlparse.parse('a.*, b.id', sql_dialect=sql_dialect)[0]
    assert isinstance(p.tokens[0], sql.IdentifierList)
    assert isinstance(p.tokens[0].tokens[0], sql.Identifier)
    assert isinstance(p.tokens[0].tokens[-1], sql.Identifier)


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_grouping_identifier_name_wildcard(sql_dialect):
    p = sqlparse.parse('a.*', sql_dialect=sql_dialect)[0]
    t = p.tokens[0]
    assert t.get_name() == '*'
    assert t.is_wildcard() is True


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_grouping_identifier_invalid(sql_dialect):
    p = sqlparse.parse('a.', sql_dialect=sql_dialect)[0]
    assert isinstance(p.tokens[0], sql.Identifier)
    assert p.tokens[0].has_alias() is False
    assert p.tokens[0].get_name() is None
    assert p.tokens[0].get_real_name() is None
    assert p.tokens[0].get_parent_name() == 'a'


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_grouping_identifier_invalid_in_middle(sql_dialect):
    # issue261
    s = 'SELECT foo. FROM foo'
    p = sqlparse.parse(s, sql_dialect=sql_dialect)[0]
    assert isinstance(p[2], sql.Identifier)
    assert p[2][1].ttype == T.Punctuation
    assert p[3].ttype == T.Whitespace
    assert str(p[2]) == 'foo.'


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_grouping_identifier_as_invalid(sql_dialect):
    # issue8
    p = sqlparse.parse('foo as select *', sql_dialect=sql_dialect)[0]
    assert len(p.tokens), 5
    assert isinstance(p.tokens[0], sql.Identifier)
    assert len(p.tokens[0].tokens) == 1
    assert p.tokens[2].ttype == T.Keyword


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_grouping_identifier_function(sql_dialect):
    p = sqlparse.parse('foo() as bar', sql_dialect=sql_dialect)[0]
    assert isinstance(p.tokens[0], sql.Identifier)
    assert isinstance(p.tokens[0].tokens[0], sql.Function)
    p = sqlparse.parse('foo()||col2 bar')[0]
    assert isinstance(p.tokens[0], sql.Identifier)
    assert isinstance(p.tokens[0].tokens[0], sql.Operation)
    assert isinstance(p.tokens[0].tokens[0].tokens[0], sql.Function)


@pytest.mark.parametrize(['s', 'sql_dialect'], [('foo+100', None),
                                                ('foo + 100', None),
                                                ('foo*100', None),
                                                ('foo+100', 'TransactSQL'),
                                                ('foo + 100', 'TransactSQL'),
                                                ('foo*100', 'TransactSQL')])
def test_grouping_operation(s, sql_dialect):
    p = sqlparse.parse(s, sql_dialect=sql_dialect)[0]
    assert isinstance(p.tokens[0], sql.Operation)


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_grouping_identifier_list(sql_dialect):
    p = sqlparse.parse('a, b, c', sql_dialect=sql_dialect)[0]
    assert isinstance(p.tokens[0], sql.IdentifierList)
    p = sqlparse.parse('(a, b, c)')[0]
    assert isinstance(p.tokens[0].tokens[1], sql.IdentifierList)


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_grouping_identifier_list_subquery(sql_dialect):
    """identifier lists should still work in subqueries with aliases"""
    p = sqlparse.parse("select * from ("
                       "select a, b + c as d from table) sub",
                       sql_dialect=sql_dialect)[0]
    subquery = p.tokens[-1].tokens[0]
    idx, iden_list = subquery.token_next_by(i=sql.IdentifierList)
    assert iden_list is not None
    # all the identifiers should be within the IdentifierList
    _, ilist = subquery.token_next_by(i=sql.Identifier, idx=idx)
    assert ilist is None


def test_grouping_identifier_list_case():
    p = sqlparse.parse('a, case when 1 then 2 else 3 end as b, c')[0]
    assert isinstance(p.tokens[0], sql.IdentifierList)
    p = sqlparse.parse('(a, case when 1 then 2 else 3 end as b, c)')[0]
    assert isinstance(p.tokens[0].tokens[1], sql.IdentifierList)


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_grouping_identifier_list_other(sql_dialect):
    # issue2
    p = sqlparse.parse("select *, null, 1, 'foo', bar from mytable, x",
                       sql_dialect=sql_dialect)[0]
    assert isinstance(p.tokens[2], sql.IdentifierList)
    assert len(p.tokens[2].tokens) == 13


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_grouping_identifier_list_with_inline_comments(sql_dialect):
    # issue163
    p = sqlparse.parse('foo /* a comment */, bar',
                       sql_dialect=sql_dialect)[0]
    assert isinstance(p.tokens[0], sql.IdentifierList)
    assert isinstance(p.tokens[0].tokens[0], sql.Identifier)
    assert isinstance(p.tokens[0].tokens[3], sql.Identifier)


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_grouping_identifiers_with_operators(sql_dialect):
    p = sqlparse.parse('a+b as c from table where (d-e)%2= 1',
                       sql_dialect=sql_dialect)[0]
    assert len([x for x in p.flatten() if x.ttype == T.Name]) == 5


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_grouping_identifier_list_with_order(sql_dialect):
    # issue101
    p = sqlparse.parse('1, 2 desc, 3', sql_dialect=sql_dialect)[0]
    assert isinstance(p.tokens[0], sql.IdentifierList)
    assert isinstance(p.tokens[0].tokens[3], sql.Identifier)
    assert str(p.tokens[0].tokens[3]) == '2 desc'


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_grouping_where(sql_dialect):
    s = 'select * from foo where bar = 1 order by id desc'
    p = sqlparse.parse(s, sql_dialect=sql_dialect)[0]
    assert str(p) == s
    assert len(p.tokens) == 14

    s = 'select x from (select y from foo where bar = 1) z'
    p = sqlparse.parse(s)[0]
    assert str(p) == s
    assert isinstance(p.tokens[-1].tokens[0].tokens[-2], sql.Where)


@pytest.mark.parametrize(['s', 'sql_dialect'], (
    ('select 1 where 1 = 2 union select 2', None),
    ('select 1 where 1 = 2 union all select 2', None),
    ('select 1 where 1 = 2 union select 2', 'TransactSQL'),
    ('select 1 where 1 = 2 union all select 2', 'TransactSQL')

))
def test_grouping_where_union(s, sql_dialect):
    p = sqlparse.parse(s, sql_dialect=sql_dialect)[0]
    assert p.tokens[5].value.startswith('union')


def test_returning_kw_ends_where_clause():
    s = 'delete from foo where x > y returning z'
    p = sqlparse.parse(s)[0]
    assert isinstance(p.tokens[6], sql.Where)
    assert p.tokens[7].ttype == T.Keyword
    assert p.tokens[7].value == 'returning'


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_into_kw_ends_where_clause(sql_dialect):  # issue324
    s = 'select * from foo where a = 1 into baz'
    p = sqlparse.parse(s, sql_dialect=sql_dialect)[0]
    assert isinstance(p.tokens[8], sql.Where)
    assert p.tokens[9].ttype == T.Keyword
    assert p.tokens[9].value == 'into'


@pytest.mark.parametrize('sql, expected', [
    # note: typecast needs to be 2nd token for this test
    ('select foo::integer from bar', 'integer'),
    ('select (current_database())::information_schema.sql_identifier',
     'information_schema.sql_identifier'),
])
def test_grouping_typecast(sql, expected):
    p = sqlparse.parse(sql)[0]
    assert p.tokens[2].get_typecast() == expected


# TODO
def test_grouping_alias():
    s = 'select foo as bar from mytable'
    p = sqlparse.parse(s)[0]
    assert str(p) == s
    assert p.tokens[2].get_real_name() == 'foo'
    assert p.tokens[2].get_alias() == 'bar'
    s = 'select foo from mytable t1'
    p = sqlparse.parse(s)[0]
    assert str(p) == s
    assert p.tokens[6].get_real_name() == 'mytable'
    assert p.tokens[6].get_alias() == 't1'
    s = 'select foo::integer as bar from mytable'
    p = sqlparse.parse(s)[0]
    assert str(p) == s
    assert p.tokens[2].get_alias() == 'bar'
    s = ('SELECT DISTINCT '
         '(current_database())::information_schema.sql_identifier AS view')
    p = sqlparse.parse(s)[0]
    assert str(p) == s
    assert p.tokens[4].get_alias() == 'view'


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_grouping_alias_case(sql_dialect):
    # see issue46
    p = sqlparse.parse('CASE WHEN 1 THEN 2 ELSE 3 END foo',
                       sql_dialect=sql_dialect)[0]
    assert len(p.tokens) == 1
    assert p.tokens[0].get_alias() == 'foo'


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_grouping_subquery_no_parens(sql_dialect):
    # Not totally sure if this is the right approach...
    # When a THEN clause contains a subquery w/o parenthesis around it *and*
    # a WHERE condition, the WHERE grouper consumes END too.
    # This takes makes sure that it doesn't fail.
    p = sqlparse.parse('CASE WHEN 1 THEN select 2 where foo = 1 end',
                       sql_dialect=sql_dialect)[0]
    assert len(p.tokens) == 1
    assert isinstance(p.tokens[0], sql.Case)


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_grouping_alias_returns_none(sql_dialect):
    # see issue185
    p = sqlparse.parse('foo.bar', sql_dialect=sql_dialect)[0]
    assert len(p.tokens) == 1
    assert p.tokens[0].get_alias() is None


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_grouping_idlist_function(sql_dialect):
    # see issue10 too
    p = sqlparse.parse('foo(1) x, bar', sql_dialect=sql_dialect)[0]
    assert isinstance(p.tokens[0], sql.IdentifierList)


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_grouping_comparison_exclude(sql_dialect):
    # make sure operators are not handled too lazy
    p = sqlparse.parse('(=)', sql_dialect=sql_dialect)[0]
    assert isinstance(p.tokens[0], sql.Parenthesis)
    assert not isinstance(p.tokens[0].tokens[1], sql.Comparison)
    p = sqlparse.parse('(a=1)', sql_dialect=sql_dialect)[0]
    assert isinstance(p.tokens[0].tokens[1], sql.Comparison)
    p = sqlparse.parse('(a>=1)', sql_dialect=sql_dialect)[0]
    assert isinstance(p.tokens[0].tokens[1], sql.Comparison)


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_grouping_function(sql_dialect):
    p = sqlparse.parse('foo()', sql_dialect=sql_dialect)[0]
    assert isinstance(p.tokens[0], sql.Function)
    p = sqlparse.parse('foo(null, bar)')[0]
    assert isinstance(p.tokens[0], sql.Function)
    assert len(list(p.tokens[0].get_parameters())) == 2


def test_grouping_function_not_in():
    # issue183
    p = sqlparse.parse('in(1, 2)')[0]
    assert len(p.tokens) == 2
    assert p.tokens[0].ttype == T.Keyword
    assert isinstance(p.tokens[1], sql.Parenthesis)


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_grouping_varchar(sql_dialect):
    p = sqlparse.parse('"text" Varchar(50) NOT NULL',
                       sql_dialect=sql_dialect)[0]
    assert isinstance(p.tokens[2], sql.Function)


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_statement_get_type(sql_dialect):
    def f(sql):
        return sqlparse.parse(sql, sql_dialect=sql_dialect)[0]

    assert f('select * from foo').get_type() == 'SELECT'
    assert f('update foo').get_type() == 'UPDATE'
    assert f(' update foo').get_type() == 'UPDATE'
    assert f('\nupdate foo').get_type() == 'UPDATE'
    assert f('foo').get_type() == 'UNKNOWN'
    # Statements that have a whitespace after the closing semicolon
    # are parsed as two statements where later only consists of the
    # trailing whitespace.
    assert f('\n').get_type() == 'UNKNOWN'


def test_identifier_with_operators():
    # issue 53
    p = sqlparse.parse('foo||bar')[0]
    assert len(p.tokens) == 1
    assert isinstance(p.tokens[0], sql.Operation)
    # again with whitespaces
    p = sqlparse.parse('foo || bar')[0]
    assert len(p.tokens) == 1
    assert isinstance(p.tokens[0], sql.Operation)


def test_identifier_with_op_trailing_ws():
    # make sure trailing whitespace isn't grouped with identifier
    p = sqlparse.parse('foo || bar ')[0]
    assert len(p.tokens) == 2
    assert isinstance(p.tokens[0], sql.Operation)
    assert p.tokens[1].ttype is T.Whitespace


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_identifier_with_string_literals(sql_dialect):
    p = sqlparse.parse("foo + 'bar'", sql_dialect=sql_dialect)[0]
    assert len(p.tokens) == 1
    assert isinstance(p.tokens[0], sql.Operation)


# This test seems to be wrong. It was introduced when fixing #53, but #111
# showed that this shouldn't be an identifier at all. I'm leaving this
# commented in the source for a while.
# def test_identifier_string_concat():
#     p = sqlparse.parse("'foo' || bar")[0]
#     assert len(p.tokens) == 1
#     assert isinstance(p.tokens[0], sql.Identifier)


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_identifier_consumes_ordering(sql_dialect):
    # issue89
    p = sqlparse.parse('select * from foo order by c1 desc, c2, c3',
                       sql_dialect=sql_dialect)[0]
    assert isinstance(p.tokens[-1], sql.IdentifierList)
    ids = list(p.tokens[-1].get_identifiers())
    assert len(ids) == 3
    assert ids[0].get_name() == 'c1'
    assert ids[0].get_ordering() == 'DESC'
    assert ids[1].get_name() == 'c2'
    assert ids[1].get_ordering() is None


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_comparison_with_keywords(sql_dialect):
    # issue90
    # in fact these are assignments, but for now we don't distinguish them
    p = sqlparse.parse('foo = NULL', sql_dialect=sql_dialect)[0]
    assert len(p.tokens) == 1
    assert isinstance(p.tokens[0], sql.Comparison)
    assert len(p.tokens[0].tokens) == 5
    assert p.tokens[0].left.value == 'foo'
    assert p.tokens[0].right.value == 'NULL'
    # make sure it's case-insensitive
    p = sqlparse.parse('foo = null')[0]
    assert len(p.tokens) == 1
    assert isinstance(p.tokens[0], sql.Comparison)


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_comparison_with_floats(sql_dialect):
    # issue145
    p = sqlparse.parse('foo = 25.5', sql_dialect=sql_dialect)[0]
    assert len(p.tokens) == 1
    assert isinstance(p.tokens[0], sql.Comparison)
    assert len(p.tokens[0].tokens) == 5
    assert p.tokens[0].left.value == 'foo'
    assert p.tokens[0].right.value == '25.5'


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_comparison_with_parenthesis(sql_dialect):
    # issue23
    p = sqlparse.parse('(3 + 4) = 7', sql_dialect=sql_dialect)[0]
    assert len(p.tokens) == 1
    assert isinstance(p.tokens[0], sql.Comparison)
    comp = p.tokens[0]
    assert isinstance(comp.left, sql.Parenthesis)
    assert comp.right.ttype is T.Number.Integer


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_comparison_with_strings(sql_dialect):
    # issue148
    p = sqlparse.parse("foo = 'bar'", sql_dialect=sql_dialect)[0]
    assert len(p.tokens) == 1
    assert isinstance(p.tokens[0], sql.Comparison)
    assert p.tokens[0].right.value == "'bar'"
    assert p.tokens[0].right.ttype == T.String.Single


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_comparison_with_functions(sql_dialect):
    # issue230
    p = sqlparse.parse('foo = DATE(bar.baz)', sql_dialect=sql_dialect)[0]
    assert len(p.tokens) == 1
    assert isinstance(p.tokens[0], sql.Comparison)
    assert len(p.tokens[0].tokens) == 5
    assert p.tokens[0].left.value == 'foo'
    assert p.tokens[0].right.value == 'DATE(bar.baz)'

    p = sqlparse.parse('DATE(foo.bar) = DATE(bar.baz)',
                       sql_dialect=sql_dialect)[0]
    assert len(p.tokens) == 1
    assert isinstance(p.tokens[0], sql.Comparison)
    assert len(p.tokens[0].tokens) == 5
    assert p.tokens[0].left.value == 'DATE(foo.bar)'
    assert p.tokens[0].right.value == 'DATE(bar.baz)'

    p = sqlparse.parse('DATE(foo.bar) = bar.baz', sql_dialect=sql_dialect)[0]
    assert len(p.tokens) == 1
    assert isinstance(p.tokens[0], sql.Comparison)
    assert len(p.tokens[0].tokens) == 5
    assert p.tokens[0].left.value == 'DATE(foo.bar)'
    assert p.tokens[0].right.value == 'bar.baz'


@pytest.mark.parametrize('start', ['FOR', 'FOREACH'])
def test_forloops(start):
    p = sqlparse.parse('{0} foo in bar LOOP foobar END LOOP'.format(start))[0]
    assert (len(p.tokens)) == 1
    assert isinstance(p.tokens[0], sql.For)


def test_nested_for():
    p = sqlparse.parse('FOR foo LOOP FOR bar LOOP END LOOP END LOOP')[0]
    assert len(p.tokens) == 1
    for1 = p.tokens[0]
    assert for1.tokens[0].value == 'FOR'
    assert for1.tokens[-1].value == 'END LOOP'
    for2 = for1.tokens[6]
    assert isinstance(for2, sql.For)
    assert for2.tokens[0].value == 'FOR'
    assert for2.tokens[-1].value == 'END LOOP'


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_begin(sql_dialect):
    p = sqlparse.parse('BEGIN foo END', sql_dialect=sql_dialect)[0]
    assert len(p.tokens) == 1
    assert isinstance(p.tokens[0], sql.Begin)


def test_keyword_followed_by_parenthesis():
    p = sqlparse.parse('USING(somecol')[0]
    assert len(p.tokens) == 3
    assert p.tokens[0].ttype == T.Keyword
    assert p.tokens[1].ttype == T.Punctuation


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_nested_begin(sql_dialect):
    p = sqlparse.parse('BEGIN foo BEGIN bar END END',
                       sql_dialect=sql_dialect)[0]
    assert len(p.tokens) == 1
    outer = p.tokens[0]
    assert outer.tokens[0].value == 'BEGIN'
    assert outer.tokens[-1].value == 'END'
    inner = outer.tokens[4]
    assert inner.tokens[0].value == 'BEGIN'
    assert inner.tokens[-1].value == 'END'
    assert isinstance(inner, sql.Begin)


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_aliased_column_without_as(sql_dialect):
    p = sqlparse.parse('foo bar',
                       sql_dialect=sql_dialect)[0].tokens
    assert len(p) == 1
    assert p[0].get_real_name() == 'foo'
    assert p[0].get_alias() == 'bar'

    p = sqlparse.parse('foo.bar baz',
                       sql_dialect=sql_dialect)[0].tokens[0]
    assert p.get_parent_name() == 'foo'
    assert p.get_real_name() == 'bar'
    assert p.get_alias() == 'baz'


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_qualified_function(sql_dialect):
    p = sqlparse.parse('foo()',
                       sql_dialect=sql_dialect)[0].tokens[0]
    assert p.get_parent_name() is None
    assert p.get_real_name() == 'foo'

    p = sqlparse.parse('foo.bar()',
                       sql_dialect=sql_dialect)[0].tokens[0]
    assert p.get_parent_name() == 'foo'
    assert p.get_real_name() == 'bar'


def test_aliased_function_without_as():
    p = sqlparse.parse('foo() bar')[0].tokens[0]
    assert p.get_parent_name() is None
    assert p.get_real_name() == 'foo'
    assert p.get_alias() == 'bar'

    p = sqlparse.parse('foo.bar() baz')[0].tokens[0]
    assert p.get_parent_name() == 'foo'
    assert p.get_real_name() == 'bar'
    assert p.get_alias() == 'baz'


def test_aliased_literal_without_as():
    p = sqlparse.parse('1 foo')[0].tokens
    assert len(p) == 1
    assert p[0].get_alias() == 'foo'
