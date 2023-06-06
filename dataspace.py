"""
Simple dataspace management for CSV files. Marko Niinimaki marko.niinimaki@protonmail.com 2017-2023
"""
import tarfile
import re
import bz2
import os
import csv
import io
import codecs
import hashlib
import base64
import random
import requests
from shutil import move, copyfile
import chardet
from dateutil.parser import parse
from flask import Flask, session, render_template, redirect, \
                  url_for, request, flash, Response
from werkzeug.utils import secure_filename
import numpy
import pandas as pd
from bs4 import BeautifulSoup
import matplotlib
import matplotlib.pyplot as plt
import geopandas as gpd
from forms import LoginForm, UploadForm, PastedTextForm, WikiForm
from classes import MetaInfo, MetaList, UTF8Recoder, UnicodeReader, CollectionList, Cube

app = Flask(__name__)
app.config['SECRET_KEY'] = '5791628bb0b13'
#app.config["APPLICATION_ROOT"] = "/home"
app.config['S'] = ''  #put the path to 'static' in it in appmain
app.config['SL'] = '' #same but with "/" at the end
app.config['U'] = ''  #url base like "/" or "/home"
app.config['UP'] = '' #for uploads
app.config['COLLIST'] = []
app.config['NEWCSVFIEDLS'] = [] #used by the 'new' function

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD_MD5 = "1db422179f1290ab1499f146972b2d82" #FpacNida986!
#                     but we read it from a file when the app starts
MAX_SHOWN_LINES = 500 #max number of lines in view
MAX_COUNTED_LINES = 10000
MAX_COLNAME = 20 #max chars in collection
TMPCUBENAME = "tmpcube.csv"
MYCUBE = Cube()

@app.route("/", methods=['GET', 'POST'])
@app.route("/home", methods=['GET', 'POST'])
def appmain():
    """
    Main route, shows the main page.
    The functionality is explained in
    https://github.com/manzikki/dataspace/wiki/Dataspace-application-technical-documentation#Program-flow-example-The-main-page
    """
    #we may receive a search request
    mydict = request.form
    #reset cube if the user abandons cube building
    global MYCUBE
    MYCUBE.reset()

    global ADMIN_PASSWORD_MD5
    dir_path = os.path.dirname(os.path.realpath(__file__))
    #read admin password from a file if it exists
    try:
        pwfile = open("pw.md5")
        ADMIN_PASSWORD_MD5 = pwfile.readline()
        pwfile.close()
    except:
        pass
    app.config['S'] = os.path.join(dir_path, "static")
    app.config['SL'] = dir_path+"/static/"
    app.config['UP'] = dir_path+"/upload/"
    app.config['COMPAT'] = dir_path+"/static/compat.file" #contains compatibility info
    if not app.config['U']:
        app.config['U'] = request.base_url
    if not app.config['COLLIST']:
        app.config['COLLIST'] = CollectionList(app.config['S'])
    if app.config['COLLIST'].getcurrent():
        app.config['S'] = dir_path+"/static/"+app.config['COLLIST'].getcurrent()
        app.config['SL'] = dir_path+"/static/"+app.config['COLLIST'].getcurrent()+"/"

    mymetas = MetaList(app.config['S'])
    username = ""
    if 'username' in session:
        username = session['username']
    #check that we can write to the static directory
    if not os.access(app.config['S'], os.W_OK):
        return "Directory "+app.config['S']+" is not writable. \
         Please follow the installation instructions."
    #and upload
    if not os.access(app.config['UP'], os.W_OK):
        return "Directory "+app.config['UP']+" is not writable. \
         Please follow the installation instructions."
    currentcoldir = "static"
    metas = mymetas.get()
    sterm = ""
    if 'search' in mydict and mydict['search']:
        sterm = mydict['search'].split()[0]
        if len(sterm) < 3:
            flash("Sorry, the search term should contain at least 3 characters.")
        else:
            newmetas = []
            for meta in metas:
                descr = meta.get_descr()
                if sterm.lower() in descr.lower():
                    newmetas.append(meta)
                fieldnames = meta.getfieldnames()
                for fieldn in fieldnames:
                    if sterm.lower() in fieldn.lower():
                        if not meta in newmetas:
                            newmetas.append(meta)
                flist = meta.get_fieldlist()
                for finfo in flist:
                    if sterm.lower() in finfo['descr'].lower():
                        if not meta in newmetas:
                            newmetas.append(meta)
            metas = newmetas
            if metas:
                flash("Showing meta data with description or fields containing \""+sterm+"\".")
            else:
                flash("Could not find meta data with description or fields\
                       containing \""+sterm+"\".")
    if app.config['COLLIST'].getcurrent():
        currentcoldir = "static/"+app.config['COLLIST'].getcurrent()
    return render_template('home.html', username=username,
                           currentcoldir=currentcoldir,
                           metas=metas, sterm=sterm,
                           coldirs=app.config['COLLIST'].get(),
                           curdir=app.config['COLLIST'].getcurrent())

@app.context_processor
def utility_processor():
    """
    Define a function that can be used in a template. This is for compatibility checking.
    """
    def is_in_compat(filea, fielda, fileb, fieldb):
        """
        Check if filea,fielda,fileb,fieldb or fileb,fieldb,filea,fielda is listed
        in the compat file.
        """
        if os.path.isfile(app.config['COMPAT']):
            with io.open(app.config['COMPAT'], 'rU') as csv_file:
                csv_reader = UnicodeReader(csv_file, delimiter=',', quotechar='"')
                for row in csv_reader:
                    if len(row) == 4:
                        if row[0] == filea and row[1] == fielda and \
                                     row[2] == fileb and row[3] == fieldb:
                            return True
                        if row[2] == filea and row[3] == fielda and \
                                     row[0] == fileb and row[1] == fieldb:
                            return True
                    #print(str(row))
            csv_file.close()
        return False
    return dict(is_in_compat=is_in_compat)

@app.route("/login", methods=['GET', 'POST'])
@app.route("/home/login", methods=['GET', 'POST'])
def login():
    """
    Shows the login page.
    The functionality is explained in:
    https://github.com/manzikki/dataspace/wiki/Dataspace-application-technical-documentation#Program-flow-example-login
    """
    form = LoginForm()
    if form.validate_on_submit():
        passw = form.password.data.encode('utf-8')
        passwmd5 = hashlib.md5(passw).hexdigest()
        #print("user entered "+passwmd5+" pw is "+ADMIN_PASSWORD_MD5)
        if form.username.data == ADMIN_USERNAME and passwmd5 == ADMIN_PASSWORD_MD5:
            #flash('You have been logged in!', 'success')
            session['username'] = ADMIN_USERNAME
            return redirect(url_for('appmain'))
        flash('Login Unsuccessful. Please check username and password', 'danger')
    return render_template('login.html', title='Login', form=form)

def file_not_ok(filename):
    """
    Check that the file is readable by csv reader. Returns "" if ok, otherwise an error msg.
    """
    if os.stat(app.config['SL']+filename).st_size == 0:
        return "File is empty."
    if ".tar.gz" in filename:
        try:
            tarf = tarfile.open(app.config['SL']+filename, "r:gz")
            for member in tarf.getmembers():
                #print(member.name)
                if member.name.startswith("/") or ".." in member.name:
                    return "Unsafe element in archive: "+member.name
                if ".CSV" not in member.name.upper():
                    return "File "+member.name+" in "+filename+" does not have extension csv."
        except:
            #return "tar.gz file open error"
            return ""
        return ""
    if ".zip" in filename:
        return "Sorry, not yet implemented."
    if ".bz2" in filename:
        #add checking here
        return ""
    myf = io.open(app.config['SL']+filename, "rb")
    myline = myf.readline()
    myf.close()
    #check that the line contains commas

    if filename.upper().endswith("CSV") and "," in str(myline):
        return ""
    if filename.upper().endswith("TSV"):
        for cha in myline:
            if cha == 9: #found a tab
                return ""
        return ""
    return "The first line of the file does not contain separator characters."

