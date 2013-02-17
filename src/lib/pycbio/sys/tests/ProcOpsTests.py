# Copyright 2006-2012 Mark Diekhans
import unittest, sys
if __name__ == '__main__':
    sys.path.append("../../..")
from pycbio.sys import procOps, Pipeline
from pycbio.sys.TestCaseBase import TestCaseBase

class ProcRunTests(TestCaseBase):
    def testCallSimple(self):
        out = procOps.callProc(["sort", self.getInputFile("simple1.txt")])
        self.failUnlessEqual(out, "five\nfour\none\nsix\nthree\ntwo")

    def testCallKeepNL(self):
        out = procOps.callProc(["sort", self.getInputFile("simple1.txt")], keepLastNewLine=True)
        self.failUnlessEqual(out, "five\nfour\none\nsix\nthree\ntwo\n")

    def testCallErr(self):
        ex = None
        try:
            procOps.callProc(["false"])
        except Exception, ex:
            pass
        self.failUnless(isinstance(ex, Pipeline.ProcException))
        self.failUnlessEqual(str(ex), 'process exited 1: false')

    def testCallLines(self):
        out = procOps.callProcLines(["sort", self.getInputFile("simple1.txt")])
        self.failUnlessEqual(out, ['five', 'four', 'one', 'six', 'three', 'two'])

    def testRunOut(self):
        outf = self.getOutputFile(".txt")
        ret = procOps.runProc(["sort", self.getInputFile("simple1.txt")], stdout=outf)
        self.failUnlessEqual(ret, 0)
        self.diffExpected(".txt")

    def testRunInOut(self):
        outf = self.getOutputFile(".txt")
        ret = procOps.runProc(["sort"], stdin=self.getInputFile("simple1.txt"), stdout=outf)
        self.failUnlessEqual(ret, 0)
        self.diffExpected(".txt")

    # base script that echos to stdout and stderr
    shOutErrCmd = ["sh", "-c", """echo "this is stdout" ; echo "this is stderr" >&2"""]

    def testRunOutErrByNum(self):
        outFile = self.getOutputFile(".stdout")
        errFile = self.getOutputFile(".stderr")
        with open(outFile, "w") as outFh, open(errFile, "w") as errFh:
            ret = procOps.runProc(self.shOutErrCmd, stdout=outFh.fileno(), stderr=errFh.fileno())
        self.failUnlessEqual(ret, 0)
        self.diffExpected(".stdout")
        self.diffExpected(".stderr")

    def testRunOutErrByName(self):
        outFile = self.getOutputFile(".stdout")
        errFile = self.getOutputFile(".stderr")
        ret = procOps.runProc(self.shOutErrCmd, stdout=outFile, stderr=errFile)
        self.failUnlessEqual(ret, 0)
        self.diffExpected(".stdout")
        self.diffExpected(".stderr")

    def testRunOutErrByFile(self):
        outFile = self.getOutputFile(".stdout")
        errFile = self.getOutputFile(".stderr")
        with open(outFile, "w") as outFh, open(errFile, "w") as errFh:
            ret = procOps.runProc(self.shOutErrCmd, stdout=outFh, stderr=errFh)
        self.failUnlessEqual(ret, 0)
        self.diffExpected(".stdout")
        self.diffExpected(".stderr")

    def testRunOutErrSameByFile(self):
        # same file handle for stdout/stderr; make sure it's not closed too soon
        outFile = self.getOutputFile(".stdouterr")
        with open(outFile, "w") as outFh:
            ret = procOps.runProc(self.shOutErrCmd, stdout=outFh, stderr=outFh)
        self.failUnlessEqual(ret, 0)
        self.diffExpected(".stdouterr")

    def testRunErr(self):
        ex = None
        try:
            procOps.runProc(["false"], stdin=self.getInputFile("simple1.txt"))
        except Exception, ex:
            pass
        self.failUnless(isinstance(ex, Pipeline.ProcException))
        self.failUnlessEqual(str(ex), 'process exited 1: false')

class ShellQuoteTests(TestCaseBase):
    # set of test words and expected response string
    testData = (
        (["a", "b"], "a b"),
        (["a b", "c$d", "e\\tf"], "a b c$d e\\tf"),
        (["a{b", "c	d", "(ef)", "${hi}", "j<k"], "a{b c	d (ef) ${hi} j<k"),
        )

    def testQuotesBash(self):
        for (words, expect) in self.testData:
            out = procOps.callProc(["sh", "-c", "/bin/echo " + " ".join(procOps.shQuote(words))])
            self.failUnlessEqual(out, expect)
        
    def testQuotesCsh(self):
        # must use /bin/echo, as some csh echos expand backslash sequences
        for (words, expect) in self.testData:
            out = procOps.callProc(["csh", "-c", "/bin/echo " + " ".join(procOps.shQuote(words))])
            self.failUnlessEqual(out, expect)
        

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ProcRunTests))
    suite.addTest(unittest.makeSuite(ShellQuoteTests))
    return suite

if __name__ == '__main__':
    unittest.main()
