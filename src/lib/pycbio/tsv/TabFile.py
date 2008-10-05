
## FIXME: needed for faster readings, but needs cleaned up, need reader/writer
## classes
# FIXME add try and error msg with file/line num, move to row reader class; see fileOps.iterRows
from pycbio.sys import fileOps
import csv

class TabFile(list):
    """Class for reading tab-separated files.  Can be used standalone
       or read into rows of a specific type.
    """

    def __init__(self, fileName, rowClass=None, hashAreComments=False):
        """Read tab file into the object
        """
        self.fileName = fileName
        self.rowClass = rowClass
        reader = TabFileReader(self.fileName, hashAreComments)
        for row in reader:
            if self.rowClass:
                self.append(self.rowClass(row))
            else:
                self.append(row)

    @staticmethod
    def write(fh, row):
        """print a row (list or tuple) to a tab file."""
        cnt = 0;
        for col in row:
            if cnt > 0:
                fh.write("\t")
            fh.write(str(col))
            cnt += 1
        fh.write("\n")

class TabFileReader(object):
    def __init__(self, tabFile, hashAreComments=False):
        self.inFh = fileOps.opengz(tabFile)
        self.csvRdr = csv.reader(self.inFh, dialect=csv.excel_tab)
        self.hashAreComments = hashAreComments
        self.lineNum = 0

    def __readRow(self):
        "read the next row, returning None on EOF"
        try:
            row = self.csvRdr.next()
        except Exception, e:
            self.close()
            if isinstance(e, StopIteration):
                return None
            else:
                raise
        self.lineNum = self.csvRdr.line_num
        return row

    def __iter__(self):
        return self

    def next(self):
        while True:
            row = self.__readRow()
            if row == None:
                raise StopIteration
            if not (self.hashAreComments and (len(row) > 0) and row[0].startswith("#")):
                return row

    def close(self):
        "close file, called automatically on EOF"
        if self.inFh != None:
            self.inFh.close()
            self.inFh = None
            self.csvRdr = None
