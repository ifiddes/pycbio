"Classes used to implement rules that execute commands and produce files"

import os.path
from pycbio.sys import typeOps,fileOps
from pycbio.exrun import ExRunException
from pycbio.exrun.Graph import Production,Rule
from pycbio.sys.Pipeline import Procline

class FileInRef(object):
    """Object used to specified a input file name argument to a command
    that is expanded just before the command is executed."""
    __slots__ = ["file", "prefix"]

    def __init__(self, file, prefix=None):
        self.file = file
        self.prefix = prefix

    def __str__(self):
        """return input file argument"""
        if self.prefix == None:
            return self.file.getInPath()
        else:
            return self.prefix + self.file.getInPath()

    def getInPath(self):
        "return File.getInPath() for referenced file"
        return self.file.getInPath()

class FileOutRef(object):
    """Object used to specified a output file name argument to a command
    that is expanded just before the command is executed."""
    __slots__ = ["file", "prefix"]

    def __init__(self, file, prefix=None):
        self.file = file
        self.prefix = prefix

    def __str__(self):
        """return input file argument"""
        if self.prefix == None:
            return self.file.getOutPath()
        else:
            return self.prefix + self.file.getOutPath()

    def getOutPath(self):
        "return File.getInPath() for referenced file"
        return self.file.getOutPath()

class File(Production):
    """Object representing a file production. This also handles atomic file
    creation. CmdRule will install productions of this class after the
    commands succesfully complete."""

    def __init__(self, path, realPath):
        "realPath is use to detect files accessed from different paths"
        Production.__init__(self, path)
        self.path = path
        self.realPath = realPath
        self.newPath = None
        self.installed = False

    def __str__(self):
        return self.path

    def getTime(self):
        "modification time of file, or -1.0 if it doesn't exist"
        if os.path.exists(self.path):
            return os.path.getmtime(self.path)
        else:
            return -1.0

    def getInPath(self):
        """Get the input path name of the file.  If a new file has been defined
        using getOutPath(), but has not been installed, it's path is return,
        otherwise path is returned.  Normally one wants to use getIn()
        to define a command argument."""
        if self.newPath != None:
            return self.newPath
        else:
            return self.path

    def getOutPath(self):
        """Get the output name for the file, which is newPath until the rule
        terminates. This will also create the output directory for the file,
        if it does not exist.  Normally one wants to use getOut() to define
        a command argument"""
        if self.installed:
            raise ExRunException("output file already installed: " + self.path)
        if self.newPath == None:
            fileOps.ensureFileDir(self.path)
            self.newPath = self.exRun.getTmpPath(self.path)
        return self.newPath

    def getIn(self, prefix=None):
        """Returns an object that causes the input file path to be substituted
        when str() is call on it.  CmdRule also adds this File as a requires
        when it is in a command specified at construction time.  If prefix is
        specified, it is added before the file name. This allows adding
        options like --foo=filepath.
        """
        return FileInRef(self, prefix)

    def getOut(self, prefix=None):
        """Returns an object that causes the output file path to be substituted
        when str() is call on it.  CmdRule also adds this File as a produces
        when it is in a command specified at construction time.  If prefix is
        specified, it is added before the file name. This allows adding
        options like --foo=filepath.
        """
        return FileOutRef(self, prefix)

    def isCompressed(self):
        return self.path.endswith(".gz") or self.path.endswith(".bz2")

    def getCatCmd(self):
        "return get the command name to use to cat the file, considering compression"
        if self.path.endswith(".Z") or self.path.endswith(".gz"):
            return "zcat"
        elif self.path.endswith(".bz2"):
            return "bzcat"
        else:
            return "cat"

    def install(self):
        "atomic install of new output file as actual file"
        if self.installed:
            raise ExRunException("output file already installed: " + self.path)
        if self.newPath == None:
            raise ExRunException("getOutPath() never called for: " + self.path)
        if not os.path.exists(self.newPath):
            raise ExRunException("output file as not created: " + self.newPath)
        if os.path.exists(self.path):
            os.unlink(self.path)
        os.rename(self.newPath, self.path)
        self.installed = True
        self.newPath = None

