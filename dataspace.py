"""
Simple dataspace management for CVS files. Marko Niinimaki niinimakim@webster.ac.th 2019
"""
import os
import codecs
import hashlib
import base64
from shutil import copyfile
from flask import Flask, session, render_template, redirect, \
                  url_for, request, flash
from werkzeug.utils import secure_filename
import numpy
import pandas as pd
from forms import LoginForm, UploadForm
from classes import MetaInfo, MetaList, UTF8Recoder, UnicodeReader, CollectionList

app = Flask(__name__)
app.config['SECRET_KEY'] = '5791628bb0b13'
app.config['S'] = ''  #put the path to 'static' in it in appmain
app.config['SL'] = '' #same but with "/" at the end
app.config['U'] = ''  #url base like "/" or "/home"
app.config['COLLIST'] = []

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'FpacNida986!'
TMPRDFNAME = "tmp.rdf"
MAX_LINES = 500 #max number of lines in view
MAX_COLNAME = 20 #max chars in collection

@app.route("/")
@app.route("/home")
def appmain():
    """
    Main route, shows the main page.
    """
    dir_path = os.path.dirname(os.path.realpath(__file__))
    app.config['S'] = os.path.join(dir_path,"static")
    app.config['SL'] = dir_path+"/static/"
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
    currentcoldir = "static"
    if app.config['COLLIST'].getcurrent():
        currentcoldir = "static/"+app.config['COLLIST'].getcurrent()
    return render_template('home.html', username=username,
                           currentcoldir=currentcoldir,
                           metas=mymetas.get(),
                           coldirs=app.config['COLLIST'].get(),
                           curdir=app.config['COLLIST'].getcurrent())

