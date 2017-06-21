#!/usr/bin/env python3
# --------------------( LICENSE                            )--------------------
# Copyright 2014-2017 by Alexis Pietak & Cecil Curry.
# See "LICENSE" for further details.

'''
Metadata constants synopsizing high-level application behaviour.

Python Version
----------
For uniformity between this codebase and the ``setup.py`` setuptools script
importing this module, this module also validates the version of the active
Python 3 interpreter. An exception is raised if this version is insufficient.

This application currently requires **Python 3.4**, as Python < 3.4:

* Provides insufficient machinery for dynamically inspecting modules at runtime.
  In particular, both the long-standing :func:`imp.find_module` function and the
  :func:`importlib.find_loader` function introduced by Python 3.3 require all
  parent packages of the passed module to be recursively imported *before* these
  functions are called; failing to do so results in these functions
  unconditionally returning ``None``. Since this has been the source of numerous
  subtle issues throughout this codebase, Python 3.3 is strictly out. Since most
  modern Linux distributions have adopted Python 3.4 as the default Python
  3 interpreters, this *should* impose no hardship.
* Fails to provide the :mod:`enum` module introduced by Python 3.4, which both
  standardizes and simplifies enumeration implementations.
'''

# ....................{ IMPORTS                            }....................
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# WARNING: To avoid race conditions during setuptools-based installation, this
# module may import *ONLY* from modules guaranteed to exist at the start of
# installation. This includes all standard Python and application modules but
# *NOT* third-party dependencies, which if currently uninstalled will only be
# installed at some later time in the installation.
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

import sys

# ....................{ METADATA                           }....................
NAME = 'BETSE'
'''
Human-readable application name.
'''


LICENSE = '2-clause BSD'
'''
Human-readable name of the license this application is licensed under.
'''

# ....................{ PYTHON ~ version                   }....................
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# WARNING: Changes to this section *MUST* be synchronized with:
# * The corresponding section of the "betsee.metadata" submodule.
# * Front-facing documentation (e.g., "README.rst", "doc/md/INSTALL.md").
# On bumping the minimum required version of Python, consider also documenting
# the justification for doing so in the "Python Version" section of this
# submodule's docstring above.
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

PYTHON_VERSION_MIN = '3.4.0'
'''
Human-readable minimum version of Python required by this application as a
``.``-delimited string.
'''


def _convert_version_str_to_tuple(version_str: str) -> tuple:
    '''
    Convert the passed human-readable ``.``-delimited version string into a
    machine-readable version tuple of corresponding integers.
    '''
    assert isinstance(version_str, str), (
        '"{}" not a version string.'.format(version_str))

    return tuple(
        int(version_part) for version_part in version_str.split('.'))


PYTHON_VERSION_MIN_PARTS = _convert_version_str_to_tuple(PYTHON_VERSION_MIN)
'''
Machine-readable minimum version of Python required by this application as a
tuple of integers.
'''


# Validate the version of the active Python interpreter *BEFORE* subsequent code
# possibly depending on such version. Since such version should be validated
# both at setuptools-based install time and post-install runtime *AND* since
# this module is imported sufficiently early by both, stash such validation here
# to avoid duplication of such logic and hence the hardcoded Python version.
#
# The "sys" module exposes three version-related constants for this purpose:
#
# * "hexversion", an integer intended to be specified in an obscure (albeit
#   both efficient and dependable) hexadecimal format: e.g.,
#    >>> sys.hexversion
#    33883376
#    >>> '%x' % sys.hexversion
#    '20504f0'
# * "version", a human-readable string: e.g.,
#    >>> sys.version
#    2.5.2 (r252:60911, Jul 31 2008, 17:28:52)
#    [GCC 4.2.3 (Ubuntu 4.2.3-2ubuntu7)]
# * "version_info", a tuple of three or more integers *OR* strings: e.g.,
#    >>> sys.version_info
#    (2, 5, 2, 'final', 0)
#
# For sanity, this application will *NEVER* conditionally depend upon the
# string-formatted release type of the current Python version exposed via the
# fourth element of the "version_info" tuple. Since the first three elements of
# that tuple are guaranteed to be integers *AND* since a comparable 3-tuple of
# integers is declared above, comparing the former and latter yield the simplest
# and most reliable Python version test.
#
# Note that the nearly decade-old and officially accepted PEP 345 proposed a new
# field "requires_python" configured via a key-value pair passed to the call to
# setup() in "setup.py" (e.g., "requires_python = ['>=2.2.1'],"), that field has
# yet to be integrated into either disutils or setuputils. Hence, that field is
# validated manually in the typical way. Behead the infidel setuptools!
if sys.version_info[:3] < PYTHON_VERSION_MIN_PARTS:
    # Human-readable current version of Python. "sys.version" is sufficiently
    # overly verbose as to be unusuable, sadly.
    PYTHON_VERSION = '.'.join(
        str(version_part) for version_part in sys.version_info[:3])

    # Die ignominiously.
    raise RuntimeError(
        '{} requires at least Python {}, but the active Python interpreter '
        'is only Python {}. We feel deep sadness for you.'.format(
            NAME, PYTHON_VERSION_MIN, PYTHON_VERSION))

