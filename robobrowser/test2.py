#Test new file functionality using robobrowser.
#pip install robobrowser
import werkzeug
import os
import sys
import time
werkzeug.cached_property = werkzeug.utils.cached_property
from robobrowser import RoboBrowser

#rewrite the password file so that the robot can log in as admin
mypw = "5f4dcc3b5aa765d61d8327deb882cf99" #password
pwfile = open('../pw.md5','w')
pwfile.write(mypw)
pwfile.close()
time.sleep(1)
ok = 0

#1: Just check that the page appears.

browser = RoboBrowser(history=True, parser='html.parser')
browser.open("http://localhost:5000")
title = browser.find("title")
assert "Dataspace" in str(title)
print("page ok")
ok = 1
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
    ok += 1

#3: Follow the link to "new"
links = browser.get_links()
urls = [link.get("href") for link in links]

linkn = -1
for url in urls:
    linkn += 1
    if url == '/home/new':
        print("link "+str(linkn)+" for new ok")
        ok += 1
        break

if not linkn:
    print("error: /home/new not found "+str(urls))
#4: Post test contents
if linkn:
    browser.follow_link(links[linkn])
    forms = browser.get_forms()
    time.sleep(2)
    if forms:
        newform = forms[0]
        #if not 'csvtext' in newform:
        #	sys.exit("Field csvtext missing. This can happen if the form submit is too fast. Please re-run")
        try:
            newform['csvtext'] = "id,name\r\n1,andy\r\n2,betty\r\n3,carol"
        except:
            sys.exit("Sorry, please run again.")
        time.sleep(1)
        browser.submit_form(newform)
        #print(str(browser.parsed))
        time.sleep(1)
        fnamef = str(browser.find("input", {"name": "file"}))
        #we found the field, thus we are at the meta data editor
        print("creating new file ok")
        ok += 1
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
            ok += 1
            os.remove("../static/"+fname+".jmeta")

#remove the pw file
os.remove('../pw.md5')
print(str(ok)+" of 5 ok")