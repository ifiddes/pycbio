"""Experiment running objects"""
import os.path,sys,socket
from pycbio.exrun.Graph import *
from pycbio.sys import typeOps
from pycbio.exrun import ExRunException,Verb
from pycbio.exrun.CmdRule import CmdRule, Cmd, File, FileIn, FileOut

os.stat_float_times(True) # very, very gross

# FIXME: should rules/prods automatically be added? ExRun object to constructor
# would do the trick
# FIXME: How about object wrappers for File for input and output?? instead of getIn or getOut?
# FIXME: Dir object that is just as a base for File objects.
# FIXME: error output is really hard to read, especially when executing a non-existent program
#        just get `OSError: [Errno 2] No such file or directory', not much help
# FIXME: need to improve graph dump
# FIXME: need tracing of what is out of date
# FIXME: Cmd should allow a Cmd as a command in the pipeline, which would
#        allow all redirection in a subcommand (Pipeline enhancement).
# FIXME: implement targets

# NOTES:
#  - thread schedule should be based on load level; setup of a cluster job
#    adds a big load, running cluster jobs doesn't.


class ExRun(object):
    "object that defines and runs an experiment"
    def __init__(self, verbFlags=None):
        self.pending = None  # pending queue
        self.verb = Verb(flags=verbFlags)
        self.graph = Graph()
        self.hostName = socket.gethostname()
        self.uniqIdCnt = 0
        self.files = {}
        self.running = False

    def __modGraphErr(self):
        "generate error on attempt to modify graph after started running"
        raise ExRunException("attempt to modify graph once running")

    def getUniqId(self):
        "get a unique id for generating file names"
        id = self.hostName + "." + str(os.getpid()) + "." + str(self.uniqIdCnt)
        self.uniqIdCnt += 1
        return id

    def getTmpPath(self, path, namePrefix="tmp"):
        """generate a unique temporary file path from path, the file will be
        in the same directory.  The file extensions will be maintained, to
        allow recognition of file types, etc. """
        # FIXME: better name than tmp, check for non-existence
        return os.path.join(os.path.dirname(path),
                            namePrefix + "." + self.getUniqId() + "." + os.path.basename(path))

    def __addNode(self, node):
        "add a new node"
        if self.running:
            self.__modGraphErr()
        self.graph.addNode(node)
        node.exrun = self
        node.verb = self.verb

    def addRule(self, rule):
        "add a new rule"
        assert(isinstance(rule, Rule))
        self.__addNode(rule)

    def addProd(self, prod):
        "add a new Production"
        assert(isinstance(prod, Production))
        self.__addNode(prod)

    def getFile(self, path):
        """get a file production, creating if it doesn't exist, if path is already
        an instance of File instead of a string, just return it."""
        if isinstance(path, File):
            return path
        realPath = os.path.realpath(path)
        fprod = self.files.get(realPath)
        if fprod == None:
            if self.running:
                self.__modGraphErr()
            fprod = File(path, realPath)
            self.__addNode(fprod)
            self.files[realPath] = fprod
        return fprod

    def getFiles(self, paths):
        """like getFile(), only path can be a single path, or a list of paths,
        or a File object, or list of File objects.  Returns a list of File
        objects"""
        files = []
        for p in typeOps.mkiter(paths):
            files.append(self.getFile(p))
        return files

    def getTarget(self, id):
        "get a target production, creating if it doesn't exist"
        n = self._getNode(id, Target)
        if n == None:
            if self.running:
                self.__modGraphErr()
            n = self.__addNode(Target(id))
        return n

    def addCmd(self, cmd, name=None, requires=None, produces=None, stdin=None, stdout=None, stderr=None):
        """add a command rule with a single command or pipeline, this is a
        shortcut for addRule(CmdRule(Cmd(....),...)"""
        if self.running:
            self.__modGraphErr()
        return self.addRule(CmdRule(Cmd(cmd, stdin=stdin, stdout=stdout, stderr=stderr), name=name, requires=requires, produces=produces))

    def __preEvalRuleCheck(self, rule):
        "Sanity check before a rule is run"
        for r in rule.requires:
            if r.getTime() < 0.0:
                raise ExRunException("require should have been built:" + str(r))

    def __finishSucceed(self, rule):
        """finish up finish up requires/produces on success, failures here
        cause the rule to fail"""
        for p in rule.produces:
            p.finishSucceed()
        for r in rule.requires:
            r.finishRequire()

    def __finishFail(self, rule):
        """finish up finish up requires/produces on failure, will log errors,
        but not fail so original error is not lost"""
        for p in rule.produces:
            try:
                p.finishFail()
            except Exception, ex:
                self.verb.prall("Error in Production.finishFail() for ", p.name, ": ", ex)
                self.verb.pr(Verb.error, "\t", sys.exc_info()[2])
        for r in rule.requires:
            try:
                r.finishRequire()
            except Exception, ex:
                self.verb.prall("Error in Production.finishRequire() for ", r.name, ": ", ex)
                self.verb.pr(Verb.error, "\t", sys.exc_info()[2])
        
    def __evalRule(self, rule):
        "evaulate a rule"
        assert(isinstance(rule, Rule))
        self.verb.enter(Verb.trace, "eval rule: ", rule)
        try:
            self.__preEvalRuleCheck(rule)
            self.verb.pr(Verb.details, "run: ", rule)
            rule.state = RuleState.running
            rule.execute()
            self.__finishSucceed(rule)
            if rule.isOutdated():
                raise ExRunException("rule didn't update all productions: " + ", ".join([str(p) for p in rule.getOutdated()]))
            rule.state = RuleState.success
            self.verb.leave(Verb.trace, "done rule: ", rule)
        except Exception, ex:
            rule.state = RuleState.failed
            self.__finishFail(rule)
            self.verb.leave((Verb.trace,Verb.error), "fail rule: ", rule, ": ", ex)
            raise

    def __buildRule(self, rule):
        "recursively build a rule"
        assert(isinstance(rule, Rule))
        for r in rule.requires:
            self.__buildProd(r)
        if rule.isOutdated():
            self.__evalRule(rule)
            
    def __buildProd(self, prod):
        "recursively build a production"
        assert(isinstance(prod, Production))
        if (prod.producedBy != None):
            self.__buildRule(prod.producedBy)
        if prod.getTime() < 0.0:
            if (prod.producedBy == None):
                raise ExRunException("No rule to build: " + str(prod))
            else:
                raise ExRunException("Product not built: " + str(prod))

    def __getRunnableRules(self, entries):
        """get list of rules that need to be run and are runnable (all
        required are current), starting with the specified list of
        entry productions"""
        rules = []
        # FIXME

    def run(self):
        "run the experiment"
        self.running = True
        if self.verb.enabled(self.verb.graph):
            self.dumpGraph()
        self.graph.check()
        for prod in self.graph.getEntryProductions():
            self.__buildProd(prod)

    def __dumpRule(self, rule, fh=None):
        self.verb.prall("Rule: ", str(rule))
        self.verb.enter()
        pre = "prd: "
        for p in rule.produces:
            self.verb.prall(pre, str(p))
            pre = "     "
        pre = "req: "
        for r in rule.requires:
            self.verb.prall(pre, str(r))
            pre = "     "
        self.verb.leave()
        
    def __dumpProduction(self, prod):
        self.verb.prall("Production: ", str(prod))
        self.verb.enter()
        self.verb.prall("producedBy: ", str(prod.producedBy))
        self.verb.leave()
        
    def dumpGraph(self, fh=None):
        if fh != None:  # FIXME: kind of hacky
            holdFh = self.verb.fh
            self.verb.fh = fh
        self.verb.prall("graph dump:")
        self.verb.enter()
        for node in self.graph.bfs():
            if isinstance(node, Rule):
                self.__dumpRule(node)
            else:
                self.__dumpProduction(node)
        self.verb.leave()
        if fh != None:
            self.verb.fh = holdFh

__all__ = (ExRun.__name__)
