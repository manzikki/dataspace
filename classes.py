"""
Classes for simple dataspace manager. Marko Niinimaki, niinimakim@webster.ac.th, 2019
"""
import os
import csv
import codecs
import sys
import json

def count_lines(fullname):
    """ counts the lines in given file, returns the number of lines """
    numlines = 0
    with open(fullname) as fil:
        for _ in fil:
            numlines += 1
    fil.close()
    return numlines

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
    name = ""
    tags = []
    fields = [] #list of fieldname->fielddesc
    fielddatatypes = []
    #fielddatatypes = [] #fieldname->fielddatatype
    measures = []

    def __init__(self, filename):
        self.fields = []
        self.fielddatatypes = []
        self.measures = []
        self.formatted_fields = ""
        self.name = filename.replace('.meta', '')

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

    def addfield(self, fieldname, fielddesc, fielddatatype=""):
        """
        Adds a field fieldname->fielddesc assoc array in the array fields and
        fieldname -> field data type in fielddatatypes.
        """
        myfield = {}
        myfield[fieldname] = fielddesc
        self.fields.append(myfield)
        myfielddt = {}
        myfielddt[fieldname] = fielddatatype
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
        nometa = filen.replace(".meta", "")
        jsonfile = open(directory+"/"+nometa+".jmeta")
        jsonstr = jsonfile.readline()
        jsonfile.close()
        #print(jsonstr)

        self.__dict__ = json.loads(jsonstr)
        if os.path.isfile(directory+"/"+nometa):
            self.fsize = os.path.getsize(directory+"/"+nometa)

        self.set_formatted_fields()

    def write_to_file(self, directory, filen):
        """
        Writes the meta info into a file.
        """
        jsonstr = json.dumps(self.__dict__)
        print(jsonstr)
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

    def get_fieldlist(self):
        """
        Returns a list of hashes as follows
        f['name'] = fieldname, f['decr'] = description, f['scale'] = nominal, ..
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
                if '.meta' in filen:
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
                if '.meta' in filen:
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
                if '.meta' in filen:
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