def process_compressed_file(fname_no_path):
    """
    Puts together all the content of a tar.gz file so that the header appears on top,
    or: decompresses a bz2 file.
    Return the name of the decompressed file.
    """
    if fname_no_path.endswith("bz2") or fname_no_path.endswith("BZ2"):
        #we support only one file inside a bz2 arhive, we should check
        #if the contents is a tar file
        inputfile = bz2.BZ2File(app.config['SL']+fname_no_path, 'rb')
        outputf = open(app.config['SL']+fname_no_path+".tsv", "ab")
        myline = inputfile.readline()
        while myline:
            outputf.write(myline)
            myline = inputfile.readline()
        outputf.close()
        inputfile.close()
        os.remove(app.config['SL']+fname_no_path)
        return fname_no_path+".tsv"

    tarf = tarfile.open(app.config['SL']+fname_no_path, "r:gz")
    tarf.extractall(app.config['SL'])
    #outputf = open(app.config['SL']+fname_no_path+".csv", "a")
    count = 0
    outputf = None
    for member in tarf.getmembers():
        count += 1
        #print(member.name)
        if count == 1:
            move(app.config['SL']+member.name, app.config['SL']+fname_no_path+".csv")
            outputf = open(app.config['SL']+fname_no_path+".csv", "a")
        else:
            #append to csv but omit the first line
            csvfile = open(app.config['SL']+member.name, 'r')
            lineno = 0
            for line in csvfile:
                lineno += 1
                if lineno == 1:
                    pass
                if line:
                    outputf.write(line)
            csvfile.close()
        #delete the copied file
        if os.path.isfile(app.config['SL']+member.name):
            os.remove(app.config['SL']+member.name)
    #delete the tar.gz file
    tarf.close()
    os.remove(app.config['SL']+fname_no_path)
    outputf.close()
    return fname_no_path+".csv"

@app.route("/editmeta", methods=['GET', 'POST'])
@app.route("/home/editmeta", methods=['GET', 'POST'])
#edit metadata. Admin only.
def editmeta():
    """
    Edit file metadata. Shows the edit form. The corresponding jmeta file must exist.
    The functionality is explained in:
    https://github.com/manzikki/dataspace/wiki/Dataspace-application-technical-documentation#Program-flow-example-edit-file-metadata
    """
    if 'username' not in session:
        return redirect(url_for('appmain'))
    #get the file field
    mydict = request.form
    myfile = mydict['file']
    #build a meta object and read it from file
    mymeta = MetaInfo(myfile)
    mymeta.read_from_file(app.config['S'], myfile)
    numlines = mymeta.get_lines()
    samples = getfieldsamples(app.config['SL']+myfile)
    fields = mymeta.get_fieldlist(samples)
    #we need to generate the fields dynamically so it's easier to use direct templating, not WTF
    return render_template('editmeta.html', file=myfile, descr=mymeta.descr,
                           fieldlist=fields, numlines=numlines)

@app.route("/add_iso", methods=['GET', 'POST'])
@app.route("/home/add_iso", methods=['GET', 'POST'])
def add_iso():
    """
    Add an ISO code in the CVS if the data is about countries -> addiso -> addiso_resp.
    """
    #get the file
    mydict = request.form
    myfile = mydict['file']
    mymeta = MetaInfo(myfile)
    mymeta.read_from_file(app.config['S'], myfile)
    fields = mymeta.get_fieldlist()
    #Is there already an ISO column?
    for field in fields:
        if field['name'] == "ISO":
            return "An ISO field already exists."
    #ask the user where the country data is
    return render_template('addiso.html', file=myfile, fieldlist=fields)

@app.route("/addiso_resp", methods=['GET', 'POST'])
@app.route("/home/addiso_resp", methods=['GET', 'POST'])
def addiso_resp():
    """
    Add an ISO code in the CVS if the data is about countries.
    """
    #get the file and field info
    mydict = request.form
    myfile = mydict['file']
    countryp = mydict['country-param']
    #put the file into a dataframe
    df = pd.read_csv(app.config['SL']+myfile)
    df["ISO"] = ""

    countries = ["united states","india","china","brazil","russia","france","canada","australia","mexico",
                 "south africa","thailand","spain","germany","sweden","vietnam","indonesia","italy","finland",
                 "turkey","united kingdom","poland","bangladesh","japan","argentina","pakistan","malaysia","iran",
                 "saudi arabia","philippines","hungary","uzbekistan","colombia","nigeria","kenya","ukraine",
                 "myanmar","dr congo","uganda","peru","mali","netherlands","algeria","austria","ethiopia",
                 "belgium","greece","sri lanka","south korea","ghana","ireland","zimbabwe","new zealand",
                 "kazakhstan","tanzania","romania","lithuania","switzerland","uruguay","denmark","zambia",
                 "czech republic","cambodia","ecuador","taiwan","chad","laos","slovakia","slovenia","libya",
                 "afghanistan","kyrgyzstan","botswana","madagascar","mozambique","sudan","tajikistan","nepal",
                 "croatia","puerto rico","north korea","central african republic","nicaragua","congo",
                 "bosnia","jamaica","lebanon","georgia","tunisia","cyprus","dominican republic","israel",
                 "bulgaria","niger","guatemala","senegal","benin","eritrea","malawi","burkina faso","somalia",
                 "honduras","gabon","north macedonia","iceland","burundi","mauritania","bhutan","togo",
                 "sierra leone","liberia","moldova","papua new guinea","el salvador","montenegro","armenia",
                 "jordan","qatar","east timor","lesotho","kuwait","new caledonia","costa rica","rwanda",
                 "west bank","guinea-bissau","suriname","haiti","bahrain","united arab","guyana","albania",
                 "eswatini","singapore","fiji","belize","gambia","brunei","djibouti","equatorial guinea",
                 "luxembourg","bahamas","french polynesia","mauritius","malta","hong kong","marshall islands",
                 "kosovo","barbados","dominica","solomon islands","cape verde","são tomé and príncipe",
                 "u.s. virgin islands","saint lucia","antigua and barbuda","samoa","grenada","isle of man",
                 "vanuatu","guam","faroe islands","comoros","cayman islands","tonga","kiribati","liechtenstein",
                 "jersey","curaçao","northern mariana islands","seychelles","bermuda","falkland islands","macau",
                 "saint kitts and nevis","andorra","cook islands","san marino","american samoa","niue",
                 "british virgin islands","saint helena","anguilla","christmas island","turks and caicos islands",
                 "saint pierre","maldives","norfolk island","sint maarten","nauru","gibraltar",
                 "cocos","tuvalu","aruba","antilles","angola","antarctica","azerbaijan","belarus","bolivia", "bouvet",
                 "chile", "ivoire", "cameroon", "of the congo", "cook", "czechoslovakia","cuba", "guinea" ,"guadeloupe",
                 "guernsey", "greenland", "french guiana", "iraq", "latvia", "morocco", "mongolia", "montserrat", "norway",
                 "oman", "paraguay", "portugal", "reunion", "serbia", "south sudan", "swaziland", "syria", "turkmenistan",
                 "timor-leste", "venezuela", "USA", "egypt", "estonia", "liectenstein", "namibia"]


    isos = ["USA","IND","CHN","BRA","RUS","FRA","CAN","AUS","MEX","ZAF","THA","ESP","DEU","SWE","VNM","IDN","ITA",
            "FIN","TUR","GBR","POL","BGD","JPN","ARG","PAK","MYS","IRN","SAU","PHL","HUN","UZB","COL","NGA","KEN",
            "UKR","MMR","COD","UGA","PER","MLI","NLD","DZA","AUT","ETH","BEL","GRC","LKA","KOR","GHA","IRL","ZWE",
            "NZL","KAZ","TZA","ROU","LTU","CHE","URY","DNK","ZMB","CZE","KHM","ECU","TWN","TCD","LAO","SVK","SVN",
            "LBY","AFG","KGZ","BWA","MDG","MOZ","SDN","TJK","NPL","HRV","PRI","PRK","CAF","NIC","COG","BIH","JAM",
            "LBN","GEO","TUN","CYP","DOM","ISR","BGR","NER","GTM","SEN","BEN","ERI","MWI","BFA","SOM","HND","GAB",
            "MKD","ISL","BDI","MRT","BTN","TGO","SLE","LBR","MDA","PNG","SLV","MNE","ARM","JOR","QAT","TLS","LSO",
            "KWT","NCL","CRI","RWA","WBG","GNB","SUR","HTI","BHR","ARE","GUY","ALB","SWZ","SGP","FJI","BLZ","GMB",
            "BRN","DJI","GNQ","LUX","BHS","PYF","MUS","MLT","HKG","MHL","XKX","BRB","DMA","SLB","CPV","STP","VIR",
            "LCA","ATG","WSM","GRD","IMN","VUT","GUM","FRO","COM","CYM","TON","KIR","LIE","JEY","CUW","MNP","SYC",
            "BMU","FLK","MAC","KNA","AND","COK","SMR","ASM","NIU","VGB","SHN","AIA","CXR","TCA","SPM","MDV","NFK",
            "SXM","NRU","GIB","CCK","TUV","ABW","ANT","AGO","ATA","AZE","BLR","BOL","BVT", "CHL", "CIV", "CMR", "COD",
            "COK", "CSK", "CUB", "GIN", "GLP", "GGY", "GRL", "GUF", "IRQ", "LVA", "MAR", "MNG", "MSR", "NOR", "OMN",
            "PRY", "PRT", "REU", "SRB", "SSD", "SWZ", "SYR", "TKM", "TLS", "VEN", "USA", "EGY", "EST", "LIE", "NAM"]


    addthese = []

    for countryname in df[countryp]:
        #print(countryname)
        matchediso = ""
        matchn = countryname.lower()
        for idx, country in enumerate(countries):
            #change rep. to republic here
            if  matchn.startswith(country):
                #print(isos[idx])
                matchediso = isos[idx]
        addthese.append(matchediso)

    df["ISO"] = addthese
    #write it back
    df.to_csv(app.config['SL']+myfile, encoding='utf-8', index=None)
    #add the metadata here
    mymeta = MetaInfo(myfile)
    mymeta.read_from_file(app.config['S'], myfile)
    mymeta.addfield("ISO", "country iso code")    
    mymeta.write_to_file(app.config['S'], myfile)
    return redirect(url_for('appmain'))


