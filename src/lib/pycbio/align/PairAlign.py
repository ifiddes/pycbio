"""
Pairwise alignment.  All coordinates are strand-specific

"""
import sys,copy,re
from pycbio.sys.Enumeration import Enumeration
from pycbio.hgdata.Psl import PslReader
from pycbio.hgdata.Frame import frameIncr,frameToPhase
from pycbio.sys.fileOps import prLine,iterLines

class Seq(object):
    """Sequence in an alignment, coordinates are strand-specific."""

    __slots__ = ("id", "start", "end", "size", "strand", "cds")
    def __init__(self, id, start, end, size, strand, cds=None):
        self.id = id
        self.start = start
        self.end = end
        self.size = size
        self.strand = strand
        self.cds = cds

    def mkSubSeq(self, start, end):
        "create a subsequence"
        assert((start >= self.start) and (end <= self.end))
        ss = SubSeq(self, start, end)
        if self.cds != None:
            st = max(self.cds.start, ss.start)
            en = min(self.cds.end, ss.end)
            if st < en:
                ss.cds = Cds(st, en)
        return ss

    def revCmpl(self):
        "return a reverse complment of this object"
        cds = self.cds.revCmpl(self.size) if self.cds != None else None
        strand = '-' if (self.strand == '+') else '+'
        return Seq(self.id, self.size-self.end, self.size-self.start, self.size, strand, cds)

    def __str__(self):
        return self.id + ":" + str(self.start) + "-" + str(self.end) + "/" \
            + self.strand + " sz: " + str(self.size) + " cds: " + str(self.cds)

    def __len__(self):
        "get sequence length"
        return self.end-self.start

    def updateCds(self, cdsStart,  cdsEnd):
        """Update the CDS bounds to include specified range, triming to bounds"""
        cdsStart = max(self.start, cdsStart)
        cdsEnd = min(self.end, cdsEnd)
        if self.cds == None:
            self.cds = Cds(cdsStart, cdsEnd)
        else:
            self.cds.start = min(self.cds.start, cdsStart)
            self.cds.end = max(self.cds.end, cdsEnd)
    

class SubSeq(object):
    "subsequence in alignment"
    __slots__ = ("seq", "start", "end", "cds")
    def __init__(self, seq, start, end, cds=None):
        self.seq = seq
        self.start = start
        self.end = end
        self.cds = cds

    def __str__(self):
        return str(self.start) + "-" + str(self.end) \
            + (("  CDS: " + str(self.cds)) if (self.cds != None) else "")

    def locStr(self):
        "get string describing location"
        return self.seq.id + ":" + str(self.start) + "-" + str(self.end)
        
    def revCmpl(self, revSeq):
        "return a reverse complment of this object for revSeq"
        cds = self.cds.revCmpl(revSeq.size) if self.cds != None else None
        return SubSeq(revSeq, revSeq.size-self.end, revSeq.size-self.start, cds)

    def __len__(self):
        "get sequence length"
        return self.end-self.start

    def overlaps(self, start, end):
        "determine if subseqs overlap"
        maxStart = max(self.start, start)
        minEnd = min(self.end, end)
        return (maxStart < minEnd)

    def updateCds(self, cdsStart,  cdsEnd):
        """Update the CDS bounds and the sequence CDS. This expands existing
        CDS, it doesn't replace it.  If cds range exceeds block bounds,
        it is adjusted"""
        cdsStart = max(self.start, cdsStart)
        cdsEnd = min(self.end, cdsEnd)
        if self.cds == None:
            self.cds = Cds(cdsStart, cdsEnd)
        else:
            self.cds.cdsStart = min(self.cds.cdsStart, cdsStart)
            self.cds.cdsEnd = max(self.cds.cdsSEnd, cdsEnd)

        self.seq.updateCds(self.cds.start, self.cds.end)

class SubSeqs(list):
    """list of subseqs of in blks, or None if one side is unaligned. Used
    to for functions that can operate on either side of alignment."""
    __slots__ = ("seq")
    def __init__(self, seq):
        self.seq = seq

    def clearCds(self):
        "clear CDS in sequences and subseqs"
        self.seq.cds = None
        for ss in self:
            if ss != None:
                ss.cds = None

class Cds(object):
    "range or subrange of CDS"
    __slots__ = ("start", "end")
    def __init__(self, start, end):
        assert(start < end)
        self.start = start
        self.end = end

    def revCmpl(self, psize):
        "return a reverse complment of this object, given parent seq or subseq size"
        return Cds(psize-self.end, psize-self.start)

    def __str__(self):
        return str(self.start) + "-" + str(self.end)
        
    def __len__(self):
        "get CDS length"
        return self.end-self.start
    
