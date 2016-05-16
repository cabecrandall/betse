#!/usr/bin/env python3
# --------------------( LICENSE                            )--------------------
# Copyright 2014-2016 by Alexis Pietak & Cecil Curry
# See "LICENSE" for further details.

'''
Low-level operating system kernel facilities.

Caveats
----------
Operating system-specific logic is poor form and should be leveraged only where
necessary.
'''

# ....................{ IMPORTS                            }....................
import platform
from betse.util.os import oses
from collections import OrderedDict

# ....................{ GETTERS                            }....................
def get_name() -> str:
    '''
    Human-readable name of the current operating system kernel.

    This function returns:

    * Under Linux, `Linux`.
    * Under OS X, `Darwin`.
    * Under Windows, `Windows`.
    * Under all other platforms, the string returned by the `platform.system()`
      function.
    '''

    # Return platform.system() as is, which appears to exactly corresponding to
    # the name of the current kernel on all platforms (e.g., "Darwin", "Linux")
    return platform.system()


def get_version() -> str:
    '''
    Human-readable `.`-delimited version specifier string of the current
    operating system kernel.

    This function returns:

    * Under Linux, the current Linux kernel version (e.g., `4.1.15-gentoo-r1`),
    * Under OS X, the current XNU kernel version (e.g., `13.0.0`).
    * Under Windows, the current Windows API version (e.g., `6.2.9200`).
    * Under all other platforms, the string returned by both the
      `get_version()` and `platform.release()` functions.
    '''

    # Version specifier to be returned, defaulting to that returned by
    # platform.release(). While this typically corresponds to the low-level
    # version of the current kernel (e.g., "4.1.15" under Linux, "13.0.0" under
    # OS X), this is *NOT* necessarily the case (e.g., "8" rather than
    # "6.2.9200" under Windows). Hence, this is only a fallback.
    kernel_version = platform.release()

    # If the Windows-specific platform.win32_ver() function is available, return
    # the second element of the 4-tuple "(release, version, csd, ptype)"
    # returned by this function (e.g., "6.2.9200"). Since platform.release()
    # returns the high-level operating system version (e.g., "8"), this version
    # is ignored when feasible.
    if oses.is_windows() and hasattr(platform, 'win32_ver'):
        kernel_version = platform.win32_ver()[1]
    # If Linux, OS X, or other platforms, accept the default version specifier
    # returned by platform.release() (e.g., "4.1.15", "13.0.0").

    # Return this version.
    return kernel_version

# ....................{ GETTERS ~ metadata                 }....................
def get_metadata() -> OrderedDict:
    '''
    Get an ordered dictionary synopsizing the current operating system kernel.
    '''

    return OrderedDict((
        ('name', get_name()),
        ('version', get_version()),
    ))