def natural_sort(mylist):
    """
    Natural sort: 1-line will appear before 10-line.
    """
    convert = lambda text: int(text) if text.isdigit() else text.lower()
    alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
    return sorted(mylist, key=alphanum_key)

@app.route("/editmetasubmit", methods=['GET', 'POST'])
@app.route("/home/editmetasubmit", methods=['GET', 'POST'])
#get the result of metadata editing
def editmetasubmit():
    """
    Receives metadata values from the edit form (editmeta). Writes the metadata into a jmeta file.
    If headers have changed, rewrites them. If columns have been deleted, rewrites the entite file.
    """
    #get the file field
    mydict = request.form
    #print(str(mydict))
    myfile = mydict['file']
    descr = mydict['descr']
    numlines = mydict['numlines']
    mymeta = MetaInfo(myfile)
    mymeta.setdescr(descr)
    if numlines:
        mymeta.setlines(numlines)
    fieldname = ""
    fielddescr = ""
    fieldunit = ""
    fieldscale = ""
    fieldevent = ""
    fielddatatype = ""
    fieldmin = ""
    fieldmax = ""
    delfields = [] #fields marked by the user as delete
    fieldnames = [] #will be written to the CSV file as header
    num = 0 #counter
    for fiter in natural_sort(mydict):
        #get the number
        hyphenpos = fiter.find("-")
        if hyphenpos > 0:
            equalpos = fiter.find("=")
            if equalpos > 0:
                delfname = fiter[hyphenpos+1:equalpos]
                num = int(fiter[:hyphenpos])
                if str(num)+"=delete" in mydict:
                    if delfname not in delfields:
                        delfields.append(delfname)
        #print(fiter)
        if fiter == "file":
            next
        if fiter == "descr":
            next
        if fiter == "numlines":
            next
        #print(str(infieldcount)+" "+fiter+" ",mydict[fiter])
        if "=name" in fiter:
            fieldname = mydict[fiter].strip().replace(',', '')
            fieldnames.append(fieldname)
        if "=datatype" in fiter: # infieldcount == 1: #datatype
            fielddatatype = mydict[fiter].strip()
        if "=descr" in fiter: #infieldcount == 2: #description
            fielddescr = mydict[fiter].strip()
        if "=event" in fiter: #infieldcount == 3: #event
            fieldevent = mydict[fiter].strip()
        if "=min" in fiter:
            if mydict[fiter]:
                fieldmin = mydict[fiter].strip()
        if "=max" in fiter:
            if mydict[fiter]:
                fieldmax = mydict[fiter].strip()
        if "=scale" in fiter: #infieldcount == 4: #scale
            fieldscale = mydict[fiter].strip()
        if "=unit" in fiter: #infieldcount == 5: #unit
            fieldunit = mydict[fiter].strip()
            #we construct here, this is the last one
            #We'll handle the deleted fields later
            #print("Adding field "+fieldname)
            mymeta.addfield(fieldname, fielddescr, fielddatatype, fieldmin, fieldmax)
            fieldmin = None
            fieldmax = None
            if fieldunit:
                mymeta.addmeasure(fieldname, fieldunit, fieldscale, fieldevent)
    mymeta.write_to_file(app.config['S'], myfile)
    #NB: since editing field names is enabled, we must re-write the first line of the CSV file
    #if the field names have changed
    hlinewithquotes = ""
    if myfile.upper().endswith("TSV"):
        headerline = '\t'.join(fieldnames)
        hlinewithquotes = '"\t"'.join(fieldnames)
    else:
        headerline = ','.join(fieldnames)
        hlinewithquotes = '","'.join(fieldnames)

    hlinewithquotes = '"'+hlinewithquotes+'"'
    encoding = ""
    with open(app.config['SL']+myfile, 'rb') as fil:
        result = chardet.detect(fil.readline())
        encoding = result['encoding']
    if encoding == "ascii":
        encoding = "utf-8"

    csvfile = io.open(app.config['SL']+myfile, encoding=encoding)
    #read the first line to see if we need to change the file
    hlinefromfile = csvfile.readline().strip()

    if hlinefromfile == headerline or hlinefromfile == hlinewithquotes:
        if not delfields:
            print("No need to rewrite.")
            csvfile.close()
            return redirect(url_for('appmain'))
            #print("Diff "+hlinefromfile+"\n"+headerline+" "+hlinewithquotes)
    #otherwise: need to rewrite headers
    #replace non-ascii
    headerline = re.sub(r'[^\x00-\x7F]+', '', headerline)

    outfilen = app.config['SL']+myfile+".out"
    outfile = io.open(outfilen, 'w', encoding='utf-8')
    outfile.write(headerline+"\n")
    line = csvfile.readline()
    #write the rest
    line = csvfile.readline()
    while line:
        outfile.write(line)
        line = csvfile.readline()
    csvfile.close()
    outfile.close()
    move(outfilen, app.config['SL']+myfile)
    if not delfields:
        return redirect(url_for('appmain'))
    #finally: we are deleting a column
    #first read the entire cvs file
    df = pd.read_csv(app.config['SL']+myfile)
    #delete the columns that are in delfields
    df = df.drop(columns=delfields)
    #write it back
    df.to_csv(app.config['SL']+myfile, encoding='utf-8', index=None)
    #remove the field from meta
    for delf in delfields:
        mymeta.removefield(delf)
    mymeta.write_to_file(app.config['S'], myfile)
    return redirect(url_for('appmain'))

