# Copyright 2006-2014 Mark Diekhans
import unittest, sys, cPickle
if __name__ == '__main__':
    sys.path.append("../../..")
from pycbio.sys.symEnum import SymEnum
from pycbio.sys.testCaseBase import TestCaseBase

class Color(SymEnum):
    red = 1
    green = 2
    blue = 3

class SymEnumTests(TestCaseBase):
    def testBasics(self):
        self.failUnlessEqual(Color.red.name, "red")
        self.failUnlessEqual(Color.green.name, "green")
        self.failUnlessEqual(Color.blue.name, "blue")
        self.failUnless(Color.red < Color.blue)
        self.failUnless(Color.red == Color.red)
        self.failUnless(Color.red != Color.blue)
        self.failUnless(Color.red != None)
        self.failUnless(None != Color.red)

    def testLookup(self):
        self.failUnless(Color.red == Color("red"))
        self.failUnless(Color.green == Color("green"))
        self.failUnless(Color.green != Color("red"))

    def testStrings(self):
        self.failUnless(str(Color.red) == "red")
        self.failUnless(str(Color.green) == "green")
        self.failUnless(sorted([str(c) for c in Color]), ["red", "green", "blue"])

    def testAliases(self):
        class Name(SymEnum):
            Fred = 1
            Rick = 2
            Richard = Dick = HeyYou = Rick
            Bill = 3
        self.failUnless(Name("Richard") is Name.Rick)
        self.failUnlessEqual(Name("Dick"), Name.Rick)
        self.failUnless(Name("Dick") is Name.Rick)
        self.failUnless(Name("Rick") == Name.Rick)
        self.failUnless(Name("HeyYou") == Name.Rick)
        self.failUnless(Name("Fred") == Name.Fred)
        self.failUnless(Name("Fred") is Name.Fred)
        self.failUnlessEqual([n for n in Name], [Name.Fred, Name.Rick, Name.Bill])

    def testSetOps(self):
        colSet = set([Color.blue, Color.green])
        self.failUnless(Color.green in colSet)
        self.failIf(Color.red in colSet)

    def testNumberDef(self):
        class NumDef(SymEnum):
            neg = -2
            zero = 0
            pos= 2
            big = 3
        values = [(v.name, v.value) for v in NumDef]
        self.failUnlessEqual(values, [('neg', -2), ('zero', 0), ('pos', 2), ('big', 3)])
        self.failUnlessEqual(NumDef(2), NumDef.pos)

    def __testPickleProtocol(self, protocol):
        stuff = {}
        stuff[Color.red] = "red one"
        stuff[Color.green] = "green one"
        world = cPickle.dumps((Color, stuff,), protocol)
        color, stuff2 = cPickle.loads(world)

        self.failUnless(Color.red in stuff2)
        self.failUnless(Color.green in stuff2)

    def testPickle2(self):
        self.failUnless(cPickle.HIGHEST_PROTOCOL == 2)
        self.__testPickleProtocol(2)
    def testPickle1(self):
        self.__testPickleProtocol(1)
    def testPickle0(self):
        self.__testPickleProtocol(0)

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(SymEnumTests))
    return suite

if __name__ == '__main__':
    unittest.main()
