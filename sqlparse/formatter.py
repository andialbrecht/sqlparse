# Copyright (C) 2008 Andi Albrecht, albrecht.andi@gmail.com
#
# This module is part of python-sqlparse and is released under
# the BSD License: http://www.opensource.org/licenses/bsd-license.php.

"""SQL formatter"""

from sqlparse import filters
from sqlparse.exceptions import SQLParseError


def validate_options(options):
    """Validates options."""
    kwcase = options.get('keyword_case', None)
    if kwcase not in [None, 'upper', 'lower', 'capitalize']:
        raise SQLParseError('Invalid value for keyword_case: %r' % kwcase)

    idcase = options.get('identifier_case', None)
    if idcase not in [None, 'upper', 'lower', 'capitalize']:
        raise SQLParseError('Invalid value for identifier_case: %r' % idcase)

    ofrmt = options.get('output_format', None)
    if ofrmt not in [None, 'sql', 'python', 'php']:
        raise SQLParseError('Unknown output format: %r' % ofrmt)

    strip_comments = options.get('strip_comments', False)
    if strip_comments not in [True, False]:
        raise SQLParseError('Invalid value for strip_comments: %r'
                            % strip_comments)

    use_space_around_operators = options.get('use_space_around_operators', False)
    if use_space_around_operators not in [True, False]:
        raise SQLParseError('Invalid value for use_space_around_operators: %r'
                            % use_space_around_operators)

    strip_ws = options.get('strip_whitespace', False)
    if strip_ws not in [True, False]:
        raise SQLParseError('Invalid value for strip_whitespace: %r'
                            % strip_ws)

    truncate_strings = options.get('truncate_strings', None)
    if truncate_strings is not None:
        try:
            truncate_strings = int(truncate_strings)
        except (ValueError, TypeError):
            raise SQLParseError('Invalid value for truncate_strings: %r'
                                % truncate_strings)
        if truncate_strings <= 1:
            raise SQLParseError('Invalid value for truncate_strings: %r'
                                % truncate_strings)
        options['truncate_strings'] = truncate_strings
        options['truncate_char'] = options.get('truncate_char', '[...]')

    reindent = options.get('reindent', False)
    if reindent not in [True, False]:
        raise SQLParseError('Invalid value for reindent: %r'
                            % reindent)
    elif reindent:
        options['strip_whitespace'] = True

    reindent_aligned = options.get('reindent_aligned', False)
    if reindent_aligned not in [True, False]:
        raise SQLParseError('Invalid value for reindent_aligned: %r'
                            % reindent)
    elif reindent_aligned:
        options['strip_whitespace'] = True

    indent_tabs = options.get('indent_tabs', False)
    if indent_tabs not in [True, False]:
        raise SQLParseError('Invalid value for indent_tabs: %r' % indent_tabs)
    elif indent_tabs:
        options['indent_char'] = '\t'
    else:
        options['indent_char'] = ' '
    indent_width = options.get('indent_width', 2)
    try:
        indent_width = int(indent_width)
    except (TypeError, ValueError):
        raise SQLParseError('indent_width requires an integer')
    if indent_width < 1:
        raise SQLParseError('indent_width requires an positive integer')
    options['indent_width'] = indent_width

    right_margin = options.get('right_margin', None)
    if right_margin is not None:
        try:
            right_margin = int(right_margin)
        except (TypeError, ValueError):
            raise SQLParseError('right_margin requires an integer')
        if right_margin < 10:
            raise SQLParseError('right_margin requires an integer > 10')
    options['right_margin'] = right_margin

    return options


def _add_grouping_and_remove_whitespace(stack):
    stack.enable_grouping()
    stack.stmtprocess.append(filters.StripWhitespaceFilter())


def build_filter_stack(stack, options):
    """Setup and return a filter stack.

    Args:
      stack: :class:`~sqlparse.filters.FilterStack` instance
      options: Dictionary with options validated by validate_options.
    """
    # Token filter
    if options.get('keyword_case', None):
        stack.preprocess.append(
            filters.KeywordCaseFilter(options['keyword_case']))

    if options.get('identifier_case', None):
        stack.preprocess.append(
            filters.IdentifierCaseFilter(options['identifier_case']))

    if options.get('truncate_strings', None) is not None:
        stack.preprocess.append(filters.TruncateStringFilter(
            width=options['truncate_strings'], char=options['truncate_char']))

    if options.get('use_space_around_operators', False):
        stack.enable_grouping()
        stack.stmtprocess.append(filters.SpacesAroundOperatorsFilter())

    # After grouping
    if options.get('strip_comments', False):
        stack.enable_grouping()
        stack.stmtprocess.append(filters.StripCommentsFilter())

    if options.get('strip_whitespace', False):
        _add_grouping_and_remove_whitespace(stack)

    if options.get('reindent', False):
        _add_grouping_and_remove_whitespace(stack)
        stack.stmtprocess.append(
            filters.ReindentFilter(char=options['indent_char'],
                                   width=options['indent_width']))

    if options.get('reindent_aligned', False):
        _add_grouping_and_remove_whitespace(stack)
        stack.stmtprocess.append(
            filters.AlignedIndentFilter(char=options['indent_char']))

    if options.get('right_margin', False):
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