# ....................{ METADATA ~ version                 }....................
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# WARNING: When modifying the current version of this application below,
# consider adhering to the Semantic Versioning schema. Specifically, the version
# should consist of three "."-delimited integers "{major}.{minor}.{patch}",
# where:
#
# * "{major}" specifies the major version, incremented only when either:
#   * Breaking configuration file backward compatibility. Since this
#     application's public API is its configuration file format rather than a
#     subset of the code itself (e.g., public subpackages, submodules, classes),
#     no change to the code itself can be considered to break backward
#     compatibility unless that change breaks the configuration file format.
#   * Implementing headline-worthy functionality (e.g., a GUI). Technically,
#     this condition breaks the Semantic Versioning schema, which stipulates
#     that *ONLY* changes breaking backward compatibility warrant major bumps.
#     But this is the real world. In the real world, significant improvements
#     are rewarded with significant version changes.
#   In either case, the minor and patch versions both reset to 0.
# * "{minor}" specifies the minor version, incremented only when implementing
#   customary functionality in a manner preserving such compatibility. In this
#   case, the patch version resets to 0.
# * "{patch}" specifies the patch version, incremented only when correcting
#   outstanding issues in a manner preserving such compatibility.
#
# When in doubt, increment only the minor version and reset the patch version.
# For further details, see http://semver.org.
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

VERSION = '0.5.1'
'''
Human-readable application version as a ``.``-delimited string.
'''


CODENAME = 'Happier Hodgkin'
'''
Human-readable code name associated with the current version of this
application.

This code name consists of an arbitrary adjective followed by the last name of
an arbitrary academic associated with field of bioelectricity whose first letter
is the same as the first letter of that adjective.

See Also
----------
:download:`/doc/rst/RELEASE.md`
    Further details on this incredible code name schema.
'''


VERSION_PARTS = _convert_version_str_to_tuple(VERSION)
'''
Machine-readable application version as a tuple of integers.
'''

# ....................{ METADATA ~ synopsis                }....................
# Note that a human-readable multiline description is exposed via the top-level
# "setup.py" script. This description is inefficiently culled from the contents
# of the top-level "README.rst" file and hence omitted here. (Doing so here
# would significantly increase program startup costs with little to no benefit.)
SYNOPSIS = 'BETSE, the Bioelectric Tissue Simulation Engine.'
'''
Human-readable single-line synopsis of this application.

By PyPI design, this string must *not* span multiple lines or paragraphs.
'''


DESCRIPTION = (
    'The Bioelectric Tissue Simulation Engine (BETSE) is a '
    'finite volume simulator for 2D computational multiphysics problems in '
    'the life sciences -- including electrodiffusion, electro-osmosis, '
    'galvanotaxis, voltage-gated ion channels, gene regulatory networks, '
    'and biochemical reaction networks.'
)
'''
Human-readable multiline description of this application.

By :mod:`argparse` design, this string may (and typically should) span both
multiple lines and paragraphs. Note that this string is *not* published to PyPI,
which accepts reStructuredText (rst) and is thus passed the contents of the
top-level :doc:`/README` file instead.
'''

# ....................{ METADATA ~ authors                 }....................
AUTHORS = 'Alexis Pietak, Cecil Curry, et al.'
'''
Human-readable list of all principal authors of this application as a
comma-delimited string.

For brevity, this string *only* lists authors explicitly assigned copyrights.
For the list of all contributors regardless of copyright assignment or
attribution, see the top-level `AUTHORS.md` file.
'''


AUTHOR_EMAIL = 'alexis.pietak@gmail.com'
'''
Email address of the principal corresponding author (i.e., the principal author
responding to public correspondence).
'''

# ....................{ METADATA ~ urls                    }....................
URL_HOMEPAGE = 'https://gitlab.com/betse/betse'
'''
URL of this application's homepage.
'''


