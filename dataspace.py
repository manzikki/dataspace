"""
Simple dataspace management for CVS files. Marko Niinimaki niinimakim@webster.ac.th 2019
"""
import os
import csv
from flask import Flask, session, render_template, redirect, \
                  url_for, request, flash
from werkzeug.utils import secure_filename
import pandas as pd
from forms import LoginForm, UploadForm
from classes import MetaInfo, MetaList



app = Flask(__name__)
app.config['SECRET_KEY'] = '5791628bb0b13'
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'FpacNida986!'
TMPRDFNAME = "tmp.rdf"
REQROOT="home" #for WSGI: what is the base URL
MAX_LINES = 500 #max number of lines in view

@app.route("/")
@app.route("/home")

def appmain():
    """
    Main route, shows the main page.
    """
    mymetas = MetaList("static")
    username = ""
    if 'username' in session:
        username = session['username']
    return render_template('home.html', username=username, metas=mymetas.get())

@app.route("/login", methods=['GET', 'POST'])
@app.route("/home/login", methods=['GET', 'POST'])
def login():
    """
    Shows the login page.
    """
    form = LoginForm()
    if form.validate_on_submit():
        if form.username.data == ADMIN_USERNAME and form.password.data == ADMIN_PASSWORD:
            flash('You have been logged in!', 'success')
            session['username'] = ADMIN_USERNAME
            return redirect(url_for('appmain'))
        else:
            flash('Login Unsuccessful. Please check username and password', 'danger')
    return render_template('login.html', title='Login', form=form)

def check_file_ok(filename):
    """
    Check that the file is readable by csv reader, TBD.
    """
    return ""

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
        fil.save(os.path.join(
            'static', filename
        ))
        #if the file is ok, prepare the fields for the dialog
        if check_file_ok(filename) == "":
            row1 = []
            #read the first line of file to get field names
            with open("static/"+filename) as csv_file:
                reader = csv.reader(csv_file, delimiter=',', quotechar='"')
                row1 = next(reader)
            csv_file.close()
            if row1:
                fieldlist = []
                for riter in row1:
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
    with open('static/'+myfile) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',', quotechar='"')
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
    mymeta.read_from_file('static', myfile)
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
    mymeta = MetaInfo(file)
    mymeta.setdescr(descr)
    for fiter in mydict:
        #print(k+" "+mydict[k])
        if not (fiter.endswith("=scale") or fiter.endswith("=unit") or \
                                            fiter.endswith("=eventness")):
            if not (fiter == "file" or fiter == "descr"):
                mymeta.addfield(fiter, mydict[fiter])
    for fiter in mymeta.getfieldnames():
        if mydict.has_key(fiter+"=unit") and mydict[fiter+"=unit"]:
            unit = mydict[fiter+"=unit"]
            scale = mydict[fiter+"=scale"]
            eventness = mydict[fiter+"=eventness"]
            mymeta.addmeasure(fiter, unit, scale, eventness)
    mymeta.write_to_file('static', myfile)
    #call appmain if ok
    return redirect(url_for('appmain'))

#route for printing all filenames
@app.route('/printurls', methods=['GET', 'POST'])
@app.route('/home/printurls', methods=['GET', 'POST'])
def printurls():
    """
    Route for printing the names of all the files.
    """
    mymetas = MetaList("static")
    return render_template('urls.html', req=request.url_root, metas=mymetas.get())


# route for handling exportrdf (export the CSV values file as RDF)
@app.route('/exportrdf', methods=['GET', 'POST'])
@app.route('/home/exportrdf', methods=['GET', 'POST'])
def exportrdf():
    """
    Route for handling exportrdf (export the CSV values file as RDF)
    """
    #rdf headers to be written
    fheaders = """<?xml version='1.0'?>
<rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#' xmlns:a='http://www.example.org/'>
    """
    mydict = request.form
    myfile = mydict['file']
    #print(file)
    if myfile:
        #open the CVS file that the user wants
        cvsdf = pd.read_csv('static'+"/"+myfile)
        rdf = open("static/"+TMPRDFNAME, 'w')
        rdf.write(fheaders)
        for index, row in cvsdf.iterrows():
            rdf.write("<Description about=\"I"+str(index)+"\" ")
            for dfh in cvsdf:
                rdf.write(dfh+"=\""+str(row[dfh]).replace("\"", "")+"\" ")
            rdf.write("/>\n")
        #write the real contents as: <RDF:Seq about="FILENAME"> <RDF:li> .. </RDF:li>
        rdf.write("</rdf:RDF>")
        rdf.close()
        return render_template('rdfexport.html')
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
    mymetalist = MetaList('static')
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

        fxpd = pd.read_csv('static'+"/"+file1) #faster than csv.DictReader
        f1uniques = fxpd[field1].unique()
        fxpd = pd.read_csv('static'+"/"+file2)
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
            f1pd = pd.read_csv('static'+"/"+file1)
            f2pd = pd.read_csv('static'+"/"+file2)
            pdcube = pd.merge(f1pd, f2pd, left_on=field1, right_on=field2)
            cube_round = 1
            #print(pdcube)
        else:
            fpd = pd.read_csv('static'+"/"+add_to_cube_file)
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
        pdcube.to_csv('static'+"/"+TMPCUBENAME, encoding='utf-8', index=False)
        cube_round = 0 #reset
        return render_template('rcubegen.html')

    #default if nothing matched
    return appmain()

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