def count_lines(filename):
    """
    Returns the number of lines of a file.
    """
    count = 0
    encoding = ""
    with open(filename, 'rb') as fil:
        result = chardet.detect(fil.readline())
        encoding = result['encoding']
    if encoding == "ascii":
        encoding = "utf-8"
    myfile = io.open(filename, 'r', encoding=encoding)

    line = myfile.readline()
    while line:
        line = myfile.readline()
        count += 1
    myfile.close()
    return count

def build_fieldlist(filename):
    """
    Using a CSV file, builds a list of field hashes that can be used in the meta edit.
    For each field, the hash contains 'name, 'descr' ..
    The filename parameter must contain the path.
    """
    row = []
    row_sample = []
    fieldlist = []
    encoding = ""
    with open(filename, 'rb') as fil:
        result = chardet.detect(fil.readline())
        encoding = result['encoding']
    if encoding == "ascii":
        encoding = "utf-8"
    delim = ','
    if filename.upper().endswith("TSV"):
        delim = '\t'
    #read the first line of file to get field names
    with io.open(filename, 'r', encoding=encoding) as csv_file: #,'rU'
        reader = UnicodeReader(csv_file, delimiter=delim, quotechar='"')
        rowno = 0
        for row in reader: #read only 1 line, containing headers
            #remove the BOM
            if row:
                r1first = row[0]
                if len(r1first) > 0:
                    while  ord(r1first[0]) > 123:
                        r1first = r1first[1:]
                    row[0] = r1first
                break
        for row_sample in reader: #read the second line only
            rowno += 1
            if row_sample and rowno == 2:
                break
    csv_file.close()
    if row:
        colno = 0
        for riter in row:
            myhash = {}
            myhash['name'] = riter
            myhash['descr'] = riter
            myhash['unit'] = ''
            myhash['scale'] = ''
            myhash['eventness'] = ''
            myhash['sample'] = ''
            myhash['datatype'] = ''
            if len(row_sample) > colno:
                myhash['sample'] = row_sample[colno]
                sample = row_sample[colno]
                #let's try to figure the datatype based on the sample
                conv_ok = False
                try:
                    dummy = int(sample)
                    myhash['datatype'] = 'integer'
                    #print("intconv")
                    conv_ok = True
                except:
                    pass
                #otherwise if can be a decimal or a string
                if not conv_ok:
                    try:
                        dummy = float(sample)
                        myhash['datatype'] = 'decimal'
                        #print("floatconv")
                        conv_ok = True
                    except:
                        pass
                if not conv_ok:
                    try:
                        dummy = parse(sample)
                        myhash['datatype'] = 'datetime'
                        #print("datetimeconv")
                        conv_ok = True
                    except:
                        pass
                if not conv_ok:
                    myhash['datatype'] = 'string'
                #fix "stupid decisions" like TH77 or 3,161 as datetime
                if myhash['datatype'] == 'datetime' or myhash['datatype'] == 'string':
                    if re.search("^[0-9]+,[0-9]+", sample) or \
                        re.search("^[0-9]+,[0-9]+,[0-9]+", sample):
                        myhash['datatype'] = 'integer'
                    if re.search("^\D", sample) and len(sample) < 6:
                        myhash['datatype'] = 'string'
                #fix odd cases
                if not sample:
                    myhash['datatype'] = 'string'
                else:
                    if re.search("^[A-Z]", sample.strip()) or re.search("^[a-z]", sample.strip()):
                        myhash['datatype'] = 'string'

            colno += 1
            fieldlist.append(myhash)
    return fieldlist


@app.route("/new", methods=['GET', 'POST'])
@app.route("/home/new", methods=['GET', 'POST'])
def new():
    """
    Create a new CSV by writing or pasting it in a text field.
    The functionality is explained in:
    https://github.com/manzikki/dataspace/wiki/Dataspace-application-technical-documentation#new_csv_file
    """
    if 'username' not in session:
        return redirect(url_for('appmain'))
    form = PastedTextForm()
    if form.validate_on_submit():
        #write the contents into a file and call meta edit
        #mydict = request.form
        csvtext = request.form.get('csvtext').replace("\r\n", "\n")
        #count number of lines
        numlines = csvtext.count("\n")
        #check next available filename
        countn = 0
        checkfilename = "data"+str(countn)+".csv"
        while os.path.isfile(app.config['SL']+checkfilename):
            countn += 1
            checkfilename = "data"+str(countn)+".csv"
        myfile = io.open(app.config['SL']+checkfilename, 'w', encoding='utf-8')

        myfile.write(csvtext)
        myfile.close()
        fieldlist = build_fieldlist(app.config['SL']+checkfilename)
        return render_template('editmeta.html', file=checkfilename, descr="",\
                                fieldlist=fieldlist, numlines=numlines)
                                #editmeta will call editmetasubmit
    return render_template('new.html', form=form)

@app.route('/fromwiki', methods=['GET', 'POST'])
@app.route('/home/fromwiki', methods=['GET', 'POST'])
#get a table from wikipedia. Available to admin only.
def fromwiki():
    """
    Show a dialog that lets the user copy-paste a link to a wikipedia article. For admin only.
    If the URL is correct and contains one table write the table into a file and go to metaedit.
    If it contains many tables, go to select_which_table that sends the data to /fromwikimany
    """
    if 'username' not in session:
        return redirect(url_for('appmain'))

    #check the URL from the form here
    form = WikiForm()
    error = ""
    if form.validate_on_submit():
        wikiurl = form.wikiurl.data #article URL from the form
        #read the article
        tables = []
        table_class = "wikitable sortable jquery-tablesorter"
        response = requests.get(wikiurl)
        if (response.status_code != 200):
            error = "Could not read the article."
        else:
            soup = BeautifulSoup(response.text, 'html.parser')
            tables = soup.find_all('table',{'class':"wikitable"})
            if len(tables) == 0:
                error = "The article does not contain tables."
        if (error == ""):
            #we have an article and it contains tables
            if len(tables) == 1:
                #just read it
                table = tables[0]
                dataf = pd.read_html(str(table))
                dataf = pd.DataFrame(dataf[0])
                #now we have the contents in a dataframe. Let's write it to a file
                #find next available file
                countn = 0
                checkfilename = "data"+str(countn)+".csv"
                while os.path.isfile(app.config['SL']+checkfilename):
                    countn += 1
                    checkfilename = "data"+str(countn)+".csv"
                dataf.to_csv(app.config['SL']+checkfilename, index=None)
                numlines = dataf.shape[0]
                fieldlist = build_fieldlist(app.config['SL']+checkfilename)
                return render_template('editmeta.html', file=checkfilename, descr="",\
                                fieldlist=fieldlist, numlines=numlines)
            else:
                rettables = []
                for table in tables:
                    dataf = pd.read_html(str(table))
                    dataf = pd.DataFrame(dataf[0])
                    snippet = str(dataf.head())
                    rettables.append(snippet)
                return render_template('select_which_table.html', rettables = rettables, wikiurl = wikiurl)
    return render_template('fromwiki.html', form = form, error = error)

@app.route('/fromwikimany', methods=['GET', 'POST'])
@app.route('/home/fromwikimany', methods=['GET', 'POST'])
#get table #n from a wikipedia article. Available to admin only.
def fromwikimany():
    if 'username' not in session:
        return redirect(url_for('appmain'))
    mydict = request.form
    wikiurl = mydict['url']
    num = int(mydict['num'])
    #now we know which table to get from the page
    tables = []
    table_class = "wikitable sortable jquery-tablesorter"
    response = requests.get(wikiurl)
    if (response.status_code != 200):
        return("Could not read the article.")
    soup = BeautifulSoup(response.text, 'html.parser')
    tables = soup.find_all('table',{'class':"wikitable"})
    #oddly, the index numbers in template start from 1 not 0
    table = tables[num - 1]
    dataf = pd.read_html(str(table))
    dataf = pd.DataFrame(dataf[0])
    #now we have the contents in a dataframe. Let's write it to a file
    #find next available file
    countn = 0
    checkfilename = "data"+str(countn)+".csv"
    while os.path.isfile(app.config['SL']+checkfilename):
        countn += 1
        checkfilename = "data"+str(countn)+".csv"
    dataf.to_csv(app.config['SL']+checkfilename, index=None)
    numlines = dataf.shape[0]
    fieldlist = build_fieldlist(app.config['SL']+checkfilename)
    return render_template('editmeta.html', file=checkfilename, descr="",\
                                fieldlist=fieldlist, numlines=numlines)