class Block(object):
    """Block in alignment, query or target SubSeq can be None.  Links allow
    for simple traversing"""
    __slots__ = ("aln", "q", "t", "idx", "prev", "next")
    def __init__(self, aln, q, t, idx=None):
        assert((q == None) or (t == None) or (len(q) == len(t)))
        self.aln = aln
        self.q = q
        self.t = t
        self.idx = idx  # FIXME: really needed?
        # FIXME: remove???
        self.prev = self.next = None

    def __len__(self):
        "length of block"
        return len(self.q) if (self.q != None) else len(self.t)

    def __str__(self):
        return str(self.q) + " <=> " + str(self.t)

    def isAln(self):
        "is this block aligned?"
        return (self.q != None) and (self.t != None)

    def isQIns(self):
        "is this block a query insert?"
        return (self.q != None) and (self.t == None)

    def isTIns(self):
        "is this block a target insert?"
        return (self.q == None) and (self.t != None)

    def __subToRow(self, seq, sub):
        if sub != None:
            return [seq.id, sub.start, sub.end]
        else:
            return [seq.id, None, None]

    def toRow(self):
        "convert to list of query and target coords"
        return  self.__subToRow(self.aln.qSeq, self.q) + self.__subToRow(self.aln.tSeq, self.t)

    def dump(self, fh):
        "print content to file"
        prLine(fh, "\t> query:  ", self.q)
        prLine(fh, "\t  target: ", self.t)

class PairAlign(list):
    """List of alignment blocks"""
    __slots__ = ("qSeq", "tSeq", "qSubSeqs", "tSubSeqs")
    def __init__(self, qSeq, tSeq, cds=None):
        self.qSeq = qSeq
        self.tSeq = tSeq
        self.qSubSeqs = SubSeqs(qSeq)
        self.tSubSeqs = SubSeqs(tSeq)

    def addBlk(self, q, t):
        blk = Block(self, q, t, len(self))
        if len(self) > 0:
            self[-1].next = blk
            blk.prev = self[-1]
        self.append(blk)
        self.qSubSeqs.append(blk.q)
        self.tSubSeqs.append(blk.t)
        return blk

    def revCmpl(self):
        "return a reverse complment of this object"
        qSeq = self.qSeq.revCmpl()
        tSeq = self.tSeq.revCmpl()
        aln = PairAlign(qSeq, tSeq)
        for i in xrange(len(self)-1, -1, -1):
            blk = self[i]
            aln.addBlk((None if (blk.q == None) else blk.q.revCmpl(qSeq)),
                       (None if (blk.t == None) else blk.t.revCmpl(tSeq)))
        return aln

    def anyTOverlap(self, other):
        "determine if the any target blocks overlap"
        if (self.tSeq.id != other.tSeq.id) or (self.tSeq.strand != other.tSeq.strand):
            return False
        oblk = other[0]
        for blk in self:
            if blk.isAln():
                while oblk != None:
                    if oblk.isAln():
                        if oblk.t.start > blk.t.end:
                            return False
                        elif blk.t.overlaps(oblk.t.start, oblk.t.end):
                            return True
                    oblk = oblk.next
            if oblk == None:
                break
        return False

    @staticmethod
    def __projectBlkCds(srcSs, destSs):
        "project CDS from one subseq to another"
        if destSs != None:
            if (srcSs != None) and (srcSs.cds != None):
                start = destSs.start+(srcSs.cds.start-srcSs.start)
                end = destSs.start+(srcSs.cds.end-srcSs.start)
                destSs.updateCds(start, end)
            else:
                destSs.cds = None

    @staticmethod
    def __projectCds(srcSubSeqs, destSubSeqs):
        "project CDS from one alignment side to the other"
        assert(srcSubSeqs.seq.cds != None)
        destSubSeqs.clearCds()
        for i in xrange(len(srcSubSeqs)):
            PairAlign.__projectBlkCds(srcSubSeqs[i], destSubSeqs[i])

    def projectCdsToTarget(self):
        "project CDS from query to target"
        PairAlign.__projectCds(self.qSubSeqs, self.tSubSeqs)

    def projectCdsToQuery(self):
        "project CDS from target to query"
        PairAlign.__projectCds(self.tSubSeqs, self.qSubSeqs)

    @staticmethod
    def __mapCdsToSubSet(destSs, srcSubSeqs, si):
        "find overlapping src blks and assign cds, incrementing si as needed"
        sl = len(srcSubSeqs)
        while si < sl:
            srcSs = srcSubSeqs[si]
            if srcSs != None:
                if srcSs.overlaps(destSs) and srcSs.cds != None:
                    destSss.updateCds(srcSs.cds.start, srcSs.cds.end)
            else:
                si += 1

    def mapCds(self, srcSeq, srcSubSeqs, destSeq, destSubSeqs):
        "map CDS from one alignment to this one via a comman sequence"
        assert((destSeq == self.qSeq) or (destSeq == self.tSeq))
        assert((srcSeq.id == destSeq.id) and (srcSeq.strand == destSeq.strand))
        si = di = 0
        sl = len(srcSubSeqs)
        dl = len(destSubSeqs)
        while (si < sl) and (di < dl):
            if destSubSeqs[di] != None:
                si = PairAlign.__mapCdsToBlk(destSubSeqs[di], srcSubSeqs, si)
            di += 1

    def dump(self, fh):
        "print content to file"
        prLine(fh, "query:  ", self.qSeq)
        prLine(fh, "target: ", self.tSeq)
        for blk in self:
            blk.dump(fh)


