#!/usr/bin/env python3
# --------------------( LICENSE                            )--------------------
# Copyright 2014-2017 by Alexis Pietak & Cecil Curry
# See "LICENSE" for further details.

'''
Low-level directory facilities.
'''

# ....................{ IMPORTS                            }....................
import os, shutil
from betse.exceptions import BetseDirException
from betse.util.io.log import logs
from betse.util.type.types import (
    type_check,
    GeneratorType,
    IterableOrNoneTypes,
    NumericTypes,
    SequenceTypes,
)
from distutils import dir_util
from os import path

# ....................{ GLOBALS                            }....................
# There exist only two possible directory separators for all modern platforms.
# Hence, this reliably suffices with no error handling required.
SEPARATOR_REGEX = r'/' if path.sep == '/' else r'\\'
'''
Regular expression matching the directory separator specific to the current
platform.

Specifically, under:

* Microsoft Windows, this is `\\\\`.
* All other platforms, this is `/`.
'''

# ....................{ EXCEPTIONS                         }....................
def die_if_dir(*dirnames: str) -> None:
    '''
    Raise an exception if any of the passed directories exist.
    '''

    for dirname in dirnames:
        if is_dir(dirname):
            raise BetseDirException(
                'Directory "{}" already exists.'.format(dirname))


def die_unless_dir(*dirnames: str) -> None:
    '''
    Raise an exception unless all passed directories exist.
    '''

    for dirname in dirnames:
        if not is_dir(dirname):
            raise BetseDirException(
                'Directory "{}" not found or unreadable.'.format(dirname))


def join_and_die_unless_dir(*pathnames: str) -> str:
    '''
    Pathname of the directory produced by joining (i.e., concatenating) the
    passed pathnames with the directory separator specific to the current
    platform if this directory exists *or* raise an exception otherwise (i.e.,
    if this directory does *not* exist).

    See Also
    -----------
    :func:`betse.util.path.pathnames.join`
    :func:`die_unless_dir`
        Further details.
    '''

    # Avoid circular import dependencies.
    from betse.util.path.pathnames import join

    # Dirname producing by joining these pathnames.
    dirname = join(*pathnames)

    # If this directory does *NOT* exist, raise an exception.
    die_unless_dir(dirname)

    # Return this dirname.
    return dirname

# ....................{ EXCEPTIONS ~ parent                }....................
def die_unless_parent_dir(pathname: str) -> None:
    '''
    Raise an exception unless the parent directory of the passed path exists.
    '''

    # Avoid circular import dependencies.
    from betse.util.path import pathnames

    # If the parent directory of this path does *NOT* exist, raise an exception.
    die_unless_dir(pathnames.get_dirname(pathname))

# ....................{ TESTERS                            }....................
@type_check
def is_dir(dirname: str) -> bool:
    '''
    ``True`` only if the passed directory exists.
    '''

    return path.isdir(dirname)

# ....................{ GETTERS ~ mtime : recursive        }....................
#FIXME: Consider contributing the get_mtime_recursive_newest() function as an
#answer to the following StackOverflow question:
#    https://stackoverflow.com/questions/26498285/find-last-update-time-of-a-directory-includes-all-levels-of-sub-folders

# If the current platform provides the os.fwalk() function *AND* the os.stat()
# function implemented by this platform accepts directory handles (which is
# currently equivalent to testing if this platform is POSIX-compatible),
# optimize this recursion by leveraging these handles.
if hasattr(os, 'fwalk') and os.stat in os.supports_dir_fd:
    @type_check
    def get_mtime_recursive_newest(dirname: str) -> NumericTypes:

        # Avoid circular import dependencies.
        from betse.util.io.exceptions import raise_exception

        # Log this recursion.
        logs.log_debug(
            'Recursively computing newest fwalk()-based mtime of: %s', dirname)

        # Return the maximum of all mtimes in the...
        return max(
            # Generator expression recursively yielding the maximum mtime of all
            # files and subdirectories of each subdirectory of this directory
            # including this directory.
            (
                # Maximum of this subdirectory's mtime and the mtimes of all
                # files in this subdirectory, whose filenames are produced by a
                # tuple comprehension joining this subdirectory's dirname to
                # each file's basename. By recursion, the mtimes of all
                # subdirectories of this subdirectory are implicitly computed
                # and hence need *NOT* be explicitly included here.
                #
                # For parity with the unoptimized get_mtime_recursive_newest()
                # implementation defined below as well to avoid unwanted
                # complications, symbolic links are *NOT* followed. Hence,
                # os.lstat() rather than os.stat() is intentionally called.
                max(
                    (os.fstat(parent_dir_fd).st_mtime,) + tuple(
                        os.lstat(
                            child_file_basename, dir_fd=parent_dir_fd).st_mtime
                        for child_file_basename in child_file_basenames
                    ),
                )
                # For the currently visited directory's dirname, a sequence of
                # the dirnames of all subdirectories of this directory, a
                # sequence of the filenames of all files in this directory, and
                # a directory handle to this directory such that errors emitted
                # by low-level functions called by os.walk() (e.g.,
                # os.listdir()) are *NOT* silently ignored...
                for _, _, child_file_basenames, parent_dir_fd
                 in os.fwalk(dirname, onerror=raise_exception)
            ),
        )

