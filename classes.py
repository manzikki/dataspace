"""
Classes for simple dataspace manager. Marko Niinimaki, niinimakim@webster.ac.th, 2019
"""
import os
import csv
import codecs
import json

class UTF8Recoder:
    """
    Iterator that reads an encoded stream and reencodes the input to UTF-8
    """
    def __init__(self, fil, encoding):
        self.reader = codecs.getreader(encoding)(fil)

    def __iter__(self):
        return self

    def next(self):
        return self.reader.next().encode("utf-8")

class UnicodeReader:
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    """
    def __init__(self, fil, dialect=csv.excel, encoding="utf-8", **kwds):
        fil1 = UTF8Recoder(fil, encoding)
        constr_ok = True
        try:
            self.reader = csv.reader(fil1, dialect=dialect, **kwds)
        except:
            constr_ok = False
        if not constr_ok:
            self.reader = csv.reader(fil, dialect=dialect, **kwds)

    def next(self):
        """
        Returns next
        """
        row = self.reader.next()
        return [unicode(s, "utf-8") for s in row]

    def __next__(self):
        row = self.reader.next()
        return [unicode(s, "utf-8") for s in row]

    def __iter__(self):
        #for Python2 this should be just "self" (self.reader)
        return self.reader

class MetaInfo:
    """
    Represents one file related meta information.
    """
    descr = ""
    formatted_fields = ""
    fsize = 0
    fsizef = "" #nicely formatted number
    lines = 0
    linesf = "" #nicely formatted number
    name = ""
    tags = []
    fields = [] #list of fieldname->fielddesc
    fielddatatypes = []
    #fielddatatypes = [] #fieldname->fielddatatype
    fieldmins = [] #fieldname->minvalue
    fieldmaxs = []
    measures = []

    def __init__(self, filename):
        self.fields = []
        self.fielddatatypes = []
        self.fieldmins = []
        self.fieldmaxs = []
        self.measures = []
        self.formatted_fields = ""
        self.lines = 0
        self.linesf = ""
        self.name = filename.replace('.jmeta', '')

    def setdescr(self, descr):
        """
        Sets description.
        """
        self.descr = descr

    def setlines(self, lines):
        """
        Set number of lines.
        """
        self.lines = lines

    def settags(self, tags):
        """
        Sets tags.
        """
        self.tags = tags

    def addfield(self, fieldname, fielddesc, fielddatatype="", mmin=None, mmax=None):
        """
        Adds a field fieldname->fielddesc assoc array in the array fields and
        fieldname -> field data type in fielddatatypes.
        """
        myfield = {}
        myfield[fieldname] = fielddesc
        self.fields.append(myfield)
        myfielddt = {}
        myfielddt[fieldname] = fielddatatype
        if mmin or mmax:
            mymins = {}
            mymins[fieldname] = mmin
            mymaxs = {}
            mymaxs[fieldname] = mmax
            self.fieldmins.append(mymins)
            self.fieldmaxs.append(mymaxs)
        self.fielddatatypes.append(myfielddt)

    def addmeasurespec(self, fieldname, measurespec):
        """
        Adds a field fieldname->measurespec assoc array in the array measures.
        measurespec is unit,scale,eventness
        """
        mymeasure = {}
        mymeasure[fieldname] = measurespec
        self.measures.append(mymeasure)

    def addmeasure(self, fieldname, unit, scale, eventness):
        """
        Adds all fields (unit, scale, eventless) of a measure.
        The measure must exists before using this.
        """
        spec = unit+","+scale+","+eventness
        self.addmeasurespec(fieldname, spec)

    def get_unit(self, measure):
        """
        Gets the unit value of a measure if it exists.
        """
        for mea in self.measures:
            mydict = mea
            for mykey, myval in mydict.items():
                if mykey == measure:
                    val_list = myval.split(",")
                    return val_list[0]
        return ""

    def get_scale(self, measure):
        """
        Gets the scale value of a measure if it exists.
        """
        for mea in self.measures:
            mydict = mea
            for mykey, myval in mydict.items():
                if mykey == measure:
                    val_list = myval.split(",")
                    return val_list[1]
        return ""

    def get_eventness(self, measure):
        """
        Gets the eventness value of a measure if it exists.
        """
        for mea in self.measures:
            mydict = mea
            for mykey, myval in mydict.items():
                if mykey == measure:
                    val_list = myval.split(",")
                    return val_list[2]
        return ""

    def get_datatype(self, fieldname):
        """
        Gets the datatype.
        """
        for fds in self.fielddatatypes:
            mydict = fds
            for mykey, myval in mydict.items():
                if mykey == fieldname:
                    return myval
        return ""

    def get_min(self, fieldname):
        """
        Gets the minimum value, if given.
        """
        for mins in self.fieldmins:
            mydict = mins
            for mykey, myval in mydict.items():
                if mykey == fieldname:
                    return myval
        return ""

    def get_max(self, fieldname):
        """
        Gets the max value, if given.
        """
        for maxs in self.fieldmaxs:
            mydict = maxs
            for mykey, myval in mydict.items():
                if mykey == fieldname:
                    return myval
        return ""

    def get_lines(self):
        return self.lines

    def get_descr(self):
        return self.descr

    def set_formatted_fields(self):
        """
        Sets the "formatted_fields" attribute that is used for printing the field information.
        """
        #set the field info for this, to be shown on the web page
        s = ""
        for h in self.fields:
            mydict = h
            for mykey, myval in mydict.items():
                s = s + " " + mykey + " : " + myval
                if self.get_unit(mykey):
                    s = s + ' ('+self.get_unit(mykey)+' '+self.get_scale(mykey)+' '+\
                                                      self.get_eventness(mykey)+') '
                mydt = self.get_datatype(mykey)
                if mydt:
                    s = s + " " + mydt
            s = s + "<br/>"
        self.formatted_fields = s

    def read_from_file(self, directory, filen):
        """
        Reads the meta info from a file. Gets fsize from the real file.
        """
        nometa = filen.replace(".jmeta", "")
        if not os.path.exists(directory+"/"+nometa+".jmeta"):
            return False
        jsonfile = open(directory+"/"+nometa+".jmeta")
        jsonstr = jsonfile.readline()
        jsonfile.close()
        #print(jsonstr)

        self.__dict__ = json.loads(jsonstr)
        if os.path.isfile(directory+"/"+nometa):
            self.fsize = os.path.getsize(directory+"/"+nometa)
            self.fsizef = '{0:,}'.format(self.fsize)
        if self.lines:
            try:
                linesf = int(self.lines)
                self.linesf = '{0:,}'.format(linesf)
            except:
                pass
        self.set_formatted_fields()
        return True

    def write_to_file(self, directory, filen):
        """
        Writes the meta info into a file.
        """
        jsonstr = json.dumps(self.__dict__)
        #print(jsonstr)
        if not filen.endswith(".jmeta"):
            filen = filen + ".jmeta"
        f = open(directory+"/"+filen, 'w')
        f.write(jsonstr)
        f.close()

    def get_as_string(self):
        """
        For debugging.
        """
        s = self.name + " " + self.descr
        for f in self.fields:
            s = s + str(f) + " "
            myhash = f
            for mykey, _ in myhash.items():
                if self.get_unit(mykey):
                    s = s + '('+self.get_unit(mykey)+' '+self.get_scale(mykey)+' '+\
                                                     self.get_eventness(mykey)+') '
        s = s + "\n"
        return s

    def __str__(self):
        """
        For debugging.
        """
        return self.get_as_string()

    def get_fieldlist(self, samplehash={}):
        """
        Returns a list of hashes as follows
        f['name'] = fieldname, f['decr'] = description, f['scale'] = nominal, ..
        If samplehash is given as a parameter, gets the sample for fields in it.
        """
        fieldlist = []
        for f in self.fields:
            myhash = f
            myfhash = {}
            for mykey, _ in myhash.items():
                myfhash['filename'] = self.name
                myfhash['name'] = mykey
                myfhash['descr'] = f[mykey]
                myfhash['scale'] = self.get_scale(mykey)
                myfhash['eventness'] = self.get_eventness(mykey)
                myfhash['unit'] = self.get_unit(mykey)
                myfhash['datatype'] = self.get_datatype(mykey)
                myfhash['min'] = self.get_min(mykey)
                myfhash['max'] = self.get_max(mykey)
                #a bit stupid but helps with formatting
                myfhash['minmax'] = myfhash['min'] + " .. " + myfhash['max']
                if samplehash:
                    sample = samplehash.get(mykey, '')
                    myfhash['sample'] = sample
                fieldlist.append(myfhash)
        return fieldlist

    def getfieldnames(self):
        """
        Gets the names of fields as a list.
        """
        fieldnames = []
        for f in self.fields:
            myhash = f
            for mykey, _ in myhash.items():
                fieldnames.append(mykey)
        return fieldnames

class MetaList:
    """
    Represents a list of meta information about files in a directory.
    """
    metas = []

    def __init__(self, filedir):
        # constructor: build the list of metas from files
        files = []
        self.metas = []
        # r=root, d=directories, f = files
        for _, _, f in os.walk(filedir):
            for filen in f:
                if '.jmeta' in filen:
                    files.append(filen)
                    #print(filen)
            break #no recurse to subdirs
        for f in files:
            #open the meta file and read the CSV
            myinfo = MetaInfo(f)
            myinfo.read_from_file(filedir, f)
            self.metas.append(myinfo)

    def get(self):
        """
        Returns the metas that is a list of MetaInfo objects.
        """
        return self.metas

    def get_meta_by_name(self, name):
        """
        Returns a MetaInfo object from the list if the list contains it.
        """
        for meta in self.metas:
            if meta.name == name:
                return meta
        return None

    def get_as_string(self):
        """
        For debugging.
        """
        s = ""
        for m in self.metas:
            s = s + m.get_as_string()
        return s

class CollectionList:
    """
    A collection is a directory that contains files and meta-files.
    """
    dirs = []
    files = []
    current = ""
    filedir = ""

    def __init__(self, filedir):
        # constructor: build the list dirs and files
        self.current = ""
        self.metas = []
        self.dirs = []
        self.files = []
        self.filedir = filedir
        # r=root, d=directories, f = files
        for _, ds, _ in os.walk(filedir):
            for dire in ds:
                self.dirs.append(dire)
            break

        for _, _, f in os.walk(filedir):
            for filen in f:
                if '.jmeta' in filen:
                    self.files.append(filen)
            break

    def reinit(self):
        """
        Re-read data.
        """
        self.current = ""
        self.metas = []
        self.dirs = []
        self.files = []
        for _, ds, _ in os.walk(self.filedir):
            for dire in ds:
                self.dirs.append(dire)
            break

        for _, _, f in os.walk(self.filedir):
            for filen in f:
                if '.jmeta' in filen:
                    self.files.append(filen)
            break

    def get(self):
        """
        Returns the list (directories).
        """
        return self.dirs

    def getfiles(self):
        """
        Returns the list of meta files.
        """
        return self.files

    def setcurrent(self, cur):
        """
        Sets the current collection.
        """
        self.current = cur

    def getcurrent(self):
        """
        Gets the current collection.
        """
        return self.current

class Cube:
    """
    Represents the cube that is used for data integration.
    """
    cubefields = []
    cubefiles = []
    pdcube = None #pandas
    cube_round = 0 #are we building the original cube or adding into it?

    def __init__(self):
        """
        Constructor.
        """
        self.cube_round = 0

    def add_cube_file(self, filename):
        """
        Adds a file in the list of cube files.
        """
        self.cubefiles.append(filename)

    def get_cube_files(self):
        """
        Get cube files.
        """
        return self.cubefiles

    def add_cube_field(self, fieldname):
        """
        Adds a field in the list of cube fields.
        """
        self.cubefields.append(fieldname)

    def get_cube_fields(self):
        """
        Get cube fields.
        """
        return self.cubefields

    def set_pdcube(self, mypdcube):
        """
        Insert the Pandas cube.
        """
        self.pdcube = mypdcube

    def get_pdcube(self):
        """
        Get Pandas cube.
        """
        return self.pdcube

    def reset(self):
        """
        Reset cube rounds.
        """
        self.cube_round = 0

    def set_cube_round(self, cround):
        """
        Set cube rounds.
        """
        self.cube_round = cround

    def get_cube_round(self):
        """
        Get cube rounds.
        """
        return self.cube_round
