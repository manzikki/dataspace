#Test cube construction using robobrowser.
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
    ok+=1

#3: Search
forms = browser.get_forms()
for searchf in forms:
    #print(str(searchf))
    if 'search' in searchf.keys():
        searchf['search'] = 'continent'
        browser.submit_form(searchf)
        time.sleep(2)
        if 'Showing meta data with description or fields containing "continent".' in str(browser.parsed()):
            print("search ok")
            ok+=1

#remove the pw file
os.remove('../pw.md5')
print(str(ok)+" of 3 ok")
