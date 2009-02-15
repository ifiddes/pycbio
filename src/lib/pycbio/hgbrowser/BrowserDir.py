"""Create a frameset that that is a directory of locations in the genome
browser.
"""

from pycbio.hgbrowser.Coords import Coords
from pycbio.html.HtmlPage import HtmlPage
from pycbio.sys import fileOps

class Entry(object):
    "entry in directory"
    __slots__= ("row", "key", "cssClass")

    def __init__(self, row, key=None, cssClass=None):
        """Entry in directory, key can be some value(s) used in sorting
        The row should be HTML encoded """
        self.row = list(row)
        self.key = key
        self.cssClass = cssClass

class BrowserDir(object):
    """Create a frameset and collection of HTML pages that index one or more
    genome browsers.
    """

    def __init__(self, browserUrl, defaultDb, colNames=None, pageSize=50,
                 title=None, dirPercent=15, below=False, pageDesc=None,
                 tracks=None, style=None, numColumns=1):
        """tracks is a dict, or none; pageSize of None creates a single
        page"""
        self.browserUrl = browserUrl
        if self.browserUrl.endswith("/"):
            self.browserUrl = self.browserUrl[0:-1] # drop trailing `/', so we don't end up with '//'
        self.defaultDb = defaultDb
        self.colNames = colNames
        self.pageSize = pageSize
        self.title = title
        self.dirPercent = dirPercent
        self.below = below
        self.numColumns = numColumns
        self.pageDesc = pageDesc
        self.entries = []
        self.tracksArgs = None
        if tracks != None:
            self.tracksArgs = self.__mkTracksArgs(tracks)
        else:
            self.tracksArgs = ""
        self.style = style

    def __mkTracksArgs(self, initialTracks):
        l = []
        for t in initialTracks:
            l.append(t + "=" + initialTracks[t])
        return "&" + "&".join(l)
        
    def mkDefaultUrl(self):
        return self.browserUrl + "/cgi-bin/hgTracks?db=" + self.defaultDb + "&position=default" + self.tracksArgs

    def mkUrl(self, coords):
        url = self.browserUrl + "/cgi-bin/hgTracks?db="
        if coords.db != None:
            url += coords.db
        else:
            url += self.defaultDb
        url += "&position=" + str(coords) + self.tracksArgs
        return url

    def mkAnchor(self, coords, text=None):
        if text == None:
            text = str(coords)
        return "<a href=\"" + self.mkUrl(coords) + "\" target=browser>" + text + "</a>"
        
    def addRow(self, row, key=None, cssClass=None):
        """add an encoded row """
        self.entries.append(Entry(row, key, cssClass))

    def add(self, coords, name=None):
        """add a simple row, linking to location If name is None, it's the
        location """
        if name == None:
            name = str(coords)
        row = [self.mkAnchor(coords, name)]
        self.addRow(row, key=coords)

    def sort(self, cmpFunc=cmp, reverse=False):
        "sort by the key"
        self.entries.sort(cmp=lambda a,b: cmpFunc(a.key, b.key), reverse=reverse)

    def __mkFrame(self, title=None, dirPercent=15, below=False):
        """create frameset as a HtmlPage object"""

        if below:
            fsAttr = "rows=%d%%,%d%%" % (100-dirPercent, dirPercent)
        else:
            fsAttr = "cols=%d%%,%d%%" % (dirPercent, 100-dirPercent)
        pg = HtmlPage(title=title, framesetAttrs=(fsAttr,))

        fdir = '<frame name="dir" src="dir1.html">'
        fbr = '<frame name="browser" src="%s">' % self.mkDefaultUrl()
        if below:
            pg.add(fbr)
            pg.add(fdir)
        else:
            pg.add(fdir)
            pg.add(fbr)
        return pg

    def __getPageLinks(self, pageNum, numPages):
        html = []
        # prev link
        if pageNum > 1:
            html.append("<a href=\"dir%d.html\">prev</a>" % (pageNum-1));
        else:
            html.append("prev")

        # page number links
        for p in xrange(1, numPages+1):
            if p != pageNum:
                html.append("<a href=\"dir%d.html\">%d</a>" % (p, p))
            else:
                html.append("[%d]" % p)

        # next link
        if pageNum < numPages:
            html.append("<a href=\"dir%d.html\">next</a>" % (pageNum+1))
        else:
            html.append("next")
        return ", ".join(html)

    def __addTblHeader(self, pg):
        row = []
        for cn in xrange(self.numColumns):
            row.extend(self.colNames)
        pg.tableHeader(row)

    # FIXME: really want table of tables for multi-column mode
    def __addTblBody(self, pg, pgEntries):
        l = len(pgEntries)
        for ie in xrange(0, l, self.numColumns):
            row = []
            for ic in xrange(ie, ie+self.numColumns):
                if ic < l:
                    row.extend(pgEntries[ic].row)
                else:
                    for i in xrange(len(pgEntries[0].row)):
                        row.append("")
            pg.tableRow(row)

    def __writeDirPage(self, outDir, pgEntries, pageNum, numPages):
        title = "page %d" % pageNum
        if self.title:
            title += ": " + self.title
        pg = HtmlPage(title=title, inStyle=self.style)
        pageLinks = self.__getPageLinks(pageNum, numPages)
        pg.h3(title)
        if self.pageDesc != None:
            pg.add(self.pageDesc)
            pg.add("<br><br>")
        pg.add(pageLinks)
        
        pg.tableStart(style="white-space:nowrap;")
        if self.colNames != None:
            self.__addTblHeader(pg)
        self.__addTblBody(pg, pgEntries)
        pg.tableEnd()
        pg.add(pageLinks)

        dirFile = outDir + "/dir%d.html" % pageNum
        pg.writeFile(dirFile)

    def __writeDirPages(self, outDir):
        if len(self.entries) == 0:
            # at least write an empty page
            self.__writeDirPage(outDir, [], 1, 0)
        elif self.pageSize == None:
            # single page
            self.__writeDirPage(outDir, self.entries, 1, 1)
        else:
            # split
            numPages = (len(self.entries)+self.pageSize-1)/self.pageSize
            for pageNum in xrange(1,numPages+1):
                first = (pageNum-1) * self.pageSize
                last = first+(self.pageSize-1)
                pgEntries = self.entries[first:last]
                self.__writeDirPage(outDir, pgEntries, pageNum, numPages)

    def write(self, outDir):
        fileOps.ensureDir(outDir)
        frame = self.__mkFrame(self.title, self.dirPercent, self.below)
        frame.writeFile(outDir + "/index.html")
        self.__writeDirPages(outDir)
