from pycbio.sys.Immutable import Immutable

# FIXME: could have user add value object direcrly instead of complex
# value typles
# should be iterable

class EnumValue(Immutable):
    """A value of an enumeration.  The object id (address) is the
    unique value, with an associated display string and numeric value
    """
    __slots__ = ["name", "numValue", "strValue"]
    def __init__(self, name, numValue, strValue=None):
        self.name = name
        self.numValue = numValue
        if strValue == None:
            self.strValue = name
        else:
            self.strValue = strValue
        self.makeImmutable();

    def __getstate__(self):
        # optimize strValue if same as name
        return (self.name, self.numValue, (None if self.strValue == self.name else self.strValue))

    def __setstate__(self, st):
        (self.name, self.numValue, self.strValue) = st
        if self.strValue == None:
            self.strValue = self.name
        self.makeImmutable();

    def __rept__(self):
        return self.name

    def __str__(self):
        return self.strValue

    def __int__(self):
        return self.numValue

    def __cmp__(self, otherVal):
        if otherVal == None:
            return -1
        elif type(otherVal) == int:
            return cmp(self.numValue, otherVal)
        else:
            return cmp(self.numValue, otherVal.numValue)

class Enumeration(Immutable):
    """A class for creating enumeration objects.
    """

    __slots__ = ("name", "aliases", "values", "maxNumValue")

    def __init__(self, name, valueDefs, valueClass=EnumValue, bitSetValues=False):
        """Name is the name of the enumeration. ValueDefs is an ordered list of
        string values.  If valueDefs contains a tuple, the first element is the
        value name, the second value is the __str__ value.  The third
        value is a list or tuple of string aliases that can be used to
        lookup the value under a different name.
        """
        self.name = name
        self.aliases = {}
        self.values = []
        self.maxNumValue = 0
        if bitSetValues:
            numValue = 1
        else:
            numValue = 0
        for valueDef in valueDefs:
            self._defValue(valueClass, valueDef, numValue)
            if bitSetValues:
                numValue = numValue << 1
            else:
                numValue += 1
        self.values = tuple(self.values)
        self.makeImmutable();

    def _createValue(self, valueClass, name, numValue, strValue):
        val = valueClass(name, numValue, strValue)
        self.__dict__[name] = val
        self.aliases[name] = val
        if strValue != None:
            self.aliases[strValue] = val
        self.maxNumValue = max(self.maxNumValue, numValue)
        self.values.append(val)
        return val
    
    def _defValue(self, valueClass, valueDef, numValue):
        if (type(valueDef) is tuple) or (type(valueDef) is list):
            val = self._createValue(valueClass, valueDef[0], numValue, valueDef[1])
            if (len(valueDef) > 2) and (valueDef[2] != None):
                assert type(valueDef[2]) is tuple
                for a in valueDef[2]:
                    self.aliases[a] = val
        else:
            self._createValue(valueClass, valueDef, numValue, valueDef)
        
    def __getstate__(self):
        return (self.name, self.aliases, self.values, self.maxNumValue)

    def __setstate__(self, st):
        (self.name, self.aliases, self.values, self.maxNumValue) = st
        self.makeImmutable();

    def lookup(self, name):
        """look up a value by name or aliases"""
        return self.aliases[name]

    def getValues(self, bitVals):
        "get a list of values associated with a bit set"
        vals = []
        for v in self.values:
            if v.numValue & bitVals:
                vals.append(v)
        return vals

    def getValuesOr(self, vals):
        "get bit-wise or of the numeric values of a sequence of values"
        numVal = 0
        for v in vals:
            numVal |= int(v)
        return v

    # FIXME: emulates meta class new
    def __call__(self, name):
        return self.lookup(name)



# FIXME: should really use meta classes; some enumeration stuff:
#
# http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/67107
# http://pytable.sourceforge.net/pydoc/basictypes.enumeration.html
# http://www.bgb.cc/garrett/originals/
# http://www.python.org/doc/essays/metaclasses/Enum.py
# http://www.python.org/cgi-bin/moinmoin/EnumerationProgramming

# FIXME: should really be a tuple instead of values field