URL_DOWNLOAD = (
    'https://gitlab.com/betse/betse/repository/archive.tar.gz?ref=v{}'.format(
        VERSION,
    )
)
'''
URL of the source tarball for the current version of this application.

This URL assumes a tag whose name is ``v{VERSION}`` where ``{VERSION}`` is the
human-readable current version of this application (e.g., ``v0.4.0``) to exist.
Typically, no such tag exists for live versions of this application -- which
have yet to be stabilized and hence tagged. Hence, this URL is typically valid
*only* for previously released (rather than live) versions of this application.
'''

# ....................{ METADATA ~ python                  }....................
PACKAGE_NAME = NAME.lower()
'''
Fully-qualified name of the top-level Python package implementing this
application.
'''


SCRIPT_BASENAME = PACKAGE_NAME
'''
Basename of the CLI-specific Python script wrapper created by :mod:`setuptools`
installation.
'''

# ....................{ METADATA ~ libs                    }....................
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# WARNING: Changes to this subsection *MUST* be synchronized with:
# * Front-facing documentation (e.g., "doc/md/INSTALL.md").
# * The "betse.util.type.modules.DISTUTILS_PROJECT_NAME_TO_MODULE_NAME"
#   dictionary, converting between the setuptools-specific names listed below
#   and the Python-specific module names imported by this application.
# * Gitlab-CI configuration (e.g., the top-level "requirements-conda.txt" file).
# * Third-party platform-specific packages (e.g., Gentoo Linux ebuilds).
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

DEPENDENCIES_RUNTIME_MANDATORY = {
    # setuptools is currently required at both install and runtime. At runtime,
    # setuptools is used to validate that dependencies are available.
    'setuptools': '>= 3.3',

    # Dependencies directly required by this application.
    'Numpy': '>= 1.8.0',
    'PyYAML': '>= 3.10',
    'SciPy': '>= 0.12.0',
    'dill': '>= 0.2.3',

    # Matplotlib >= 1.5.0 is required for the newly added "viridis" colormap.
    'matplotlib': '>= 1.5.0',

    # Dependencies indirectly required by this application but only optionally
    # required by dependencies directly required by this application. Since the
    # "setup.py" scripts for the latter do *NOT* list these dependencies as
    # mandatory, these dependencies *MUST* be explicitly listed here.
    'Pillow': '>= 2.3.0',    # required by the "scipy.misc.imread" module

    # Dependencies directly required by dependencies directly required by this
    # application. While these dependencies need *NOT* be explicitly listed
    # here, doing so improves detection of missing dependencies in a
    # human-readable manner.
    'six': '>= 1.5.2',       # required by everything that should not be
}
'''
Dictionary mapping from the :mod:`setuptools`-specific project name of each
mandatory runtime dependency for this application to the suffix of a
:mod:`setuptools`-specific requirements string constraining this dependency.

To simplify subsequent lookup, these dependencies are contained by a dictionary
rather than a simple set or sequence such that each:

* Key is the name of a :mod:`setuptools`-specific project identifying this
  dependency, which may have no relation to the name of that project's top-level
  module or package (e.g., the ``PyYAML`` project's top-level package is
  :mod:`yaml`). For human readability in error messages, this name should
  typically be case-sensitively capitalized -- despite being parsed
  case-insensitively by :mod:`setuptools`.
* Value is either:
  * ``None`` or the empty string, in which case this dependency is unconstrained
    (i.e., any version of this dependency is sufficient).
  * A string of the form ``{comparator} {version}``, where:
    * ``{comparator}`` is a comparison operator (e.g., ``>=``, ``!=``).
    * ``{version}`` is the required version of this project to compare.

Concatenating each such key and value yields a :mod:`setuptools`-specific
requirements string of the form either ``{project_name}`` or ``{project_name}
{comparator} {version}``.

Official :mod:`setuptools` documentation suggests the ``install_requires`` and
``setup_requires`` keys of the ``setup()`` packaging function to accept only
sequences rather than dictionaries of strings. While undocumented, these keys
*do* actually accept both sequences and dictionaries of strings.

Caveats
----------
This application requires :mod:`setuptools` at both installation time *and*
runtime -- in the latter case, to validate all application dependencies at
runtime. Note that doing so technically only requires the :mod:`pkg_resources`
package installed with :mod:`setuptools` rather than the :mod:`setuptools`
package itself. Since there exists no means of asserting a dependency on only
:mod:`pkg_resources`, however, :mod:`setuptools` is depended upon instead.

See Also
----------
https://setuptools.readthedocs.io/en/latest/setuptools.html#id12
    Further details on the :mod:`setuptools` string format for dependencies.
:download:`/doc/md/INSTALL.md`
    Human-readable list of these dependencies.
'''