@app.context_processor
def utility_processor():
    """
    Define a function that can be used in a template
    """
    def is_in_compat(filea, fielda, fileb, fieldb):
        """
        Check if filea,fielda,fileb,fieldb or fileb,fieldb,filea,fielda is listed
        in the compat file.
        """
        if os.path.isfile(app.config['COMPAT']):
            with open(app.config['COMPAT'], 'rU') as csv_file:
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
    """
    form = LoginForm()
    if form.validate_on_submit():
        if form.username.data == ADMIN_USERNAME and form.password.data == ADMIN_PASSWORD:
            #flash('You have been logged in!', 'success')
            session['username'] = ADMIN_USERNAME
            return redirect(url_for('appmain'))
    flash('Login Unsuccessful. Please check username and password', 'danger')
    return render_template('login.html', title='Login', form=form)

def file_not_ok(filename):
    """
    Check that the file is readable by csv reader.
    """
    if os.stat(app.config['SL']+filename).st_size == 0:
        return "File is empty."
    myf = open(app.config['SL']+filename, "r")
    myline = myf.readline()
    myf.close()
    #check that the line contains commas
    if "," in myline:
        return ""
    return "First line of the file does not contain commas."

@app.route('/upload', methods=['GET', 'POST'])
@app.route('/home/upload', methods=['GET', 'POST'])
#file upload. Should be available to admin only
def upload():
    """
    Upload function, shows the file upload dialog, receives the file.
    """
    if 'username' not in session:
        return redirect(url_for('appmain'))
    form = UploadForm()
    if form.validate_on_submit():
        fil = form.CSV_file.data
        filename = secure_filename(fil.filename)
        #already such file?
        if os.path.isfile(app.config['SL']+filename):
            pass #call another template to ask the user
        fil.save(os.path.join(
            app.config['SL'], filename
        ))
        #if the file is ok, prepare the fields for the dialog
        if file_not_ok(filename):
            flash(file_not_ok(filename))
            return redirect(url_for('appmain'))
        else:
            row1 = []
            #read the first line of file to get field names
            with open(app.config['SL']+filename, 'rU') as csv_file: #,'rU'
                reader = UnicodeReader(csv_file, delimiter=',', quotechar='"')
                for row in reader: #read only 1 line
                    #remove the BOM
                    if row:
                        r1first = row[0]
                        while  ord(r1first[0]) > 123:
                            r1first = r1first[1:]
                        row[0] = r1first
                    break
            csv_file.close()
            if row:
                fieldlist = []
                for riter in row:
                    myhash = {}
                    myhash['name'] = riter
                    myhash['descr'] = ""
                    myhash['unit'] = ''
                    myhash['scale'] = ''
                    myhash['eventness'] = ''
                    fieldlist.append(myhash)
                return render_template('fileedit.html', file=filename, descr="",\
                                       fieldlist=fieldlist)
        return redirect(url_for('appmain'))
    return render_template('upload.html', form=form)

@app.route("/view", methods=['GET', 'POST'])
@app.route("/home/view", methods=['GET', 'POST'])
#view the file
def view():
    """
    View N lines of the file using template view.html
    """
    mydict = request.form
    myfile = mydict['file']
    rows = []
    headers = []
    with open(app.config['SL']+myfile, 'rU') as csv_file: #,'rU'
        #csv_reader = csv.reader(csv_file, delimiter=',', quotechar='"')
        csv_reader = UnicodeReader(csv_file, delimiter=',', quotechar='"')
        line_no = 0
        for row in csv_reader:
            if line_no == 0:
                headers = row
            else:
                if line_no >= 500:
                    break
                rows.append(row)
            line_no = line_no + 1
    return render_template('view.html', file=myfile, headers=headers, rows=rows)

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
        flash('Admin privileges required. Plase log in.')
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
        with open(app.config['COMPAT'], 'rU') as csv_file:
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
        with open(app.config['COMPAT'], 'rU') as csv_file:
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
    cfile = open(app.config['COMPAT'], "a+")
    cfile.write(file1+","+field1+","+file2+","+field2+"\n")
    cfile.close()
    return redirect(url_for('compatible', file=file1, **request.args))

@app.route("/edit", methods=['GET', 'POST'])
@app.route("/home/edit", methods=['GET', 'POST'])
#edit metadata. admin user only
def edit():
    """
    Edit file metadata. Shows the edit form.
    """
    #get the file field
    mydict = request.form
    myfile = mydict['file']
    #build a meta object and read it from file
    mymeta = MetaInfo(myfile)
    mymeta.read_from_file(app.config['S'], myfile)
    fields = mymeta.get_fieldlist()
    #we need to generate the fields dynamically so it's easier to use direct templating, not WTF
    return render_template('fileedit.html', file=myfile, descr=mymeta.descr, fieldlist=fields)

@app.route("/editsubmit", methods=['GET', 'POST'])
@app.route("/home/editsubmit", methods=['GET', 'POST'])
#get the result of metadata editing
def editsubmit():
    """
    Receives metadata values from the edit form.
    """
    #get the file field
    mydict = request.form
    myfile = mydict['file']
    descr = mydict['descr']
    mymeta = MetaInfo(myfile)
    mymeta.setdescr(descr)
    for fiter in mydict:
        #print(k+" "+mydict[k])
        if not (fiter.endswith("=scale") or fiter.endswith("=unit") or \
                                            fiter.endswith("=eventness")):
            if not (fiter == "file" or fiter == "descr"):
                mymeta.addfield(fiter, mydict[fiter])
    for fiter in mymeta.getfieldnames():
        if fiter+"=unit" in mydict and mydict[fiter+"=unit"]:
            unit = mydict[fiter+"=unit"]
            scale = mydict[fiter+"=scale"]
            eventness = mydict[fiter+"=eventness"]
            mymeta.addmeasure(fiter, unit, scale, eventness)
    mymeta.write_to_file(app.config['S'], myfile)
    #call appmain if ok
    return redirect(url_for('appmain'))

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
    return render_template('urls.html', req=request.url_root, cdir=currentcoldir, metas=mymetas.get())


# route for handling exportrdf (export the CSV values file as RDF)
@app.route('/exportrdf', methods=['GET', 'POST'])
@app.route('/home/exportrdf', methods=['GET', 'POST'])
def exportrdf():
    """
    Route for handling exportrdf (export the CSV values file as RDF)
    """
    #rdf headers to be written
    fheaders = """<?xml version='1.0'?>
<rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#' xmlns:a='http://www.olaprdf.org/'>
"""
    mydict = request.form
    myfile = mydict['file']
    #print(file)
    if myfile:
        #get a short hash of the file. we'll use it for ID
        myid = myfile.encode('utf-8')
        myid = hashlib.md5(myid).digest()
        myid = str(base64.b64encode(myid));
        myid = myid.replace('=', '')
        myid = myid.replace('\'', '')
        #open the CVS file that the user wants
        cvsdf = pd.read_csv(app.config['SL']+myfile)
        rdf = open(os.path.join(app.config['S'],TMPRDFNAME), 'w')
        rdf.write(fheaders)
        for index, row in cvsdf.iterrows():
            rdf.write("<Description about=\""+myid+str(index)+"\" ")
            for dfh in cvsdf:
                rdf.write("a:"+dfh+"=\""+str(row[dfh]).replace("\"", "")+"\" ")
            rdf.write("/>\n")
        rdf.write("</rdf:RDF>")
        rdf.close()
        myurl = app.config['U']+'/static/tmp.rdf'
        myurl = myurl.replace("//static", "/static")
        return render_template('rdfexport.html', url=myurl)
    return redirect(url_for('appmain'))

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
            if filen.endswith(".meta") or filen.endswith(".csv") or filen.endswith(".file"):
                src = os.path.join(dir_path, "static", filen)
                dst = os.path.join(dir_path, "static", myname, filen)
                if os.path.isfile(src):
                    copyfile(src, dst)
                    os.remove(src)
        break #no recurse to subdirs
    #re-init the collection list to get the new collection in it
    app.config['COLLIST'].reinit()
    return redirect(url_for('appmain'))

TMPCUBENAME = "tmpcube.csv"
cubefields = []
cubefiles = []
cube_round = 0
pdcube = pd.DataFrame()

# route for handling "cube". Renders the cube construction pages.
# This horrible function should be re-written.
@app.route('/cube', methods=['GET', 'POST'])
@app.route('/home/cube', methods=['GET', 'POST'])
def cube():
    """
    Handle the cube construction.
    """
    global cubefields
    global cubefiles
    global pdcube
    global cube_round
    # 0 cancel
    if 'cancel' in request.args:
        #print("Cancel")
        cube_round = 0 #reset
        return appmain()
    # 1 Starting point: The user will first select 2 files.
    username = ''
    if 'username' in session:
        username = session['username']
    mymetalist = MetaList(app.config['S'])
    #print(mymetalist.get_as_string())
    if 'start' in request.args:
         #TBD: Should return login page if user is not admin.
        return render_template('rcube.html', username=username, entries=mymetalist.get())

    selfiles = request.args.getlist('fileselect')

    # 2: User has selected files, show their fields
    if 'twoselect' in request.args:
        if len(selfiles) == 2:
            #generate select boxes for joining files by fields
            shown_files = []
            for s in selfiles:
                meta = mymetalist.get_meta_by_name(s)
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
            for cubef in cubefiles:
                meta = mymetalist.get_meta_by_name(cubef)
                for fie in meta.getfieldnames():
                    cubemeta.addfield(fie, "")

            shown_files.append(cubemeta)

            for s in selfiles:
                meta = mymetalist.get_meta_by_name(s)
                shown_files.append(meta)
            return render_template('rcubefields.html', entries=shown_files)
        return render_template('rcube.html', error="Please select 1 file")
# 4 User has selected fields from one more
    if 'fieldsubmit' in request.args:
        file1 = ""
        file2 = ""
        field1 = ""
        field2 = ""
        mround = 1
        add_to_cube_file = ""
        add_to_cube_field = ""
        #check here if the fields are compatible: use file1, file1, field1, field2
        for ar in request.args:
            if ar != "fieldsubmit":
                if ar != "cube":
                    add_to_cube_file = ar
                    add_to_cube_field = request.args.get(ar).split(":")[0]
                if mround == 1:
                    file1 = ar
                    field1 = request.args[ar].split(":")[0]
                    mround = 2
                else:
                    file2 = ar
                    field2 = request.args[ar].split(":")[0]
        if cube_round > 0:
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
            if file1 == cube:
                #we need to get field1's real file to file1
                for fname in cubefiles:
                    meta = mymetalist.get_meta_by_name(fname)
                    for fie in meta.getfieldnames():
                        #print fname+" "+fie
                        if fie == field1:
                            #print "Found field "+field1+" in "+fname
                            file1 = fname
            else:
                #we need to get field2's real file to file2
                for fname in cubefiles:
                    meta = mymetalist.get_meta_by_name(fname)
                    for fie in meta.getfieldnames():
                        #print fname+" "+fie
                        if fie == field2:
                            #print "Found field "+field2+" in "+fname
                            file2 = fname
        fxpd = pd.read_csv(app.config['SL']+file1) #faster than csv.DictReader
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
        cubefiles.append(file1)
        cubefiles.append(file2)

        cubefields.append(field1)
        cubefields.append(field2)
        #make numpy/pandas cube
        if cube_round == 0:
            f1pd = pd.read_csv(app.config['SL']+file1)
            f2pd = pd.read_csv(app.config['SL']+file2)
            pdcube = pd.merge(f1pd, f2pd, left_on=field1, right_on=field2)
            cube_round = 1
            #print(pdcube)
        else:
            fpd = pd.read_csv(app.config['SL']+add_to_cube_file)
            pdcube = pd.merge(pdcube, fpd, left_on=in_cube_field, right_on=add_to_cube_field)

        return render_template('rcubecontinue.html', msg=msg, csize=pdcube.shape[0])

    # 4 there is some integration stuff already and we continue
    if 'more' in request.args:
        #put information about what's already there in msg
        msg = ""
        for i in range(0, len(cubefiles)-1):
            if i % 2 == 0:
                msg += cubefiles[i] + ":" + cubefields[i] + " &rarr; " + \
                cubefiles[i+1] + ":" + cubefields[i+1]+"<br/>"

        ok_files = mymetalist.get()
        return render_template('rcubemore.html', msg=msg, entries=ok_files)

    # 5 The user wants the cube
    if 'generatecube' in request.args:
        #write it into a file
        pdcube.to_csv(app.config['SL']+TMPCUBENAME, encoding='utf-8', index=False)
        cube_round = 0 #reset
        return render_template('rcubegen.html')

    #default if nothing matched
    return appmain()

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