class Cmd(list):
    """A command in a CmdRule. An instance can either be a simple command,
    which is a list of words, or a command pipe line, which is a list of list
    of words. The stdin,stdout, stderr arguments are used for redirect I/O.
    stdin/out/err can be open files, strings, or File production objects.
    If they are File objects, the atomic file handling methods are used
    to get the path.
    """

    def __init__(self, cmd, stdin=None, stdout=None, stderr=None):
        """The str() function is called on each word when assembling arguments
        to a comand, so arguments do not need to be strings."""
        # copy list(s)
        if isinstance(cmd[0], str):
            self.append(tuple(cmd))
        else:
            for c in cmd:
                self.append(tuple(c))
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr

    def isPipe(self):
        "determine if this command contains multiple processes"
        return isinstance(self[0], list) or isinstance(self[0], tuple)
        
    def _getInput(self, fspec):
        "get an input file, if fspec is a file object, return getInPath(), fspec string"
        if fspec == None:
            return None
        elif isinstance(fspec, File) or isinstance(fspec, FileInRef):
            return fspec.getInPath()
        else:
            return str(fspec)

    def _getOutput(self, fspec):
        "get an output file, if fspec is a file object, return getOutPath(), fspec string"
        if fspec == None:
            return None
        elif isinstance(fspec, File) or isinstance(fspec, FileOutRef):
            return fspec.getOutPath()
        else:
            return str(fspec)

    def call(self, verb):
        "run command, with tracing"
        pl = Procline(self, self._getInput(self.stdin), self._getOutput(self.stdout), self._getOutput(self.stderr))
        if verb.enabled(verb.trace):
            verb.pr(verb.trace, pl.getDesc())
        pl.wait()

class CmdRule(Rule):
    """Rule to execute processes.  Automatically installs File producions after
    completion.

    This can be used it two ways, either give a lists of commands which are
    executed, or a rule class can be derived from this that executes the
    command when the rule is evaluated.
    
    If commands are specified to the constructor, they are either a Cmd object
    or a list of Cmd objects.  If the input of the Cmd are File objects, they
    are added to the requires, and output of type File are added to the
    produces.  However, if the input of a command is an output of a previous
    command, it the list, it doesn't become a require, to allow outputs to
    also be inputs of other comments for the rule.

    The derived class overrides run() function to evaulate the rule and uses
    the call() function to execute each command or pipeline.

    Rule name is generated from productions if not specified.
    """

    def _mkNamePart(prods):
        if typeOps.isIterable(prods):
            return ",".join(map(str, prods))
        else:
            return str(prods)
    _mkNamePart = staticmethod(_mkNamePart)

    def _mkName(requires, produces):
        return "Rule["+ CmdRule._mkNamePart(requires) + "=>" + CmdRule._mkNamePart(produces)+"]"
    _mkName = staticmethod(_mkName)

    def __init__(self, cmds=None, name=None, requires=None, produces=None):
        requires = typeOps.mkset(requires)
        produces = typeOps.mkset(produces)

        # deal with commands before super init, so all requires and produces
        # are there for the name generation
        self.cmds = None
        if cmds != None:
            self.cmds = []
            if isinstance(cmds, Cmd):
                self._addCmd(cmds, requires, produces)
            else:
                for cmd in cmds:
                    self._addCmd(cmd, requires, produces)
        if name == None:
            name = CmdRule._mkName(requires, produces)
        Rule.__init__(self, name, requires, produces)

    def _addCmd(self, cmd, requires, produces):
        assert(isinstance(cmd, Cmd))
        self._addCmdStdio(cmd.stdin, requires, produces)
        self._addCmdStdio(cmd.stdout, produces)
        self._addCmdStdio(cmd.stderr, produces)
        if cmd.isPipe():
            for c in cmd:
                self._addCmdArgFiles(c, requires, produces)
        else:
            self._addCmdArgFiles(c, requires, produces)
        self.cmds.append(cmd)

    def _addCmdStdio(self, fspecs, specSet, exclude=None):
        "add None, a single or a list of file specs as requires or produces links"
        for fspec in typeOps.mkiter(fspecs):
            if  (isinstance(fspec, FileInRef) or isinstance(fspec, FileOutRef)):
                fspec = fspec.file  # get File object for reference
            if (isinstance(fspec, File) and ((exclude == None) or (fspec not in exclude))):
                specSet.add(fspec)

    def _addCmdArgFiles(self, cmd, requires, produces):
        """scan a command's arguments for FileInRef and FileOutRef object and add these to
        requires or produces"""
        for a in cmd:
            if isinstance(a, FileInRef):
                requires.add(a.file)
            elif isinstance(a, FileOutRef):
                produces.add(a.file)
            elif isinstance(a, File):
                raise ExRunException("can't use File object in command argument, use getIn() or getOut() to generate a reference object")

    def call(self, cmd):
        "run a commands with optional tracing"
        cmd.call(self.verb)

    def runCmds(self):
        "run commands supplied in the constructor"
        if self.cmds == None:
            raise ExRunException("no commands specified and run() not overridden for CmdRule: " + self.name)
        for cmd in self.cmds:
            self.call(cmd)

    def run(self):
        """run the commands for the rule, the default version runs the
        commands specified at construction, overrider this for a derived class"""
        self.runCmds()

    def _installFileProductions(self):
        for p in self.produces:
            if isinstance(p, File):
                p.install()

    def execute(self):
        "execute the rule"
        self.verb.enter()
        try:
            self.run()
            self._installFileProductions()
        finally:
            self.verb.leave()
