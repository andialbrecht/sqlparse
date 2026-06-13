#
# Copyright (C) 2009-2020 the sqlparse authors and contributors
# <see AUTHORS file>
#
# This module is part of python-sqlparse and is released under
# the BSD License: https://opensource.org/licenses/BSD-3-Clause

"""SQL formatter"""

from sqlparse import filters
from sqlparse.exceptions import SQLParseError


# ─── Option validation schema ────────────────────────────────────────────────
# Each entry defines: valid values/coercion, side effects, and error messages.
# This replaces the repetitive if/raise pattern from the original code.

_BOOL_VALUES = [True, False]
_CASE_VALUES = [None, 'upper', 'lower', 'capitalize']
_OUTPUT_FORMAT_VALUES = [None, 'sql', 'python', 'php']


def _validate_choice(option_name, value, valid_choices):
    """Validate that a value is one of the allowed choices."""
    if value not in valid_choices:
        raise SQLParseError(f'Invalid value for {option_name}: {value!r}')


def _validate_positive_int(option_name, value, min_value=1):
    """Validate and coerce to a positive integer."""
    try:
        value = int(value)
    except (TypeError, ValueError):
        raise SQLParseError(f'{option_name} requires an integer')
    if value < min_value:
        raise SQLParseError(
            f'{option_name} requires a positive integer'
            if min_value == 1
            else f'{option_name} requires an integer > {min_value - 1}'
        )
    return value


def validate_options(options):
    """Validates formatting options using a declarative schema.

    Each option is validated according to its type and allowed values.
    Side effects (like setting dependent options) are applied after
    validation passes.
    """
    # ── Choice-type options ────────────────────────────────────────────────
    _validate_choice('keyword_case', options.get('keyword_case'), _CASE_VALUES)
    _validate_choice('identifier_case', options.get('identifier_case'), _CASE_VALUES)
    _validate_choice('output_format', options.get('output_format'), _OUTPUT_FORMAT_VALUES)
    _validate_choice('strip_comments', options.get('strip_comments', False), _BOOL_VALUES)
    _validate_choice('use_space_around_operators',
                     options.get('use_space_around_operators', False), _BOOL_VALUES)
    _validate_choice('strip_whitespace', options.get('strip_whitespace', False), _BOOL_VALUES)
    _validate_choice('reindent', options.get('reindent', False), _BOOL_VALUES)
    _validate_choice('reindent_aligned', options.get('reindent_aligned', False), _BOOL_VALUES)
    _validate_choice('indent_tabs', options.get('indent_tabs', False), _BOOL_VALUES)

    # ── Integer-type options ───────────────────────────────────────────────
    truncate_strings = options.get('truncate_strings')
    if truncate_strings is not None:
        truncate_strings = _validate_positive_int(
            'truncate_strings', truncate_strings, min_value=2)
        options['truncate_strings'] = truncate_strings
        options['truncate_char'] = options.get('truncate_char', '[...]')

    indent_width = options.get('indent_width', 2)
    options['indent_width'] = _validate_positive_int('indent_width', indent_width)

    wrap_after = options.get('wrap_after', 0)
    options['wrap_after'] = _validate_positive_int('wrap_after', wrap_after, min_value=0)

    right_margin = options.get('right_margin')
    if right_margin is not None:
        right_margin = _validate_positive_int(
            'right_margin', right_margin, min_value=11)
    options['right_margin'] = right_margin

    # ── Side effects: dependent options ────────────────────────────────────
    indent_columns = options.get('indent_columns', False)
    _validate_choice('indent_columns', indent_columns, _BOOL_VALUES)
    if indent_columns:
        options['reindent'] = True  # enforce reindent
    options['indent_columns'] = indent_columns

    indent_after_first = options.get('indent_after_first', False)
    _validate_choice('indent_after_first', indent_after_first, _BOOL_VALUES)
    options['indent_after_first'] = indent_after_first

    comma_first = options.get('comma_first', False)
    _validate_choice('comma_first', comma_first, _BOOL_VALUES)
    options['comma_first'] = comma_first

    compact = options.get('compact', False)
    _validate_choice('compact', compact, _BOOL_VALUES)
    options['compact'] = compact

    if options.get('reindent', False):
        options['strip_whitespace'] = True

    if options.get('reindent_aligned', False):
        options['strip_whitespace'] = True

    if options.get('indent_tabs', False):
        options['indent_char'] = '\t'
    else:
        options['indent_char'] = ' '

    return options


def build_filter_stack(stack, options):
    """Setup and return a filter stack.

    Args:
      stack: :class:`~sqlparse.filters.FilterStack` instance
      options: Dictionary with options validated by validate_options.
    """
    # Token filter
    if options.get('keyword_case'):
        stack.preprocess.append(
            filters.KeywordCaseFilter(options['keyword_case']))

    if options.get('identifier_case'):
        stack.preprocess.append(
            filters.IdentifierCaseFilter(options['identifier_case']))

    if options.get('truncate_strings'):
        stack.preprocess.append(filters.TruncateStringFilter(
            width=options['truncate_strings'], char=options['truncate_char']))

    if options.get('use_space_around_operators', False):
        stack.enable_grouping()
        stack.stmtprocess.append(filters.SpacesAroundOperatorsFilter())

    # After grouping
    if options.get('strip_comments'):
        stack.enable_grouping()
        stack.stmtprocess.append(filters.StripCommentsFilter())

    if options.get('strip_whitespace') or options.get('reindent'):
        stack.enable_grouping()
        stack.stmtprocess.append(filters.StripWhitespaceFilter())

    if options.get('reindent'):
        stack.enable_grouping()
        stack.stmtprocess.append(
            filters.ReindentFilter(
                char=options['indent_char'],
                width=options['indent_width'],
                indent_after_first=options['indent_after_first'],
                indent_columns=options['indent_columns'],
                wrap_after=options['wrap_after'],
                comma_first=options['comma_first'],
                compact=options['compact'],))

    if options.get('reindent_aligned', False):
        stack.enable_grouping()
        stack.stmtprocess.append(
            filters.AlignedIndentFilter(char=options['indent_char']))

    if options.get('right_margin'):
        stack.enable_grouping()
        stack.stmtprocess.append(
            filters.RightMarginFilter(width=options['right_margin']))

    # Serializer
    if options.get('output_format'):
        frmt = options['output_format']
        if frmt.lower() == 'php':
            fltr = filters.OutputPHPFilter()
        elif frmt.lower() == 'python':
            fltr = filters.OutputPythonFilter()
        else:
            fltr = None
        if fltr is not None:
            stack.postprocess.append(fltr)

    return stack