#FIXME: Should these be dependencies also be added to our "setup.py" metadata,
#perhaps as so-called "extras"? Contemplate. Consider. Devise.
DEPENDENCIES_RUNTIME_OPTIONAL = {
    # To simplify subsequent lookup at runtime, project names for optional
    # dependencies should be *STRICTLY LOWERCASE*. Since setuptools parses
    # project names case-insensitively, case is only of internal relevance.

    # Dependencies directly required by this application.
    'pympler': '>= 0.4.1',
    'pprofile': '>= 1.8',
    'ptpython': '>= 0.29',

    # A relatively modern version of NetworkX *EXCLUDING* 1.11, which
    # critically broke backwards compatibility by coercing use of the unofficial
    # inactive "pydotplus" PyDot fork rather than the official active "pydot"
    # PyDot project, is directly required by this application. NetworkX >= 1.12
    # reverted to supporting "pydot", thus warranting blacklisting of only
    # NetworkX 1.11. It is confusing, maybe?
    'networkx': '>= 1.8, != 1.11',
    'pydot': '>= 1.0.28',
}
'''
Dictionary mapping from the :mod:`setuptools`-specific project name of each
optional runtime dependency for this application to the suffix of a
:mod:`setuptools`-specific requirements string constraining this dependency.

See Also
----------
:data:`DEPENDENCIES_RUNTIME_MANDATORY`
    Further details on dictionary structure.
:download:`/doc/md/INSTALL.md`
    Human-readable list of these dependencies.
:func:`get_dependencies_runtime_optional_tuple`
    Function converting this dictionary of key-value string pairs into a tuple
    of strings (e.g., within :download:`/setup.py`).
'''


DEPENDENCIES_TESTING_MANDATORY = {
    # For simplicity, py.test should remain the only hard dependency for testing
    # on local machines. While our setuptools-driven testing regime optionally
    # leverages third-party py.test plugins (e.g., "pytest-xdist"), these
    # plugins are *NOT* required for simple testing.
    'pytest': '>= 2.5.0',
}
'''
Dictionary mapping from the :mod:`setuptools`-specific project name of each
mandatory testing dependency for this application to the suffix of a
:mod:`setuptools`-specific requirements string constraining this dependency.

See Also
----------
:data:`DEPENDENCIES_RUNTIME_MANDATORY`
    Further details on dictionary structure.
:download:`/doc/md/INSTALL.md`
    Human-readable list of these dependencies.
'''

# ....................{ METADATA ~ libs : external         }....................
class DependencyCommand(object):
    '''
    Lightweight metadata describing a single external command required by some
    application dependency (of any type, including optional, mandatory, runtime,
    testing, or otherwise).

    Attributes
    ----------
    name : str
        Human-readable name associated with this command (e.g., ``Graphviz``).
    basename : str
        Basename of this command to be searched for in the current ``${PATH}``.
    '''

    def __init__(self, name: str, basename: str) -> None:
        self.name = name
        self.basename = basename


#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# WARNING: Changes to this dictionary *MUST* be synchronized with:
# * Front-facing documentation (e.g., "doc/md/INSTALL.md").
# * Gitlab-CI configuration (e.g., the top-level "requirements-conda.txt" file).
# * Third-party platform-specific packages (e.g., Gentoo Linux ebuilds).
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
DEPENDENCIES_COMMANDS = {
    'pydot': (DependencyCommand(name='Graphviz', basename='dot'),),
}
'''
Dictionary mapping from the :mod:`setuptools`-specific project name of each
application dependency (of any type, including optional, mandatory, runtime,
testing, or otherwise) requiring one or more external commands to a tuple of
:class:`DependencyCommand` instances describing these requirements.

See Also
----------
:download:`/doc/md/INSTALL.md`
    Human-readable list of these dependencies.
'''

# ....................{ METADATA ~ private                 }....................
_IS_TESTING = False
'''
``True`` only if the active Python interpreter is running a test session (e.g.,
with the ``py.test`` test harness).

This private global is subject to change and thus *not* intended to be publicly
accessed. Consider calling the public :func:`betse.util.py.pys.is_testing`
function instead.
'''
