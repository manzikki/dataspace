"""
Classes for simple dataspace manager. Marko Niinimaki, niinimakim@webster.ac.th, 2019
"""
import os
import csv

def count_lines(fullname):
    """ counts the lines in given file, returns the number of lines """
    numlines = 0
    with open(fullname) as fil:
        for line in fil:
            numlines += 1
    fil.close()
    return numlines

class MetaInfo:
    """
    Represents one file related meta information.
    """
    descr = ""
    formatted_fields = ""
    lines = 0
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
        Adds all fields of a measure.
        """
        spec = unit+","+scale+","+eventness
        self.addmeasurespec(fieldname, spec)

    def get_unit(self, measure):
        for m in self.measures:
            key = m.keys()[0]
            if key == measure:
                values = m[key]
                val_list = values.split(",")
                return val_list[0]
        return ""

    def get_scale(self, measure):
        for m in self.measures:
            key = m.keys()[0]
            if key == measure:
                values = m[key]
                val_list = values.split(",")
                return val_list[1]
        return ""

    def get_eventness(self, measure):
        for m in self.measures:
            key = m.keys()[0]
            if key == measure:
                values = m[key]
                val_list = values.split(",")
                return val_list[2]
        return ""

    def set_formatted_fields(self):
        #set the field info for this, to be shown on the web page
        s = ""
        for f in self.fields:
            mykey = f.keys()[0]
            myval = f[mykey]
            s = s + " " + mykey + " : " + myval
            if self.get_unit(mykey):
                s = s + ' ('+self.get_unit(mykey)+' '+self.get_scale(mykey)+' '+\
                                                      self.get_eventness(mykey)+') '
            s = s + "<br/>"
        self.formatted_fields = s

    def read_from_file(self, directory, filen):
        if not filen.endswith(".meta"):
            filen = filen + ".meta"
        with open(directory+"/"+filen) as csv_file:
            reader = csv.reader(csv_file, delimiter=',', quotechar='"')
            for row in reader:
                #print('* '.join(row))
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
        if not filen.endswith(".meta"):
            filen = filen + ".meta"
        #construct rows
        row = ['descr', self.descr]
        with open(directory+"/"+filen, 'w') as writeFile:
            writer = csv.writer(writeFile)
            writer.writerow(row)
            for f in self.fields:
                mykey = f.keys()[0]
                mydesc = f[mykey]
                row = ['FIELD', mykey, mydesc]
                if self.get_scale(mykey):
                    unit = self.get_unit(mykey)
                    scale = self.get_scale(mykey)
                    ev = self.get_eventness(mykey)
                    row = ['FIELD', mykey, mydesc, unit, scale, ev]
                writer.writerow(row)

    def get_as_string(self):
        s = self.name + " " + self.descr
        for f in self.fields:
            s = s + str(f) + " "
            mykey = f.keys()[0]
            if self.get_unit(mykey):
                s = s + '('+self.get_unit(mykey)+' '+self.get_scale(mykey)+' '+\
                                                     self.get_eventness(mykey)+') '
        s = s + "\n"
        return s

    def get_fieldlist(self):
        """
        returns a list of hashes as follows
        f['name'] = fieldname, f['decr'] = description, f['scale'] = nominal, ..
        """
        fieldlist = []
        for f in self.fields:
            #print(str(f))
            myfhash = {}
            mykey = f.keys()[0]
            myfhash['name'] = mykey
            myfhash['descr'] = f[mykey]
            myfhash['scale'] = self.get_scale(mykey)
            myfhash['eventness'] = self.get_eventness(mykey)
            myfhash['unit'] = self.get_unit(mykey)
            fieldlist.append(myfhash)
        return fieldlist          

    def getfieldnames(self):
        fieldnames = []
        for f in self.fields:
            mykey = f.keys()[0]
            fieldnames.append(mykey)
        return fieldnames

class MetaList:
    #represents a list of meta information about files in a directory
    metas = []

    def __init__(self, filedir):
        # constructor: build the list of metas from files
        files = []
        self.metas = []
        # r=root, d=directories, f = files
        for r, d, f in os.walk(filedir):
            for file in f:
                if '.meta' in file:
                    files.append(file)
                    #print(file)
        for f in files:
            #open the meta file and read the CSV
            myinfo = MetaInfo(f)
            myinfo.read_from_file(filedir, f)
            self.metas.append(myinfo)

    def get(self):
        return self.metas

    def get_meta_by_name(self, name):
        for m in self.metas:
            if m.name == name:
                return m
        return None

    def get_as_string(self):
        s = ""
        for m in self.metas:
            s = s + m.get_as_string()
        return s