@app.route('/upload', methods=['GET', 'POST'])
@app.route('/home/upload', methods=['GET', 'POST'])
#file upload. Available to admin only.
def upload():
    """
    Upload function, shows the file upload dialog, receives the file.
    """
    if 'username' not in session:
        return redirect(url_for('appmain'))
    form = UploadForm()
    uploaded = []
    if form.validate_on_submit():
        for fil in form.CSVfiles.data:
            if fil.filename == "":
                #empty form submit
                return render_template('upload.html', form=form)
            if '.CSV' in fil.filename.upper() or '.TSV' in fil.filename.upper() or \
                '.TAR.GZ' in fil.filename.upper():
                pass
            else:
                return "Sorry, only csv and tar.gz archives of csv files supported."
            filename = secure_filename(fil.filename)
            uploaded.append(filename)
            #upload to app.config['UP'], check if ok to overwrite
            fil.save(os.path.join(
                app.config['UP'], filename
            ))

        if len(uploaded) == 1:
            if os.path.exists(app.config['SL']+filename):
                return render_template('confirm_overwrite.html', file=filename)
            #it did not exist, so move it
            move(app.config['UP']+filename, app.config['SL']+filename)
            #just one file: go to meta edit
            #if the file is ok, prepare the fields for the dialog
            if file_not_ok(filename):
                flash(file_not_ok(filename))
                return redirect(url_for('appmain'))

            if ".TAR.GZ" in filename.upper() or ".BZ2" in filename.upper():
                filename = process_compressed_file(filename)

            #simple one file upload is here
            numlines = count_lines(app.config['SL']+filename)
            fieldlist = build_fieldlist(app.config['SL']+filename)
            return render_template('editmeta.html', file=filename, descr="",\
                                       fieldlist=fieldlist, numlines=numlines)

        #TBD: Check here if files with same names exist here too. Show a template with yes/no.
        if len(uploaded) > 1:
            #move the files to static
            for upl in uploaded:
                move(app.config['UP']+upl, app.config['SL']+upl)
            #combine multiple files
            fileno = 0
            #process tar.gz's
            uncompressed = []
            numlines = 0
            for fname in uploaded:
                if ".TAR.GZ" in fname.upper() or ".BZ2" in fname.upper():
                    bfname = os.path.basename(fname)
                    process_compressed_file(bfname)
                    uncompressed.append(bfname+".csv")
            if uncompressed:
                uploaded = uncompressed
            numlines = count_lines(app.config['SL']+uploaded[0])
            appendto = open(app.config['SL']+uploaded[0], 'a')
            for fname in uploaded:
                if ".CSV" not in fname.upper():
                    return "Sorry, combining other than CSV files not yet implemented."
                else:
                    fileno += 1
                    if fileno == 1:
                        pass
                    else:
                        appendfrom = open(app.config['SL']+fname)
                        #remove the first line of appendfrom
                        line = appendfrom.readline() #skip headers
                        while line:
                            line = appendfrom.readline()
                            numlines += 1
                            appendto.write(line)
                        appendfrom.close()
                        #delete appendfrom
                        os.remove(app.config['SL']+fname)
            appendto.close()
            filename = uploaded[0]
            fieldlist = build_fieldlist(app.config['SL']+filename)
            return render_template('editmeta.html', file=filename, descr="",\
                                       fieldlist=fieldlist, numlines=numlines)
    return render_template('upload.html', form=form)

@app.route('/confirm_overwrite', methods=['GET', 'POST'])
@app.route('/home/confirm_overwrite', methods=['GET', 'POST'])
#file upload with a file whose name is the same as an existing file
def confirm_overwrite():
    """
    Processes the response from "ok to overwrite?" If yes, do things, otherwise delete uploaded.
    """
    mydict = request.form
    #print(str(mydict))
    filename = mydict['file']
    if "yes" in mydict:
        #move the file:
        move(app.config['UP']+filename, app.config['SL']+filename)
        #do the rest
        if file_not_ok(filename):
            flash(file_not_ok(filename))
            return redirect(url_for('appmain'))

        if ".TAR.GZ" in filename.upper() or ".BZ2" in filename.upper():
            filename = process_compressed_file(filename)

        #simple one file upload is here
        numlines = count_lines(app.config['SL']+filename)
        fieldlist = build_fieldlist(app.config['SL']+filename)
        return render_template('editmeta.html', file=filename, descr="",\
                                fieldlist=fieldlist, numlines=numlines)
    #else: remove the uploaded
    os.remove(app.config['UP']+filename)
    return redirect(url_for('appmain'))

@app.route("/view", methods=['GET', 'POST'])
@app.route("/home/view", methods=['GET', 'POST'])
#view the file
def view(pfile=""):
    """
    View N lines of the file using template view.html or edit.html
    Param pfile is the name of the file.
    """
    mydict = request.form
    if pfile:
        myfile = pfile
    else:
        myfile = mydict['file']
    noedit = 0
    if 'noedit' in mydict:
        noedit = 1
    rows = []
    headers = []
    #Get the metadata so that we know the min/max values
    mymeta = MetaInfo(myfile)
    fieldlist = []
    if mymeta.read_from_file(app.config['SL'], myfile):
        fieldlist = mymeta.get_fieldlist()

    with open(app.config['SL']+myfile, 'rb') as fil:
        result = chardet.detect(fil.readline())
        encoding = result['encoding']

    if encoding == "ascii":
        encoding = "utf-8"

    with io.open(app.config['SL']+myfile, 'r', encoding=encoding) as csv_file: #,'rU'
        #csv_reader = csv.reader(csv_file, delimiter=',', quotechar='"')
        delim = ','
        if myfile.upper().endswith("TSV"):
            delim = '\t'
        csv_reader = UnicodeReader(csv_file, delimiter=delim, quotechar='"')
        line_no = 0
        for row in csv_reader:
            if line_no == 0:
                headers = row
            else:
                if line_no <= MAX_SHOWN_LINES:
                    rows.append(row)
                if line_no > MAX_COUNTED_LINES:
                    break
            line_no = line_no + 1
    shownum = str(line_no) + " lines."
    if line_no > MAX_COUNTED_LINES:
        shownum = "More than " + str(MAX_COUNTED_LINES) + " lines (too large to edit)."
    if 'username' not in session or line_no > MAX_SHOWN_LINES or noedit:
        return render_template('view.html', file=myfile, num=shownum, headers=headers, rows=rows,
                               fields=fieldlist)
    return render_template('edit.html', file=myfile, num=shownum, headers=headers, rows=rows,
                           numcols=len(headers), fields=fieldlist)


