.. _analyze:

Analyzing the Parsed Statement
==============================

When the :meth:`~sqlparse.parse` function is called the returned value
is a tree-ish representation of the analyzed statements. The returned
objects can be used by applications to retrieve further information about
the parsed SQL.


Base Classes
------------

All returned objects inherit from these base classes.
The :class:`~sqlparse.sql.Token` class represents a single token and
:class:`~sqlparse.sql.TokenList` class is a group of tokens.
The latter provides methods for inspecting its child tokens.

.. autoclass:: sqlparse.sql.Token
   :members:

.. autoclass:: sqlparse.sql.TokenList
   :members:


SQL Representing Classes
------------------------

The following classes represent distinct parts of a SQL statement.

.. autoclass:: sqlparse.sql.Statement
   :members:

.. autoclass:: sqlparse.sql.Comment
   :members:

.. autoclass:: sqlparse.sql.Identifier
   :members:

.. autoclass:: sqlparse.sql.IdentifierList
   :members:

.. autoclass:: sqlparse.sql.Where
   :members:

.. autoclass:: sqlparse.sql.Case
   :members:

.. autoclass:: sqlparse.sql.Parenthesis
   :members:

.. autoclass:: sqlparse.sql.If
   :members:

.. autoclass:: sqlparse.sql.For
   :members:

.. autoclass:: sqlparse.sql.Assignment
   :members:

.. autoclass:: sqlparse.sql.Comparison
   :members:

