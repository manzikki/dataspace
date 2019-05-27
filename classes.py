"""
Classes for simple dataspace manager. Marko Niinimaki, niinimakim@webster.ac.th, 2019
"""
import os
import csv
import codecs

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
    def __init__(self, f, encoding):
        self.reader = codecs.getreader(encoding)(f)

    def __iter__(self):
        return self

    def next(self):
        return self.reader.next().encode("utf-8")

class UnicodeReader:
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    """
    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        f1 = UTF8Recoder(f, encoding)
        constr_ok = True
        try:
            self.reader = csv.reader(f1, dialect=dialect, **kwds)
        except:
            constr_ok = False
        if not constr_ok:
            self.reader = csv.reader(f, dialect=dialect, **kwds)

    def next(self):
        row = self.reader.next()
        return [unicode(s, "utf-8") for s in row]

    def __iter__(self):
        #for Python2 this should be just "self".
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
    measures = []

    def __init__(self, filename):
        self.fields = []
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

    def addfield(self, fieldname, fielddesc):
        """
        Adds a field fieldname->fielddesc assoc array in the array fields
        """
        myfield = {}
        myfield[fieldname] = fielddesc
        self.fields.append(myfield)

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
            s = s + "<br/>"
        self.formatted_fields = s

    def read_from_file(self, directory, filen):
        """
        Reads the meta info from a file. Gets fsize from the real file.
        """
        if not filen.endswith(".meta"):
            filen = filen + ".meta"
        nometa = filen.replace(".meta","")
        if os.path.isfile(directory+"/"+nometa):
            self.fsize = os.path.getsize(directory+"/"+nometa)
        with open(directory+"/"+filen) as csv_file:
            reader = csv.reader(csv_file, delimiter=',', quotechar='"')
            for row in reader:
                #print('* '.join(row))
                if len(row) > 0:
                    if row[0] == 'FIELD':
                        self.addfield(row[1], row[2])
                        if len(row) > 3:
                            #print("Adding "+str(row[3:]))
                            self.addmeasurespec(row[1], ",".join(row[3:]))
                    if row[0] == 'descr':
                        self.setdescr(row[1])
                    if row[0] == 'lines':
                        self.setlines(row[1])
            self.set_formatted_fields()

    def write_to_file(self, directory, filen):
        """
        Writes the meta info into a file.
        """
        if not filen.endswith(".meta"):
            filen = filen + ".meta"
        row = ['descr', self.descr]
        with open(directory+"/"+filen, 'w') as writeFile:
            writer = csv.writer(writeFile)
            writer.writerow(row)
            for f in self.fields:
                mydict = f
                for mykey, myval in mydict.items():
                    mydesc = f[mykey]
                    row = ['FIELD', mykey, mydesc]
                    if self.get_scale(mykey):
                        unit = self.get_unit(mykey)
                        scale = self.get_scale(mykey)
                        ev = self.get_eventness(mykey)
                        row = ['FIELD', mykey, mydesc, unit, scale, ev]
                    writer.writerow(row)

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
                myfhash['name'] = mykey
                myfhash['descr'] = f[mykey]
                myfhash['scale'] = self.get_scale(mykey)
                myfhash['eventness'] = self.get_eventness(mykey)
                myfhash['unit'] = self.get_unit(mykey)
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
        for r, d, f in os.walk(filedir):
            for filen in f:
                if '.meta' in filen:
                    files.append(filen)
                    #print(filen)
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