def _getCds(cdsRange, strand, size):
    if cdsRange == None:
        return None
    cds = Cds(cdsRange[0], cdsRange[1])
    if strand == '-':
        cds = cds.revCmpl(size)
    return cds

def _mkPslSeq(name, start, end, size, strand, cds=None):
    "make a seq from a PSL q or t, reversing range is neg strand"
    if strand == '-':
        return Seq(name, size-end, size-start, size, strand, cds)
    else:
        return Seq(name, start, end, size, strand, cds)

def _addPslBlk(psl, aln, i, prevBlk, inclUnaln):
    """add an aligned block, and optionally preceeding unaligned blocks"""
    qStart = psl.qStarts[i]
    qEnd = psl.getQEnd(i)
    tStart = psl.tStarts[i]
    tEnd = psl.getTEnd(i)
    if inclUnaln and (i > 0):
        if qStart > prevBlk.q.end:
            aln.addBlk(aln.qSeq.mkSubSeq(prevBlk.q.end, qStart), None)
        if tStart > prevBlk.t.end:
            aln.addBlk(None, aln.tSeq.mkSubSeq(prevBlk.t.end, tStart))
    blk = aln.addBlk(aln.qSeq.mkSubSeq(qStart, qEnd),
                     aln.tSeq.mkSubSeq(tStart, tEnd))
    return blk

def fromPsl(psl, qCdsRange=None, inclUnaln=False):
    """generate a PairAlign from a PSL. cdsRange is None or a tuple. In
    inclUnaln is True, then include Block objects for unaligned regions"""
    qCds = _getCds(qCdsRange, psl.getQStrand(), psl.qSize)
    qSeq = _mkPslSeq(psl.qName, psl.qStart, psl.qEnd, psl.qSize, psl.getQStrand(), qCds)
    tSeq = _mkPslSeq(psl.tName, psl.tStart, psl.tEnd, psl.tSize, psl.getTStrand())
    aln = PairAlign(qSeq, tSeq)
    prevBlk = None
    for i in xrange(psl.blockCount):
        prevBlk = _addPslBlk(psl, aln, i, prevBlk, inclUnaln)
    return aln

class CdsTable(dict):
    """table mapping ids to tuple of zero-based (start end),
    Load from CDS seperated file in form:
       cds start..end
    """
    def __init__(self, cdsFile):
        for line in iterLines(cdsFile):
            if not line.startswith('#'):
                self.__parseCds(line)
    
    __parseRe = re.compile("^([^\t]+)\t([0-9]+)\\.\\.([0-9]+)$")
    def __parseCds(self, line):
        m = self.__parseRe.match(line)
        if m == None:
            raise Exception("can't parse CDS line: " + line)
        st = int(m.group(2))-1
        en = int(m.group(3))-1
        self[m.group(1)] = (st, en)

def loadPslFile(pslFile, cdsFile=None, inclUnaln=False):
    "build list of PairAlign from a PSL file and optional CDS file"
    cdsTbl = CdsTable(cdsFile) if (cdsFile != None) else {}
    alns = []
    for psl in PslReader(pslFile):
        alns.append(fromPsl(psl, cdsTbl.get(psl.qName), inclUnaln))
    return alns