@app.route('/editsave', methods=['GET', 'POST'])
@app.route('/home/editsave', methods=['GET', 'POST'])
#save the file including the line the user edited. The edited line's columns are decoded
#from [row]-[column] labels
def editsave():
    """
    Save the file including the line the user edited. Admin only.
    """
    if 'username' not in session:
        return redirect(url_for('appmain'))
    mydict = request.form.to_dict()
    fname = request.form.get('fname', '')
    if not fname:
        return "Required parameter fname missing."
    #if the user wanted a new line at the end, just append a new file with commas
    if 'addrow' in mydict:
        numcommas = int(mydict['numcols'])-1
        fil = io.open(app.config['SL']+fname, 'a+')
        for _ in range(numcommas):
            fil.write(",")
        fil.write("\n")
        fil.close()
        return view(pfile=fname)
    row = 0
    for key in mydict:
        if key == 'fname':
            next
        #print(key+" "+mydict[key])
        #get the key value that looks like [row]-[col]
        rowcol = re.findall(r'\d+', key)
        if len(rowcol) == 2:
            row = int(rowcol[0])
    #copy the file to a temporary file up to row-1
    #print(str(row))
    #print(str(col))
    fil = io.open(app.config['SL']+fname, 'r')
    filw = io.open(app.config['SL']+fname+"tmp", 'w')
    if not os.access(app.config['SL']+fname+"tmp", os.W_OK):
        return "Could not open a temporary file for writing!"
    rowr = 0
    while rowr < row:
        rowr += 1
        line = fil.readline()
        #print(line, end='')
        filw.write(line)
    #print the changed line
    changed = ""
    for key in mydict:
        if key != 'fname' and key != 'addrow':
            if "," in mydict[key]:
                changed += '"'+mydict[key]+'",'
            else:
                changed += mydict[key]+","
        #print(key+" "+mydict[key])
    changed = changed[:-1] #remove the last comma
    filw.write(changed+"\n")
    #copy the rest
    fil.readline()
    while True:
        line = fil.readline()
        if not line:
            break
        #print(line, end='')
        filw.write(line)
    fil.close()
    #move the temp file to orig file
    filw.close()
    move(app.config['SL']+fname+"tmp", app.config['SL']+fname)
    return view(pfile=fname)

@app.route('/saveasfile', methods=['GET', 'POST'])
@app.route('/home/saveasfile', methods=['GET', 'POST'])
#save the generated cube as a CSV file. Admin only.
def saveasfile():
    """
    Saves the tmpcube as file.
    """
    if 'username' not in session:
        return redirect(url_for('appmain'))
    mydict = request.form
    if 'savefilename' not in mydict:
        return "Required parameter (savefilename) missing."
    myfile = mydict['savefilename']
    move(app.config['SL']+TMPCUBENAME, app.config['SL']+myfile)
    #Reconstruct field names from the cubefile- request params and build the jmeta.
    metafieldhashes = []
    for key in mydict:
        if key.startswith("cubefile-"):
            fname = key.replace("cubefile-", "")
            #open the corresponding file
            mymeta = MetaInfo(fname)
            mymeta.read_from_file(app.config['SL'], fname)
            fieldh = mymeta.get_fieldlist()
            metafieldhashes.append(fieldh)
    savemeta = MetaInfo(myfile) #build the meta for the saved file
    savemeta.setdescr("Cube generated")
    #read the file "samples" to get fieldnames
    samples = getfieldsamples(app.config['SL']+myfile)
    #add the metadata to fields
    for field in samples:
        fdesc = ""
        #scan the meta hashes for this field
        for mhashes in metafieldhashes:
            #print(str(mhash))
            for mhash in mhashes:
                name = mhash['name']
                descr = mhash['descr']
                if field == name:
                    fdesc = descr
        savemeta.addfield(field, fdesc)
    savemeta.set_formatted_fields()
    savemeta.write_to_file(app.config['S'], myfile)
    return redirect(url_for('appmain'))

@app.route('/visualize', methods=['GET', 'POST'])
@app.route('/home/visualize', methods=['GET', 'POST'])
#create maps by going to the selection of area (country ISO code) to visualize -> areaselect
#which file to visualize: get the file parameter
def visualize():
    file = ""
    mydict = request.form
    if 'file' in mydict:
        file = mydict['file']
    else:
        file = request.args.get('file')
    return render_template('select_area.html', file=file)

@app.route('/areaselect', methods=['GET', 'POST'])
@app.route('/home/areaselect', methods=['GET', 'POST'])
#get the area (area like THA, file like data0.csv) and generate the map
#OR: get the parameters (visualize-param, iso-param) and generate the map
def areaselect():
    matplotlib.use('Agg') #prevent crash
    area = "" #like THA
    file = "" #the CSV file
    vparam = "" #parameter to visualize.
    isoparam = "" #province code. If not submitted, give a hint.
    mydict = request.form
    if 'visualize-param' in mydict:
        vparam = mydict['visualize-param']
    if 'iso-param' in mydict:
        isoparam = mydict['iso-param']    
    if 'area' in mydict:
        area = mydict['area']
    else:
        area = request.args.get('area')
    mydict = request.form
    if 'file' in mydict:
        file = mydict['file']
    else:
        file = request.args.get('file')
    mapdata = gpd.read_file("static/"+area+".geojson")
    #merge with the data if we have the parameters
    if isoparam and vparam:
        df = pd.read_csv(app.config['SL']+file)
        mapdata = mapdata.merge(df,left_on="ISO", right_on=isoparam) #We know it's ISO in our map data
    # Save plot with matplotlib in a random file
    myrand = str(random.randint(0, 5000))
    mypic = "static/tmp"+myrand+".jpg"
    plt.ioff()
    minmaxstr = "" #info string about min and max values to be shown in the form
    mymaph = "" #link to interactive map
    if isoparam and vparam:
        mymaph = "static/map"+myrand+".html"
        maxval = mapdata[vparam].max()
        minval = mapdata[vparam].min()
        maxValueIndex = mapdata[vparam].idxmax()
        minValueIndex = mapdata[vparam].idxmin()
        isomax = mapdata['ISO'][maxValueIndex]
        isomin = mapdata['ISO'][minValueIndex]
        minmaxstr = "max "+str(maxval)+" "+isomax + " min "+str(minval)+" "+isomin
        mymap=mapdata.explore(column=vparam, cmap='OrRd', legend=True)
        mymap.save(mymaph)
        mapdata.plot(column=vparam, cmap='OrRd', legend=True)
        #return redirect("/"+mymaph)
    else:
        mapdata.plot()
    plt.savefig(mypic)
    plt.close()
    mymeta = MetaInfo(file)
    mymeta.read_from_file(app.config['S'], file)
    fields = mymeta.get_fieldlist()
    #try to find something like ISO in the fields
    #get the first numeric field, maybe the user wants to visualize it
    #NB: We should limit the fields to numeric only!
    isohint = ""
    vhint = ""
    for field in fields:
        if "ISO" in field['name'] or "iso" in field['name']:
            isohint = field['name']
        if field['datatype'] == "integer":
            vhint = field['name']

    #if we have the isoparam and vparam, use them
    if isoparam:
        isohint=isoparam
    if vparam:
        vhint=vparam
    return render_template('select_area_params.html', file=file, 
                           area=area, mypic=mypic, fieldlist=fields, isoparam=isoparam, vparam=vparam,
                           isohint = isohint, vhint=vhint, mymaph = mymaph, minmaxstr = minmaxstr)

@app.route('/compatible', methods=['GET', 'POST'])
@app.route('/home/compatible', methods=['GET', 'POST'])
#show/let user declare compatible fields. Should be available to admin only
def compatible():
    """
    Show/let user declare compatible fields that are compatible with some field in this file.
    """
    mydict = request.form
    if 'file' in mydict:
        myfile = mydict['file']
    else:
        myfile = request.args.get('file')
    if session['username'] != ADMIN_USERNAME:
        flash('Admin privileges required. Please log in.')
        return redirect(url_for('appmain'))
    #get field information
    dimmetas = []    #metas concerning dimensions, not measures
    filemetas = []   #metas in the file given in the request
    filenames = []   #names of files, but not myfile
    allmetalist = MetaList(app.config['S'])
    allmetas = allmetalist.get()

    compat_list = []
    #does the file exist?
    if os.path.isfile(app.config['COMPAT']):
        with io.open(app.config['COMPAT'], 'rU') as csv_file:
            csv_reader = UnicodeReader(csv_file, delimiter=',', quotechar='"')
            for row in csv_reader:
                compat_list.append(row)
                #print(str(row))
        csv_file.close()

    #print(str(mymetas))
    for meta in allmetas:
        metafields = meta.get_fieldlist()
        for fieldh in metafields:
            #is this a measure or dimension?
            if fieldh['unit']:
                #cannot use this
                pass
            else:
                #print(fieldh['filename']+":"+fieldh['name'])
                if fieldh['filename'] == myfile:
                    filemetas.append(fieldh)
                else:
                    dimmetas.append(fieldh)
                    if fieldh['filename'] not in filenames:
                        filenames.append(fieldh['filename'])

    compat_list = []
    #does the file exist?
    if os.path.isfile(app.config['COMPAT']):
        with io.open(app.config['COMPAT'], 'rU') as csv_file:
            csv_reader = UnicodeReader(csv_file, delimiter=',', quotechar='"')
            for row in csv_reader:
                compat_list.append(row)
                #print(str(row))
        csv_file.close()

    return render_template('compat.html', compat=compat_list, fname=myfile, filemetas=filemetas,\
                            filenames=filenames, othermetas=dimmetas)