# Else, fallback to unoptimized recursion leveraging dirnames.
else:
    @type_check
    def get_mtime_recursive_newest(dirname: str) -> NumericTypes:

        # Avoid circular import dependencies.
        from betse.util.io.exceptions import raise_exception

        # Log this recursion.
        logs.log_debug(
            'Recursively computing newest walk()-based mtime of: %s', dirname)

        # Return the maximum of all mtimes in the...
        return max(
            # Generator expression recursively yielding the maximum mtime of all
            # files and subdirectories of each subdirectory of this directory
            # including this directory.
            (
                # Maximum of this subdirectory's mtime and the mtimes of all
                # files in this subdirectory, whose filenames are produced by a
                # tuple comprehension joining this subdirectory's dirname to
                # each file's basename. By recursion, the mtimes of all
                # subdirectories of this subdirectory are implicitly computed
                # and hence need *NOT* be explicitly included here.
                max(
                    (path.getmtime(parent_dirname),) + tuple(
                        path.getmtime(path.join(
                            parent_dirname, child_file_basename))
                        for child_file_basename in child_file_basenames
                    ),
                )
                # For the currently visited directory's dirname, a sequence of
                # the dirnames of all subdirectories of this directory, and a
                # sequence of the filenames of all files in this directory such
                # that errors emitted by low-level functions called by
                # os.walk() (e.g., os.listdir()) are *NOT* silently ignored...
                for parent_dirname, _, child_file_basenames
                 in os.walk(dirname, onerror=raise_exception)
            ),
        )

# Docstring dynamically set for the getter defined above.
get_mtime_recursive_newest.__doc__ = '''
    Most recent **recursive mtime** (i.e., recursively calculated modification
    time) in seconds of all paths in the set of this directory and all files and
    subdirectories transitively reachable from this directory *witthout*
    following symbolic links to directories.

    Caveats
    -----------
    Note that symbolic links whose transitive targets are:

    * Directories are *not* followed, avoiding infinite recursion in edge cases
      (e.g., directories containing symbolic links to themselves). Such links
      are effectively non-directory files. Since the mtime of a symbolic link is
      typically its ctime (i.e., creation time), such links thus contribute
      their own ctime to this calculation.
    * Files are followed, improving the accuracy of this calculation.

    Parameters
    -----------
    dirname : str
        Absolute or relative path of the directory to inspect.

    Returns
    -----------
    NumericTypes
        Most recent mtime in seconds of this directory calculated recursively as
        either an integer or float, depending on the boolean returned by the
        platform-specific :func:`os.stat_float_times` function.

    Raises
    -----------
    OSError
        If either this directory *or* any file or subdirectory reachable from
        this directory is unreadable by the current user (e.g., due to
        insufficient permissions).
    '''

# ....................{ COPIERS                            }....................
@type_check
def copy_into_dir(src_dirname: str, trg_dirname: str, *args, **kwargs) -> None:
    '''
    Recursively copy the passed source directory to a subdirectory of the passed
    target directory having the same basename as this source directory.

    Parameters
    -----------
    src_dirname : str
        Absolute or relative path of the source directory to be recursively
        copied from.
    trg_dirname : str
        Absolute or relative path of the target directory to copy into.

    All remaining parameters are passed as is to the :func:`copy` function.

    See Also
    ----------
    :func:`copy`
        Further details.

    Examples
    ----------
        >>> from betse.util.path import dirs
        >>> dirs.copy_into_dir('/usr/src/linux/', '/tmp/')
        >>> dirs.is_dir('/tmp/linux/')
        True
    '''

    # Avoid circular import dependencies.
    from betse.util.path import pathnames

    # Basename of this source directory.
    src_basename = pathnames.get_basename(src_dirname)

    # Absolute or relative path of the target directory to copy to.
    trg_subdirname = pathnames.join(trg_dirname, src_basename)

    # Recursively copy this source to target directory.
    copy(*args, src_dirname=src_dirname, trg_dirname=trg_subdirname, **kwargs)


