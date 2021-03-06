# Copyright 2006-2012 Mark Diekhans
"""Miscellaneous file operations"""

import os, errno, sys, stat, fcntl, socket, random, shutil, string, gzip


class TemporaryFilePath(object):
    """
    Generates a path pointing to a temporary file. Context manager wrapper for tmpFileGet.
    """
    def __init__(self, prefix=None, suffix="tmp", tmpDir=None):
        self.path = tmpFileGet(prefix=prefix, suffix=suffix, tmpDir=tmpDir)

    def __enter__(self):
        return self.path

    def __exit__(self, type, value, traceback):
        rmFiles(self.path)


class TemporaryDirectoryPath(object):
    """
    Generates a path pointing to a temporary directory. Context manager wrapper for tmpFileGet,
    except creates a directory out of the path.
    """
    def __init__(self, prefix=None, suffix="tmp", tmpDir=None):
        self.path = tmpFileGet(prefix=prefix, suffix=suffix, tmpDir=tmpDir)
        ensureDir(self.path)

    def __enter__(self):
        return self.path

    def __exit__(self, type, value, traceback):
        rmTree(self.path)


_pipelineMod = None
def _getPipelineClass():
    """To avoid mutual import issues, we get the Pipeline class dynamically on
    first use"""
    global _pipelineMod
    if _pipelineMod is None:
        _pipelineMod = __import__("pycbio.sys.pipeline", fromlist=["pycbio.sys.pipeline"])
    return _pipelineMod.Pipeline

def ensureDir(dir):
    """Ensure that a directory exists, creating it (and parents) if needed."""
    try:
        os.makedirs(dir)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(dir):
            pass
        elif len(dir) == 0:
            pass
        else:
            raise

def ensureFileDir(file_path):
    """Ensure that the parent directory for a file exists"""
    dir = os.path.dirname(file_path)
    try:
        os.makedirs(dir)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(dir):
            pass
        elif len(dir) == 0:
            pass
        else:
            raise

def rmFiles(files):
    """remove one or more files if they exist. files can be a single file
    name of a list of file names"""
    if isinstance(files, str):
        if os.path.exists(files):
            os.unlink(files)
    else:
        for f in files:
            if os.path.exists(f):
                os.unlink(f)

def rmTree(root):
    "In case anyone has any legacy uses"
    shutil.rmtree(root)

def isCompressed(path):
    "determine if a file appears to be compressed by extension"
    return path.endswith(".gz") or path.endswith(".bz2") or path.endswith(".Z")

def compressCmd(path, default="cat"):
    """return the command to compress the path, or default if not compressed, which defaults
    to the `cat' command, so that it just gets written through"""
    if path.endswith(".Z"):
        raise Exception("writing compress .Z files not supported")
    elif path.endswith(".gz"):
        return "gzip"
    elif path.endswith(".bz2"):
        return "bzip2"
    else:
        return default

def decompressCmd(path, default="cat"):
    """"return the command to decompress the file to stdout, or default if not compressed, which defaults
    to the `cat' command, so that it just gets written through"""
    if path.endswith(".Z") or path.endswith(".gz"):
        return "zcat"
    elif path.endswith(".bz2"):
        return "bzcat"
    else:
        return default

def opengz(file, mode="r"):
    """Transparently open a potentially gzipped file. If mode is writing, infer compression based on
    mode + file ending."""
    assert mode in ['r', 'rb', 'a', 'ab', 'w', 'wb']
    if mode == 'wb' or (mode == 'w' and file.endswith('.gz')):
        return gzip.open(file, 'wb')
    elif mode == 'w':
        return open(file, 'w')
    f = open(file, 'rb')
    if f.read(2) == '\x1f\x8b':
        f.seek(0)
        return gzip.GzipFile(fileobj=f, mode=mode)
    else:
        f.close()
        return open(file, mode)


# FIXME: make these consistent and remove redundant code.  Maybe use
# keyword for flush

def prLine(fh, *objs):
    "write each str(obj) followed by a newline"
    for o in objs:
        fh.write(str(o))
    fh.write("\n")

def prsLine(fh, *objs):
    "write each str(obj), seperated by a space followed by a newline"
    n = 0
    for o in objs:
        if n > 0:
            fh.write(' ')
        fh.write(str(o))
        n += 1
    fh.write("\n")

def prOut(*objs):
    "write each str(obj) to stdout followed by a newline"
    for o in objs:
        sys.stdout.write(str(o))
    sys.stdout.write("\n")

def prErr(*objs):
    "write each str(obj) to stderr followed by a newline"
    for o in objs:
        sys.stderr.write(str(o))
    sys.stderr.write("\n")

def prsOut(*objs):
    "write each str(obj) to stdout, separating with spaces and followed by a newline"
    n = 0
    for o in objs:
        if n > 0:
            sys.stdout.write(' ')
        sys.stdout.write(str(o))
        n += 1
    sys.stdout.write("\n")

