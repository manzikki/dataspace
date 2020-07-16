#Test upload file functionality using robobrowser.
#pip install robobrowser
import werkzeug
import os
import sys
import time
werkzeug.cached_property = werkzeug.utils.cached_property
from robobrowser import RoboBrowser

#0: Do we already have the file there? Don't run.
if os.path.exists("../static/population.csv"):
    print("File already exists!")
    os.exit(1)

#1: Just check that the page appears.

browser = RoboBrowser(history=True, parser='html.parser')
browser.open("http://localhost:5000")
title = browser.find("title")
assert "Dataspace" in str(title)
print("page ok")

#rewrite the password file so that the robot can log in as admin
mypw = "5f4dcc3b5aa765d61d8327deb882cf99" #password
pwfile = open('../pw.md5','w')
pwfile.write(mypw)
pwfile.close()

#2: Log in
browser.open("http://localhost:5000/login")
forms = browser.get_forms()
#print(str(forms))
loginf = forms[0]
loginf['username'] = 'admin'
loginf['password'] = 'password'
browser.submit_form(loginf)
time.sleep(2)

#login was ok?  there should be "admin" in span "user"
if "admin</span>" in str(browser.parsed):
    print("login ok")

#3: Follow the link to "upload"
links = browser.get_links()
urls = [link.get("href") for link in links]

linkn = 0
for url in urls:
	if url == '/home/upload':
	    print("link "+str(linkn)+" for upload ok")
	    break
	linkn += 1

#4: Post test contents
if linkn:
    browser.follow_link(links[linkn])
    forms = browser.get_forms()
    #print(str(forms))
    time.sleep(2)
    fnamef = ""
    if forms:
        upform = forms[0]
        upform['CSVfiles'].value = open("population.csv",'r')
        time.sleep(1)
        browser.submit_form(upform)
        #print(str(browser.parsed))
        time.sleep(1)
        fnamef = str(browser.find("input", {"name": "file"}))
        #we found the field, thus we are at the meta data editor
    
    if fnamef:
        print("uploading file ok")

        #get the form
        metaforms = browser.get_forms()
        if metaforms:
            metaform = metaforms[0]
            #print(str(metaform))
            metaform['descr'] = "demo"
            browser.submit_form(metaform)
            time.sleep(1)
        
        #print(fnamef)
        fnameparts = fnamef.split('"')
        fname = fnameparts[5] 
        if os.path.exists("../static/"+fname):
            os.remove("../static/"+fname)
        if os.path.exists("../static/"+fname+".jmeta"):
            print("entering metadata for a file ok")
            os.remove("../static/"+fname+".jmeta")

#remove the pw file
os.remove('../pw.md5')
