from __future__ import print_function

from ._compat import string_types

import ast
import errno
import hashlib
import sys
import os
import shutil
import stat
import tempfile
import zipfile

from os.path import basename, isdir, isfile, islink, join

from enstaller.errors import InvalidFormat

if sys.version_info[:2] < (2, 7):
    class ZipFile(zipfile.ZipFile):
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            self.close()
else:
    ZipFile = zipfile.ZipFile

on_win = bool(sys.platform == 'win32')

if on_win:
    bin_dir_name = 'Scripts'
    rel_site_packages = r'Lib\site-packages'
else:
    bin_dir_name = 'bin'
    rel_site_packages = 'lib/python%i.%i/site-packages' % sys.version_info[:2]

ZIP_SOFTLINK_ATTRIBUTE_MAGIC = 0xA1ED0000

def rm_empty_dir(path):
    """
    Remove the directory `path` if it is a directory and empty.
    If the directory does not exist or is not empty, do nothing.
    """
    try:
        os.rmdir(path)
    except OSError: # directory might not exist or not be empty
        pass


def rm_rf(path, verbose=False):
    if not on_win and islink(path):
        # Note that we have to check if the destination is a link because
        # exists('/path/to/dead-link') will return False, although
        # islink('/path/to/dead-link') is True.
        if verbose:
            print("Removing: %r (link)" % path)
        os.unlink(path)

    elif isfile(path):
        if verbose:
            print("Removing: %r (file)" % path)
        if on_win:
            try:
                os.unlink(path)
            except (WindowsError, IOError):
                os.rename(path, join(tempfile.mkdtemp(), basename(path)))
        else:
            os.unlink(path)

    elif isdir(path):
        if verbose:
            print("Removing: %r (directory)" % path)
        if on_win:
            try:
                shutil.rmtree(path)
            except (WindowsError, IOError):
                os.rename(path, join(tempfile.mkdtemp(), basename(path)))
        else:
            shutil.rmtree(path)


def get_executable(prefix):
    if on_win:
        paths = [prefix, join(prefix, bin_dir_name)]
        for path in paths:
            executable = join(path, 'python.exe')
            if isfile(executable):
                return executable
    else:
        path = join(prefix, bin_dir_name, 'python')
        if isfile(path):
            from subprocess import Popen, PIPE
            cmd = [path, '-c', 'import sys;print(sys.executable)']
            p = Popen(cmd, stdout=PIPE)
            return p.communicate()[0].strip()
    return sys.executable


def human_bytes(n):
    """
    Return the number of bytes n in more human readable form.
    """
    if n < 1024:
        return '%i B' % n
    k = (n - 1) / 1024 + 1
    if k < 1024:
        return '%i KB' % k
    return '%.2f MB' % (float(n) / (2**20))

def makedirs(path):
    """Recursive directory creation function that does not fail if the
    directory already exists."""
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

def ensure_dir(path):
    """
    Create the parent directory of the give path, recursively is necessary.
    """
    makedirs(os.path.dirname(path))

def is_zipinfo_symlink(zip_info):
    """Return True if the given zip_info instance refers to a symbolic link."""
    return zip_info.external_attr == ZIP_SOFTLINK_ATTRIBUTE_MAGIC

def is_zipinfo_dir(zip_info):
    """Returns True if the given zip_info refers to a directory."""
    return stat.S_ISDIR(zip_info.external_attr >> 16)

def zip_write_symlink(fp, link_name, source):
    """Add to the zipfile the given link_name as a softlink to source

    Parameters
    ----------
    fp: file object
        ZipFile instance
    link_name: str
        Path of the symlink
    source: str
        Path the symlink points to (the output of os.readlink)
    """
    zip_info = zipfile.ZipInfo(link_name)
    zip_info.create_system = 3
    zip_info.external_attr = ZIP_SOFTLINK_ATTRIBUTE_MAGIC
    fp.writestr(zip_info, source)


class _AssignmentParser(ast.NodeVisitor):
    def __init__(self):
        self._data = {}

    def parse(self, s):
        self._data.clear()

        root = ast.parse(s)
        self.visit(root)
        return self._data

    def generic_visit(self, node):
        if type(node) != ast.Module:
            raise InvalidFormat("Unexpected expression @ line {0}".
                                format(node.lineno))
        super(_AssignmentParser, self).generic_visit(node)

    def visit_Assign(self, node):
        try:
            value = ast.literal_eval(node.value)
        except ValueError:
            msg = "Invalid configuration syntax at line {0}".format(node.lineno)
            raise InvalidFormat(msg)
        else:
            for target in node.targets:
                self._data[target.id] = value


def parse_assignments(file_or_filename):
    """
    Parse files which contain only python assignements, and returns the
    corresponding dictionary name: value

    Parameters
    ----------
    file_or_filename: str, file object
        If a string, interpreted as a filename. File object otherwise.
    """
    if isinstance(file_or_filename, string_types):
        with open(file_or_filename) as fp:
            return _AssignmentParser().parse(fp.read())
    else:
        return _AssignmentParser().parse(file_or_filename.read())


def compute_md5(path, block_size=256 * 1024):
    """Compute the md5 checksum of the given path.

    Avoids reading the whole file in RAM, and computes the md5 in chunks.

    Parameters
    ----------
    path: str or file object
        If a string, assumed to be the path to the file to be checksumed. If a
        file object, checksum will start at the current file position.
    block_size: int
        Block size to use when reading data.
    """
    m = hashlib.md5()

    def _compute_checksum(fp):
        while True:
            data = fp.read(block_size)
            m.update(data)
            if len(data) < block_size:
                break
        return m.hexdigest()

    if isinstance(path, string_types):
        with open(path, "rb") as fp:
            return _compute_checksum(fp)
    else:
        return _compute_checksum(path)