def prsfErr(*objs):
    "write each str(obj) to stderr, separating with spaces and followed by a newline and a flush"
    n = 0
    for o in objs:
        if n > 0:
            sys.stderr.write(' ')
        sys.stderr.write(str(o))
        n += 1
    sys.stderr.write("\n")
    sys.stderr.flush()

def prfErr(*objs):
    "write each str(obj) to stderr followed by a newline and a flush"
    for o in objs:
        sys.stderr.write(str(o))
    sys.stderr.write("\n")
    sys.stderr.flush()

def prsErr(*objs):
    "write each str(obj) to stderr, separating with spaces and followed by a newline"
    n = 0
    for o in objs:
        if n > 0:
            sys.stderr.write(' ')
        sys.stderr.write(str(o))
        n += 1
    sys.stderr.write("\n")

def prStrs(fh, *objs):
    "write each str(obj), with no newline"
    for o in objs:
        fh.write(str(o))

def prRow(fh, row):
    """Print a row (list or tupe) to a tab file.
    Does string conversion on each columns"""
    first = True
    for col in row:
        if not first:
            fh.write("\t")
        fh.write(str(col))
        first = False
    fh.write("\n")

def prRowv(fh, *objs):
    """Print a row from each argument to a tab file.
    Does string conversion on each columns"""
    first = True
    for col in objs:
        if not first:
            fh.write("\t")
        fh.write(str(col))
        first = False
    fh.write("\n")

def readFileLines(fname):
    "read lines from a file into a list, removing the newlines"
    fh = opengz(fname)
    lines = []
    for l in fh:
        if l[-1:] == "\n":
            l = l[:-1]
        lines.append(l)
    fh.close()
    return lines

def readLine(fh):
    "read a line from a file, dropping a newline; None on eof"
    l = fh.readline()
    if len(l) == 0:
        return None
    if l[-1:] == "\n":
        l = l[:-1]
    return l

def iterLines(fspec, skipLines=0):
    """generator over lines in file, dropping newlines.  If fspec is a string,
    open the file and close at end. Otherwise it is file-like object and will
    not be closed."""
    if isinstance(fspec, str):
        fh = opengz(fspec)
    else:
        fh = fspec
    try:
        _ = [fh.next() for _ in range(skipLines)]
        for line in fh:
            yield line[:-1]
    finally:
        if isinstance(fspec, str):
            fh.close()

def iterRows(fspec, skipLines=0, skipComments=True):
    """generator over rows in a tab-separated file.  Each line of the file is
    parsed, split into columns and returned.  If fspec is a string, open the
    file and close at end. Otherwise it is file-like object and will not be
    closed."""
    if isinstance(fspec, str):
        fh = opengz(fspec)
    else:
        fh = fspec
    try:
        _ = [fh.next() for _ in range(skipLines)]
        for line in fh:
            if not line.startswith('#'):
                yield line[0:-1].split("\t")
    finally:
        if isinstance(fspec, str):
            fh.close()

__tmpFileCnt = 0
def tmpFileGet(prefix=None, suffix="tmp", tmpDir=None):
    "obtain a tmp file with a unique name"
    # FIXME should jump through security hoops, have version that returns an open name
    if tmpDir is None:
        tmpDir = os.getenv("TMPDIR")
    if tmpDir is None:
        tmpDir = "/scratch/tmp"
        if not os.path.exists(tmpDir):
            tmpDir = "/var/tmp"
    pre = tmpDir
    if not pre.endswith("/"):
        pre += "/"
    if prefix is not None:
        pre += prefix + "."
    pre += socket.gethostname() + "." + str(os.getpid())
    global __tmpFileCnt
    while True:
        path = pre + "." + str(__tmpFileCnt) + "." + suffix
        __tmpFileCnt += 1
        if not os.path.exists(path):
            return path

def atomicTmpFile(finalPath):
    "return a tmp file to use with atomicInstall.  This will be in the same directory as finalPath"
    finalPathDir = os.path.dirname(finalPath)
    if finalPathDir == "":
        finalPathDir = '.'
    return tmpFileGet(prefix=os.path.basename(finalPath), suffix="tmp"+os.path.splitext(finalPath)[1], tmpDir=finalPathDir)

def atomicInstall(tmpPath, finalPath):
    "atomic install of tmpPath as finalPath"
    try:
        os.rename(tmpPath, finalPath)
    except OSError:
        tmp = tmpFileGet(tmpDir=os.path.dirname(finalPath))
        shutil.copy(tmpPath, tmp)
        os.rename(tmp, finalPath)
        os.remove(tmpPath)

def uncompressedBase(path):
    "return the file path, removing a compression extension if it exists"
    if path.endswith(".gz") or path.endswith(".bz2") or path.endswith(".Z"):
        return os.path.splitext(path)[0]
    else:
        return path

_devNullFh = None
def getDevNull():
    "get a file object open to /dev/null, caching only one instance"
    global _devNullFh
    if _devNullFh is None:
        _devNullFh = open("/dev/null", "r+")
    return _devNullFh

def touch(path):
    """
    Creates a file at path
    """
    _ = open(path, 'w').close()
