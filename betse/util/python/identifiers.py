#!/usr/bin/env python3
# --------------------( LICENSE                            )--------------------
# Copyright 2014-2015 by Alexis Pietak & Cecil Curry
# See "LICENSE" for further details.

'''
Low-level **regex** (i.e., Python-compatible regular expression) facilities.
'''

# ....................{ IMPORTS                            }....................
from betse.util.type import regexes

# ....................{ CLASSES                            }....................
PYTHON_IDENTIFIER_CHAR_CLASS = r'a-zA-Z0-9_'
'''
Character class (excluding `[` and `]` delimiters) matching any character of a
**Python identifier** (i.e., class, function, module, or variable name).
'''

# ....................{ REGEXES                            }....................
PYTHON_IDENTIFIER_CAMEL_CASE_CHAR_REGEX_RAW = (
    r'(?:(?<=[a-z0-9])|(?!^))([A-Z])(?=[a-z]|$)')
'''
Uncompiled regular expression matching the next first character of a contiguous
run of uppercase characters in a CamelCase-formatted Python identifier (e.g.,
the `I` in `Capitel IV`), excluding the first character of such identifier..

== Examples ==

This expression is intended to be used in substitutions converting CamelCase to
some other format. For example, to convert CamelCase to snake_case:

    >>> from betse.util.type import regexes
    >>> regexes.substitute_substrings(
    ...     'MesseIoXaVIaX',
    ...     rexeges.PYTHON_IDENTIFIER_CAMEL_CASE_CHAR_REGEX_RAW,
    ...     r'_\1')
    Messe_io_xa_via_x
'''


PYTHON_IDENTIFIER_UNQUALIFIED_REGEX_RAW = r'[{}]+'.format(
    PYTHON_IDENTIFIER_CHAR_CLASS)
'''
Uncompiled regular expression matching an **unqualified Python identifier**
(i.e., class, function, module, or variable name _not_ prefixed by a package or
module name).
'''


PYTHON_IDENTIFIER_QUALIFIED_REGEX_RAW = (
    r'(?:{identifier_unqualified}\.)*{identifier_unqualified}'.format(
        identifier_unqualified = PYTHON_IDENTIFIER_UNQUALIFIED_REGEX_RAW))
'''
Uncompiled regular expression matching a **qualified Python identifier** (i.e.,
class, function, module, or variable name possibly prefixed by a package or
module name).
'''

# ....................{ CONVERTERS ~ camel                 }....................
def convert_camelcase_to_snakecase(text: str) -> str:
    '''
    Convert the passed CamelCase-formatted Python identifier to snake_case
    (e.g., from `ThePMRC` to `the_pmrc`).
    '''
    return regexes.substitute_substrings(
        text, PYTHON_IDENTIFIER_CAMEL_CASE_CHAR_REGEX_RAW, r'_\1').lower()


def convert_camelcase_to_whitespaced_lowercase(text: str) -> str:
    '''
    Convert the passed CamelCase-formatted Python identifier to whitespaced
    lowercase (e.g., from `CleanseIII` to `cleanse iii`).
    '''
    return regexes.substitute_substrings(
        text, PYTHON_IDENTIFIER_CAMEL_CASE_CHAR_REGEX_RAW, r' \1').lower()