@app.route('/compatible-d', methods=['GET', 'POST'])
@app.route('/home/compatible-d', methods=['GET', 'POST'])
#store the information that the user just declared compatible. Should be available to admin only.
def compatible_d():
    """
    Store the information that the user just declared compatible. Should be available to admin only.
    """
    file1 = request.args.get('f1')
    field1 = request.args.get('fd1')
    file2 = request.args.get('f2')
    field2 = request.args.get('fd2')
    #print(file1+" "+field1+" "+file2+" "+field2)
    #write the info into the compat file
    cfile = io.open(app.config['COMPAT'], "a+")
    cfile.write(file1+","+field1+","+file2+","+field2+"\n")
    cfile.close()
    return redirect(url_for('compatible', file=file1, **request.args))


def getfieldsamples(filename):
    """
    Get a samples of fields in file by reading the header line and the line after that.
    Return a hash: fieldname -> sample.
    """
    headers = []
    samples = []
    hsample = {}
    with io.open(filename, 'r', encoding='utf-8') as csvfile:
        csvreader = csv.reader(csvfile)
        lineno = 0
        for row in csvreader:
            lineno += 1
            if lineno == 1:
                headers = row
            if lineno == 2:
                samples = row
                break
    if headers and samples:
        for i in range(0, len(headers)):
            header = headers[i]
            sample = ""
            if i < len(samples):
                sample = samples[i]
            hsample[header] = sample
    return hsample

#route for printing all filenames
@app.route('/printurls', methods=['GET', 'POST'])
@app.route('/home/printurls', methods=['GET', 'POST'])
def printurls():
    """
    Route for printing the names of all the files.
    """
    mymetas = MetaList(app.config['S'])
    currentcoldir = "static"
    if app.config['COLLIST'].getcurrent():
        currentcoldir = "static/"+app.config['COLLIST'].getcurrent()
    return render_template('urls.html', req=request.url_root,
                           cdir=currentcoldir, metas=mymetas.get())

# route for handling exportrdf (export the CSV values file as RDF)
@app.route('/exportrdf', methods=['GET', 'POST'])
@app.route('/home/exportrdf', methods=['GET', 'POST'])
def exportrdf():
    """
    Route for handling exportrdf (export the CSV values file as RDF)
    """
    mydict = request.form
    myfile = mydict['file']

    def generate(myfile):
        #rdf headers to be written
        yield("""<?xml version='1.0'?>
<rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#' xmlns:a='http://www.olaprdf.org/'>
""")
        myid = myfile.encode('utf-8')
        myid = hashlib.md5(myid).digest()
        myid = str(base64.b64encode(myid))[1:]
        myid = myid.replace('=', '')
        myid = myid.replace('\'', '')
        cvsdf = pd.read_csv(app.config['SL']+myfile)
        for index, row in cvsdf.iterrows():
            mystr = "<rdf:Description rdf:about=\""+myid+str(index)+"\" "
            for dfh in cvsdf:
                mystr += "a:"+dfh+"=\""+str(row[dfh]).replace("\"", "")+"\" "
            mystr += "/>\n"
            yield(mystr)
        yield("</rdf:RDF>\n")
    if myfile:
        return Response(generate(myfile), mimetype='text/plain',
                        headers={"Content-Disposition": "attachment;filename=export.rdf"})
    return ""

@app.route('/changecollection', methods=['GET', 'POST'])
@app.route('/home/changecollection', methods=['GET', 'POST'])
def changecollection():
    """
    Change the collection.
    """
    mycoll = ""
    if "coll" in request.args:
        mycoll = request.args["coll"]
    app.config['COLLIST'].setcurrent(mycoll)
    return redirect(url_for('appmain'))

@app.route('/renamecollection', methods=['GET', 'POST'])
@app.route('/home/renamecollection', methods=['GET', 'POST'])
def renamecollection():
    """
    Show form to rename the main collection.
    """
    #check that there are some files here
    if app.config['COLLIST'].getcurrent():
        flash("You can only rename the main collection.")
        return redirect(url_for('appmain'))
    if not app.config['COLLIST'].getfiles():
        flash("Cannot rename an empty collection.")
        return redirect(url_for('appmain'))
    return render_template('rename.html')

@app.route('/renamesubmit', methods=['GET', 'POST'])
@app.route('/home/renamesubmit', methods=['GET', 'POST'])
def renamesubmit():
    """
    Rename the main collection.
    """
    if 'username' not in session:
        flash("Not authenticated.")
        return redirect(url_for('appmain'))
    #get the name parameter
    mydict = request.form
    if "name" not in mydict:
        flash("Invalid input.")
        return redirect(url_for('appmain'))
    myname = mydict['name']
    myname = myname[0:MAX_COLNAME]
    #is this a valid name?
    if not myname.isalnum():
        flash("Only alphanumeric characters allowed.")
        return redirect(url_for('appmain'))
    #if we are here it's ok to make the directory
    dir_path = os.path.dirname(os.path.realpath(__file__))
    newdir = dir_path+"/static/"+myname
    try:
        os.mkdir(newdir)
    except:
        flash("Cannot create collection.")
        return redirect(url_for('appmain'))
    #move all the files to the new directory
    for _, _, files in os.walk(dir_path+"/static"):
        for filen in files:
            if filen.endswith(".jmeta") or filen.endswith(".csv") or filen.endswith(".file"):
                src = os.path.join(dir_path, "static", filen)
                dst = os.path.join(dir_path, "static", myname, filen)
                if os.path.isfile(src):
                    copyfile(src, dst)
                    os.remove(src)
        break #no recurse to subdirs
    #re-init the collection list to get the new collection in it
    app.config['COLLIST'].reinit()
    return redirect(url_for('appmain'))

