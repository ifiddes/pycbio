import os

class HgConf(dict):
    """read hg.conf into this object.  Search order:
       1) supplied path
       2) HGDB_CONF env variable
       3) ~/.hg.conf
       user name is expanded"""
    def __init__(self, confFile=None):
        if confFile == None:
            confFile = os.getenv("HGDB_CONF")
        if confFile == None:
            confFile = "~/.hg.conf"
        confFile = os.path.expanduser(confFile)
        with open(confFile) as fh:
            for line in fh:
                self.__parseLine(line)

    def __parseLine(self, line):
        line = line.strip()
        if (len(line) > 0) and not line.startswith("#"):
            i = line.find("=")
            if i < 0:
                raise Exception("expected name=value, got: " + line)
            self[line[0:i].strip()] = line[i+1:].strip()