@type_check
def copy(
    # Mandatory parameters.
    src_dirname: str,
    trg_dirname: str,

    # Optional parameters.
    is_overwritable: bool = False,
    ignore_basename_globs: IterableOrNoneTypes = None,
) -> None:
    '''
    Recursively copy the passed source to target directory.

    All nonexistent parents of the target directory will be recursively created,
    mimicking the action of the ``mkdir -p`` shell command. All symbolic links
    in the source directory will be preserved (i.e., copied as is rather than
    their transitive targets copied instead).

    Parameters
    -----------
    src_dirname : str
        Absolute or relative path of the source directory to be recursively
        copied from.
    trg_dirname : str
        Absolute or relative path of the target directory to recursively copy to.
    is_overwritable : optional[bool]
        If this target directory already exists and this boolean is ``True``,
        this directory is silently updated with the contents of this source
        directory; else, an exception is raised. For safety, all child paths of
        this target directory *not* also child paths of this source directory
        are preserved as is rather than removed. Defaults to ``False``.
    ignore_basename_globs : optional[IterableTypes]
        Iterable of shell-style globs (e.g., ``('*.tmp', '.keep')``) matching
        the basenames of all paths transitively owned by this source directory
        to be ignored during recursion and hence neither copied nor visited.
        If non-``None`` and the ``is_overwritable`` parameter is ``True``, this
        iterable is ignored and a non-fatal warning logged. Defaults to
        ``None``, in which case *all* paths transitively owned by this source
        directory are unconditionally copied and visited.

    Raises
    -----------
    BetseDirException
        If:
        * The source directory does not exist.
        * One or more subdirectories of the target directory already exist that
          are also subdirectories of the source directory. For safety, this
          function always preserves rather than overwrites existing target
          subdirectories.
    '''

    # Log this copy.
    logs.log_debug('Copying directory: %s -> %s', src_dirname, trg_dirname)

    # Raise an exception unless the source directory exists.
    die_unless_dir(src_dirname)

    # If overwriting the contents of this target directory with those of this
    # source directory...
    if is_overwritable:
        # If an iterable of shell-style globs matching ignorable basenames was
        # passed, log a non-fatal warning. Since the dir_util.copy_tree()
        # function fails to support such functionality and we are currently too
        # lazy to do so, a warning is as much as we're willing to give.
        if ignore_basename_globs is not None:
            logs.log_warning(
                'dirs.copy() parameter "ignore_basename_globs" '
                'ignored when parameter "is_overwritable" enabled.')

        # Recursively copy this source to target directory, preserving symbolic
        # links as is. To silently overwrite all conflicting target paths, the
        # dir_util.copy_tree() rather than shutil.copytree() function is called.
        dir_util.copy_tree(
            src=src_dirname, trg=trg_dirname, preserve_symlinks=1)
    else:
        # Dictionary of all keyword arguments to pass to shutil.copytree(),
        # preserving symbolic links as is.
        copytree_kwargs = {
            'symlinks': True,
        }

        # If an iterable of shell-style globs matching ignorable basenames was
        # passed, convert this iterable into a predicate function of the form
        # required by the shutil.copytree() function.
        if ignore_basename_globs is not None:
            copytree_kwargs['ignore'] = shutil.ignore_patterns(
                *ignore_basename_globs)

        # Raise an exception if this target directory already exists. While we
        # could defer to the exception raised by the shutil.copytree() function
        # for this case, this exception's message erroneously refers to this
        # directory as a file and is hence best avoided as non-human-readable:
        #
        #     [Errno 17] File exists: 'sample_sim'
        die_if_dir(trg_dirname)

        # Recursively copy this source to target directory. To avoid silently
        # overwriting all conflicting target paths, the shutil.copytree() rather
        # than dir_util.copy_tree() function is called.
        shutil.copytree(src=src_dirname, dst=trg_dirname, **copytree_kwargs)

