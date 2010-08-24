# Copyright 2006-2010 Mark Diekhans
import unittest, sys, string
if __name__ == '__main__':
    sys.path.append("../../..")
from pycbio.stats.Venn import Venn
from pycbio.sys.TestCaseBase import TestCaseBase
from pycbio.sys.fileOps import prRowv

class VennTests(TestCaseBase):
    def _checkVenn(self, venn):
        vi = self.getOutputFile(".vinfo")
        viFh = open(vi, "w")
        for subset in venn.subsets.getSubsets():
            prRowv(viFh, subset, venn.getSubsetIds(subset))
        viFh.close()
        self.diffExpected(".vinfo")
        
    def testVenn1(self):
        venn = Venn()
        venn.addItems("A", (1, 2, 3))
        venn.addItems("B", (3, 4, 5))
        venn.addItems("C", (3, 5, 6))
        self._checkVenn(venn)

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(VennTests))
    return suite

if __name__ == '__main__':
    unittest.main()
