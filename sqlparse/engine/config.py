#
# Copyright (C) 2009-2020 the sqlparse authors and contributors
# <see AUTHORS file>
#
# This module is part of python-sqlparse and is released under
# the BSD License: https://opensource.org/licenses/BSD-3-Clause

from sqlparse.engine import grouping


def set_max_grouping_tokens(limit: int | None) -> None:
    """Set the token limit used by grouping operations.

    ``None`` disables the limit and should only be used for trusted input.
    Positive integer values replace the default limit.
    """
    if limit is not None and (
        isinstance(limit, bool) or not isinstance(limit, int) or limit < 1
    ):
        raise ValueError("limit must be a positive integer or None")

    grouping.MAX_GROUPING_TOKENS = limit