def handle_fieldsubmit(req):
    """
    Handles cube building when the user has submitted information about files and fields
    to be integrated.
    Returns a message about field values.
    """
    global MYCUBE
    file1 = ""
    file2 = ""
    field1 = ""
    field2 = ""
    mround = 1
    add_to_cube_file = ""
    add_to_cube_field = ""

    mymetalist = MetaList(app.config['S'])

    #check here if the fields are compatible: use file1, file1, field1, field2
    for arg in req.args:
        if arg != "fieldsubmit":
            if arg != "cube":
                add_to_cube_file = arg
                add_to_cube_field = request.args.get(arg).split(":")[0]
            if mround == 1:
                file1 = arg
                field1 = request.args[arg].split(":")[0]
                mround = 2
            else:
                file2 = arg
                field2 = request.args[arg].split(":")[0]
    if MYCUBE.get_cube_round() > 0:
        #we are adding stuff to existing cube
        in_cube_field = request.args.get('cube')
        #print("in cube: "+in_cube_field)
        #print("to add file "+add_to_cube_file+" field "+add_to_cube_field)

        #open the files and analyze the fields
        #print "Looking for field "+field1+" or "+field2
        #print "from "+file1+" "+file2
        #print "cube has "+str(cubefiles)

    if file1 == "cube" or file2 == "cube":
        #print(str(ok_files))
        #find out which file in cube has this field
        if file1 == "cube":
            #we need to get field1's real file to file1
            for fname in MYCUBE.get_cube_files():
                meta = mymetalist.get_meta_by_name(fname)
                for fie in meta.getfieldnames():
                    #print fname+" "+fie
                    if fie == field1:
                        #print "Found field "+field1+" in "+fname
                        file1 = fname
        else:
            #we need to get field2's real file to file2
            for fname in MYCUBE.get_cube_files():
                meta = mymetalist.get_meta_by_name(fname)
                for fie in meta.getfieldnames():
                    #print fname+" "+fie
                    if fie == field2:
                        #print "Found field "+field2+" in "+fname
                        file2 = fname
    fxpd = pd.read_csv(app.config['SL']+file1)
    f1uniques = fxpd[field1].unique()
    fxpd = pd.read_csv(app.config['SL']+file2)
    f2uniques = fxpd[field2].unique()

    notexample = ""
    msg = " Field "+field1+" in "+file1+" has "+str(len(f1uniques))+" unique values."
    notinuf2 = 0
    for f1u in f1uniques:
        if f1u not in f2uniques:
            notinuf2 += 1
            notexample = str(f1u)

    if notinuf2:
        msg += " "+str(notinuf2)+" of them are not in "+field2+". "
    else:
        msg += " All of them are in "+field2+". "
        notexample = ""

    if notexample:
        msg += "Example: "+notexample+". "
    msg += "<br/>"
    msg += "Field "+field2+" in "+file2+" has "+str(len(f2uniques))+" unique values. "

    notexample = ""
    notinuf1 = 0
    for f2u in f2uniques:
        if f2u not in f1uniques:
            notinuf1 += 1
            notexample = str(f2u)

    if notinuf1:
        msg += " "+str(notinuf1)+" of them are not in "+field1+". "
    else:
        msg += " All of them are in "+field1+". "
        notexample = ""

    if notexample:
        msg += "Example: "+notexample+". "
        #put the selected files and fields in the session
        #print("adding "+file1+" etc in cube")
        #print(str(cubefiles))

    MYCUBE.add_cube_file(file1)
    MYCUBE.add_cube_file(file2)

    MYCUBE.add_cube_field(field1)
    MYCUBE.add_cube_field(field2)

    #make numpy/pandas cube
    if MYCUBE.get_cube_round() == 0:
        f1pd = pd.read_csv(app.config['SL']+file1)
        f2pd = pd.read_csv(app.config['SL']+file2)
        try:
            pdcube = pd.merge(f1pd, f2pd, left_on=field1, right_on=field2)
            MYCUBE.set_pdcube(pdcube)
        except:
            flash("These types cannot be joined")
            return redirect(url_for('appmain'))
        MYCUBE.set_cube_round(1)

    else:
        fpd = pd.read_csv(app.config['SL']+add_to_cube_file)
        pdcube = pd.merge(MYCUBE.get_pdcube(), fpd, left_on=in_cube_field, \
                          right_on=add_to_cube_field)
        MYCUBE.set_pdcube(pdcube)
    return msg

# route for handling "cube". Renders the cube construction pages.
# This horrible function should be re-written.
@app.route('/cube', methods=['GET', 'POST'])
@app.route('/home/cube', methods=['GET', 'POST'])
def cube():
    """
    Handle the cube construction.
    """
    global MYCUBE
    if 'username' not in session:
        flash("Not authenticated.")
        return redirect(url_for('appmain'))
    # 0 cancel
    if 'cancel' in request.args:
        #print("Cancel")
        return redirect(url_for('appmain'))
    # 1 Starting point: The user will first select 2 files.
    mymetalist = MetaList(app.config['S'])
    #print(mymetalist.get_as_string())
    if 'start' in request.args:
        return render_template('rcube.html', entries=mymetalist.get())

    selfiles = request.args.getlist('fileselect')

    # 2: User has selected files, show their fields
    if 'twoselect' in request.args:
        if len(selfiles) == 2:
            #generate select boxes for joining files by fields
            shown_files = []
            for sel in selfiles:
                meta = mymetalist.get_meta_by_name(sel)
                shown_files.append(meta)
            return render_template('rcubefields.html', entries=shown_files) #note: the action is
                                                                            #"fieldsubmit", see 4

        return render_template('rcube.html', error="Please select 2 files",\
                                                    entries=mymetalist.get())

    # 3: the user has built the initial cube, now add stuff from one more
    if 'oneselect' in request.args:
        if len(selfiles) == 1:
            #generate select boxes for joining files by fields.
            shown_files = []
            #get the files that are used in the cube and all the fields in those files
            cubemeta = MetaInfo("cube")
            for cubef in MYCUBE.get_cube_files():
                meta = mymetalist.get_meta_by_name(cubef)
                for fie in meta.getfieldnames():
                    cubemeta.addfield(fie, "")

            shown_files.append(cubemeta)

            for sel in selfiles:
                meta = mymetalist.get_meta_by_name(sel)
                shown_files.append(meta)
            return render_template('rcubefields.html', entries=shown_files)
        return render_template('rcube.html', error="Please select 1 file")

    # 4 User has selected fields from one more
    if 'fieldsubmit' in request.args:
        msg = handle_fieldsubmit(request)

        return render_template('rcubecontinue.html', msg=msg, csize=MYCUBE.get_pdcube().shape[0],
                               cubefiles=MYCUBE.get_cube_files())

    # 4 there is some integration stuff already and we continue
    if 'more' in request.args:
        #put information about what's already there in msg
        msg = ""
        cubefiles = MYCUBE.get_cube_files()
        cubefields = MYCUBE.get_cube_fields()
        for i in range(0, len(cubefiles)-1):
            if i % 2 == 0:
                msg += cubefiles[i] + ":" + cubefields[i] + " &rarr; " + \
                cubefiles[i+1] + ":" + cubefields[i+1]+"<br/>"

        ok_files = mymetalist.get()
        return render_template('rcubemore.html', msg=msg, entries=ok_files)

    # 5 The user wants the cube
    if 'generatecube' in request.args:
        #write it into a file
        pdcube = MYCUBE.get_pdcube()
        cubefiles = MYCUBE.get_cube_files()
        pdcube.to_csv(app.config['SL']+TMPCUBENAME, encoding='utf-8', index=False)
        return render_template('rcubegen.html', cubefiles=cubefiles, baseurl=request.base_url)

    #default if nothing matched
    return redirect(url_for('appmain'))


@app.route('/delfile', methods=['GET'])
@app.route('/home/delfile', methods=['GET'])
def delfile():
    """
    Deletes the file given as a parameter. For admin.
    """
    if 'username' not in session:
        flash("Not authenticated.")
        return redirect(url_for('appmain'))
    if 'f' not in request.args:
        return "Required parameter missing."
    myfile = request.args.get('f')
    #delete the file and its jmeta
    os.remove(app.config['SL']+myfile)
    os.remove(app.config['SL']+myfile+".jmeta")
    return redirect(url_for('appmain'))

@app.route('/graphrow', methods=['GET','POST'])
@app.route('/home/graphrow', methods=['GET','POST'])
def graphrow():
    """
    Simple graph of just 1 row of numbers.
    """
    #debug: print everything
    mydict = request.form
    #print(mydict)
    mytitle = ""
    fname = mydict['00fname']
    itemno = 0
    countnumitems = 0
    xitems = []
    yitems = []
    for key, val in request.form.items():
        itemno = itemno + 1
        if itemno == 2: # 1 is 00fname
             mytitle = fname + " " + val
        else:
             try:
                float(val)
                countnumitems = countnumitems + 1
                yitems.append(float(val))
                xitems.append(key)
             except:
                 pass
        print(key + " " + val)
    if countnumitems < 2:
        return "Less than 2 numeric items."
    #build the graph
    rastr = str(random.randint(0, 99999999))
    matplotlib.use('Agg')
    plt.plot(xitems, yitems, 'o')
    plt.title(mytitle)
    plt.xticks(rotation=45, fontsize=12)
    plt.savefig("static/"+rastr+"tmp.svg")
    return "<a href=../static/"+rastr+"tmp.svg>Your graph</a>."

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)

