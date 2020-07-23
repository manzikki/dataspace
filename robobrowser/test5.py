#Test checking file exists functionality using robobrowser.
#pip install robobrowser
import werkzeug
import os
import sys
import time
werkzeug.cached_property = werkzeug.utils.cached_property
from robobrowser import RoboBrowser

#0: Do we already have the file there? Don't run.
if not os.path.exists("../static/countryname-iso3-continent.csv"):
    print("File countryname-iso3-continent.csv is not there, cannot test.")
    os.exit(1)

#rewrite the password file so that the robot can log in as admin
mypw = "5f4dcc3b5aa765d61d8327deb882cf99" #password
pwfile = open('../pw.md5','w')
pwfile.write(mypw)
pwfile.close()
time.sleep(1)

#1: Just check that the page appears.
browser = RoboBrowser(history=True, parser='html.parser')
browser.open("http://localhost:5000")
title = browser.find("title")
assert "Dataspace" in str(title)
print("page ok")
ok=1

#2: Log in
browser.open("http://localhost:5000/login")
forms = browser.get_forms()
for loginf in forms:
    if 'username' in loginf.keys():
        loginf['username'] = 'admin'
        loginf['password'] = 'password'
        browser.submit_form(loginf)
        time.sleep(2)

#login was ok?  there should be "admin" in span "user"
if "admin</span>" in str(browser.parsed):
    print("login ok")
    ok += 1
#3: Follow the link to "upload"
links = browser.get_links()
urls = [link.get("href") for link in links]

linkn = 0
for url in urls:
    if url == '/home/upload':
        print("link "+str(linkn)+" for upload ok")
        ok+=1
        break
    linkn += 1

#4: Post test contents
if linkn:
    browser.follow_link(links[linkn])
    forms = browser.get_forms()
    #print(str(forms))
    time.sleep(2)
    fnamef = ""
    for upform in forms:
        if 'CSVfiles' in upform.keys():
            upform['CSVfiles'].value = open("countryname-iso3-continent.csv",'rb')
            time.sleep(1)
            browser.submit_form(upform)
            #print(str(browser.parsed))
            if "Do you want to overwrite it" in str(browser.parsed):
                print("Overwrite check ok")
                ok+=1
            if os.path.exists("../upload/countryname-iso3-continent.csv"):
                os.remove("../upload/countryname-iso3-continent.csv")

#remove the pw file
os.remove('../pw.md5')
print(str(ok)+" of 4 ok")