# ....................{ MAKERS                             }....................
@type_check
def make_unless_dir(dirname: str) -> None:
    '''
    Create the directory with the passed path if this directory does not already
    exist *or* noop otherwise.

    All nonexistent parents of this directory are also recursively created,
    reproducing the action of the POSIX-compliant ``mkdir -p`` shell command.

    See Also
    -----------
    :func:`make_parent_unless_dir`
        Related function creating the parent directory of this path.
    '''

    # If this directory does *NOT* already exist, create this directory. To
    # support logging, this condition is explicitly tested for. To avoid race
    # conditions (e.g., in the event this directory is created between testing
    # and creating this directory), we preserve the makedirs() keyword argument
    # "exist_ok=True" below.
    if not is_dir(dirname):
        # Log this creation.
        logs.log_debug('Creating directory: %s', dirname)

        # Create this directory if still needed.
        os.makedirs(dirname, exist_ok=True)


def make_parent_unless_dir(*pathnames: str) -> None:
    '''
    Create the parent directory of each passed path for each such directory that
    does not already exist.

    See Also
    -----------
    :func:`make_unless_dir`
        Further details.
    '''

    # Avoid circular import dependencies.
    from betse.util.path.pathnames import get_dirname, canonicalize

    # Canonicalize each pathname *BEFORE* attempting to get its dirname.
    # Relative pathnames do *NOT* have sane dirnames (e.g., the dirname for a
    # relative pathname "metatron" is the empty string) and hence *MUST* be
    # converted to absolute pathnames first.
    for pathname in pathnames:
        make_unless_dir(get_dirname(canonicalize(pathname)))

# ....................{ MAKERS ~ convenience               }....................
def canonicalize_and_make_unless_dir(dirname: str) -> str:
    '''
    Create the directory with the passed absolute or relative path if this
    directory does not already exist and return the **canonical form** (i.e.,
    unique absolute path) of this path.

    This convenience function chains the lower-level
    :func:`betse.util.path.pathnames.canonicalize` and
    :func:`make_unless_dir` functions.
    '''

    # Avoid circular import dependencies.
    from betse.util.path import pathnames

    # Dirname canonicalized from this possibly non-canonical dirname.
    dirname = pathnames.canonicalize(dirname)

    # Create this directory if needed.
    make_unless_dir(dirname)

    # Return this dirname.
    return dirname


def join_and_make_unless_dir(*partnames: str) -> str:
    '''
    Join (i.e., concatenate) the passed pathnames with the directory separator
    specific to the current platform, create the directory with the resulting
    absolute or relative path, and return this path.

    This convenience function chains the lower-level
    :func:`betse.util.path.pathnames.join` and :func:`make_unless_dir`
    functions.
    '''

    # Avoid circular import dependencies.
    from betse.util.path import pathnames

    # Dirname joined from these pathnames.
    dirname = pathnames.join(*partnames)

    # Create this directory if needed.
    make_unless_dir(dirname)

    # Return this dirname.
    return dirname

# ....................{ ITERATORS                          }....................
#FIXME: For orthogonality, rename to iter_basenames().
def list_basenames(dirname: str) -> SequenceTypes:
    '''
    Sequence of the basenames of all paths (e.g., non-directory files,
    subdirectories) directly contained within the passed directory.
    '''

    # If this directory does *NOT* exist, raise an exception.
    die_unless_dir(dirname)

    # Sequence of all such basenames.
    return os.listdir(dirname)


def iter_subdirnames(dirname: str) -> GeneratorType:
    '''
    Generator yielding the pathname of each direct subdirectory of the passed
    parent directory.

    Parameters
    -----------
    dirname : str
        Absolute or relative path of the parent directory to inspect.

    Returns
    -----------
    GeneratorType
        Generator yielding direct subdirectory pathnames.

    Yields
    -----------
    str
        Absolute or relative path of each direct subdirectory of this directory.

    See Also
    -----------
    https://stackoverflow.com/a/25705093/2809027
        StackOverflow answer strongly inspiring this implementation.
    '''

    # Avoid circular import dependencies.
    from betse.util.io.exceptions import raise_exception

    # Sequence of the basenames of all subdirectories of this directory
    # implemented as follows:
    #
    # * The generator returned by os.walk() is iterated once and then promptly
    #   discarded, yielding:
    #   * The ignorable absolute or relative path of this parent directory,
    #     which we (of course) were passed as input and thus already have.
    #   * This desired sequence.
    #   * An ignorable sequence of the basenames of all files of this directory.
    # * Errors emitted by low-level functions called by os.walk() (e.g.,
    #   os.listdir()) are *NOT* silently ignored.
    _, subdir_basenames, _ = next(os.walk(dirname, onerror=raise_exception))

    # Return a generator comprehension prefixing each such basename by the
    # absolute or relative path of the parent directory.
    return (
        path.join(dirname, subdir_basename)
        for subdir_basename in subdir_basenames
    )
