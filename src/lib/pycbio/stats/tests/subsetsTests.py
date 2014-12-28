# Copyright 2006-2012 Mark Diekhans
import unittest, sys
if __name__ == '__main__':
    sys.path.append("../../..")
from pycbio.stats.subsets import Subsets
from pycbio.sys.testCaseBase import TestCaseBase

class SubsetsTests(TestCaseBase):
    testSet = frozenset(("A","B","C"))
    def testGetSubsets(self):
        expectSet = ((frozenset(("A",)),
                      frozenset(("B",)),
                      frozenset(("C",)),
                      frozenset(("A","B",)),
                      frozenset(("A","C",)),
                      frozenset(("B","C",)),
                      frozenset(("A","B","C"))))
        
        subsets = Subsets(SubsetsTests.testSet)
        ss = subsets.getSubsets()
        self.assertEqual(ss, expectSet)

    def testGetInclusizeSubsets(self):
        expectSet = ((frozenset(("A",)),
                      frozenset(("C",)),
                      frozenset(("A","C",))))
        subsets = Subsets(SubsetsTests.testSet)
        iss = subsets.getInclusiveSubsets(frozenset(("A", "C",)))
        self.assertEqual(iss, expectSet)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(SubsetsTests))
    return suite

if __name__ == '__main__':
    unittest.main()
